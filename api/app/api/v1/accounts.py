from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...models.account import Account
from ...schemas.account import AccountCreate, AccountRead

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Account).where(Account.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    account = Account(email=body.email, display_name=body.display_name)
    db.add(account)
    await db.flush()
    return account


@router.get("/me", response_model=AccountRead)
async def get_me(auth=Depends(lambda: None)):
    # Placeholder — real implementation uses get_current_account
    raise HTTPException(status_code=501, detail="Use authenticated endpoint")
