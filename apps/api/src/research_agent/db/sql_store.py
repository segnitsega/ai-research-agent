import base64
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from research_agent.db.memory_store import empty_usage
from research_agent.db.models import (
    FeedbackRow,
    FindingRow,
    MemoryRow,
    RunEventRow,
    RunRow,
    RunSourceRow,
    SourceChunkRow,
    SourceRow,
)
from research_agent.db.records import RunRecord, SourceRecord, StoredFeedback, StoredFinding, StoredMemory
from research_agent.schemas.agents import Finding, Report, ResearchPlan
from research_agent.schemas.budget import Budget
from research_agent.schemas.enums import AgentName, FindingStatus
from research_agent.schemas.run_state import RunEvent, RunState, RunUsage


class SqlResearchStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

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
        row = RunRow(
            id=uuid4(),
            user_id=user_id,
            question=question,
            depth=depth,
            use_memory=use_memory,
            status="queued",
            phase=None,
            budget=budget.model_dump(mode="json"),
            state=RunState().model_dump(mode="json"),
            plan=None,
            report=None,
            usage=empty_usage().model_dump(mode="json"),
            error=None,
            language=language,
            idempotency_key=idempotency_key,
            created_at=now,
        )
        async with self._sessions() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return await self._run(session, row)

    async def find_idempotent(self, user_id: UUID, key: str) -> RunRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(select(RunRow).where(RunRow.user_id == user_id, RunRow.idempotency_key == key))
            if row is None:
                return None
            return await self._run(session, row)

    async def get_run(self, user_id: UUID, run_id: UUID) -> RunRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(select(RunRow).where(RunRow.user_id == user_id, RunRow.id == run_id))
            if row is None:
                return None
            return await self._run(session, row)

    async def list_runs(
        self,
        user_id: UUID,
        *,
        status: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[RunRecord], str | None]:
        async with self._sessions() as session:
            stmt = select(RunRow).where(RunRow.user_id == user_id)
            if status:
                stmt = stmt.where(RunRow.status == status)
            if cursor:
                raw = base64.urlsafe_b64decode(cursor.encode()).decode()
                stamp, run_id = raw.split("|", 1)
                stmt = stmt.where(RunRow.created_at < datetime.fromisoformat(stamp))
                _ = run_id
            stmt = stmt.order_by(RunRow.created_at.desc()).limit(limit + 1)
            rows = list(await session.scalars(stmt))
            page = rows[:limit]
            records = [await self._run(session, row) for row in page]
            next_cursor = None
            if len(rows) > limit and page:
                last = page[-1]
                token = f"{last.created_at.isoformat()}|{last.id}"
                next_cursor = base64.urlsafe_b64encode(token.encode()).decode()
            return records, next_cursor

    async def update_run(self, user_id: UUID, run_id: UUID, **changes: object) -> None:
        payload: dict[str, Any] = {}
        for key, value in changes.items():
            if isinstance(value, BaseModel):
                payload[key] = value.model_dump(mode="json")
            else:
                payload[key] = value
        async with self._sessions() as session:
            await session.execute(update(RunRow).where(RunRow.user_id == user_id, RunRow.id == run_id).values(**payload))
            await session.commit()

    async def delete_run(self, user_id: UUID, run_id: UUID) -> bool:
        async with self._sessions() as session:
            row = await session.scalar(select(RunRow).where(RunRow.user_id == user_id, RunRow.id == run_id))
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def add_event(self, user_id: UUID, event: RunEvent) -> None:
        run_id = UUID(event.run_id)
        async with self._sessions() as session:
            owner = await session.scalar(select(RunRow.id).where(RunRow.user_id == user_id, RunRow.id == run_id))
            if owner is None:
                return
            session.add(
                RunEventRow(
                    run_id=run_id,
                    seq=event.seq,
                    ts=event.ts,
                    type=event.type,
                    agent=event.agent.value,
                    data=event.data,
                )
            )
            await session.commit()

    async def list_events(self, user_id: UUID, run_id: UUID, after: int) -> list[RunEvent]:
        async with self._sessions() as session:
            owner = await session.scalar(select(RunRow.id).where(RunRow.user_id == user_id, RunRow.id == run_id))
            if owner is None:
                return []
            rows = await session.scalars(select(RunEventRow).where(RunEventRow.run_id == run_id, RunEventRow.seq > after).order_by(RunEventRow.seq))
            return [
                RunEvent(
                    seq=row.seq,
                    run_id=str(row.run_id),
                    ts=row.ts,
                    type=row.type,
                    agent=AgentName(row.agent),
                    data=row.data,
                )
                for row in rows
            ]

    async def max_seq(self, user_id: UUID, run_id: UUID) -> int:
        events = await self.list_events(user_id, run_id, 0)
        if not events:
            return 0
        return max(event.seq for event in events)

    async def find_source(self, canonical_url: str, content_hash: str) -> SourceRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(SourceRow).where(
                    SourceRow.canonical_url == canonical_url,
                    SourceRow.content_hash == content_hash,
                )
            )
            return None if row is None else _source(row, "", "fetched", None, False)

    async def latest_source(self, canonical_url: str) -> SourceRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(select(SourceRow).where(SourceRow.canonical_url == canonical_url).order_by(SourceRow.fetched_at.desc()))
            return None if row is None else _source(row, "", "fetched", None, True)

    async def save_source(self, source: SourceRecord) -> UUID:
        async with self._sessions() as session:
            existing = await session.scalar(
                select(SourceRow).where(
                    SourceRow.canonical_url == source.canonical_url,
                    SourceRow.content_hash == source.content_hash,
                )
            )
            if existing is not None:
                return existing.id
            session.add(
                SourceRow(
                    id=source.id,
                    canonical_url=source.canonical_url,
                    content_hash=source.content_hash,
                    title=source.title,
                    domain=source.domain,
                    text=source.text,
                    published_at=source.published_at,
                    fetched_at=source.fetched_at,
                    content_type=source.content_type,
                )
            )
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raced = await session.scalar(
                    select(SourceRow).where(
                        SourceRow.canonical_url == source.canonical_url,
                        SourceRow.content_hash == source.content_hash,
                    )
                )
                if raced is not None:
                    return raced.id
                raise
            return source.id

    async def link_source(self, run_id: UUID, source_id: UUID, sub_question_id: str) -> None:
        async with self._sessions() as session:
            existing = await session.scalar(
                select(RunSourceRow).where(
                    RunSourceRow.run_id == run_id,
                    RunSourceRow.source_id == source_id,
                    RunSourceRow.sub_question_id == sub_question_id,
                )
            )
            if existing is None:
                session.add(
                    RunSourceRow(
                        run_id=run_id,
                        source_id=source_id,
                        sub_question_id=sub_question_id,
                        status="fetched",
                        from_cache=False,
                    )
                )
                await session.commit()

    async def list_sources(self, user_id: UUID, run_id: UUID) -> list[SourceRecord]:
        async with self._sessions() as session:
            owner = await session.scalar(select(RunRow.id).where(RunRow.user_id == user_id, RunRow.id == run_id))
            if owner is None:
                return []
            rows = await session.execute(select(SourceRow, RunSourceRow).join(RunSourceRow, RunSourceRow.source_id == SourceRow.id).where(RunSourceRow.run_id == run_id))
            return [_source(source, link.sub_question_id, link.status, link.error, link.from_cache) for source, link in rows]

    async def add_finding(self, item: StoredFinding) -> None:
        finding = item.finding
        async with self._sessions() as session:
            session.add(
                FindingRow(
                    id=UUID(finding.id),
                    run_id=UUID(finding.run_id),
                    user_id=item.user_id,
                    source_id=UUID(finding.source_id),
                    sub_question_id=finding.sub_question_id,
                    claim=finding.claim,
                    evidence_quote=finding.evidence_quote,
                    confidence=finding.confidence,
                    stance=finding.stance,
                    status=finding.status.value,
                    reject_reason=finding.reject_reason,
                    from_memory=finding.from_memory,
                    embedding=item.embedding,
                )
            )
            await session.commit()

    async def list_findings(
        self,
        user_id: UUID,
        run_id: UUID,
        *,
        status: str | None = None,
        sub_question_id: str | None = None,
    ) -> list[Finding]:
        async with self._sessions() as session:
            stmt = select(FindingRow).where(FindingRow.user_id == user_id, FindingRow.run_id == run_id)
            if status:
                stmt = stmt.where(FindingRow.status == status)
            if sub_question_id:
                stmt = stmt.where(FindingRow.sub_question_id == sub_question_id)
            rows = await session.scalars(stmt)
            return [_finding(row) for row in rows]

    async def flag_findings(self, user_id: UUID, run_id: UUID, finding_ids: list[UUID]) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(FindingRow)
                .where(
                    FindingRow.user_id == user_id,
                    FindingRow.run_id == run_id,
                    FindingRow.id.in_(finding_ids),
                )
                .values(status=FindingStatus.FLAGGED.value)
            )
            await session.commit()

    async def add_feedback(self, item: StoredFeedback) -> None:
        async with self._sessions() as session:
            session.add(
                FeedbackRow(
                    id=item.id,
                    run_id=item.run_id,
                    rating=item.rating,
                    comment=item.comment,
                    flagged_finding_ids=item.flagged_finding_ids,
                    created_at=item.created_at or datetime.now(UTC),
                )
            )
            await session.commit()

    async def create_memory(self, item: StoredMemory) -> StoredMemory:
        async with self._sessions() as session:
            session.add(
                MemoryRow(
                    id=item.id,
                    user_id=item.user_id,
                    kind=item.kind,
                    content=item.content,
                    importance=item.importance,
                    embedding=item.embedding,
                    source_run_id=item.source_run_id,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    last_used_at=item.last_used_at,
                )
            )
            await session.commit()
            return item

    async def list_memories(
        self,
        user_id: UUID,
        *,
        kind: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[StoredMemory], str | None]:
        async with self._sessions() as session:
            stmt = select(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.deleted_at.is_(None))
            if kind:
                stmt = stmt.where(MemoryRow.kind == kind)
            stmt = stmt.order_by(MemoryRow.created_at.desc()).limit(limit + 1)
            if cursor:
                stmt = stmt.offset(int(cursor))
            rows = list(await session.scalars(stmt))
            page = rows[:limit]
            next_cursor = str(int(cursor or 0) + limit) if len(rows) > limit else None
            return [_memory(row) for row in page], next_cursor

    async def get_memory(self, user_id: UUID, memory_id: UUID) -> StoredMemory | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(MemoryRow).where(
                    MemoryRow.user_id == user_id,
                    MemoryRow.id == memory_id,
                    MemoryRow.deleted_at.is_(None),
                )
            )
            return None if row is None else _memory(row)

    async def update_memory(
        self,
        user_id: UUID,
        memory_id: UUID,
        *,
        content: str | None,
        importance: float | None,
        embedding: list[float] | None,
    ) -> StoredMemory | None:
        values: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if content is not None:
            values["content"] = content
        if importance is not None:
            values["importance"] = importance
        if embedding is not None:
            values["embedding"] = embedding
        async with self._sessions() as session:
            await session.execute(update(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.id == memory_id, MemoryRow.deleted_at.is_(None)).values(**values))
            await session.commit()
        return await self.get_memory(user_id, memory_id)

    async def delete_memory(self, user_id: UUID, memory_id: UUID) -> bool:
        async with self._sessions() as session:
            result = await session.execute(
                update(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.id == memory_id, MemoryRow.deleted_at.is_(None)).values(deleted_at=datetime.now(UTC))
            )
            await session.commit()
            return bool(getattr(result, "rowcount", 0))

    async def forget_all(self, user_id: UUID) -> int:
        async with self._sessions() as session:
            result = await session.execute(update(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.deleted_at.is_(None)).values(deleted_at=datetime.now(UTC)))
            await session.commit()
            return int(getattr(result, "rowcount", 0) or 0)

    async def search_memories(self, user_id: UUID, query: str, embedding: list[float], limit: int) -> list[StoredMemory]:
        async with self._sessions() as session:
            distance = MemoryRow.embedding.cosine_distance(embedding)
            rows = await session.scalars(select(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.deleted_at.is_(None)).order_by(distance).limit(limit))
            found = []
            for row in rows:
                item = _memory(row)
                if query.casefold() in item.content.casefold():
                    item.similarity = 1.0
                found.append(item)
            return found

    async def count_memories(self, user_id: UUID) -> int:
        async with self._sessions() as session:
            value = await session.scalar(select(func.count()).select_from(MemoryRow).where(MemoryRow.user_id == user_id, MemoryRow.deleted_at.is_(None)))
            return int(value or 0)

    async def save_chunks(self, source_id: UUID, chunks: list[tuple[int, str, list[float]]]) -> None:
        async with self._sessions() as session:
            for index, text, embedding in chunks:
                existing = await session.scalar(
                    select(SourceChunkRow).where(
                        SourceChunkRow.source_id == source_id,
                        SourceChunkRow.chunk_index == index,
                    )
                )
                if existing is not None:
                    continue
                session.add(
                    SourceChunkRow(
                        id=uuid4(),
                        source_id=source_id,
                        chunk_index=index,
                        text=text,
                        embedding=embedding,
                    )
                )
            await session.commit()

    async def _run(self, session: AsyncSession, row: RunRow) -> RunRecord:
        accepted = await session.scalar(
            select(func.count())
            .select_from(FindingRow)
            .where(
                FindingRow.user_id == row.user_id,
                FindingRow.run_id == row.id,
                FindingRow.status == FindingStatus.ACCEPTED.value,
            )
        )
        sources = await session.scalar(select(func.count()).select_from(RunSourceRow).where(RunSourceRow.run_id == row.id))
        return RunRecord(
            id=row.id,
            user_id=row.user_id,
            question=row.question,
            depth=row.depth,
            use_memory=row.use_memory,
            status=row.status,
            phase=row.phase,
            budget=Budget.model_validate(row.budget),
            state=RunState.model_validate(row.state or {}),
            plan=None if row.plan is None else ResearchPlan.model_validate(row.plan),
            report=None if row.report is None else Report.model_validate(row.report),
            usage=RunUsage.model_validate(row.usage or empty_usage().model_dump()),
            error=row.error,
            language=row.language,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            idempotency_key=row.idempotency_key,
            accepted_findings=int(accepted or 0),
            sources_used=int(sources or 0),
        )


