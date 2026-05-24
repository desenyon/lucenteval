from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.api_key import ApiKey
from ..models.account import Account
from ..core.database import get_db
from ..core.security import verify_api_key
from ..core.redis import get_redis
import time

security = HTTPBearer()


async def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[Account, ApiKey]:
    raw_key = credentials.credentials
    redis = get_redis()

    # Enforce rate limiting first (token bucket in Redis)
    # Look up key hash
    import hashlib
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if not api_key.is_active or api_key.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key revoked")

    # Token bucket rate limiting
    bucket_key = f"ratelimit:{api_key.id}"
    rpm = api_key.rate_limit_rpm
    now = int(time.time())
    window = now // 60

    pipe = redis.pipeline()
    pipe.incr(f"{bucket_key}:{window}")
    pipe.expire(f"{bucket_key}:{window}", 120)
    results = await pipe.execute()
    count = results[0]

    if count > rpm:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rpm} requests/minute",
            headers={"Retry-After": "60"},
        )

    # Update last_used_at
    from ..core.security import utcnow
    api_key.last_used_at = utcnow()

    result = await db.execute(select(Account).where(Account.id == api_key.account_id))
    account = result.scalar_one_or_none()

    if not account or not account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    return account, api_key


def require_scope(scope: str):
    async def checker(auth: tuple[Account, ApiKey] = Depends(get_current_account)):
        account, api_key = auth
        if scope not in api_key.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing scope: {scope}")
        return account, api_key
    return checker
