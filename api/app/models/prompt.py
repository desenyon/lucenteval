import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from ..core.database import Base
from ..core.security import utcnow


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="v1")
    contributor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    in_quarantine: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_prompt_severity"),
        CheckConstraint(
            "category IN ('injection','jailbreak','role_confusion','goal_hijack','tool_abuse','factual_trap','multi_turn_trap')",
            name="ck_prompt_category",
        ),
    )
