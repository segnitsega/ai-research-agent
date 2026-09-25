from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_agent.schemas.agents import Report, ResearchPlan
from research_agent.schemas.budget import Budget
from research_agent.schemas.enums import Depth, Phase, RunStatus
from research_agent.schemas.run_state import RunUsage

T = TypeVar("T")


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    question: str
    depth: Depth
    status: RunStatus
    phase: Phase | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cost_usd: float
    accepted_findings: int
    sources_used: int


class RunDetail(RunSummary):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: ResearchPlan | None
    report: Report | None
    usage: RunUsage
    budget: Budget
    error: str | None
    use_memory: bool


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[T]
    next_cursor: str | None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None
    flagged_finding_ids: list[str] = Field(default_factory=list)


class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str
    content: str = Field(max_length=300)
    importance: float = Field(default=0.5, ge=0, le=1)


class MemoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str | None = Field(default=None, max_length=300)
    importance: float | None = Field(default=None, ge=0, le=1)


class PublicConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    depth_presets: dict[str, dict[str, int | float]]
    server_max: dict[str, int | float]
    search_providers: list[str]
    models: dict[str, str]
