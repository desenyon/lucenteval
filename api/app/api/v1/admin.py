"""Admin endpoints: seed corpus, approve quarantined prompts."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.prompt import Prompt


async def require_admin(x_admin_token: str | None = Header(None)):
    import hmac

    from ...core.config import get_settings

    expected = get_settings().ADMIN_TOKEN
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(403, "Operator token required")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/seed-corpus")
async def seed_corpus_endpoint(db: AsyncSession = Depends(get_db)):
    from ...services.seed_corpus import ALL_PROMPTS, CORPUS_VERSION

    existing = await db.execute(select(Prompt).where(Prompt.corpus_version == CORPUS_VERSION).limit(1))
    if existing.scalar_one_or_none():
        return {"message": "Corpus already seeded", "count": 0}

    inserted = 0
    for raw in ALL_PROMPTS:
        p = Prompt(
            id=uuid.uuid4(),
            text=raw["text"],
            category=raw["category"],
            subcategory=raw.get("subcategory"),
            severity=raw["severity"],
            expected_behavior=raw["expected_behavior"],
            corpus_version=CORPUS_VERSION,
            is_active=True,
            in_quarantine=False,
        )
        db.add(p)
        inserted += 1

    await db.flush()
    return {"message": "Corpus seeded", "count": inserted}


@router.post("/prompts/{prompt_id}/approve")
async def approve_prompt(prompt_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException

    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    prompt.in_quarantine = False
    prompt.is_active = True
    await db.flush()
    return {"message": "Prompt approved", "id": str(prompt_id)}
