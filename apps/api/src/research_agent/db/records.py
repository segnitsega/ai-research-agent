from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from research_agent.schemas.agents import Finding, Report, ResearchPlan
from research_agent.schemas.budget import Budget
from research_agent.schemas.run_state import RunState, RunUsage


@dataclass
class RunRecord:
    id: UUID
    user_id: UUID
    question: str
    depth: str
    use_memory: bool
    status: str
    phase: str | None
    budget: Budget
    state: RunState
    plan: ResearchPlan | None
    report: Report | None
    usage: RunUsage
    error: str | None
    language: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    idempotency_key: str | None
    accepted_findings: int = 0
    sources_used: int = 0


@dataclass
class SourceRecord:
    id: UUID
    canonical_url: str
    content_hash: str
    title: str | None
    domain: str
    text: str
    published_at: datetime | None
    fetched_at: datetime
    content_type: str | None
    sub_question_id: str
    status: str
    error: str | None
    from_cache: bool


@dataclass
class StoredFinding:
    finding: Finding
    user_id: UUID
    embedding: list[float] | None = None


@dataclass
class StoredMemory:
    id: UUID
    user_id: UUID
    kind: str
    content: str
    importance: float
    embedding: list[float]
    source_run_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    deleted_at: datetime | None = None
    similarity: float = 0.0


@dataclass
class StoredFeedback:
    id: UUID
    run_id: UUID
    rating: int | None
    comment: str | None
    flagged_finding_ids: list[UUID] = field(default_factory=list)
    created_at: datetime | None = None
