from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from research_agent.api.http import RateLimiter, install_errors, problem
from research_agent.api.routes import _AuthError, _BudgetError, _Conflict, _LimitError, _Missing, router
from research_agent.composition import build_runtime
from research_agent.config import Settings, get_settings
from research_agent.memory.embeddings import HashEmbedder, build_embedder
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.registry import RunRegistry


def create_app(
    settings: Settings | None = None,
    store: object | None = None,
    orchestrator: object | None = None,
    bus: InProcessEventBus | None = None,
    registry: RunRegistry | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    resolved.apply_provider_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if getattr(app.state, "store", None) is None:
            sql_store, sql_bus, sql_registry, sql_orchestrator = build_runtime(resolved)
            app.state.store = sql_store
            app.state.bus = sql_bus
            app.state.registry = sql_registry
            app.state.orchestrator = sql_orchestrator
            app.state.embedder = build_embedder(resolved)
        app.state.ready = True
        yield

    app = FastAPI(title="Research Agent", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved
    app.state.store = store
    app.state.orchestrator = orchestrator
    app.state.bus = bus or InProcessEventBus()
    app.state.registry = registry or RunRegistry(resolved.max_active_runs_per_user)
    app.state.embedder = HashEmbedder(resolved.embedding_dim)
    app.state.limiter = RateLimiter(10, 60)
    app.state.ready = store is not None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    install_errors(app)

    @app.exception_handler(_AuthError)
    async def auth_error(_request: Request, _exc: _AuthError) -> object:
        return problem(
            401,
            "API key missing or incorrect. Set the same API_KEY on both the web and API services.",
        )

    @app.exception_handler(_Missing)
    async def missing(_request: Request, _exc: _Missing) -> object:
        return problem(404, "Not found")

    @app.exception_handler(_Conflict)
    async def conflict(_request: Request, exc: _Conflict) -> object:
        return problem(409, exc.detail)

    @app.exception_handler(_BudgetError)
    async def budget(_request: Request, exc: _BudgetError) -> object:
        return problem(422, exc.detail)

    @app.exception_handler(_LimitError)
    async def limited(_request: Request, _exc: _LimitError) -> object:
        return problem(
            429,
            "Too many runs started recently, or another run is already active. Wait and try again.",
        )

    @app.middleware("http")
    async def request_guard(request: Request, call_next: object) -> object:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > 1_000_000:
            return problem(413, "Request body is too large")
        request.state.request_id = request.headers.get("x-request-id", "local")
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    return app


app = create_app()
