import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    question: Mapped[str] = mapped_column(Text)
    depth: Mapped[str] = mapped_column(Text)
    use_memory: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(Text)
    phase: Mapped[str | None] = mapped_column(Text)
    budget: Mapped[dict[str, Any]] = mapped_column(JSONB)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    error: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, default="en")
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("runs_user_created", "user_id", created_at.desc()),)


class RunEventRow(Base):
    __tablename__ = "run_events"

    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    type: Mapped[str] = mapped_column(Text)
    agent: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_type: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("canonical_url", "content_hash"),
        Index("sources_url", "canonical_url", fetched_at.desc()),
    )


class RunSourceRow(Base):
    __tablename__ = "run_sources"

    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sources.id"), primary_key=True
    )
    sub_question_id: Mapped[str] = mapped_column(Text, primary_key=True)
    rank: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    from_cache: Mapped[bool] = mapped_column(default=False)


class SourceChunkRow(Base):
    __tablename__ = "source_chunks"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))

    __table_args__ = (UniqueConstraint("source_id", "chunk_index"),)


class FindingRow(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sources.id"))
    sub_question_id: Mapped[str] = mapped_column(Text)
    claim: Mapped[str] = mapped_column(Text)
    evidence_quote: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column()
    stance: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    from_memory: Mapped[bool] = mapped_column(default=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("findings_run", "run_id"),)


class MemoryRow(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(default=0.5)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "memories_user_kind",
            "user_id",
            "kind",
            postgresql_where=(deleted_at.is_(None)),
        ),
    )


class FeedbackRow(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE")
    )
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    flagged_finding_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="feedback_rating_check"),)
