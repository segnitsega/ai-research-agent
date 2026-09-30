import json
from pathlib import Path

from research_agent.config import Settings
from research_agent.db.memory_store import InMemoryResearchStore
from research_agent.main import create_app
from research_agent.workflow.event_bus import InProcessEventBus
from research_agent.workflow.registry import RunRegistry


class Idle:
    async def run(self, user_id: object, run_id: object) -> None:
        _ = (user_id, run_id)


def main() -> None:
    app = create_app(
        settings=Settings(),
        store=InMemoryResearchStore(),
        orchestrator=Idle(),
        bus=InProcessEventBus(),
        registry=RunRegistry(),
    )
    target = Path(__file__).resolve().parents[1] / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
