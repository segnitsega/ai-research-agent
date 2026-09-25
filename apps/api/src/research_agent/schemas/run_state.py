from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from research_agent.schemas.agents import Gap, ResearchPlan, Review
from research_agent.schemas.enums import AgentName, Phase
from research_agent.schemas.memory import MemoryItem


class AgentUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class RunUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requests: int
    input_tokens: int
    output_tokens: int
    fetches: int
    cost_usd: float
    by_agent: dict[AgentName, AgentUsage]


class PriorFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str
    claim: str
    evidence_quote: str
    source_id: str
    source_url: str
    source_title: str | None
    fetched_at: datetime
    similarity: float
    stale: bool


class MemoryContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    preferences: list[MemoryItem]
    episodes: list[MemoryItem]
    facts: list[MemoryItem]
    prior_findings: list[PriorFinding]


class FindingView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    sub_question_id: str
    claim: str
    evidence_quote: str
    confidence: float
    stance: str
    source_domain: str
    source_title: str | None
    source_published_at: datetime | None
    source_fetched_at: datetime
    from_memory: bool


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase_done: list[Phase] = Field(default_factory=list)
    iteration: int = 0
    plan: ResearchPlan | None = None
    pending_gaps: list[Gap] = Field(default_factory=list)
    last_review: Review | None = None
    memory_context: MemoryContext | None = None
    usage: RunUsage = Field(
        default_factory=lambda: RunUsage(
            requests=0,
            input_tokens=0,
            output_tokens=0,
            fetches=0,
            cost_usd=0.0,
            by_agent={},
        )
    )


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    seq: int
    run_id: str
    ts: datetime
    type: str
    agent: AgentName
    data: dict[str, object]
