import pytest

from research_agent.config import Settings

pytestmark = pytest.mark.unit


def test_normalizes_render_postgres_url_to_asyncpg_with_ssl() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:pass@dpg-abc-a/db",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://user:pass@dpg-abc-a/db")
    assert settings.database_url.endswith("?ssl=require")


def test_leaves_asyncpg_local_url_alone() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://research:research@localhost:5433/research",
    )
    assert settings.database_url == "postgresql+asyncpg://research:research@localhost:5433/research"
