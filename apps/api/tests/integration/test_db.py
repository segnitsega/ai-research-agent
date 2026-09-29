import pytest
from sqlalchemy import text

from research_agent.config import Settings
from research_agent.db.session import create_engine

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_database_accepts_connections() -> None:
    engine = create_engine(Settings())
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(text("select 1"))
    except OSError as exc:
        pytest.skip(f"Postgres is not running: {exc}")
    finally:
        await engine.dispose()
    assert value == 1
