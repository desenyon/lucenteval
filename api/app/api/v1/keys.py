from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ...core.database import get_db
from ...core.auth import get_current_account
from ...core.security import generate_api_key, utcnow
from ...models.api_key import ApiKey
from ...models.audit_log import AuditLog
from ...schemas.api_key import ApiKeyCreate, ApiKeyRead, ApiKeyCreateResponse
import uuid

router = APIRouter(prefix="/keys", tags=["keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreate,
    request: Request,
    auth=Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    raw_key, key_hash = generate_api_key()

    api_key = ApiKey(
        account_id=account.id,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        name=body.name,
        scopes=list(body.scopes),
        rate_limit_rpm=body.rate_limit_rpm,
    )
    db.add(api_key)

    log = AuditLog(
        account_id=account.id,
        action="key.create",
        resource_type="api_key",
        resource_id=str(api_key.id),
        actor_ip=request.client.host if request.client else None,
        metadata={"name": body.name, "scopes": list(body.scopes)},
    )
    db.add(log)
    await db.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        rate_limit_rpm=api_key.rate_limit_rpm,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.get("", response_model=list[ApiKeyRead])
async def list_keys(auth=Depends(get_current_account), db: AsyncSession = Depends(get_db)):
    account, _ = auth
    result = await db.execute(select(ApiKey).where(ApiKey.account_id == account.id, ApiKey.is_active == True))
    return result.scalars().all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: uuid.UUID,
    request: Request,
    auth=Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
):
    account, _ = auth
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.account_id == account.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Key not found")

    api_key.is_active = False
    api_key.revoked_at = utcnow()

    log = AuditLog(
        account_id=account.id,
        action="key.revoke",
        resource_type="api_key",
        resource_id=str(key_id),
        actor_ip=request.client.host if request.client else None,
        metadata={},
    )
    db.add(log)
