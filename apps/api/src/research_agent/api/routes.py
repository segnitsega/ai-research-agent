import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from research_agent.api.http import check_api_key, sse_events
from research_agent.db.records import StoredFeedback, StoredMemory
from research_agent.schemas.agents import Report
from research_agent.schemas.api import (
    FeedbackRequest,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    PaginatedResponse,
    PublicConfig,
    RunDetail,
    RunSummary,
)
from research_agent.schemas.budget import RunRequest
from research_agent.schemas.enums import MemoryKind, RunStatus
from research_agent.schemas.memory import MemoryItem

router = APIRouter()


def _user_id(request: Request) -> UUID:
    return UUID(request.app.state.settings.seeded_user_id)


def _auth(request: Request, api_key: str | None) -> None:
    if not check_api_key(request.app.state.settings, api_key):
        raise _AuthError()


class _AuthError(Exception):
    pass


def summary_of(record: object) -> RunSummary:
    return RunSummary(
        id=record.id,  # type: ignore[attr-defined]
        question=record.question,  # type: ignore[attr-defined]
        depth=record.depth,  # type: ignore[attr-defined]
        status=record.status,  # type: ignore[attr-defined]
        phase=record.phase,  # type: ignore[attr-defined]
        created_at=record.created_at,  # type: ignore[attr-defined]
        started_at=record.started_at,  # type: ignore[attr-defined]
        finished_at=record.finished_at,  # type: ignore[attr-defined]
        cost_usd=record.usage.cost_usd,  # type: ignore[attr-defined]
        accepted_findings=record.accepted_findings,  # type: ignore[attr-defined]
        sources_used=record.sources_used,  # type: ignore[attr-defined]
    )


def detail_of(record: object) -> RunDetail:
    base = summary_of(record)
    return RunDetail(
        **base.model_dump(),
        plan=record.plan,  # type: ignore[attr-defined]
        report=record.report,  # type: ignore[attr-defined]
        usage=record.usage,  # type: ignore[attr-defined]
        budget=record.budget,  # type: ignore[attr-defined]
        error=record.error,  # type: ignore[attr-defined]
        use_memory=record.use_memory,  # type: ignore[attr-defined]
    )


def memory_of(item: StoredMemory) -> MemoryItem:
    return MemoryItem(
        id=str(item.id),
        kind=MemoryKind(item.kind),
        content=item.content,
        importance=item.importance,
        source_run_id=None if item.source_run_id is None else str(item.source_run_id),
        created_at=item.created_at,
        updated_at=item.updated_at,
        last_used_at=item.last_used_at,
    )


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    if not getattr(request.app.state, "ready", True):
        raise _Missing()
    return {"status": "ready"}


@router.get("/v1/config", response_model=PublicConfig)
async def config(request: Request, x_api_key: str | None = Header(default=None)) -> PublicConfig:
    _auth(request, x_api_key)
    return PublicConfig.model_validate(request.app.state.settings.public_config())


