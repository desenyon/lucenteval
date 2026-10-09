import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer, field_validator

from ..core.outbound import validate_headers, validate_url


class RunCreate(BaseModel):
    endpoint_url: str = Field(max_length=2048)
    headers: dict[str, str] = Field(default_factory=dict)
    _url = field_validator("endpoint_url")(validate_url)
    _headers = field_validator("headers")(validate_headers)
    system_prompt: str | None = Field(None, max_length=32000)
    corpus_version: str = Field("v1", min_length=1, max_length=32)


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
    failed_count: int
    manifest_sha256: str | None
    scorer_version: str
    rates_snapshot: dict
    weights_version: str
    weights_snapshot: dict
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RunSummary(BaseModel):
    endpoint_url: str
    failed_count: int
    id: uuid.UUID
    status: str
    composite_score: float | None
    prompt_count: int
    completed_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicRunRead(RunRead):
    """Public scores identify only the origin, never endpoint paths or URL secrets."""

    @field_serializer("endpoint_url")
    def public_origin(self, value: str):
        from urllib.parse import urlsplit

        try:
            parts = urlsplit(value)
            host = parts.hostname or "unknown"
            if ":" in host:
                host = f"[{host}]"
            return f"{parts.scheme}://{host}" + (f":{parts.port}" if parts.port else "")
        except ValueError:
            return "redacted"
