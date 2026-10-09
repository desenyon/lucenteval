"""Database-backed work ledger; Celery messages contain only identifiers.

Claims are bounded leases and writes are fenced by a unique token. Reconciliation
repairs lost broker publications and worker crashes. External effects are at least
once: agents/receivers can deduplicate using the stable Idempotency-Key header.
"""

import json
import math
import time
import uuid
from datetime import timedelta
from functools import lru_cache

from celery.utils.log import get_task_logger
from engine.app.scorers.adversarial import AdversarialScorer
from engine.app.scorers.composite import CompositeScorer
from engine.app.scorers.cost import CostScorer
from engine.app.scorers.hallucination import HallucinationScorer
from engine.app.scorers.latency import LatencyScorer
from engine.app.scorers.recovery import RecoveryScorer
from engine.app.scorers.tool_misuse import ToolMisuseScorer
from sqlalchemy import and_, create_engine, or_, select, update
from sqlalchemy.orm import sessionmaker

from ..core.config import get_settings
from ..core.credentials import decrypt_secret
from ..core.outbound import agent_response, extract_text, post_json
from ..core.security import sign_webhook_payload, utcnow
from ..models import Delivery, Result, Run, Webhook
from ..services.manifest import compute_cost
from .celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()
DIMENSIONS = ("adversarial", "tool_misuse", "hallucination", "recovery", "latency", "cost")
TERMINAL_RUNS = ("completed", "failed")


@lru_cache
def _session_factory():
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _get_db_sync():
    return _session_factory()()


def _publish(task, *args):
    try:
        task.apply_async(args=list(args))
    except Exception as exc:
        logger.warning("Publish deferred to reconciler: %s", type(exc).__name__)


def _due(model):
    return or_(model.next_attempt_at.is_(None), model.next_attempt_at <= utcnow())


def dispatch_run(run_id: str):
    """Best-effort immediate dispatch, safe to repeat after the submission commits."""
    with _get_db_sync() as db:
        run = db.get(Run, uuid.UUID(run_id))
        if not run or run.status in TERMINAL_RUNS:
            return
        rows = db.scalars(select(Result).where(Result.run_id == run.id, _due(Result))).all()
        for row in rows:
            if row.status == "pending" or (row.status == "running" and _expired(row.lease_expires_at)):
                _publish(run_prompt, run_id, str(row.id))
            elif row.status == "captured" or (row.status == "scoring" and _expired(row.lease_expires_at)):
                _publish(score_result, run_id, str(row.id))
        _maybe_finalize_run(run_id, db)


def _expired(value):
    # SQLite drops timezone info; production PostgreSQL preserves it.
    return value is None or value.replace(tzinfo=utcnow().tzinfo) <= utcnow()


@celery_app.task(queue="runner")
def reconcile_work():
    """Run every 30s with one Beat scheduler; repeated scans are harmless."""
    with _get_db_sync() as db:
        # Scan all active IDs so long-lived runs do not starve newer submissions.
        ids = db.scalars(select(Run.id).where(Run.status.not_in(TERMINAL_RUNS))).all()
        for run_id in ids:
            dispatch_run(str(run_id))
        deliveries = db.scalars(
            select(Delivery).where(Delivery.status.in_(["pending", "sending"]), _due(Delivery))
        ).all()
        for delivery in deliveries:
            if delivery.status == "pending" or _expired(delivery.lease_expires_at):
                _publish(deliver_webhook, str(delivery.id))


