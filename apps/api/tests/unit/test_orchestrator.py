from uuid import UUID, uuid4

import pytest

from research_agent.agents.runtime import ModelUsage
from research_agent.config import Settings
from research_agent.db.memory_store import InMemoryResearchStore
from research_agent.memory.embeddings import HashEmbedder
from research_agent.schemas.agents import (
    Citation,
    FindingDraft,
    Gap,
    ReaderOutput,
    Report,
    ReportSection,
    ResearchPlan,
    Review,
    SearcherOutput,
    SourceCandidate,
    SubQuestion,
)
from research_agent.schemas.budget import Budget
from research_agent.schemas.memory import CuratorOutput
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.orchestrator import FIXTURE_PAGES, AgentPorts, RunOrchestrator
from research_agent.workflow.registry import RunRegistry

pytestmark = pytest.mark.unit

USER = UUID("00000000-0000-0000-0000-000000000001")
QUOTE = "Gemini models are developed by Google DeepMind"


class ScriptedAgents:
    def __init__(self, *, needs_more: int = 0, bad_quote: bool = False) -> None:
        self.needs_more = needs_more
        self.bad_quote = bad_quote
        self.critiques = 0

    async def plan(self, question: str, memory_block: str, max_sub_questions: int) -> tuple[ResearchPlan, ModelUsage]:
        _ = (question, memory_block, max_sub_questions)
        plan = ResearchPlan(
            objective="Explain Gemini",
            sub_questions=[SubQuestion(id="q1", question="Who develops Gemini?", rationale="Core fact", priority=1)],
            success_criteria=["Name the developer"],
        )
        return plan, ModelUsage(10, 10, 0.001)

    async def search(self, question: str, sub_question_id: str, queries: list[str]) -> tuple[SearcherOutput, ModelUsage]:
        _ = (question, queries)
        output = SearcherOutput(
            candidates=[
                SourceCandidate(
                    url="https://research.example/gemini",
                    title="Gemini overview",
                    sub_question_id=sub_question_id,
                    reason="Official-style overview",
                    expected_quality="high",
                )
            ],
            queries_used=queries or [question],
        )
        return output, ModelUsage(5, 5, 0.001)

    async def read(self, source_text: str, sub_question_id: str, question: str) -> tuple[ReaderOutput, ModelUsage]:
        _ = (source_text, question)
        quote = "This quote was altered by the model" if self.bad_quote else QUOTE
        if self.bad_quote:
            quote = "This quote was altered by the model."
        output = ReaderOutput(
            findings=[
                FindingDraft(
                    sub_question_id=sub_question_id,
                    claim="Gemini is developed by Google DeepMind",
                    evidence_quote=quote,
                    confidence=0.9,
                )
            ]
        )
        return output, ModelUsage(8, 8, 0.001)

    async def critique(self, question: str, plan: ResearchPlan, findings: list[object]) -> tuple[Review, ModelUsage]:
        _ = (question, findings)
        self.critiques += 1
        coverage = {item.id: "good" for item in plan.sub_questions}
        if self.critiques <= self.needs_more:
            review = Review(
                verdict="needs_more",
                coverage_by_sub_question={item.id: "partial" for item in plan.sub_questions},
                gaps=[Gap(sub_question_id="q1", description="Need a second source", suggested_queries=["Gemini DeepMind"])],
                rationale="Evidence is thin",
            )
        else:
            review = Review(
                verdict="sufficient",
                coverage_by_sub_question=coverage,  # type: ignore[arg-type]
                rationale="The developer is identified",
            )
        return review, ModelUsage(4, 4, 0.001)

    async def write(self, question: str, findings: list[object], limitations: list[str]) -> tuple[Report, ModelUsage]:
        _ = question
        first = findings[0]
        report = Report(
            title="Gemini",
            executive_summary=f"{first.claim} [1]",  # type: ignore[attr-defined]
            sections=[
                ReportSection(
                    heading="Developer",
                    body_markdown=f"{first.claim} [1]",  # type: ignore[attr-defined]
                    finding_ids=[first.id],  # type: ignore[attr-defined]
                )
            ],
            limitations=limitations,
            citations=[Citation(n=1, source_id=first.id, finding_ids=[first.id])],  # type: ignore[attr-defined]
        )
        return report, ModelUsage(6, 6, 0.001)

    async def curate(self, question: str, summary: str) -> tuple[CuratorOutput, ModelUsage]:
        _ = (question, summary)
        return CuratorOutput(ops=[], run_summary="User asked about Gemini models."), ModelUsage(2, 2, 0.0)


