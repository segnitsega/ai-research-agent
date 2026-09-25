from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry

from research_agent.config import Settings
from research_agent.schemas.agents import ReaderOutput, Report, ResearchPlan, Review, SearcherOutput
from research_agent.schemas.memory import CuratorOutput

PROMPTS = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


@dataclass
class PlannerDeps:
    question: str
    max_sub_questions: int
    memory_block: str


@dataclass
class SearcherDeps:
    allowed_urls: set[str]


@dataclass
class ReaderDeps:
    source_text: str
    sub_question_id: str


@dataclass
class CriticDeps:
    finding_ids: set[str]
    sub_question_ids: set[str]


@dataclass
class WriterDeps:
    accepted_finding_ids: set[str]


@dataclass
class CuratorDeps:
    user_id: str


def build_planner(settings: Settings) -> Agent[PlannerDeps, ResearchPlan]:
    settings.apply_provider_env()
    return Agent(
        settings.model_planner,
        deps_type=PlannerDeps,
        output_type=ResearchPlan,
        instructions=_load("planner.md"),
        name="planner",
    )


def build_searcher(settings: Settings) -> Agent[SearcherDeps, SearcherOutput]:
    settings.apply_provider_env()
    agent: Agent[SearcherDeps, SearcherOutput] = Agent(
        settings.model_searcher,
        deps_type=SearcherDeps,
        output_type=SearcherOutput,
        instructions=_load("searcher.md"),
        name="searcher",
    )

    @agent.output_validator
    def only_tool_urls(ctx: RunContext[SearcherDeps], output: SearcherOutput) -> SearcherOutput:
        for candidate in output.candidates:
            if str(candidate.url) not in ctx.deps.allowed_urls:
                raise ModelRetry("Candidate URL was not returned by a search tool")
        return output

    return agent


def build_reader(settings: Settings) -> Agent[ReaderDeps, ReaderOutput]:
    settings.apply_provider_env()
    agent: Agent[ReaderDeps, ReaderOutput] = Agent(
        settings.model_reader,
        deps_type=ReaderDeps,
        output_type=ReaderOutput,
        instructions=_load("reader.md"),
        name="reader",
    )

    @agent.output_validator
    def quotes_exist(ctx: RunContext[ReaderDeps], output: ReaderOutput) -> ReaderOutput:
        from research_agent.workflow.verify import quote_found_in_source

        for finding in output.findings:
            if not quote_found_in_source(finding.evidence_quote, ctx.deps.source_text):
                raise ModelRetry("evidence_quote must be copied from the source text")
        return output

    return agent


def build_critic(settings: Settings) -> Agent[CriticDeps, Review]:
    settings.apply_provider_env()
    agent: Agent[CriticDeps, Review] = Agent(
        settings.model_critic,
        deps_type=CriticDeps,
        output_type=Review,
        instructions=_load("critic.md"),
        name="critic",
    )

    @agent.output_validator
    def coverage(ctx: RunContext[CriticDeps], output: Review) -> Review:
        missing = ctx.deps.sub_question_ids - set(output.coverage_by_sub_question)
        if missing:
            raise ModelRetry("coverage_by_sub_question must include every sub-question")
        return output

    return agent


def build_writer(settings: Settings) -> Agent[WriterDeps, Report]:
    settings.apply_provider_env()
    agent: Agent[WriterDeps, Report] = Agent(
        settings.model_writer,
        deps_type=WriterDeps,
        output_type=Report,
        instructions=_load("writer.md"),
        name="writer",
    )

    @agent.output_validator
    def citations(ctx: RunContext[WriterDeps], output: Report) -> Report:
        from research_agent.workflow.verify import validate_report_citations

        errors = validate_report_citations(output, ctx.deps.accepted_finding_ids)
        if errors:
            raise ModelRetry("; ".join(errors))
        return output

    return agent


def build_curator(settings: Settings) -> Agent[CuratorDeps, CuratorOutput]:
    settings.apply_provider_env()
    return Agent(
        settings.model_curator,
        deps_type=CuratorDeps,
        output_type=CuratorOutput,
        instructions=_load("curator.md"),
        name="curator",
    )
