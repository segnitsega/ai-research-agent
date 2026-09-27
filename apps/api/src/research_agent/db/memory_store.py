import base64
import math
from datetime import UTC, datetime
from uuid import UUID, uuid4

from research_agent.db.records import RunRecord, SourceRecord, StoredFeedback, StoredFinding, StoredMemory
from research_agent.schemas.agents import Finding
from research_agent.schemas.budget import Budget
from research_agent.schemas.enums import FindingStatus
from research_agent.schemas.run_state import RunEvent, RunState, RunUsage


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


class InMemoryResearchStore:
    def __init__(self) -> None:
        self.runs: dict[UUID, RunRecord] = {}
        self.events: dict[UUID, list[RunEvent]] = {}
        self.sources: dict[UUID, SourceRecord] = {}
        self.run_sources: list[tuple[UUID, UUID, str]] = []
        self.findings: list[StoredFinding] = []
        self.memories: list[StoredMemory] = []
        self.feedback: list[StoredFeedback] = []
        self.source_chunks: list[tuple[UUID, UUID, int, str, list[float]]] = []

    async def create_run(
        self,
        *,
        user_id: UUID,
        question: str,
        depth: str,
        use_memory: bool,
        budget: Budget,
        language: str,
        idempotency_key: str | None,
    ) -> RunRecord:
        now = datetime.now(UTC)
        record = RunRecord(
            id=uuid4(),
            user_id=user_id,
            question=question,
            depth=depth,
            use_memory=use_memory,
            status="queued",
            phase=None,
            budget=budget,
            state=RunState(),
            plan=None,
            report=None,
            usage=RunUsage(
                requests=0,
                input_tokens=0,
                output_tokens=0,
                fetches=0,
                cost_usd=0.0,
                by_agent={},
            ),
            error=None,
            language=language,
            created_at=now,
            started_at=None,
            finished_at=None,
            idempotency_key=idempotency_key,
        )
        self.runs[record.id] = record
        self.events[record.id] = []
        return record

    async def find_idempotent(self, user_id: UUID, key: str) -> RunRecord | None:
        for record in self.runs.values():
            if record.user_id == user_id and record.idempotency_key == key:
                return self._with_counts(record)
        return None

    async def get_run(self, user_id: UUID, run_id: UUID) -> RunRecord | None:
        record = self.runs.get(run_id)
        if record is None or record.user_id != user_id:
            return None
        return self._with_counts(record)

    async def list_runs(
        self,
        user_id: UUID,
        *,
        status: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[RunRecord], str | None]:
        rows = [self._with_counts(row) for row in self.runs.values() if row.user_id == user_id]
        if status:
            rows = [row for row in rows if row.status == status]
        rows.sort(key=lambda row: (row.created_at, str(row.id)), reverse=True)
        if cursor:
            marker = base64.urlsafe_b64decode(cursor.encode()).decode()
            rows = [row for row in rows if f"{row.created_at.isoformat()}|{row.id}" < marker]
        page = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page:
            last = page[-1]
            token = f"{last.created_at.isoformat()}|{last.id}"
            next_cursor = base64.urlsafe_b64encode(token.encode()).decode()
        return page, next_cursor

    async def update_run(self, user_id: UUID, run_id: UUID, **changes: object) -> None:
        record = await self.get_run(user_id, run_id)
        if record is None:
            return
        for key, value in changes.items():
            setattr(record, key, value)

    async def delete_run(self, user_id: UUID, run_id: UUID) -> bool:
        record = await self.get_run(user_id, run_id)
        if record is None:
            return False
        self.runs.pop(run_id, None)
        self.events.pop(run_id, None)
        self.findings = [item for item in self.findings if item.finding.run_id != str(run_id)]
        self.run_sources = [item for item in self.run_sources if item[0] != run_id]
        return True

    async def add_event(self, user_id: UUID, event: RunEvent) -> None:
        record = await self.get_run(user_id, UUID(event.run_id))
        if record is None:
            return
        self.events[record.id].append(event)

    async def list_events(self, user_id: UUID, run_id: UUID, after: int) -> list[RunEvent]:
        if await self.get_run(user_id, run_id) is None:
            return []
        return [event for event in self.events.get(run_id, []) if event.seq > after]

    async def max_seq(self, user_id: UUID, run_id: UUID) -> int:
        events = await self.list_events(user_id, run_id, 0)
        if not events:
            return 0
        return max(event.seq for event in events)

    async def find_source(self, canonical_url: str, content_hash: str) -> SourceRecord | None:
        for source in self.sources.values():
            if source.canonical_url == canonical_url and source.content_hash == content_hash:
                return source
        return None

    async def latest_source(self, canonical_url: str) -> SourceRecord | None:
        matches = [source for source in self.sources.values() if source.canonical_url == canonical_url]
        if not matches:
            return None
        return max(matches, key=lambda source: source.fetched_at)

    async def save_source(self, source: SourceRecord) -> None:
        self.sources[source.id] = source

    async def link_source(self, run_id: UUID, source_id: UUID, sub_question_id: str) -> None:
        key = (run_id, source_id, sub_question_id)
        if key not in self.run_sources:
            self.run_sources.append(key)

    async def list_sources(self, user_id: UUID, run_id: UUID) -> list[SourceRecord]:
        if await self.get_run(user_id, run_id) is None:
            return []
        ids = [item[1] for item in self.run_sources if item[0] == run_id]
        return [self.sources[item] for item in ids if item in self.sources]

    async def add_finding(self, item: StoredFinding) -> None:
        self.findings.append(item)

    async def list_findings(
        self,
        user_id: UUID,
        run_id: UUID,
        *,
        status: str | None = None,
        sub_question_id: str | None = None,
    ) -> list[Finding]:
        if await self.get_run(user_id, run_id) is None:
            return []
        rows = [item.finding for item in self.findings if item.user_id == user_id and item.finding.run_id == str(run_id)]
        if status:
            rows = [row for row in rows if row.status == status]
        if sub_question_id:
            rows = [row for row in rows if row.sub_question_id == sub_question_id]
        return rows

    async def flag_findings(self, user_id: UUID, run_id: UUID, finding_ids: list[UUID]) -> None:
        wanted = {str(item) for item in finding_ids}
        updated: list[StoredFinding] = []
        for item in self.findings:
            if item.user_id == user_id and item.finding.id in wanted:
                updated.append(
                    StoredFinding(
                        finding=item.finding.model_copy(update={"status": FindingStatus.FLAGGED}),
                        user_id=item.user_id,
                        embedding=item.embedding,
                    )
                )
            else:
                updated.append(item)
        self.findings = updated

    async def add_feedback(self, item: StoredFeedback) -> None:
        self.feedback.append(item)

    async def create_memory(self, item: StoredMemory) -> StoredMemory:
        self.memories.append(item)
        return item

    async def list_memories(
        self,
        user_id: UUID,
        *,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[StoredMemory], str | None]:
        rows = [item for item in self.memories if item.user_id == user_id and item.deleted_at is None]
        if kind:
            rows = [item for item in rows if item.kind == kind]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        start = int(cursor) if cursor else 0
        page = rows[start : start + limit]
        next_cursor = str(start + limit) if start + limit < len(rows) else None
        return page, next_cursor

    async def get_memory(self, user_id: UUID, memory_id: UUID) -> StoredMemory | None:
        for item in self.memories:
            if item.id == memory_id and item.user_id == user_id and item.deleted_at is None:
                return item
        return None

    async def update_memory(
        self,
        user_id: UUID,
        memory_id: UUID,
        *,
        content: str | None,
        importance: float | None,
        embedding: list[float] | None,
    ) -> StoredMemory | None:
        item = await self.get_memory(user_id, memory_id)
        if item is None:
            return None
        if content is not None:
            item.content = content
        if importance is not None:
            item.importance = importance
        if embedding is not None:
            item.embedding = embedding
        item.updated_at = datetime.now(UTC)
        return item

    async def delete_memory(self, user_id: UUID, memory_id: UUID) -> bool:
        item = await self.get_memory(user_id, memory_id)
        if item is None:
            return False
        item.deleted_at = datetime.now(UTC)
        return True

    async def forget_all(self, user_id: UUID) -> int:
        count = 0
        now = datetime.now(UTC)
        for item in self.memories:
            if item.user_id == user_id and item.deleted_at is None:
                item.deleted_at = now
                count += 1
        return count

    async def search_memories(self, user_id: UUID, query: str, embedding: list[float], limit: int) -> list[StoredMemory]:
        rows: list[StoredMemory] = []
        for item in self.memories:
            if item.user_id != user_id or item.deleted_at is not None:
                continue
            similarity = 1.0 if query.casefold() in item.content.casefold() else _cosine(item.embedding, embedding)
            if similarity <= 0:
                continue
            item.similarity = similarity
            rows.append(item)
        rows.sort(key=lambda item: item.similarity, reverse=True)
        return rows[:limit]

    async def count_memories(self, user_id: UUID) -> int:
        return len([item for item in self.memories if item.user_id == user_id and item.deleted_at is None])

    async def save_chunks(self, source_id: UUID, chunks: list[tuple[int, str, list[float]]]) -> None:
        self.source_chunks = [item for item in self.source_chunks if item[1] != source_id]
        for index, text, embedding in chunks:
            self.source_chunks.append((uuid4(), source_id, index, text, embedding))

    def _with_counts(self, record: RunRecord) -> RunRecord:
        record.accepted_findings = len([item for item in self.findings if item.finding.run_id == str(record.id) and item.finding.status == FindingStatus.ACCEPTED])
        record.sources_used = len({item[1] for item in self.run_sources if item[0] == record.id})
        return record


def empty_usage() -> RunUsage:
    return RunUsage(
        requests=0,
        input_tokens=0,
        output_tokens=0,
        fetches=0,
        cost_usd=0.0,
        by_agent={},
    )


def normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / length for value in vector]
