from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ...core.database import get_db
from ...models.run import Run
from ...schemas.run import RunRead

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[RunRead])
async def leaderboard(
    sort_by: str = Query("composite_score", description="composite_score | score_adversarial | score_hallucination | ..."),
    corpus_version: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    valid_sort = {
        "composite_score", "score_adversarial", "score_tool_misuse",
        "score_hallucination", "score_recovery", "score_latency", "score_cost",
    }
    if sort_by not in valid_sort:
        sort_by = "composite_score"

    sort_col = getattr(Run, sort_by)
    q = select(Run).where(Run.status == "completed", sort_col.isnot(None))
    if corpus_version:
        q = q.where(Run.corpus_version == corpus_version)

    q = q.order_by(desc(sort_col)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return result.scalars().all()
