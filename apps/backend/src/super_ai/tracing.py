"""Unified, failure-tolerant Agent trace lifecycle service."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Final, cast
from uuid import uuid4

from super_ai.memory.repositories import AgentTraceRepository, JsonDict
from super_ai.observability import emit_event

logger = logging.getLogger(__name__)

TRACE_STATUSES: Final = frozenset({"running", "succeeded", "failed"})
SPAN_KINDS: Final = frozenset(
    {"agent", "planner", "executor", "replanner", "tool", "retrieval", "model", "report"}
)
_SENSITIVE_KEYS: Final = frozenset(
    {"apikey", "api_key", "authorization", "credential", "password", "secret", "token"}
)


@dataclass(slots=True)
class AgentTraceContext:
    """Mutable execution-local state for one Agent trace."""

    trace_id: str
    owner_user_id: str
    execution_type: str
    resource_type: str
    resource_id: str
    enabled: bool = True
    next_sequence: int = 1
    tool_span_ids: dict[str, str] = field(default_factory=lambda: _new_tool_span_ids())


class AgentTraceService:
    """Create and finalize traces without making observability a business dependency."""

    def __init__(self, repository: AgentTraceRepository | None) -> None:
        self._repository = repository

    async def start_trace(
        self,
        *,
        owner_user_id: str,
        execution_type: str,
        resource_type: str,
        resource_id: str,
        request_id: str | None = None,
        metadata: JsonDict | None = None,
    ) -> AgentTraceContext:
        context = AgentTraceContext(
            trace_id=f"trace_{uuid4().hex}",
            owner_user_id=owner_user_id,
            execution_type=execution_type,
            resource_type=resource_type,
            resource_id=resource_id,
            enabled=self._repository is not None,
        )
        if self._repository is None:
            return context
        try:
            await self._repository.create_trace(
                owner_user_id=owner_user_id,
                trace_id=context.trace_id,
                execution_type=execution_type,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                metadata=sanitize_trace_attributes(metadata or {}),
            )
        except Exception as exc:
            context.enabled = False
            emit_event(
                logger,
                "agent.trace.write_failed",
                traceId=context.trace_id,
                executionType=execution_type,
                resourceType=resource_type,
                resourceId=resource_id,
                errorCategory=exc.__class__.__name__,
            )
        return context

    async def start_span(
        self,
        context: AgentTraceContext,
        *,
        kind: str,
        name: str,
        parent_span_id: str | None = None,
        external_id: str | None = None,
        attributes: JsonDict | None = None,
    ) -> str:
        span_id = f"span_{uuid4().hex}"
        sequence = context.next_sequence
        context.next_sequence += 1
        if not context.enabled or self._repository is None:
            return span_id
        try:
            await self._repository.create_span(
                owner_user_id=context.owner_user_id,
                trace_id=context.trace_id,
                span_id=span_id,
                sequence=sequence,
                kind=kind if kind in SPAN_KINDS else "agent",
                name=_safe_text(name, limit=160) or "agent.stage",
                parent_span_id=parent_span_id,
                external_id=_safe_text(external_id, limit=160),
                attributes=sanitize_trace_attributes(attributes or {}),
            )
        except Exception as exc:
            self._log_write_failure(context, exc)
        return span_id

    async def finalize_span(
        self,
        context: AgentTraceContext,
        *,
        span_id: str,
        status: str,
        summary: str | None = None,
        attributes: JsonDict | None = None,
    ) -> None:
        if not context.enabled or self._repository is None:
            return
        try:
            await self._repository.finalize_span(
                owner_user_id=context.owner_user_id,
                trace_id=context.trace_id,
                span_id=span_id,
                status=_terminal_status(status),
                summary=_safe_text(summary),
                attributes=(
                    sanitize_trace_attributes(attributes) if attributes is not None else None
                ),
            )
        except Exception as exc:
            self._log_write_failure(context, exc)

    async def finalize_trace(
        self,
        context: AgentTraceContext,
        *,
        status: str,
        summary: str | None = None,
        error_category: str | None = None,
    ) -> None:
        if not context.enabled or self._repository is None:
            return
        try:
            await self._repository.finalize_trace(
                owner_user_id=context.owner_user_id,
                trace_id=context.trace_id,
                status=_terminal_status(status),
                summary=_safe_text(summary),
                error_category=_safe_text(error_category, limit=160),
            )
        except Exception as exc:
            self._log_write_failure(context, exc)

    async def record_tool_event(
        self,
        context: AgentTraceContext,
        *,
        tool_call_id: str,
        tool_name: str,
        status: str,
    ) -> str:
        span_id = context.tool_span_ids.get(tool_call_id)
        if span_id is None:
            span_id = await self.start_span(
                context,
                kind="tool",
                name=tool_name,
                external_id=tool_call_id,
                attributes={"toolCallId": tool_call_id, "toolName": tool_name},
            )
            context.tool_span_ids[tool_call_id] = span_id
        if status in {"completed", "failed"}:
            await self.finalize_span(
                context,
                span_id=span_id,
                status="succeeded" if status == "completed" else "failed",
                summary=f"Tool {status}",
                attributes={"toolCallId": tool_call_id, "toolName": tool_name},
            )
        return span_id

    def _log_write_failure(self, context: AgentTraceContext, exc: Exception) -> None:
        emit_event(
            logger,
            "agent.trace.write_failed",
            traceId=context.trace_id,
            executionType=context.execution_type,
            resourceType=context.resource_type,
            resourceId=context.resource_id,
            errorCategory=exc.__class__.__name__,
        )


def sanitize_trace_attributes(value: JsonDict) -> JsonDict:
    """Return a bounded JSON dictionary with secret-bearing keys redacted."""

    return {str(key)[:120]: _sanitize_value(str(key), item) for key, item in value.items()}


def _sanitize_value(key: str, value: object) -> object:
    if key.casefold().replace("-", "_") in _SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        items = cast(dict[object, object], value)
        return sanitize_trace_attributes({str(k): v for k, v in items.items()})
    if isinstance(value, list):
        items_list = cast(list[object], value)
        return [_sanitize_value("item", item) for item in items_list[:20]]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return _safe_text(str(value)) or ""


def _safe_text(value: str | None, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized[:limit] if normalized else None


def _terminal_status(status: str) -> str:
    return status if status in {"succeeded", "failed"} else "failed"


def _new_tool_span_ids() -> dict[str, str]:
    return {}
