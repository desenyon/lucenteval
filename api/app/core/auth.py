import time

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.redis import get_redis
from ..models.account import Account
from ..models.api_key import ApiKey

security = HTTPBearer(auto_error=False)


async def get_current_account(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[Account, ApiKey]:
    if credentials is None:
        raise HTTPException(401, "Bearer API key required")
    raw_key = credentials.credentials
    redis = get_redis()

    # Look up and validate the key before applying the fixed-window limiter.
    # Look up key hash
    import hashlib

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if not api_key.is_active or api_key.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key revoked")

    # Fixed minute-window rate limiting
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

    account_result = await db.execute(select(Account).where(Account.id == api_key.account_id))
    account = account_result.scalar_one_or_none()

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
