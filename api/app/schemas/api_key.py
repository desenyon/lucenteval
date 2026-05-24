import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel

KeyScope = Literal["run:create", "run:read", "prompt:read"]


class ApiKeyCreate(BaseModel):
    name: str | None = None
    scopes: list[KeyScope] = ["run:create", "run:read", "prompt:read"]
    rate_limit_rpm: int = 60


class ApiKeyRead(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str | None
    scopes: list[str]
    is_active: bool
    rate_limit_rpm: int
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyRead):
    raw_key: str
