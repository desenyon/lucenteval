from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_current_account
from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import generate_api_key
from ...models.account import Account
from ...models.api_key import ApiKey
from ...schemas.account import AccountCreate, AccountCreateResponse, AccountRead

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Account).where(Account.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    account = Account(email=body.email, display_name=body.display_name)
    raw_key, key_hash = generate_api_key()
    db.add(account)
    try:
        await db.flush()
        db.add(
            ApiKey(
                account_id=account.id,
                key_hash=key_hash,
                key_prefix=raw_key[:12],
                name="Initial key",
                rate_limit_rpm=get_settings().DEFAULT_RATE_LIMIT_RPM,
                scopes=["run:create", "run:read", "prompt:read"],
            )
        )
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Email already registered") from None
    return {**AccountRead.model_validate(account).model_dump(), "raw_key": raw_key}


@router.get("/me", response_model=AccountRead)
async def get_me(auth=Depends(get_current_account)):
    return auth[0]
