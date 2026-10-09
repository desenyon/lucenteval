import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class AccountCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None


class AccountRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountCreateResponse(AccountRead):
    raw_key: str
