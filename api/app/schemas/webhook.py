import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class WebhookCreate(BaseModel):
    url: str
    description: str | None = None


class WebhookRead(BaseModel):
    id: uuid.UUID
    url: str
    description: str | None
    is_active: bool
    failure_count: int
    last_delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookCreateResponse(WebhookRead):
    signing_secret: str
