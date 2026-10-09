import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PromptCategory = Literal[
    "injection", "jailbreak", "role_confusion", "goal_hijack", "tool_abuse", "factual_trap", "multi_turn_trap"
]
PromptSeverity = Literal["low", "medium", "high", "critical"]


class PromptRead(BaseModel):
    id: uuid.UUID
    text: str
    category: str
    subcategory: str | None
    severity: str
    expected_behavior: str
    corpus_version: str
    upvotes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptFilter(BaseModel):
    category: PromptCategory | None = None
    subcategory: str | None = None
    severity: PromptSeverity | None = None
    version: str | None = None
    page: int = 1
    page_size: int = 50


class PromptContribute(BaseModel):
    text: str
    category: PromptCategory
    subcategory: str | None = None
    severity: PromptSeverity
    expected_behavior: str
