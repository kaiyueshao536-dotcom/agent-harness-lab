from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict, cast

import httpx
import pytest
from alembic import command
from alembic.config import Config

from super_ai.api.app import create_app
from super_ai.memory.database import create_memory_engine, create_memory_session_factory
from super_ai.memory.trace_sqlite import SQLiteAgentTraceRepository


class _RegisteredUser(TypedDict):
    id: str


class _Registration(TypedDict):
    user: _RegisteredUser
    accessToken: str


@pytest.mark.asyncio
async def test_agent_trace_api_filters_orders_and_enforces_owner_scope(
    migrated_database_url: str,
) -> None:
    transport = httpx.ASGITransport(app=create_app(database_url=migrated_database_url))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        owner = await _register(client, "trace-owner@example.com", "Trace Owner")
        other = await _register(client, "trace-other@example.com", "Trace Other")

        engine = create_memory_engine(migrated_database_url)
        try:
            repository = SQLiteAgentTraceRepository(create_memory_session_factory(engine))
            started_at = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
            await repository.create_trace(
                owner_user_id=owner["user"]["id"],
                trace_id="trace_owner_chat",
                execution_type="chat",
                resource_type="chat_session",
                resource_id="session_owner",
                request_id="req_owner",
                metadata={"eventCount": 3},
                started_at=started_at,
            )
            await repository.create_span(
                owner_user_id=owner["user"]["id"],
                trace_id="trace_owner_chat",
                span_id="span_owner_2",
                sequence=2,
                kind="tool",
                name="knowledge_retrieval",
                started_at=started_at + timedelta(milliseconds=10),
            )
            await repository.create_span(
                owner_user_id=owner["user"]["id"],
                trace_id="trace_owner_chat",
                span_id="span_owner_1",
                sequence=1,
                kind="agent",
                name="chat.agent",
                started_at=started_at,
            )
            await repository.finalize_trace(
                owner_user_id=owner["user"]["id"],
                trace_id="trace_owner_chat",
                status="succeeded",
                summary="Chat completed",
                completed_at=started_at + timedelta(milliseconds=50),
            )
            await repository.create_trace(
                owner_user_id=other["user"]["id"],
                trace_id="trace_other_aiops",
                execution_type="aiops",
                resource_type="diagnostic_task",
                resource_id="diagnostic_other",
                started_at=started_at,
            )
        finally:
            await engine.dispose()

        anonymous = await client.get("/agent-traces")
        owner_list = await client.get(
            "/agent-traces?executionType=chat&status=succeeded&resourceId=session_owner",
            headers=_auth_headers(owner["accessToken"]),
        )
        owner_detail = await client.get(
            "/agent-traces/trace_owner_chat",
            headers=_auth_headers(owner["accessToken"]),
        )
        hidden_detail = await client.get(
            "/agent-traces/trace_owner_chat",
            headers=_auth_headers(other["accessToken"]),
        )

    assert anonymous.status_code == 401
    assert owner_list.status_code == 200
    assert [item["id"] for item in owner_list.json()["data"]["items"]] == [
        "trace_owner_chat"
    ]
    detail = owner_detail.json()["data"]
    assert owner_detail.status_code == 200
    assert detail["trace"] == {
        "id": "trace_owner_chat",
        "executionType": "chat",
        "resourceType": "chat_session",
        "resourceId": "session_owner",
        "requestId": "req_owner",
        "status": "succeeded",
        "summary": "Chat completed",
        "errorCategory": None,
        "metadata": {"eventCount": 3},
        "startedAt": "2026-08-06T12:00:00+00:00",
        "completedAt": "2026-08-06T12:00:00.050000+00:00",
        "durationMs": 50,
    }
    assert [span["id"] for span in detail["spans"]] == ["span_owner_1", "span_owner_2"]
    assert hidden_detail.status_code == 404
    assert hidden_detail.json()["error"]["code"] == "BUSINESS_NOT_FOUND"


async def _register(
    client: httpx.AsyncClient,
    email: str,
    display_name: str,
) -> _Registration:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "displayName": display_name,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return cast(_Registration, response.json()["data"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> str:
    database_path = tmp_path / "agent-trace-api.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    return f"sqlite+aiosqlite:///{database_path}"
