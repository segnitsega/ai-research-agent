from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from research_agent.agents.runtime import ModelUsage
from research_agent.config import Settings
from research_agent.db.memory_store import InMemoryResearchStore, empty_usage
from research_agent.main import create_app
from research_agent.schemas.budget import Budget
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.registry import RunRegistry

pytestmark = pytest.mark.unit

USER = UUID("00000000-0000-0000-0000-000000000001")


class QuietOrchestrator:
    async def run(self, user_id: UUID, run_id: UUID) -> None:
        _ = (user_id, run_id)


def _app() -> tuple[object, InMemoryResearchStore, InProcessEventBus]:
    settings = Settings(api_key="test-key")  # type: ignore[arg-type]
    store = InMemoryResearchStore()
    bus = InProcessEventBus()
    app = create_app(
        settings=settings,
        store=store,
        orchestrator=QuietOrchestrator(),
        bus=bus,
        registry=RunRegistry(),
    )
    return app, store, bus


@pytest.mark.asyncio
async def test_missing_api_key_is_rejected() -> None:
    app, _store, _bus = _app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/runs")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.asyncio
async def test_create_run_and_replay_events() -> None:
    app, store, bus = _app()
    headers = {"X-API-Key": "test-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/v1/runs",
            headers=headers,
            json={"question": "Who develops the Gemini models?"},
        )
        assert created.status_code == 202
        run_id = created.json()["id"]
        record = await store.get_run(USER, UUID(run_id))
        assert record is not None
        started = await bus.publish(
            UUID(run_id),
            "run.completed",
            {
                "type": "run.completed",
                "report_available": False,
                "usage": empty_usage().model_dump(mode="json"),
            },
        )
        await store.add_event(USER, started)
        await store.update_run(USER, UUID(run_id), status="completed")
        streamed = await client.get(f"/v1/runs/{run_id}/events", headers=headers)
    assert "event: run.completed" in streamed.text
    assert f"id: {started.seq}" in streamed.text
    _ = ModelUsage
    _ = Budget
