"""Celery tasks for the agent runner and scoring pipeline."""
import asyncio
import json
import time
import uuid
import io
from datetime import datetime, timezone
from typing import Any

import boto3
import httpx
from celery import shared_task
from celery.utils.log import get_task_logger

from .celery_app import celery_app
from ..core.config import get_settings

logger = get_task_logger(__name__)
settings = get_settings()


def _get_db_sync():
    """Synchronous DB session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def dispatch_run(run_id: str):
    """Called from FastAPI background task — enqueues all runner jobs."""
    from ..models.run import Run
    from ..models.result import Result
    from ..models.prompt import Prompt

    db = _get_db_sync()
    try:
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        if not run:
            return

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        results = db.query(Result).filter(Result.run_id == run.id).all()
        for result in results:
            run_prompt.apply_async(
                args=[str(run.id), str(result.id)],
                queue="runner",
            )
    finally:
        db.close()


@celery_app.task(bind=True, queue="runner", max_retries=3, default_retry_delay=30)
def run_prompt(self, run_id: str, result_id: str):
    """Execute one prompt against the developer's agent endpoint."""
    from ..models.run import Run
    from ..models.result import Result
    from ..models.prompt import Prompt

    db = _get_db_sync()
    try:
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        result = db.query(Result).filter(Result.id == uuid.UUID(result_id)).first()
        if not run or not result:
            return

        prompt = db.query(Prompt).filter(Prompt.id == result.prompt_id).first()
        if not prompt:
            return

        result.status = "running"
        db.commit()

        # Build messages
        messages = []
        if run.system_prompt:
            messages.append({"role": "system", "content": run.system_prompt})
        messages.append({"role": "user", "content": prompt.text})

        # Call the developer's endpoint via LiteLLM-compatible interface
        start_ts = time.perf_counter()
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    run.endpoint_url,
                    headers={**run.headers, "Content-Type": "application/json"},
                    json={"messages": messages},
                )
                resp.raise_for_status()
                raw_payload = resp.json()
        except Exception as exc:
            result.status = "error"
            result.error = str(exc)
            db.commit()
            # Retry with backoff
            raise self.retry(exc=exc)

        latency_ms = int((time.perf_counter() - start_ts) * 1000)

        # Extract token counts from OpenAI-compatible response
        usage = raw_payload.get("usage", {})
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")

        # Compute cost from provider rate table
        cost_usd = _compute_cost(raw_payload.get("model", ""), input_tokens, output_tokens)

        # Store raw payload in S3
        s3_key = f"runs/{run_id}/results/{result_id}.json"
        try:
            s3 = _s3_client()
            s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key,
                Body=json.dumps(raw_payload).encode(),
                ContentType="application/json",
            )
        except Exception as e:
            logger.warning(f"S3 upload failed for {s3_key}: {e}")
            s3_key = None

        # Atomic write: all fields in one transaction
        result.s3_key = s3_key
        result.latency_ms = latency_ms
        result.input_tokens = input_tokens
        result.output_tokens = output_tokens
        result.cost_usd = cost_usd
        result.captured_at = datetime.now(timezone.utc)
        result.status = "captured"
        db.commit()

        # Enqueue scoring
        score_result.apply_async(
            args=[run_id, result_id, json.dumps(raw_payload)],
            queue="scorer",
        )

    finally:
        db.close()


@celery_app.task(bind=True, queue="scorer")
def score_result(self, run_id: str, result_id: str, raw_payload_json: str):
    """Run all 6 scorers on a captured result."""
    from ..models.run import Run
    from ..models.result import Result
    from ..models.prompt import Prompt

    db = _get_db_sync()
    try:
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        result = db.query(Result).filter(Result.id == uuid.UUID(result_id)).first()
        if not run or not result:
            return

        prompt = db.query(Prompt).filter(Prompt.id == result.prompt_id).first()
        raw_payload = json.loads(raw_payload_json)

        # Extract response text
        response_text = _extract_text(raw_payload)

        # Import scorers lazily
        from ...engine.app.scorers.adversarial import AdversarialScorer
        from ...engine.app.scorers.tool_misuse import ToolMisuseScorer
        from ...engine.app.scorers.hallucination import HallucinationScorer
        from ...engine.app.scorers.latency import LatencyScorer
        from ...engine.app.scorers.cost import CostScorer
        from ...engine.app.scorers.composite import CompositeScorer

        adv = AdversarialScorer().score(prompt.text, response_text, prompt.expected_behavior)
        tool = ToolMisuseScorer().score(raw_payload)
        hall = HallucinationScorer().score(response_text)
        lat = LatencyScorer().score(result.latency_ms, run_id, db)
        cost_score = CostScorer().score(result.cost_usd, run_id, db)

        weights = run.weights_snapshot
        composite = CompositeScorer(weights).score({
            "adversarial": adv["score"],
            "tool_misuse": tool["score"],
            "hallucination": hall["score"],
            "recovery": None,  # recovery is separate multi-turn harness
            "latency": lat["score"],
            "cost": cost_score["score"],
        })

        result.score_adversarial = adv["score"]
        result.score_tool_misuse = tool["score"]
        result.score_hallucination = hall["score"]
        result.score_latency = lat["score"]
        result.score_cost = cost_score["score"]
        result.composite_score = composite["score"]
        result.rationale_adversarial = adv
        result.rationale_tool_misuse = tool
        result.rationale_hallucination = hall
        result.rationale_recovery = None
        result.tool_call_graph = tool.get("call_graph")
        result.scored_at = datetime.now(timezone.utc)
        result.status = "scored"
        db.commit()

        # Check if all results for this run are scored → finalize run
        _maybe_finalize_run(run_id, db)

    finally:
        db.close()


