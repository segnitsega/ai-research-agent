from fastapi import FastAPI

from research_agent.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.apply_provider_env()
    app = FastAPI(title="Research Agent", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/config")
    async def public_config() -> dict[str, object]:
        return settings.public_config()

    return app


app = create_app()
