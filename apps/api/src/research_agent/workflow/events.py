from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_agent.schemas.agents import Report, ResearchPlan, Review
from research_agent.schemas.budget import Budget
from research_agent.schemas.enums import AgentName, Depth
from research_agent.schemas.run_state import RunUsage


class RunStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["run.started"] = "run.started"
    question: str
    depth: Depth
    budget: Budget
    use_memory: bool


class MemoryRecalledData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["memory.recalled"] = "memory.recalled"
    preferences: list[str]
    episodes: list[str]
    prior_findings: int


class PlanCreatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["plan.created"] = "plan.created"
    plan: ResearchPlan


class IterationStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["iteration.started"] = "iteration.started"
    iteration: int
    max_iterations: int
    focus_sub_question_ids: list[str]


class SearchStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["search.started"] = "search.started"
    sub_question_id: str
    query: str


class SourceFoundData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["source.found"] = "source.found"
    source_id: str
    url: str
    title: str
    domain: str
    sub_question_id: str
    reason: str
    expected_quality: str


class SourceFetchedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["source.fetched"] = "source.fetched"
    source_id: str
    url: str
    chars: int
    from_cache: bool
    fetched_at: datetime


class SourceFailedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["source.failed"] = "source.failed"
    source_id: str | None = None
    url: str
    reason: Literal[
        "blocked_ssrf",
        "timeout",
        "http_error",
        "too_large",
        "unsupported_type",
        "robots",
    ]


class FindingExtractedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["finding.extracted"] = "finding.extracted"
    finding_id: str
    source_id: str
    sub_question_id: str
    claim: str
    evidence_quote: str
    confidence: float
    stance: str


class FindingRejectedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["finding.rejected"] = "finding.rejected"
    source_id: str
    sub_question_id: str
    claim: str
    reason: str


class CriticReviewData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["critic.review"] = "critic.review"
    review: Review


class IterationCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["iteration.completed"] = "iteration.completed"
    iteration: int
    accepted_findings_total: int
    decision: Literal["continue", "write"]


class ReportStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["report.started"] = "report.started"
    findings_used: int


class ReportCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["report.completed"] = "report.completed"
    report: Report


class MemoryUpdatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["memory.updated"] = "memory.updated"
    added: int
    updated: int
    deleted: int
    episode_saved: bool


class UsageUpdatedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["usage.updated"] = "usage.updated"
    usage: RunUsage


class BudgetWarningData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["budget.warning"] = "budget.warning"
    resource: Literal["cost", "fetches", "tokens", "time"]
    used: float
    limit: float


class BudgetExhaustedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["budget.exhausted"] = "budget.exhausted"
    resource: Literal["cost", "fetches", "tokens", "time", "iterations"]
    action: Literal["proceeding_to_write"]


class RunCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["run.completed"] = "run.completed"
    report_available: bool
    usage: RunUsage


class RunFailedData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["run.failed"] = "run.failed"
    error_code: str
    message: str


class RunCancelledData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["run.cancelled"] = "run.cancelled"
    phase: str


EventData = Annotated[
    RunStartedData
    | MemoryRecalledData
    | PlanCreatedData
    | IterationStartedData
    | SearchStartedData
    | SourceFoundData
    | SourceFetchedData
    | SourceFailedData
    | FindingExtractedData
    | FindingRejectedData
    | CriticReviewData
    | IterationCompletedData
    | ReportStartedData
    | ReportCompletedData
    | MemoryUpdatedData
    | UsageUpdatedData
    | BudgetWarningData
    | BudgetExhaustedData
    | RunCompletedData
    | RunFailedData
    | RunCancelledData,
    Field(discriminator="type"),
]

EVENT_TYPES: dict[str, type[BaseModel]] = {
    "run.started": RunStartedData,
    "memory.recalled": MemoryRecalledData,
    "plan.created": PlanCreatedData,
    "iteration.started": IterationStartedData,
    "search.started": SearchStartedData,
    "source.found": SourceFoundData,
    "source.fetched": SourceFetchedData,
    "source.failed": SourceFailedData,
    "finding.extracted": FindingExtractedData,
    "finding.rejected": FindingRejectedData,
    "critic.review": CriticReviewData,
    "iteration.completed": IterationCompletedData,
    "report.started": ReportStartedData,
    "report.completed": ReportCompletedData,
    "memory.updated": MemoryUpdatedData,
    "usage.updated": UsageUpdatedData,
    "budget.warning": BudgetWarningData,
    "budget.exhausted": BudgetExhaustedData,
    "run.completed": RunCompletedData,
    "run.failed": RunFailedData,
    "run.cancelled": RunCancelledData,
}

TERMINAL_EVENT_TYPES = frozenset({"run.completed", "run.failed", "run.cancelled"})


def agent_for_event_type(event_type: str) -> AgentName:
    mapping: dict[str, AgentName] = {
        "run.started": AgentName.SYSTEM,
        "memory.recalled": AgentName.SYSTEM,
        "plan.created": AgentName.PLANNER,
        "iteration.started": AgentName.SYSTEM,
        "search.started": AgentName.SEARCHER,
        "source.found": AgentName.SEARCHER,
        "source.fetched": AgentName.SYSTEM,
        "source.failed": AgentName.SYSTEM,
        "finding.extracted": AgentName.READER,
        "finding.rejected": AgentName.READER,
        "critic.review": AgentName.CRITIC,
        "iteration.completed": AgentName.SYSTEM,
        "report.started": AgentName.WRITER,
        "report.completed": AgentName.WRITER,
        "memory.updated": AgentName.CURATOR,
        "usage.updated": AgentName.SYSTEM,
        "budget.warning": AgentName.SYSTEM,
        "budget.exhausted": AgentName.SYSTEM,
        "run.completed": AgentName.SYSTEM,
        "run.failed": AgentName.SYSTEM,
        "run.cancelled": AgentName.SYSTEM,
    }
    return mapping.get(event_type, AgentName.SYSTEM)
