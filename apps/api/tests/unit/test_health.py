import pytest
from httpx import ASGITransport, AsyncClient

from research_agent.config import Settings
from research_agent.db.memory_store import InMemoryResearchStore
from research_agent.main import create_app
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.registry import RunRegistry

pytestmark = pytest.mark.unit


class Idle:
    async def run(self, user_id: object, run_id: object) -> None:
        _ = (user_id, run_id)


def _app() -> object:
    settings = Settings(api_key="test-key")  # type: ignore[arg-type]
    return create_app(
        settings=settings,
        store=InMemoryResearchStore(),
        orchestrator=Idle(),
        bus=InProcessEventBus(),
        registry=RunRegistry(),
    )


@pytest.mark.asyncio
async def test_healthz() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_public_config_uses_gemini() -> None:
    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/config", headers={"X-API-Key": "test-key"})
    models = response.json()["models"]
    assert models["planner"].startswith("google-gla:")
    assert "openai" not in models["planner"]
    assert "test-key" not in response.text
