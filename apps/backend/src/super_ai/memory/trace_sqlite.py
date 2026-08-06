"""SQLite persistence for tenant-scoped Agent traces."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from super_ai.memory.models import AgentTraceModel, AgentTraceSpanModel, utc_now
from super_ai.memory.repositories import AgentTraceRecord, AgentTraceSpanRecord, JsonDict


class SQLiteAgentTraceRepository:
    """Store Agent traces with owner-scoped reads and writes."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_trace(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
        execution_type: str,
        resource_type: str,
        resource_id: str,
        request_id: str | None = None,
        metadata: JsonDict | None = None,
        started_at: datetime | None = None,
    ) -> AgentTraceRecord:
        timestamp = started_at or utc_now()
        row = AgentTraceModel(
            id=trace_id,
            owner_user_id=owner_user_id,
            execution_type=execution_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            status="running",
            summary=None,
            error_category=None,
            metadata_json=metadata or {},
            started_at=timestamp,
            completed_at=None,
            duration_ms=None,
            created_at=timestamp,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return _trace_record(row)

    async def finalize_trace(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
        status: str,
        summary: str | None = None,
        error_category: str | None = None,
        completed_at: datetime | None = None,
    ) -> AgentTraceRecord | None:
        timestamp = completed_at or utc_now()
        async with self._session_factory() as session:
            row = await session.scalar(
                select(AgentTraceModel).where(
                    AgentTraceModel.id == trace_id,
                    AgentTraceModel.owner_user_id == owner_user_id,
                )
            )
            if row is None:
                return None
            row.status = status
            row.summary = summary
            row.error_category = error_category
            row.completed_at = timestamp
            row.duration_ms = _duration_ms(row.started_at, timestamp)
            await session.commit()
        return _trace_record(row)

    async def create_span(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
        span_id: str,
        sequence: int,
        kind: str,
        name: str,
        parent_span_id: str | None = None,
        external_id: str | None = None,
        attributes: JsonDict | None = None,
        started_at: datetime | None = None,
    ) -> AgentTraceSpanRecord:
        timestamp = started_at or utc_now()
        async with self._session_factory() as session:
            trace = await session.scalar(
                select(AgentTraceModel).where(
                    AgentTraceModel.id == trace_id,
                    AgentTraceModel.owner_user_id == owner_user_id,
                )
            )
            if trace is None:
                raise ValueError("Owned Agent trace does not exist.")
            row = AgentTraceSpanModel(
                id=span_id,
                owner_user_id=owner_user_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                external_id=external_id,
                sequence=sequence,
                kind=kind,
                name=name,
                status="running",
                summary=None,
                attributes=attributes or {},
                started_at=timestamp,
                completed_at=None,
                duration_ms=None,
                created_at=timestamp,
            )
            session.add(row)
            await session.commit()
        return _span_record(row)

    async def finalize_span(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
        span_id: str,
        status: str,
        summary: str | None = None,
        attributes: JsonDict | None = None,
        completed_at: datetime | None = None,
    ) -> AgentTraceSpanRecord | None:
        timestamp = completed_at or utc_now()
        async with self._session_factory() as session:
            row = await session.scalar(
                select(AgentTraceSpanModel).where(
                    AgentTraceSpanModel.id == span_id,
                    AgentTraceSpanModel.trace_id == trace_id,
                    AgentTraceSpanModel.owner_user_id == owner_user_id,
                )
            )
            if row is None:
                return None
            row.status = status
            row.summary = summary
            if attributes is not None:
                row.attributes = attributes
            row.completed_at = timestamp
            row.duration_ms = _duration_ms(row.started_at, timestamp)
            await session.commit()
        return _span_record(row)

    async def get_trace(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
    ) -> AgentTraceRecord | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(AgentTraceModel).where(
                    AgentTraceModel.id == trace_id,
                    AgentTraceModel.owner_user_id == owner_user_id,
                )
            )
        return _trace_record(row) if row is not None else None

    async def list_traces(
        self,
        *,
        owner_user_id: str,
        execution_type: str | None = None,
        status: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        limit: int = 50,
    ) -> list[AgentTraceRecord]:
        stmt = select(AgentTraceModel).where(AgentTraceModel.owner_user_id == owner_user_id)
        if execution_type is not None:
            stmt = stmt.where(AgentTraceModel.execution_type == execution_type)
        if status is not None:
            stmt = stmt.where(AgentTraceModel.status == status)
        if resource_type is not None:
            stmt = stmt.where(AgentTraceModel.resource_type == resource_type)
        if resource_id is not None:
            stmt = stmt.where(AgentTraceModel.resource_id == resource_id)
        stmt = stmt.order_by(AgentTraceModel.started_at.desc(), AgentTraceModel.id.desc()).limit(
            max(1, min(limit, 100))
        )
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_trace_record(row) for row in rows]

    async def list_spans(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
    ) -> list[AgentTraceSpanRecord]:
        stmt = (
            select(AgentTraceSpanModel)
            .where(
                AgentTraceSpanModel.owner_user_id == owner_user_id,
                AgentTraceSpanModel.trace_id == trace_id,
            )
            .order_by(AgentTraceSpanModel.sequence.asc(), AgentTraceSpanModel.id.asc())
        )
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_span_record(row) for row in rows]


def _trace_record(row: AgentTraceModel) -> AgentTraceRecord:
    return AgentTraceRecord(
        id=row.id,
        owner_user_id=row.owner_user_id,
        execution_type=row.execution_type,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        request_id=row.request_id,
        status=row.status,
        summary=row.summary,
        error_category=row.error_category,
        metadata=dict(row.metadata_json),
        started_at=_ensure_utc(row.started_at),
        completed_at=_ensure_utc_optional(row.completed_at),
        duration_ms=row.duration_ms,
        created_at=_ensure_utc(row.created_at),
    )


def _span_record(row: AgentTraceSpanModel) -> AgentTraceSpanRecord:
    return AgentTraceSpanRecord(
        id=row.id,
        owner_user_id=row.owner_user_id,
        trace_id=row.trace_id,
        parent_span_id=row.parent_span_id,
        external_id=row.external_id,
        sequence=row.sequence,
        kind=row.kind,
        name=row.name,
        status=row.status,
        summary=row.summary,
        attributes=dict(row.attributes),
        started_at=_ensure_utc(row.started_at),
        completed_at=_ensure_utc_optional(row.completed_at),
        duration_ms=row.duration_ms,
        created_at=_ensure_utc(row.created_at),
    )


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((_ensure_utc(completed_at) - _ensure_utc(started_at)).total_seconds() * 1000))


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ensure_utc_optional(value: datetime | None) -> datetime | None:
    return _ensure_utc(value) if value is not None else None
