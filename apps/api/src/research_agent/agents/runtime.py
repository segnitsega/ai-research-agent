from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from research_agent.agents.factories import (
    CriticDeps,
    CuratorDeps,
    PlannerDeps,
    ReaderDeps,
    SearcherDeps,
    WriterDeps,
    build_critic,
    build_curator,
    build_planner,
    build_reader,
    build_searcher,
    build_writer,
)
from research_agent.config import Settings
from research_agent.schemas.agents import (
    ReaderOutput,
    Report,
    ResearchPlan,
    Review,
    SearcherOutput,
    SourceCandidate,
)
from research_agent.schemas.memory import CuratorOutput
from research_agent.schemas.run_state import FindingView
from research_agent.tools.search import SearchProvider
from research_agent.workflow.cost import gemini_cost


@dataclass
class ModelUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


class GeminiAgents:
    def __init__(self, settings: Settings, search: SearchProvider, arxiv: SearchProvider) -> None:
        self.settings = settings
        self.search_provider = search
        self.arxiv_provider = arxiv
        self.planner = build_planner(settings)
        self.searcher = _with_search_tools(build_searcher(settings))
        self.reader = build_reader(settings)
        self.critic = build_critic(settings)
        self.writer = build_writer(settings)
        self.curator = build_curator(settings)

    async def plan(self, question: str, memory_block: str, max_sub_questions: int) -> tuple[ResearchPlan, ModelUsage]:
        result = await self.planner.run(
            f"Question:\n{question}\n\n<memory_data>\n{memory_block}\n</memory_data>\nCreate at most {max_sub_questions} sub-questions.",
            deps=PlannerDeps(
                question=question,
                max_sub_questions=max_sub_questions,
                memory_block=memory_block,
            ),
        )
        return result.output, _usage(result.usage.input_tokens, result.usage.output_tokens)

    async def search(self, sub_question: str, sub_question_id: str, queries: list[str]) -> tuple[SearcherOutput, ModelUsage]:
        deps = SearcherDeps(allowed_urls=set(), provider=self.search_provider, arxiv=self.arxiv_provider, hits=[])
        result = await self.searcher.run(
            f"Sub-question {sub_question_id}: {sub_question}\nCall web_search before choosing candidates. Suggested queries: {', '.join(queries) if queries else sub_question}",
            deps=deps,
        )
        output = result.output
        if not output.candidates and deps.hits:
            output = SearcherOutput(
                candidates=[
                    SourceCandidate(
                        url=hit.url,
                        title=hit.title,
                        sub_question_id=sub_question_id,
                        reason=hit.snippet[:240] or "Returned by search",
                        expected_quality="medium",
                    )
                    for hit in deps.hits[:8]
                ],
                queries_used=queries or [sub_question],
            )
        return output, _usage(result.usage.input_tokens, result.usage.output_tokens)

    async def read(self, source_text: str, sub_question_id: str, question: str) -> tuple[ReaderOutput, ModelUsage]:
        result = await self.reader.run(
            f"<untrusted_source>\n{source_text[:12000]}\n</untrusted_source>\nSub-question {sub_question_id}: {question}\nCopy evidence quotes verbatim from the untrusted source.",
            deps=ReaderDeps(source_text=source_text, sub_question_id=sub_question_id),
        )
        return result.output, _usage(result.usage.input_tokens, result.usage.output_tokens)

    async def critique(
        self,
        question: str,
        plan: ResearchPlan,
        findings: list[FindingView],
    ) -> tuple[Review, ModelUsage]:
        result = await self.critic.run(
            f"Question: {question}\nPlan: {plan.model_dump_json()}\nFindings: " + "\n".join(f"{item.id}: {item.claim}" for item in findings),
            deps=CriticDeps(
                finding_ids={item.id for item in findings},
                sub_question_ids={item.id for item in plan.sub_questions},
            ),
        )
        return result.output, _usage(result.usage.input_tokens, result.usage.output_tokens)

    async def write(
        self,
        question: str,
        findings: list[FindingView],
        limitations: list[str],
    ) -> tuple[Report, ModelUsage]:
        result = await self.writer.run(
            f"Question: {question}\nLimitations: {limitations}\nFindings:\n"
            + "\n".join(f"{item.id} source={item.source_domain} {item.claim} quote={item.evidence_quote}" for item in findings),
            deps=WriterDeps(accepted_finding_ids={item.id for item in findings}),
        )
        return result.output, _usage(result.usage.input_tokens, result.usage.output_tokens)

    async def curate(self, question: str, summary: str) -> tuple[CuratorOutput, ModelUsage]:
        result = await self.curator.run(
            f"<run_data>\nQuestion: {question}\nSummary: {summary}\n</run_data>",
            deps=CuratorDeps(user_id=""),
        )
        return result.output, _usage(result.usage.input_tokens, result.usage.output_tokens)


def _with_search_tools(agent: Agent[SearcherDeps, SearcherOutput]) -> Agent[SearcherDeps, SearcherOutput]:
    @agent.tool
    async def web_search(ctx: RunContext[SearcherDeps], query: str) -> list[dict[str, str]]:
        if ctx.deps.provider is None:
            return []
        hits = await ctx.deps.provider.search(query)
        ctx.deps.hits.extend(hits)
        ctx.deps.allowed_urls.update(str(hit.url) for hit in hits)
        return [{"url": str(hit.url), "title": hit.title, "snippet": hit.snippet} for hit in hits]

    @agent.tool
    async def arxiv_search(ctx: RunContext[SearcherDeps], query: str) -> list[dict[str, str]]:
        if ctx.deps.arxiv is None:
            return []
        hits = await ctx.deps.arxiv.search(query)
        ctx.deps.hits.extend(hits)
        ctx.deps.allowed_urls.update(str(hit.url) for hit in hits)
        return [{"url": str(hit.url), "title": hit.title, "snippet": hit.snippet} for hit in hits]

    @agent.tool
    async def recall_sources(ctx: RunContext[SearcherDeps], query: str) -> list[dict[str, str]]:
        _ = (ctx, query)
        return []

    return agent


def _usage(input_tokens: int, output_tokens: int) -> ModelUsage:
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=gemini_cost(input_tokens, output_tokens),
    )
