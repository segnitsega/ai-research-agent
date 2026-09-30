from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from research_agent.schemas.enums import FindingStatus


class SubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str
    rationale: str
    priority: Literal[1, 2, 3]
    preferred_source_types: list[Literal["academic", "official", "news", "industry", "community", "any"]] = ["any"]


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str
    sub_questions: list[SubQuestion] = Field(min_length=1, max_length=8)
    success_criteria: list[str] = Field(min_length=1, max_length=6)
    out_of_scope: list[str] = []


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: HttpUrl
    title: str
    snippet: str
    provider: str
    published_at: datetime | None = None
    score: float | None = None


class SourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: HttpUrl
    title: str
    sub_question_id: str
    reason: str
    expected_quality: Literal["high", "medium", "low"]


class SearcherOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidates: list[SourceCandidate] = Field(max_length=12)
    queries_used: list[str]


class FindingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sub_question_id: str
    claim: str = Field(max_length=500)
    evidence_quote: str = Field(min_length=20, max_length=400)
    confidence: float = Field(ge=0, le=1)
    stance: Literal["supports", "contradicts", "context"] = "supports"


class ReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: list[FindingDraft] = Field(max_length=8)
    source_quality_note: str | None = None
    off_topic: bool = False


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    run_id: str
    source_id: str
    sub_question_id: str
    claim: str
    evidence_quote: str
    confidence: float
    stance: Literal["supports", "contradicts", "context"]
    status: FindingStatus
    reject_reason: str | None = None
    from_memory: bool = False


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sub_question_id: str
    description: str
    suggested_queries: list[str] = Field(max_length=4)


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_ids: list[str] = Field(min_length=2)
    description: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: Literal["sufficient", "needs_more"]
    coverage_by_sub_question: dict[str, Literal["none", "partial", "good"]]
    gaps: list[Gap] = []
    contradictions: list[Contradiction] = []
    weak_finding_ids: list[str] = []
    rationale: str


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str
    body_markdown: str
    finding_ids: list[str]


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    n: int
    source_id: str
    finding_ids: list[str]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str
    executive_summary: str
    sections: list[ReportSection] = Field(min_length=1)
    limitations: list[str]
    citations: list[Citation]
