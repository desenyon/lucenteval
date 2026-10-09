import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from ..core.security import utcnow


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True
    )
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    corpus_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

    headers_encrypted: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    scorer_version: Mapped[str] = mapped_column(String(32), default="v2", nullable=False)
    rates_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("account_id", "idempotency_key", name="uq_run_idempotency"),)

    # Composite score (0.0-1.0), set after all prompts scored
    composite_score: Mapped[float | None] = mapped_column(Float)

    # Per-dimension scores
    score_adversarial: Mapped[float | None] = mapped_column(Float)
    score_tool_misuse: Mapped[float | None] = mapped_column(Float)
    score_hallucination: Mapped[float | None] = mapped_column(Float)
    score_recovery: Mapped[float | None] = mapped_column(Float)
    score_latency: Mapped[float | None] = mapped_column(Float)
    score_cost: Mapped[float | None] = mapped_column(Float)

    # Latency percentiles (ms)
    latency_p50: Mapped[float | None] = mapped_column(Float)
    latency_p95: Mapped[float | None] = mapped_column(Float)
    latency_p99: Mapped[float | None] = mapped_column(Float)

    prompt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    weights_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    weights_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="runs")
    results: Mapped[list["Result"]] = relationship("Result", back_populates="run", cascade="all, delete-orphan")


if TYPE_CHECKING:
    from .account import Account
    from .result import Result
