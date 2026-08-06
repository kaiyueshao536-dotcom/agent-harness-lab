from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config

from super_ai.memory.database import create_memory_engine, create_memory_session_factory
from super_ai.memory.repositories import AgentTraceRepository
from super_ai.memory.trace_sqlite import SQLiteAgentTraceRepository
from super_ai.tracing import AgentTraceService


@pytest.mark.asyncio
async def test_trace_repository_orders_spans_and_enforces_owner_scope(
    migrated_database_url: str,
) -> None:
    engine = create_memory_engine(migrated_database_url)
    started_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
    try:
        repository = SQLiteAgentTraceRepository(create_memory_session_factory(engine))
        await repository.create_trace(
            owner_user_id="user-a",
            trace_id="trace-a",
            execution_type="chat",
            resource_type="chat_session",
            resource_id="session-a",
            metadata={"source": "test"},
            started_at=started_at,
        )
        await repository.create_trace(
            owner_user_id="user-b",
            trace_id="trace-b",
            execution_type="aiops",
            resource_type="diagnostic_task",
            resource_id="task-b",
            started_at=started_at,
        )
        second = await repository.create_span(
            owner_user_id="user-a",
            trace_id="trace-a",
            span_id="span-2",
            sequence=2,
            kind="tool",
            name="SearchLog",
            started_at=started_at + timedelta(milliseconds=10),
        )
        first = await repository.create_span(
            owner_user_id="user-a",
            trace_id="trace-a",
            span_id="span-1",
            sequence=1,
            kind="planner",
            name="Planner",
            started_at=started_at,
        )
        finalized_span = await repository.finalize_span(
            owner_user_id="user-a",
            trace_id="trace-a",
            span_id=second.id,
            status="succeeded",
            completed_at=started_at + timedelta(milliseconds=35),
        )
        finalized_trace = await repository.finalize_trace(
            owner_user_id="user-a",
            trace_id="trace-a",
            status="succeeded",
            summary="completed",
            completed_at=started_at + timedelta(milliseconds=50),
        )
        spans = await repository.list_spans(owner_user_id="user-a", trace_id="trace-a")
        own_traces = await repository.list_traces(
            owner_user_id="user-a", execution_type="chat", status="succeeded"
        )
        hidden = await repository.get_trace(owner_user_id="user-b", trace_id="trace-a")
    finally:
        await engine.dispose()

    assert [span.id for span in spans] == [first.id, second.id]
    assert finalized_span is not None and finalized_span.duration_ms == 25
    assert finalized_trace is not None and finalized_trace.duration_ms == 50
    assert own_traces == [finalized_trace]
    assert hidden is None


@pytest.mark.asyncio
async def test_trace_service_reuses_tool_span_and_redacts_sensitive_attributes(
    migrated_database_url: str,
) -> None:
    engine = create_memory_engine(migrated_database_url)
    try:
        repository = SQLiteAgentTraceRepository(create_memory_session_factory(engine))
        service = AgentTraceService(repository)
        context = await service.start_trace(
            owner_user_id="user-a",
            execution_type="chat",
            resource_type="chat_session",
            resource_id="session-a",
            metadata={"apiKey": "top-secret", "safe": "visible"},
        )
        started_span_id = await service.record_tool_event(
            context,
            tool_call_id="call-1",
            tool_name="SearchLog",
            status="started",
        )
        completed_span_id = await service.record_tool_event(
            context,
            tool_call_id="call-1",
            tool_name="SearchLog",
            status="completed",
        )
        await service.finalize_trace(context, status="succeeded", summary="done")
        trace = await repository.get_trace(owner_user_id="user-a", trace_id=context.trace_id)
        spans = await repository.list_spans(
            owner_user_id="user-a", trace_id=context.trace_id
        )
    finally:
        await engine.dispose()

    assert started_span_id == completed_span_id
    assert len(spans) == 1
    assert spans[0].status == "succeeded"
    assert trace is not None
    assert trace.metadata == {"apiKey": "[REDACTED]", "safe": "visible"}
    assert "top-secret" not in str(trace)


@pytest.mark.asyncio
async def test_trace_service_degrades_without_interrupting_execution() -> None:
    class FailingRepository:
        async def create_trace(self, **_kwargs: object) -> object:
            raise RuntimeError("database unavailable")

    service = AgentTraceService(cast(AgentTraceRepository, FailingRepository()))
    context = await service.start_trace(
        owner_user_id="user-a",
        execution_type="aiops",
        resource_type="diagnostic_task",
        resource_id="task-a",
    )

    assert context.trace_id.startswith("trace_")
    assert context.enabled is False
    await service.finalize_trace(context, status="failed", error_category="RuntimeError")


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> str:
    database_path = tmp_path / "agent-traces.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    return f"sqlite+aiosqlite:///{database_path}"