def _claim(db, run_id: str, result_id: str, scoring: bool = False):
    ready, working = ("captured", "scoring") if scoring else ("pending", "running")
    token = str(uuid.uuid4())
    count = Result.score_attempt_count if scoring else Result.attempt_count
    stmt = (
        update(Result)
        .where(
            Result.id == uuid.UUID(result_id),
            Result.run_id == uuid.UUID(run_id),
            _due(Result),
            or_(
                Result.status == ready,
                and_(
                    Result.status == working,
                    or_(Result.lease_expires_at.is_(None), Result.lease_expires_at <= utcnow()),
                ),
            ),
            Result.run_id.in_(select(Run.id).where(Run.status.not_in(TERMINAL_RUNS))),
        )
        .values(
            status=working,
            claim_token=token,
            lease_expires_at=utcnow() + timedelta(seconds=settings.WORK_LEASE_SECONDS),
            **{count.key: count + 1},
        )
        .execution_options(synchronize_session=False)
    )
    if db.execute(stmt).rowcount != 1:
        db.rollback()
        return None
    db.execute(
        update(Run)
        .where(Run.id == uuid.UUID(run_id), Run.status == "pending")
        .values(status="running", started_at=utcnow())
    )
    db.commit()
    db.expire_all()
    result = db.get(Result, uuid.UUID(result_id))
    if getattr(result, count.key) > settings.MAX_WORK_ATTEMPTS:
        _store(db, result.id, token, {"status": "error", "error": "attempts_exhausted"})
        _maybe_finalize_run(run_id, db)
        return None
    return result, token


def _store(db, result_id, token, values) -> bool:
    changed = db.execute(
        update(Result)
        .where(
            Result.id == result_id,
            Result.claim_token == token,
            Result.lease_expires_at > utcnow(),
            Result.status.in_(["running", "scoring"]),
        )
        .values(**values, claim_token=None, lease_expires_at=None)
        .execution_options(synchronize_session=False)
    ).rowcount
    db.commit()
    return changed == 1


def _work_failed(db, result, token, exc, scoring=False):
    attempts = result.score_attempt_count if scoring else result.attempt_count
    terminal = attempts >= settings.MAX_WORK_ATTEMPTS
    status = "error" if terminal else ("captured" if scoring else "pending")
    _store(
        db,
        result.id,
        token,
        {
            "status": status,
            # Exception messages may contain credentials or response bodies. Keep a safe code only.
            "error": ("scoring_" if scoring else "agent_") + type(exc).__name__,
            "next_attempt_at": utcnow() + timedelta(seconds=settings.RETRY_DELAY_SECONDS * 2 ** (attempts - 1)),
        },
    )
    _maybe_finalize_run(str(result.run_id), db)


def _usage(payload):
    usage = payload.get("usage", {})
    return (
        usage.get("prompt_tokens", usage.get("input_tokens")),
        usage.get("completion_tokens", usage.get("output_tokens")),
    )


@celery_app.task(queue="runner")
def run_prompt(run_id: str, result_id: str):
    with _get_db_sync() as db:
        claimed = _claim(db, run_id, result_id)
        if not claimed:
            return
        result, token = claimed
        run = db.get(Run, result.run_id)
        try:
            frozen = result.prompt_snapshot
            if not frozen:
                raise ValueError("Missing frozen prompt")
            headers = json.loads(decrypt_secret(run.headers_encrypted)) if run.headers_encrypted else {}
            messages = []
            if run.system_prompt:
                messages.append({"role": "system", "content": run.system_prompt})
            messages.append({"role": "user", "content": frozen["text"]})
            start = time.perf_counter()
            payload = agent_response(run.endpoint_url, headers, messages, f"{result_id}:initial")
            input_tokens, output_tokens = _usage(payload)
            cost = compute_cost(payload.get("model", ""), input_tokens, output_tokens, run.rates_snapshot)
            turns = []
            if scenario := frozen.get("recovery"):
                # Synthetic context is a user turn, not a forged tool message without a call ID.
                messages += [
                    {"role": "assistant", "content": extract_text(payload)},
                    {"role": "user", "content": scenario["injection"]},
                ]
                recovered = agent_response(run.endpoint_url, headers, messages, f"{result_id}:recovery")
                turns.append(
                    {
                        **scenario,
                        "response_text": extract_text(recovered),
                        "raw_payload": recovered,
                        "messages": messages,
                    }
                )
                in2, out2 = _usage(recovered)
                cost2 = compute_cost(recovered.get("model", ""), in2, out2, run.rates_snapshot)
                input_tokens = input_tokens + in2 if input_tokens is not None and in2 is not None else None
                output_tokens = output_tokens + out2 if output_tokens is not None and out2 is not None else None
                cost = round(cost + cost2, 8) if cost is not None and cost2 is not None else None
            values = {
                "raw_payload": payload,
                "recovery_turns": turns,
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost,
                "captured_at": utcnow(),
                "status": "captured",
                "error": None,
                "next_attempt_at": None,
            }
            stored = _store(db, result.id, token, values)
        except Exception as exc:
            db.rollback()
            _work_failed(db, result, token, exc)
            return
        if stored:
            _publish(score_result, run_id, result_id)
            if settings.ARCHIVE_RESPONSES:
                _archive(result_id, run_id, payload, turns)


