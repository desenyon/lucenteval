import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from ..core.database import Base
from ..core.security import utcnow


class Result(Base):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=False, index=True)

    # Raw response (full payload stored in S3; this is metadata)
    s3_key: Mapped[str | None] = mapped_column(String(512))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)

    # Scores per dimension
    score_adversarial: Mapped[float | None] = mapped_column(Float)
    score_tool_misuse: Mapped[float | None] = mapped_column(Float)
    score_hallucination: Mapped[float | None] = mapped_column(Float)
    score_recovery: Mapped[float | None] = mapped_column(Float)
    score_latency: Mapped[float | None] = mapped_column(Float)
    score_cost: Mapped[float | None] = mapped_column(Float)
    composite_score: Mapped[float | None] = mapped_column(Float)

    # Scorer rationale / evidence (JSON blobs)
    rationale_adversarial: Mapped[dict | None] = mapped_column(JSON)
    rationale_tool_misuse: Mapped[dict | None] = mapped_column(JSON)
    rationale_hallucination: Mapped[dict | None] = mapped_column(JSON)
    rationale_recovery: Mapped[dict | None] = mapped_column(JSON)

    # Tool call graph (for tool misuse scorer)
    tool_call_graph: Mapped[dict | None] = mapped_column(JSON)

    # Recovery conversation (multi-turn)
    recovery_turns: Mapped[list | None] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text)

    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    run: Mapped["Run"] = relationship("Run", back_populates="results")
    prompt: Mapped["Prompt"] = relationship("Prompt")