def _source(
    row: SourceRow,
    sub_question_id: str,
    status: str,
    error: str | None,
    from_cache: bool,
) -> SourceRecord:
    return SourceRecord(
        id=row.id,
        canonical_url=row.canonical_url,
        content_hash=row.content_hash,
        title=row.title,
        domain=row.domain,
        text=row.text,
        published_at=row.published_at,
        fetched_at=row.fetched_at,
        content_type=row.content_type,
        sub_question_id=sub_question_id,
        status=status,
        error=error,
        from_cache=from_cache,
    )


def _finding(row: FindingRow) -> Finding:
    if row.stance == "contradicts":
        stance = "contradicts"
    elif row.stance == "context":
        stance = "context"
    else:
        stance = "supports"
    return Finding(
        id=str(row.id),
        run_id=str(row.run_id),
        source_id=str(row.source_id),
        sub_question_id=row.sub_question_id,
        claim=row.claim,
        evidence_quote=row.evidence_quote,
        confidence=float(row.confidence),
        stance=stance,
        status=FindingStatus(row.status),
        reject_reason=row.reject_reason,
        from_memory=row.from_memory,
    )


def _memory(row: MemoryRow) -> StoredMemory:
    embedding = list(row.embedding) if row.embedding is not None else []
    return StoredMemory(
        id=row.id,
        user_id=row.user_id,
        kind=row.kind,
        content=row.content,
        importance=row.importance,
        embedding=embedding,
        source_run_id=row.source_run_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_used_at=row.last_used_at,
        deleted_at=row.deleted_at,
    )