def _archive(result_id, run_id, payload, turns):
    import boto3
    from botocore.config import Config

    try:
        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 0}),
        )
        key = f"runs/{run_id}/results/{result_id}.json"
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=json.dumps({"response": payload, "recovery_turns": turns}).encode(),
            ContentType="application/json",
        )
        with _get_db_sync() as db:
            db.execute(update(Result).where(Result.id == uuid.UUID(result_id)).values(s3_key=key))
            db.commit()
    except Exception as exc:
        logger.warning("Optional archive failed: %s", type(exc).__name__)


@celery_app.task(queue="scorer")
def score_result(run_id: str, result_id: str):
    with _get_db_sync() as db:
        claimed = _claim(db, run_id, result_id, scoring=True)
        if not claimed:
            return
        result, token = claimed
        run = db.get(Run, result.run_id)
        try:
            frozen, payload = result.prompt_snapshot, result.raw_payload
            response_text = extract_text(payload)
            scores = {
                "adversarial": AdversarialScorer().score(frozen["text"], response_text, frozen["expected_behavior"]),
                "tool_misuse": ToolMisuseScorer().score(payload),
                "hallucination": HallucinationScorer().score(response_text),
                "recovery": RecoveryScorer().score(result.recovery_turns or []),
                "latency": LatencyScorer().score(result.latency_ms, run_id, db),
                "cost": CostScorer().score(result.cost_usd, run_id, db),
            }
            values = {f"score_{name}": value["score"] for name, value in scores.items()}
            values.update(
                {
                    f"rationale_{name}": scores[name]
                    for name in ("adversarial", "tool_misuse", "hallucination", "recovery")
                }
            )
            values.update(
                {
                    "composite_score": CompositeScorer(run.weights_snapshot).score(
                        {name: value["score"] for name, value in scores.items()}
                    )["score"],
                    "tool_call_graph": scores["tool_misuse"].get("call_graph"),
                    "scored_at": utcnow(),
                    "status": "scored",
                    "error": None,
                    "next_attempt_at": None,
                }
            )
            _store(db, result.id, token, values)
        except Exception as exc:
            db.rollback()
            _work_failed(db, result, token, exc, scoring=True)
            return
        _maybe_finalize_run(run_id, db)


