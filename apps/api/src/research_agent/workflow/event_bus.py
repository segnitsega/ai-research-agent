import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from research_agent.schemas.enums import AgentName
from research_agent.schemas.run_state import RunEvent
from research_agent.workflow.events import EVENT_TYPES, agent_for_event_type


class EventBus(Protocol):
    async def publish(
        self,
        run_id: UUID,
        event_type: str,
        data: dict[str, Any],
        *,
        agent: AgentName | None = None,
    ) -> RunEvent: ...

    async def subscribe(self, run_id: UUID) -> AsyncIterator[RunEvent]: ...


PersistHook = Callable[[RunEvent], Coroutine[Any, Any, None]]


class InProcessEventBus:
    def __init__(self) -> None:
        self._channels: dict[UUID, asyncio.Queue[RunEvent | None]] = defaultdict(asyncio.Queue)
        self._seq: dict[UUID, int] = defaultdict(int)
        self._persist_hooks: list[PersistHook] = []

    def add_persist_hook(self, hook: PersistHook) -> None:
        self._persist_hooks.append(hook)

    async def publish(
        self,
        run_id: UUID,
        event_type: str,
        data: dict[str, Any],
        *,
        agent: AgentName | None = None,
    ) -> RunEvent:
        self._seq[run_id] += 1
        event = RunEvent(
            seq=self._seq[run_id],
            run_id=str(run_id),
            ts=datetime.now(UTC),
            type=event_type,
            agent=agent or agent_for_event_type(event_type),
            data=data,
        )
        model = EVENT_TYPES.get(event_type)
        if model is not None:
            model.model_validate(data)
        for hook in self._persist_hooks:
            await hook(event)
        await self._channels[run_id].put(event)
        return event

    async def subscribe(self, run_id: UUID) -> AsyncIterator[RunEvent]:
        queue = self._channels[run_id]
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    async def close(self, run_id: UUID) -> None:
        await self._channels[run_id].put(None)
