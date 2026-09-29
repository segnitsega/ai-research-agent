import asyncio
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from research_agent.composition import build_runtime
from research_agent.config import get_settings
from research_agent.schemas.enums import Depth

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def run(question: str, depth: Depth = Depth.QUICK) -> None:
    asyncio.run(_run(question, depth))


async def _run(question: str, depth: Depth) -> None:
    settings = get_settings()
    settings.apply_provider_env()
    if settings.resolved_google_api_key() is None:
        console.print("Set GOOGLE_API_KEY or GEMINI_API_KEY before starting a run.")
        raise typer.Exit(code=1)
    store, bus, registry, orchestrator = build_runtime(settings)
    user_id = UUID(settings.seeded_user_id)
    budget = settings.resolve_budget(depth, None)
    record = await store.create_run(
        user_id=user_id,
        question=question,
        depth=depth.value,
        use_memory=True,
        budget=budget,
        language="en",
        idempotency_key=None,
    )
    task = asyncio.create_task(orchestrator.run(user_id, record.id))
    registry.register(user_id, record.id, task)
    table = Table(title="Research events")
    table.add_column("seq")
    table.add_column("type")
    async for event in bus.subscribe(record.id):
        table.add_row(str(event.seq), event.type)
        console.print(f"{event.seq:>4}  {event.type}")
        if event.type in {"run.completed", "run.failed", "run.cancelled"}:
            break
    await task
    finished = await store.get_run(user_id, record.id)
    if finished and finished.report is not None:
        console.print(finished.report.model_dump_json(indent=2))
    elif finished and finished.error:
        console.print(finished.error)


if __name__ == "__main__":
    app()
