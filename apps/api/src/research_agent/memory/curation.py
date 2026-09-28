import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from research_agent.db.records import StoredMemory
from research_agent.schemas.memory import CuratorOutput

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key\s*[:=]\s*\S+|secret\s*[:=]\s*\S+|password\s*[:=]\s*\S+|sk-[a-z0-9]{8,}|AIza[0-9A-Za-z\-_]{20,})")

EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


class MemoryWriter(Protocol):
    async def count_memories(self, user_id: UUID) -> int: ...

    async def create_memory(self, item: StoredMemory) -> StoredMemory: ...

    async def get_memory(self, user_id: UUID, memory_id: UUID) -> StoredMemory | None: ...

    async def update_memory(
        self,
        user_id: UUID,
        memory_id: UUID,
        *,
        content: str | None,
        importance: float | None,
        embedding: list[float] | None,
    ) -> StoredMemory | None: ...

    async def delete_memory(self, user_id: UUID, memory_id: UUID) -> bool: ...


async def apply_curator_ops(
    store: MemoryWriter,
    *,
    user_id: UUID,
    run_id: UUID,
    output: CuratorOutput,
    embed: EmbedFn,
    max_items: int,
) -> tuple[int, int, int, bool]:
    added = 0
    updated = 0
    deleted = 0
    for op in output.ops:
        if op.op == "noop" or (op.content and SECRET_PATTERN.search(op.content)):
            continue
        if op.op == "add" and op.kind is not None and op.content:
            if await store.count_memories(user_id) >= max_items:
                continue
            vector = (await embed([op.content]))[0]
            now = datetime.now(UTC)
            await store.create_memory(
                StoredMemory(
                    id=uuid4(),
                    user_id=user_id,
                    kind=op.kind.value,
                    content=op.content[:300],
                    importance=op.importance if op.importance is not None else 0.5,
                    embedding=vector,
                    source_run_id=run_id,
                    created_at=now,
                    updated_at=now,
                    last_used_at=None,
                )
            )
            added += 1
        elif op.op == "update" and op.target_id:
            target_id = UUID(op.target_id)
            if await store.get_memory(user_id, target_id) is None:
                continue
            vector = (await embed([op.content]))[0] if op.content else None
            await store.update_memory(
                user_id,
                target_id,
                content=op.content,
                importance=op.importance,
                embedding=vector,
            )
            updated += 1
        elif op.op == "delete" and op.target_id:
            if await store.delete_memory(user_id, UUID(op.target_id)):
                deleted += 1
    episode_saved = False
    if output.run_summary and not SECRET_PATTERN.search(output.run_summary):
        vector = (await embed([output.run_summary]))[0]
        now = datetime.now(UTC)
        await store.create_memory(
            StoredMemory(
                id=uuid4(),
                user_id=user_id,
                kind="episode",
                content=output.run_summary[:300],
                importance=0.4,
                embedding=vector,
                source_run_id=run_id,
                created_at=now,
                updated_at=now,
                last_used_at=None,
            )
        )
        episode_saved = True
    return added, updated, deleted, episode_saved