def _maybe_finalize_run(run_id: str, db):
    from ..models.run import Run
    from ..models.result import Result
    import numpy as np

    run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
    results = db.query(Result).filter(Result.run_id == run.id).all()

    scored = [r for r in results if r.status == "scored"]
    if len(scored) < len(results):
        return  # not done yet

    latencies = [r.latency_ms for r in scored if r.latency_ms]
    latencies.sort()

    def percentile(arr, p):
        if not arr:
            return None
        idx = int(len(arr) * p / 100)
        return arr[min(idx, len(arr) - 1)]

    run.latency_p50 = percentile(latencies, 50)
    run.latency_p95 = percentile(latencies, 95)
    run.latency_p99 = percentile(latencies, 99)

    # Aggregate per-dimension scores
    def avg(vals):
        v = [x for x in vals if x is not None]
        return sum(v) / len(v) if v else None

    run.score_adversarial = avg([r.score_adversarial for r in scored])
    run.score_tool_misuse = avg([r.score_tool_misuse for r in scored])
    run.score_hallucination = avg([r.score_hallucination for r in scored])
    run.score_recovery = avg([r.score_recovery for r in scored])
    run.score_latency = avg([r.score_latency for r in scored])
    run.score_cost = avg([r.score_cost for r in scored])
    run.completed_count = len(scored)

    weights = run.weights_snapshot
    dim_scores = {
        "adversarial": run.score_adversarial,
        "tool_misuse": run.score_tool_misuse,
        "hallucination": run.score_hallucination,
        "recovery": run.score_recovery,
        "latency": run.score_latency,
        "cost": run.score_cost,
    }
    total_w = sum(weights[k] for k, v in dim_scores.items() if v is not None)
    composite = sum(weights[k] * v for k, v in dim_scores.items() if v is not None)
    run.composite_score = composite / total_w if total_w > 0 else None
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    # Deliver webhooks
    from ..models.webhook import Webhook
    webhooks = db.query(Webhook).filter(
        Webhook.account_id == run.account_id,
        Webhook.is_active == True,
    ).all()
    for webhook in webhooks:
        deliver_webhook.apply_async(args=[str(webhook.id), run_id], queue="webhook")


@celery_app.task(bind=True, queue="webhook", max_retries=5)
def deliver_webhook(self, webhook_id: str, run_id: str):
    """Deliver run completion event to a registered webhook URL."""
    from ..models.webhook import Webhook
    from ..models.run import Run
    import hashlib

    db = _get_db_sync()
    try:
        webhook = db.query(Webhook).filter(Webhook.id == uuid.UUID(webhook_id)).first()
        run = db.query(Run).filter(Run.id == uuid.UUID(run_id)).first()
        if not webhook or not run:
            return

        payload = {
            "run_id": str(run.id),
            "status": run.status,
            "composite_score": run.composite_score,
            "scores_by_dimension": {
                "adversarial": run.score_adversarial,
                "tool_misuse": run.score_tool_misuse,
                "hallucination": run.score_hallucination,
                "recovery": run.score_recovery,
                "latency": run.score_latency,
                "cost": run.score_cost,
            },
            "run_url": f"https://lucenteval.dev/runs/{run.id}",
        }
        payload_bytes = json.dumps(payload).encode()

        import hmac as _hmac
        secret = hashlib.sha256(webhook.secret_hash.encode()).hexdigest()  # we stored hash; re-derive for signing
        sig = "sha256=" + _hmac.new(webhook.secret_hash.encode(), payload_bytes, hashlib.sha256).hexdigest()

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    webhook.url,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-LucentEval-Signature": sig,
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            webhook.failure_count += 1
            db.commit()
            # Exponential backoff: 30s, 60s, 120s, 240s, 480s
            countdown = 30 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

        webhook.failure_count = 0
        webhook.last_delivered_at = datetime.now(timezone.utc)
        db.commit()

    finally:
        db.close()


def _extract_text(raw_payload: dict) -> str:
    try:
        choices = raw_payload.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        # Anthropic format
        content = raw_payload.get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", "")
        return str(raw_payload)
    except Exception:
        return str(raw_payload)


def _compute_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    """Compute cost in USD using a versioned rate table."""
    if not input_tokens and not output_tokens:
        return None

    RATES = {
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "gpt-4-turbo": (10.00 / 1_000_000, 30.00 / 1_000_000),
        "claude-opus-4": (15.00 / 1_000_000, 75.00 / 1_000_000),
        "claude-sonnet-4": (3.00 / 1_000_000, 15.00 / 1_000_000),
        "claude-haiku-4": (0.80 / 1_000_000, 4.00 / 1_000_000),
        "default": (1.00 / 1_000_000, 3.00 / 1_000_000),
    }

    rates = RATES.get(model, RATES["default"])
    in_cost = (input_tokens or 0) * rates[0]
    out_cost = (output_tokens or 0) * rates[1]
    return round(in_cost + out_cost, 8)
