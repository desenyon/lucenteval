import json
import math
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import require_scope
from ...core.config import get_settings
from ...core.credentials import encrypt_secret
from ...core.database import get_db
from ...models.prompt import Prompt
from ...models.result import Result
from ...models.run import Run
from ...schemas.result import ResultRead, ResultTrace
from ...schemas.run import RunCreate, RunRead, RunSummary
from ...services.manifest import RATES_V1, digest, snapshot

router = APIRouter(prefix="/runs", tags=["runs"])
settings = get_settings()


@router.post("", response_model=RunRead, status_code=201)
async def create_run(
    body: RunCreate,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(None, max_length=128, min_length=1),
    auth=Depends(require_scope("run:create")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    request_hash = digest(body.model_dump())
    if idempotency_key:
        existing = (
            await db.execute(select(Run).where(Run.account_id == account.id, Run.idempotency_key == idempotency_key))
        ).scalar_one_or_none()
        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(409, "Idempotency key was already used for another request")
            return existing
    weights = {
        "adversarial": settings.WEIGHT_ADVERSARIAL,
        "tool_misuse": settings.WEIGHT_TOOL_MISUSE,
        "hallucination": settings.WEIGHT_HALLUCINATION,
        "recovery": settings.WEIGHT_RECOVERY,
        "latency": settings.WEIGHT_LATENCY,
        "cost": settings.WEIGHT_COST,
    }
    if any(not math.isfinite(w) or w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise HTTPException(503, "Invalid scoring weights configuration")
    prompts = (
        (
            await db.execute(
                select(Prompt)
                .where(
                    Prompt.corpus_version == body.corpus_version,
                    Prompt.is_active.is_(True),
                    Prompt.in_quarantine.is_(False),
                )
                .order_by(Prompt.id)
            )
        )
        .scalars()
        .all()
    )
    if not prompts:
        raise HTTPException(422, "Corpus has no active prompts")
    snapshots = [snapshot(prompt) for prompt in prompts]
    encrypted = None
    if body.headers:
        try:
            encrypted = encrypt_secret(json.dumps(body.headers))
        except ValueError:
            raise HTTPException(503, "Credential encryption is not configured") from None
    manifest_hash = digest({"prompts": snapshots, "weights": weights, "rates": RATES_V1, "scorer_version": "v2"})
    run = Run(
        account_id=account.id,
        endpoint_url=body.endpoint_url,
        headers={},
        headers_encrypted=encrypted,
        system_prompt=body.system_prompt,
        corpus_version=body.corpus_version,
        status="pending",
        prompt_count=len(prompts),
        weights_version="v1",
        weights_snapshot=weights,
        scorer_version="v2",
        rates_snapshot=RATES_V1,
        manifest_sha256=manifest_hash,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    db.add(run)
    try:
        await db.flush()
        for prompt, frozen in zip(prompts, snapshots, strict=True):
            db.add(Result(run_id=run.id, prompt_id=prompt.id, prompt_snapshot=frozen, status="pending"))
        # Commit the work ledger before publishing. Beat repairs a failed/lost publication.
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if not idempotency_key:
            raise
        existing = (
            await db.execute(select(Run).where(Run.account_id == account.id, Run.idempotency_key == idempotency_key))
        ).scalar_one()
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key was already used for another request") from None
        return existing
    from ...workers.tasks import dispatch_run

    background_tasks.add_task(dispatch_run, str(run.id))
    return run


@router.get("", response_model=list[RunSummary])
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth=Depends(require_scope("run:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    q = (
        select(Run)
        .where(Run.account_id == account.id)
        .order_by(Run.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunRead)
async def get_run(
    run_id: uuid.UUID,
    auth=Depends(require_scope("run:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    result = await db.execute(select(Run).where(Run.id == run_id, Run.account_id == account.id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/results", response_model=list[ResultRead])
async def list_results(
    run_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    auth=Depends(require_scope("run:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    run_result = await db.execute(select(Run).where(Run.id == run_id, Run.account_id == account.id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    q = (
        select(Result)
        .where(Result.run_id == run_id)
        .order_by(Result.prompt_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{run_id}/results/{prompt_id}", response_model=ResultTrace)
async def get_result_trace(
    run_id: uuid.UUID,
    prompt_id: uuid.UUID,
    auth=Depends(require_scope("run:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    run_result = await db.execute(select(Run).where(Run.id == run_id, Run.account_id == account.id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    result = await db.execute(select(Result).where(Result.run_id == run_id, Result.prompt_id == prompt_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    return row


@router.get("/{run_id}/export")
async def export_run(
    run_id: uuid.UUID,
    auth=Depends(require_scope("run:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    run_result = await db.execute(select(Run).where(Run.id == run_id, Run.account_id == account.id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    result = await db.execute(select(Result).where(Result.run_id == run_id).order_by(Result.prompt_id))
    rows = result.scalars().all()

    def ndjson_stream():
        for row in rows:
            line = ResultTrace.model_validate(row).model_dump_json()
            yield line + "\n"

    return StreamingResponse(
        ndjson_stream(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="run_{run_id}.ndjson"'},
    )
