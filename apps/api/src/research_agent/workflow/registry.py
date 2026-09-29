import asyncio
from uuid import UUID


class RunRegistry:
    def __init__(self, max_active_per_user: int = 2) -> None:
        self.max_active_per_user = max_active_per_user
        self.tasks: dict[UUID, asyncio.Task[None]] = {}
        self.owners: dict[UUID, UUID] = {}
        self.flags: dict[UUID, asyncio.Event] = {}

    def active_for(self, user_id: UUID) -> int:
        return sum(1 for run_id, owner in self.owners.items() if owner == user_id and run_id in self.tasks)

    def register(self, user_id: UUID, run_id: UUID, task: asyncio.Task[None]) -> None:
        self.owners[run_id] = user_id
        self.flags.setdefault(run_id, asyncio.Event())
        self.tasks[run_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(run_id, None))

    def cancel(self, run_id: UUID) -> bool:
        flag = self.flags.setdefault(run_id, asyncio.Event())
        flag.set()
        task = self.tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
            return True
        return flag.is_set()

    def is_cancelled(self, run_id: UUID) -> bool:
        flag = self.flags.get(run_id)
        return flag is not None and flag.is_set()
