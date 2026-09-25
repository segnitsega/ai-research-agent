from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_agent.schemas.enums import MemoryKind


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    kind: MemoryKind
    content: str
    importance: float
    source_run_id: str | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class MemoryOp(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    op: Literal["add", "update", "delete", "noop"]
    target_id: str | None = None
    kind: MemoryKind | None = None
    content: str | None = None
    importance: float | None = None
    reason: str


class CuratorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ops: list[MemoryOp] = Field(max_length=10)
    run_summary: str = Field(max_length=600)
