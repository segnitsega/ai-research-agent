import pytest
from httpx import ASGITransport, AsyncClient

from research_agent.main import create_app


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_healthz() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_public_config_uses_gemini() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/config")
    models = response.json()["models"]
    assert models["planner"].startswith("google-gla:")
    assert "openai" not in models["planner"]
    assert "api_key" not in response.text.lower() or "google" in models["planner"]
