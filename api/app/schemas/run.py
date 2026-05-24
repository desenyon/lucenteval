import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class RunCreate(BaseModel):
    endpoint_url: str
    headers: dict[str, str] = {}
    system_prompt: str | None = None
    corpus_version: str = "v1"


class RunRead(BaseModel):
    id: uuid.UUID
    endpoint_url: str
    status: str
    corpus_version: str
    composite_score: float | None
    score_adversarial: float | None
    score_tool_misuse: float | None
    score_hallucination: float | None
    score_recovery: float | None
    score_latency: float | None
    score_cost: float | None
    latency_p50: float | None
    latency_p95: float | None
    latency_p99: float | None
    prompt_count: int
    completed_count: int
    weights_version: str
    weights_snapshot: dict
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunSummary(BaseModel):
    id: uuid.UUID
    status: str
    composite_score: float | None
    prompt_count: int
    completed_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
