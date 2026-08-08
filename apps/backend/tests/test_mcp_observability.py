from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from super_ai.mcp_client import (
    LocalMcpClient,
    McpAttemptEvent,
    McpClientError,
    McpServerConnection,
)


@dataclass(frozen=True, slots=True)
class FakeMcpContent:
    type: str
    text: str


@dataclass(frozen=True, slots=True)
class FakeMcpResult:
    isError: bool
    content: list[FakeMcpContent]


class FakeLocalMcpClient(LocalMcpClient):
    async def _run(
        self,
        operation: Callable[[Any], Awaitable[Any]],
        *,
        attempt_observer: Callable[[McpAttemptEvent], Awaitable[None]] | None = None,
    ) -> Any:
        del operation
        del attempt_observer
        return FakeMcpResult(
            isError=False,
            content=[FakeMcpContent(type="text", text="mcp-output-secret")],
        )


@pytest.mark.asyncio
async def test_mcp_tool_logs_lifecycle_without_argument_values_or_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logging.getLogger("super_ai.mcp_client").disabled = False
    caplog.set_level(logging.INFO, logger="super_ai.mcp_client")
    client = FakeLocalMcpClient("http://mcp.test/sse")

    result = await client.call_tool(
        "SearchLog",
        {"query": "query-secret", "topicId": "topic-secret"},
    )

    assert result == [{"type": "text", "text": "mcp-output-secret"}]
    events = [
        json.loads(record.message) for record in caplog.records if record.message.startswith("{")
    ]
    assert [event["event"] for event in events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert events[0]["argumentKeys"] == ["query", "topicId"]
    emitted = "\n".join(record.message for record in caplog.records)
    assert "query-secret" not in emitted
    assert "topic-secret" not in emitted
    assert "mcp-output-secret" not in emitted


class RetryingMcpClient(LocalMcpClient):
    def __init__(self) -> None:
        super().__init__(
            connections=[
                McpServerConnection(
                    name="cls",
                    url="http://mcp.test/sse",
                    retries=2,
                )
            ]
        )
        self.calls = 0

    async def _run_sse(
        self,
        connection: McpServerConnection,
        operation: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        del connection, operation
        self.calls += 1
        if self.calls < 3:
            raise TimeoutError("secret-provider-message")
        return "ok"

    async def run_with_observer(
        self,
        observer: Callable[[McpAttemptEvent], Awaitable[None]],
    ) -> Any:
        return await self._run(
            lambda session: session,
            attempt_observer=observer,
        )


class AlwaysFailingMcpClient(LocalMcpClient):
    def __init__(self) -> None:
        super().__init__(
            connections=[
                McpServerConnection(
                    name="cls",
                    url="http://mcp.test/sse",
                    retries=1,
                )
            ]
        )

    async def _run_sse(
        self,
        connection: McpServerConnection,
        operation: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        del connection, operation
        raise TimeoutError("provider-detail-must-not-be-observed")

    async def run_with_observer(
        self,
        observer: Callable[[McpAttemptEvent], Awaitable[None]],
    ) -> Any:
        return await self._run(
            lambda session: session,
            attempt_observer=observer,
        )


@pytest.mark.asyncio
async def test_mcp_attempt_observer_reports_bounded_retries_without_error_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[McpAttemptEvent] = []
    sleeps: list[float] = []

    async def observe(event: McpAttemptEvent) -> None:
        events.append(event)

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("super_ai.mcp_client.asyncio.sleep", fake_sleep)
    client = RetryingMcpClient()

    result = await client.run_with_observer(observe)

    assert result == "ok"
    assert client.calls == 3
    assert sleeps == [0.2, 0.4]
    assert [(event.attempt_number, event.status) for event in events] == [
        (1, "started"),
        (1, "failed"),
        (2, "started"),
        (2, "failed"),
        (3, "started"),
        (3, "succeeded"),
    ]
    assert events[1].error_category == "TimeoutError"
    assert "secret-provider-message" not in repr(events)


@pytest.mark.asyncio
async def test_mcp_attempt_observer_failure_does_not_change_tool_result() -> None:
    client = RetryingMcpClient()
    client.calls = 2

    async def broken_observer(event: McpAttemptEvent) -> None:
        del event
        raise RuntimeError("observer-secret")

    result = await client.run_with_observer(broken_observer)

    assert result == "ok"


@pytest.mark.asyncio
async def test_mcp_connection_stops_after_configured_attempt_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[McpAttemptEvent] = []
    client = AlwaysFailingMcpClient()

    async def observe(event: McpAttemptEvent) -> None:
        events.append(event)

    async def no_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr("super_ai.mcp_client.asyncio.sleep", no_sleep)

    with pytest.raises(McpClientError, match="MCP server unavailable"):
        await client.run_with_observer(observe)

    assert [(event.attempt_number, event.status) for event in events] == [
        (1, "started"),
        (1, "failed"),
        (2, "started"),
        (2, "failed"),
    ]
    assert all(event.error_category in {None, "TimeoutError"} for event in events)
    assert "provider-detail-must-not-be-observed" not in repr(events)
