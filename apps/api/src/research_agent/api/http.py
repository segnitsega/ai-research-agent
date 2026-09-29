import asyncio
import hmac
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from research_agent.config import Settings
from research_agent.schemas.run_state import RunEvent
from research_agent.workflow.events import TERMINAL_EVENT_TYPES


class RateLimiter:
    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = limit
        self.window_s = window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self.hits[key]
        while bucket and now - bucket[0] > self.window_s:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def install_errors(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(exc.status_code, exc.detail if isinstance(exc.detail, str) else "Request failed")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(422, "Validation failed", errors=exc.errors(), instance=str(request.url))

    @app.exception_handler(ValueError)
    async def value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return problem(422, str(exc))


def problem(
    status: int,
    detail: str,
    *,
    errors: object | None = None,
    instance: str | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": "about:blank",
        "title": detail,
        "status": status,
        "detail": detail,
        "instance": instance,
    }
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type="application/problem+json")


def check_api_key(settings: Settings, presented: str | None) -> bool:
    if not presented:
        return False
    expected = settings.api_key.get_secret_value()
    return hmac.compare_digest(presented, expected)


def format_sse(event: RunEvent) -> str:
    payload = event.model_dump_json()
    return f"id: {event.seq}\nevent: {event.type}\ndata: {payload}\n\n"


async def sse_events(
    store: object,
    bus: object,
    user_id: UUID,
    run_id: UUID,
    after: int,
    keepalive_s: float = 15,
) -> AsyncIterator[str]:
    seen: set[int] = set()
    live: asyncio.Queue[RunEvent | None] = asyncio.Queue()

    async def pump() -> None:
        async for event in bus.subscribe(run_id):  # type: ignore[attr-defined]
            await live.put(event)
        await live.put(None)

    task = asyncio.create_task(pump())
    try:
        replay = await store.list_events(user_id, run_id, after)  # type: ignore[attr-defined]
        terminal = False
        for event in replay:
            seen.add(event.seq)
            yield format_sse(event)
            if event.type in TERMINAL_EVENT_TYPES:
                terminal = True
        if terminal:
            return
        while True:
            try:
                event = await asyncio.wait_for(live.get(), timeout=keepalive_s)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if event is None:
                break
            if event.seq in seen or event.seq <= after:
                continue
            seen.add(event.seq)
            yield format_sse(event)
            if event.type in TERMINAL_EVENT_TYPES:
                break
    finally:
        task.cancel()