def ports(agents: ScriptedAgents) -> AgentPorts:
    return AgentPorts(
        plan=agents.plan,
        search=agents.search,
        read=agents.read,
        critique=agents.critique,
        write=agents.write,
        curate=agents.curate,
    )


def settings() -> Settings:
    return Settings(api_key="test-key", allow_model_requests=False)  # type: ignore[arg-type]


async def _run(agents: ScriptedAgents, budget: Budget, registry: RunRegistry | None = None) -> tuple[InMemoryResearchStore, list[str]]:
    store = InMemoryResearchStore()
    bus = InProcessEventBus()
    record = await store.create_run(
        user_id=USER,
        question="Who develops the Gemini models?",
        depth="quick",
        use_memory=True,
        budget=budget,
        language="en",
        idempotency_key=None,
    )
    orchestrator = RunOrchestrator(
        settings(),
        store,
        bus,
        ports(agents),
        registry=registry,
        embedder=HashEmbedder(),
    )
    await orchestrator.run(USER, record.id)
    events = await store.list_events(USER, record.id, 0)
    return store, [event.type for event in events]


def budget() -> Budget:
    return Budget(max_iterations=2, max_fetches=10, max_cost_usd=1, max_tokens=100000, max_wall_seconds=120)


@pytest.mark.asyncio
async def test_run_accepts_verbatim_quote_and_writes_report() -> None:
    store, types = await _run(ScriptedAgents(), budget())
    record = next(iter(store.runs.values()))
    assert record.status == "completed"
    assert record.report is not None
    assert "run.completed" in types
    assert "finding.extracted" in types
    assert QUOTE in FIXTURE_PAGES["https://research.example/gemini"]


@pytest.mark.asyncio
async def test_altered_quote_is_rejected() -> None:
    store, types = await _run(ScriptedAgents(bad_quote=True), budget())
    assert "finding.rejected" in types
    assert "finding.extracted" not in types
    record = next(iter(store.runs.values()))
    assert record.report is not None
    assert record.report.citations == []


@pytest.mark.asyncio
async def test_needs_more_then_sufficient() -> None:
    agents = ScriptedAgents(needs_more=1)
    _store, types = await _run(agents, budget())
    assert agents.critiques == 2
    assert types.count("critic.review") == 2
    assert "run.completed" in types


@pytest.mark.asyncio
async def test_cancel_writes_no_report() -> None:
    store = InMemoryResearchStore()
    bus = InProcessEventBus()
    registry = RunRegistry()
    record = await store.create_run(
        user_id=USER,
        question="Who develops the Gemini models?",
        depth="quick",
        use_memory=False,
        budget=budget(),
        language="en",
        idempotency_key=None,
    )
    registry.cancel(record.id)
    orchestrator = RunOrchestrator(settings(), store, bus, ports(ScriptedAgents()), registry=registry)
    await orchestrator.run(USER, record.id)
    assert record.status == "cancelled"
    assert record.report is None


@pytest.mark.asyncio
async def test_user_isolation() -> None:
    store = InMemoryResearchStore()
    other = uuid4()
    created = await store.create_run(
        user_id=USER,
        question="Who develops the Gemini models?",
        depth="quick",
        use_memory=True,
        budget=budget(),
        language="en",
        idempotency_key=None,
    )
    assert await store.get_run(other, created.id) is None
    assert await store.list_findings(other, created.id) == []
    assert await store.delete_run(other, created.id) is False
