import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from ..core.database import Base
from ..core.security import utcnow


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    corpus_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)

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
