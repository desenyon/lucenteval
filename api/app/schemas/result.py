import uuid
from datetime import datetime
from pydantic import BaseModel


class ResultRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    prompt_id: uuid.UUID
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    score_adversarial: float | None
    score_tool_misuse: float | None
    score_hallucination: float | None
    score_recovery: float | None
    score_latency: float | None
    score_cost: float | None
    composite_score: float | None
    status: str
    captured_at: datetime | None
    scored_at: datetime | None

    model_config = {"from_attributes": True}


class ResultTrace(ResultRead):
    rationale_adversarial: dict | None
    rationale_tool_misuse: dict | None
    rationale_hallucination: dict | None
    rationale_recovery: dict | None
    tool_call_graph: dict | None
    recovery_turns: list | None
    error: str | None