@router.post("/v1/runs", status_code=202, response_model=RunSummary)
async def create_run(
    request: Request,
    body: RunRequest,
    x_api_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> RunSummary:
    _auth(request, x_api_key)
    settings = request.app.state.settings
    if not request.app.state.limiter.allow(x_api_key or "anon"):
        raise _LimitError()
    user_id = _user_id(request)
    store = request.app.state.store
    if idempotency_key:
        existing = await store.find_idempotent(user_id, idempotency_key)
        if existing is not None:
            return summary_of(existing)
    if request.app.state.registry.active_for(user_id) >= settings.max_active_runs_per_user:
        raise _LimitError()
    try:
        budget = settings.resolve_budget(body.depth, body.budget)
    except ValueError as exc:
        raise _BudgetError(str(exc)) from exc
    record = await store.create_run(
        user_id=user_id,
        question=body.question,
        depth=body.depth.value,
        use_memory=body.use_memory,
        budget=budget,
        language=body.language,
        idempotency_key=idempotency_key,
    )
    task = asyncio.create_task(request.app.state.orchestrator.run(user_id, record.id))
    request.app.state.registry.register(user_id, record.id, task)
    return summary_of(record)


@router.get("/v1/runs", response_model=PaginatedResponse[RunSummary])
async def list_runs(
    request: Request,
    x_api_key: str | None = Header(default=None),
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> PaginatedResponse[RunSummary]:
    _auth(request, x_api_key)
    rows, next_cursor = await request.app.state.store.list_runs(_user_id(request), status=status, limit=limit, cursor=cursor)
    return PaginatedResponse[RunSummary](items=[summary_of(row) for row in rows], next_cursor=next_cursor)


@router.get("/v1/runs/{run_id}", response_model=RunDetail)
async def get_run(request: Request, run_id: UUID, x_api_key: str | None = Header(default=None)) -> RunDetail:
    _auth(request, x_api_key)
    record = await request.app.state.store.get_run(_user_id(request), run_id)
    if record is None:
        raise _Missing()
    return detail_of(record)


@router.get("/v1/runs/{run_id}/events")
async def events(
    request: Request,
    run_id: UUID,
    x_api_key: str | None = Header(default=None),
    after: int = 0,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    _auth(request, x_api_key)
    user_id = _user_id(request)
    record = await request.app.state.store.get_run(user_id, run_id)
    if record is None:
        raise _Missing()
    start = after
    if last_event_id and last_event_id.isdigit():
        start = max(start, int(last_event_id))
    stream = sse_events(request.app.state.store, request.app.state.bus, user_id, run_id, start)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/v1/runs/{run_id}/cancel", status_code=202)
async def cancel_run(request: Request, run_id: UUID, x_api_key: str | None = Header(default=None)) -> dict[str, str]:
    _auth(request, x_api_key)
    record = await request.app.state.store.get_run(_user_id(request), run_id)
    if record is None:
        raise _Missing()
    if record.status in {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value}:
        raise _Conflict("Run is already finished")
    request.app.state.registry.cancel(run_id)
    return {"status": "cancelling"}


@router.delete("/v1/runs/{run_id}", status_code=204)
async def delete_run(request: Request, run_id: UUID, x_api_key: str | None = Header(default=None)) -> None:
    _auth(request, x_api_key)
    record = await request.app.state.store.get_run(_user_id(request), run_id)
    if record is None:
        raise _Missing()
    if record.status in {RunStatus.QUEUED.value, RunStatus.RUNNING.value}:
        raise _Conflict("Run is still active")
    await request.app.state.store.delete_run(_user_id(request), run_id)


@router.get("/v1/runs/{run_id}/sources")
async def sources(request: Request, run_id: UUID, x_api_key: str | None = Header(default=None)) -> list[dict[str, object]]:
    _auth(request, x_api_key)
    rows = await request.app.state.store.list_sources(_user_id(request), run_id)
    return [
        {
            "id": str(row.id),
            "url": row.canonical_url,
            "title": row.title,
            "domain": row.domain,
            "status": row.status,
            "from_cache": row.from_cache,
            "sub_question_id": row.sub_question_id,
            "error": row.error,
        }
        for row in rows
    ]


@router.get("/v1/runs/{run_id}/findings")
async def findings(
    request: Request,
    run_id: UUID,
    x_api_key: str | None = Header(default=None),
    status: str | None = None,
    sub_question_id: str | None = None,
) -> list[dict[str, object]]:
    _auth(request, x_api_key)
    rows = await request.app.state.store.list_findings(_user_id(request), run_id, status=status, sub_question_id=sub_question_id)
    return [row.model_dump(mode="json") for row in rows]


@router.get("/v1/runs/{run_id}/report.md")
async def report_md(request: Request, run_id: UUID, x_api_key: str | None = Header(default=None)) -> PlainTextResponse:
    _auth(request, x_api_key)
    record = await request.app.state.store.get_run(_user_id(request), run_id)
    if record is None or record.report is None:
        raise _Missing()
    return PlainTextResponse(render_markdown(record.report))


@router.post("/v1/runs/{run_id}/feedback", status_code=201)
async def feedback(
    request: Request,
    run_id: UUID,
    body: FeedbackRequest,
    x_api_key: str | None = Header(default=None),
) -> dict[str, str]:
    _auth(request, x_api_key)
    user_id = _user_id(request)
    record = await request.app.state.store.get_run(user_id, run_id)
    if record is None:
        raise _Missing()
    flagged = [UUID(item) for item in body.flagged_finding_ids]
    await request.app.state.store.add_feedback(
        StoredFeedback(
            id=uuid4(),
            run_id=run_id,
            rating=body.rating,
            comment=body.comment,
            flagged_finding_ids=flagged,
            created_at=datetime.now(UTC),
        )
    )
    if flagged:
        await request.app.state.store.flag_findings(user_id, run_id, flagged)
    return {"status": "stored"}


@router.get("/v1/memories", response_model=PaginatedResponse[MemoryItem])
async def list_memories(
    request: Request,
    x_api_key: str | None = Header(default=None),
    kind: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> PaginatedResponse[MemoryItem]:
    _auth(request, x_api_key)
    rows, next_cursor = await request.app.state.store.list_memories(_user_id(request), kind=kind, limit=limit, cursor=cursor)
    return PaginatedResponse[MemoryItem](items=[memory_of(row) for row in rows], next_cursor=next_cursor)


@router.post("/v1/memories", status_code=201, response_model=MemoryItem)
async def create_memory(
    request: Request,
    body: MemoryCreateRequest,
    x_api_key: str | None = Header(default=None),
) -> MemoryItem:
    _auth(request, x_api_key)
    if body.kind not in {MemoryKind.PREFERENCE.value, MemoryKind.FACT.value}:
        raise _BudgetError("Only preference and fact memories can be created directly")
    user_id = _user_id(request)
    vector = (await request.app.state.embedder.embed([body.content]))[0]
    now = datetime.now(UTC)
    item = await request.app.state.store.create_memory(
        StoredMemory(
            id=uuid4(),
            user_id=user_id,
            kind=body.kind,
            content=body.content,
            importance=body.importance,
            embedding=vector,
            source_run_id=None,
            created_at=now,
            updated_at=now,
            last_used_at=None,
        )
    )
    return memory_of(item)


@router.patch("/v1/memories/{memory_id}", response_model=MemoryItem)
async def update_memory(
    request: Request,
    memory_id: UUID,
    body: MemoryUpdateRequest,
    x_api_key: str | None = Header(default=None),
) -> MemoryItem:
    _auth(request, x_api_key)
    vector = None
    if body.content:
        vector = (await request.app.state.embedder.embed([body.content]))[0]
    item = await request.app.state.store.update_memory(
        _user_id(request),
        memory_id,
        content=body.content,
        importance=body.importance,
        embedding=vector,
    )
    if item is None:
        raise _Missing()
    return memory_of(item)


@router.delete("/v1/memories/{memory_id}", status_code=204)
async def delete_memory(request: Request, memory_id: UUID, x_api_key: str | None = Header(default=None)) -> None:
    _auth(request, x_api_key)
    deleted = await request.app.state.store.delete_memory(_user_id(request), memory_id)
    if not deleted:
        raise _Missing()


@router.delete("/v1/memories", status_code=204)
async def forget_all(
    request: Request,
    x_api_key: str | None = Header(default=None),
    confirm: bool = False,
) -> None:
    _auth(request, x_api_key)
    if not confirm:
        raise _BudgetError("confirm=true is required")
    await request.app.state.store.forget_all(_user_id(request))


@router.get("/v1/memories/search", response_model=list[MemoryItem])
async def search_memories(
    request: Request,
    q: str,
    x_api_key: str | None = Header(default=None),
) -> list[MemoryItem]:
    _auth(request, x_api_key)
    vector = (await request.app.state.embedder.embed([q]))[0]
    rows = await request.app.state.store.search_memories(_user_id(request), q, vector, 10)
    return [memory_of(row) for row in rows]


def render_markdown(report: Report) -> str:
    lines = [f"# {report.title}", "", report.executive_summary, ""]
    for section in report.sections:
        lines.extend([f"## {section.heading}", "", section.body_markdown, ""])
    if report.limitations:
        lines.append("## Limitations")
        lines.extend(f"- {item}" for item in report.limitations)
        lines.append("")
    lines.append("## References")
    for citation in report.citations:
        lines.append(f"[{citation.n}] source {citation.source_id}")
    return "\n".join(lines)


class _Missing(Exception):
    pass


class _Conflict(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class _BudgetError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class _LimitError(Exception):
    pass
