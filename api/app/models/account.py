import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.security import utcnow


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="account", cascade="all, delete-orphan")
    runs: Mapped[list["Run"]] = relationship("Run", back_populates="account")
    webhooks: Mapped[list["Webhook"]] = relationship("Webhook", back_populates="account", cascade="all, delete-orphan")


if TYPE_CHECKING:
    from .api_key import ApiKey
    from .run import Run
    from .webhook import Webhook
