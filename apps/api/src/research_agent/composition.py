from research_agent.agents.runtime import GeminiAgents
from research_agent.config import Settings
from research_agent.db.session import create_session_factory
from research_agent.db.sql_store import SqlResearchStore
from research_agent.memory.embeddings import build_embedder
from research_agent.schemas.agents import SearchHit
from research_agent.tools.fetch import GuardedFetcher
from research_agent.tools.search import ArxivProvider, DuckDuckGoProvider, FakeSearchProvider, TavilyProvider
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.orchestrator import FIXTURE_PAGES, RunOrchestrator, ports_from_gemini
from research_agent.workflow.registry import RunRegistry


class FixtureSearch:
    name = "fake"

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        _ = query
        return [
            SearchHit.model_validate(
                {
                    "url": "https://research.example/gemini",
                    "title": "Gemini overview",
                    "snippet": FIXTURE_PAGES["https://research.example/gemini"][:180],
                    "provider": self.name,
                }
            )
        ][:limit]


def build_search(settings: Settings) -> FakeSearchProvider | TavilyProvider | DuckDuckGoProvider | FixtureSearch:
    if settings.search_provider == "tavily" and settings.tavily_api_key is not None:
        secret = settings.tavily_api_key.get_secret_value()
        if secret:
            return TavilyProvider(secret)
    if settings.search_provider == "duckduckgo":
        return DuckDuckGoProvider()
    if settings.search_provider == "fake":
        return FixtureSearch()
    return FixtureSearch()


def build_runtime(settings: Settings) -> tuple[SqlResearchStore, InProcessEventBus, RunRegistry, RunOrchestrator]:
    sessions = create_session_factory(settings)
    store = SqlResearchStore(sessions)
    bus = InProcessEventBus()
    registry = RunRegistry(settings.max_active_runs_per_user)
    agents = GeminiAgents(settings, build_search(settings), ArxivProvider())
    orchestrator = RunOrchestrator(
        settings,
        store,
        bus,
        ports_from_gemini(agents),
        fetcher=GuardedFetcher(settings),
        registry=registry,
        embedder=build_embedder(settings),
    )
    return store, bus, registry, orchestrator