def _maybe_finalize_run(run_id: str, db):
    # Take a write lock before reading aggregates. This also serializes the offline
    # SQLite harness, where SELECT FOR UPDATE alone is ignored.
    locked = db.execute(
        update(Run).where(Run.id == uuid.UUID(run_id), Run.status.not_in(TERMINAL_RUNS))
        .values(status=Run.status).execution_options(synchronize_session=False)
    ).rowcount
    if not locked:
        db.rollback()
        return
    # Serialize aggregate updates and outbox creation across concurrent final results.
    run = db.scalar(
        select(Run).where(Run.id == uuid.UUID(run_id)).with_for_update().execution_options(populate_existing=True)
    )
    if not run or run.status in TERMINAL_RUNS:
        db.rollback()
        return
    results = db.scalars(select(Result).where(Result.run_id == run.id).execution_options(populate_existing=True)).all()
    scored = [r for r in results if r.status == "scored"]
    errors = [r for r in results if r.status == "error"]
    run.completed_count, run.failed_count = len(scored), len(errors)
    if len(scored) + len(errors) != run.prompt_count or len(results) != run.prompt_count:
        db.commit()
        return
    for name in DIMENSIONS:
        values = [getattr(r, f"score_{name}") for r in scored if getattr(r, f"score_{name}") is not None]
        setattr(run, f"score_{name}", sum(values) / len(values) if values else None)
    latencies = sorted(r.latency_ms for r in scored if r.latency_ms is not None)
    for p in (50, 95, 99):
        setattr(run, f"latency_p{p}", latencies[max(0, math.ceil(len(latencies) * p / 100) - 1)] if latencies else None)
    # Failed runs expose partial dimensions for diagnosis but never rank as successful.
    run.status = "failed" if errors or not results else "completed"
    run.composite_score = (
        None
        if run.status == "failed"
        else CompositeScorer(run.weights_snapshot).score({name: getattr(run, f"score_{name}") for name in DIMENSIONS})[
            "score"
        ]
    )
    run.completed_at = utcnow()
    run.headers = {}
    run.headers_encrypted = None
    payload = {
        "run_id": str(run.id),
        "status": run.status,
        "composite_score": run.composite_score,
        "scores_by_dimension": {name: getattr(run, f"score_{name}") for name in DIMENSIONS},
        "completed_count": run.completed_count,
        "failed_count": run.failed_count,
        "run_url": f"{settings.PLATFORM_URL.rstrip('/')}/dashboard/runs/{run.id}",
    }
    for hook in db.scalars(select(Webhook).where(Webhook.account_id == run.account_id, Webhook.is_active.is_(True))):
        db.add(Delivery(run_id=run.id, webhook_id=hook.id, payload=payload))
    db.commit()


@celery_app.task(queue="webhook")
def deliver_webhook(delivery_id: str):
    with _get_db_sync() as db:
        token = str(uuid.uuid4())
        changed = db.execute(
            update(Delivery)
            .where(
                Delivery.id == uuid.UUID(delivery_id),
                _due(Delivery),
                or_(
                    Delivery.status == "pending",
                    and_(Delivery.status == "sending", Delivery.lease_expires_at <= utcnow()),
                ),
            )
            .values(
                status="sending",
                claim_token=token,
                attempts=Delivery.attempts + 1,
                lease_expires_at=utcnow() + timedelta(seconds=settings.WORK_LEASE_SECONDS),
            )
        ).rowcount
        db.commit()
        if changed != 1:
            return
        delivery = db.get(Delivery, uuid.UUID(delivery_id))
        hook = db.get(Webhook, delivery.webhook_id)
        status = "delivered"
        try:
            if not hook or not hook.is_active or not hook.secret_encrypted:
                status = "cancelled"
            elif delivery.attempts > settings.WEBHOOK_MAX_RETRIES + 1:
                status = "failed"
            else:
                body = json.dumps({**delivery.payload, "event_id": delivery_id}, sort_keys=True).encode()
                post_json(
                    hook.url,
                    body=body,
                    timeout=30,
                    headers={
                        "X-LucentEval-Signature": sign_webhook_payload(body, decrypt_secret(hook.secret_encrypted)),
                        "X-LucentEval-Event-ID": delivery_id,
                        "Idempotency-Key": delivery_id,
                    },
                )
        except Exception:
            status = "failed" if delivery.attempts >= settings.WEBHOOK_MAX_RETRIES + 1 else "pending"
        changed = db.execute(
            update(Delivery)
            .where(
                Delivery.id == delivery.id,
                Delivery.claim_token == token,
                Delivery.lease_expires_at > utcnow(),
            )
            .execution_options(synchronize_session=False)
            .values(
                status=status,
                claim_token=None,
                lease_expires_at=None,
                next_attempt_at=utcnow() + timedelta(seconds=30 * 2 ** (delivery.attempts - 1)),
            )
        ).rowcount
        if changed and hook:
            if status == "delivered":
                hook.failure_count = 0
                hook.last_delivered_at = utcnow()
            elif status in ("pending", "failed"):
                hook.failure_count += 1
        db.commit()
