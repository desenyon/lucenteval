from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ...core.database import get_db
from ...core.auth import require_scope
from ...models.prompt import Prompt
from ...schemas.prompt import PromptRead, PromptContribute
import uuid

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptRead])
async def list_prompts(
    category: str | None = Query(None),
    subcategory: str | None = Query(None),
    severity: str | None = Query(None),
    version: str | None = Query(None, alias="version"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    auth=Depends(require_scope("prompt:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Prompt).where(Prompt.is_active == True, Prompt.in_quarantine == False)
    if category:
        q = q.where(Prompt.category == category)
    if subcategory:
        q = q.where(Prompt.subcategory == subcategory)
    if severity:
        q = q.where(Prompt.severity == severity)
    if version:
        q = q.where(Prompt.corpus_version == version)

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{prompt_id}", response_model=PromptRead)
async def get_prompt(
    prompt_id: uuid.UUID,
    auth=Depends(require_scope("prompt:read")),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/contribute", response_model=PromptRead, status_code=201)
async def contribute_prompt(
    body: PromptContribute,
    auth=Depends(require_scope("prompt:read")),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    prompt = Prompt(
        text=body.text,
        category=body.category,
        subcategory=body.subcategory,
        severity=body.severity,
        expected_behavior=body.expected_behavior,
        contributor_id=account.id,
        in_quarantine=True,
        is_active=False,
    )
    db.add(prompt)
    await db.flush()
    return prompt


@router.post("/{prompt_id}/upvote", response_model=PromptRead)
async def upvote_prompt(
    prompt_id: uuid.UUID,
    auth=Depends(require_scope("prompt:read")),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt.upvotes += 1
    return prompt
