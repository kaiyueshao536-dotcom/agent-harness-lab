"""Session-scoped, source-grounded Chat memory lifecycle."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast

from langchain_core.messages.utils import count_tokens_approximately

from super_ai.chat.memory_models import (
    MemorySnapshotValidationError,
    legacy_or_structured_snapshot,
    memory_snapshot_prompt,
    parse_memory_snapshot,
    validate_memory_snapshot,
)
from super_ai.llm import LlmProvider
from super_ai.memory.repositories import (
    ChatMessageRecord,
    ChatSessionRecord,
    MemoryRepositories,
)
from super_ai.tracing import AgentTraceContext, AgentTraceService

ChatMemoryMode = Literal["every_30_turns", "context_70_percent", "manual"]
SUPPORTED_CHAT_MEMORY_MODES: tuple[ChatMemoryMode, ...] = (
    "every_30_turns",
    "context_70_percent",
    "manual",
)
AUTO_CONTEXT_THRESHOLD_PERCENT = 70.0
HARD_CONTEXT_THRESHOLD_PERCENT = 95.0


class ChatContextLimitReached(RuntimeError):
    """Raised when the persisted candidate message exceeds the hard budget."""


class ChatMemoryPreparationError(RuntimeError):
    """A bounded memory preparation attempt failed without losing the user message."""

    def __init__(self, error_category: str) -> None:
        super().__init__(error_category)
        self.error_category = error_category


@dataclass(frozen=True, slots=True)
class PreparedChatContext:
    session: ChatSessionRecord
    messages: tuple[ChatMessageRecord, ...]
    system_prompt: str
    compacted: bool = False


class ChatMemoryService:
    """Apply a bounded, traceable memory policy without deleting history."""

    def __init__(
        self,
        *,
        repositories: MemoryRepositories,
        llm_provider: LlmProvider,
        context_window_tokens: int,
        trace_service: AgentTraceService | None = None,
        compression_timeout_seconds: float = 45.0,
        compression_max_attempts: int = 2,
    ) -> None:
        if context_window_tokens <= 0:
            raise ValueError("context_window_tokens must be positive")
        if compression_timeout_seconds <= 0:
            raise ValueError("compression_timeout_seconds must be positive")
        if compression_max_attempts <= 0:
            raise ValueError("compression_max_attempts must be positive")
        self._repositories = repositories
        self._llm_provider = llm_provider
        self._trace_service = trace_service
        self.context_window_tokens = context_window_tokens
        self.compression_timeout_seconds = compression_timeout_seconds
        self.compression_max_attempts = compression_max_attempts

    async def prepare_message(
        self,
        *,
        owner_user_id: str,
        session: ChatSessionRecord,
        history: list[ChatMessageRecord],
        system_prompt: str,
        candidate_message: ChatMessageRecord | None = None,
        content: str | None = None,
        trace_context: AgentTraceContext | None = None,
    ) -> PreparedChatContext:
        """Prepare context after the user message has already been persisted."""

        if candidate_message is None:
            if content is None:
                raise ValueError("candidate_message or content is required")
            candidate_message = ChatMessageRecord(
                id="candidate",
                owner_user_id=owner_user_id,
                session_id=session.id,
                role="user",
                content=content,
                metadata={},
                created_at=datetime.now(timezone.utc),
            )

        prepare_span_id = await self._start_span(
            trace_context,
            kind="memory",
            name="chat.memory.prepare",
            attributes={
                "messageId": candidate_message.id,
                "memoryMode": session.memory_mode,
            },
        )
        try:
            current = session
            uncompressed = history[current.compacted_message_count :]
            candidate_messages = [*uncompressed, candidate_message]
            candidate_tokens = estimate_context_tokens(
                system_prompt=system_prompt,
                memory_summary=current.memory_summary,
                messages=candidate_messages,
            )
            completed_turns = sum(
                message.role == "assistant" for message in uncompressed
            )
            should_compact = (
                current.memory_mode == "every_30_turns" and completed_turns >= 30
            ) or (
                current.memory_mode == "context_70_percent"
                and _usage_percent(candidate_tokens, self.context_window_tokens)
                >= AUTO_CONTEXT_THRESHOLD_PERCENT
            )
            compacted = False
            if should_compact and uncompressed:
                current = await self._compact_messages(
                    owner_user_id=owner_user_id,
                    session=current,
                    messages=uncompressed,
                    all_history=history,
                    system_prompt=system_prompt,
                    trace_context=trace_context,
                    parent_span_id=prepare_span_id,
                )
                compacted = True
                candidate_messages = [candidate_message]
                candidate_tokens = estimate_context_tokens(
                    system_prompt=system_prompt,
                    memory_summary=current.memory_summary,
                    messages=candidate_messages,
                )

            if (
                _usage_percent(candidate_tokens, self.context_window_tokens)
                >= HARD_CONTEXT_THRESHOLD_PERCENT
            ):
                raise ChatContextLimitReached

            updated = await self._repositories.chat.update_memory_state(
                owner_user_id=owner_user_id,
                session_id=current.id,
                context_tokens=candidate_tokens,
            )
            await self._finalize_span(
                trace_context,
                prepare_span_id,
                status="succeeded",
                summary="Chat memory context prepared",
                attributes={
                    "compacted": compacted,
                    "contextTokens": candidate_tokens,
                    "memoryVersion": current.memory_version,
                },
            )
            return PreparedChatContext(
                session=updated or current,
                messages=tuple(candidate_messages),
                system_prompt=_prompt_with_memory(
                    system_prompt,
                    current.memory_summary,
                ),
                compacted=compacted,
            )
        except Exception as exc:
            await self._finalize_span(
                trace_context,
                prepare_span_id,
                status="failed",
                summary="Chat memory preparation failed",
                attributes={"errorCategory": exc.__class__.__name__},
            )
            raise

    async def refresh_usage(
        self,
        *,
        owner_user_id: str,
        session: ChatSessionRecord,
        history: list[ChatMessageRecord],
        system_prompt: str,
    ) -> ChatSessionRecord:
        tokens = estimate_context_tokens(
            system_prompt=system_prompt,
            memory_summary=session.memory_summary,
            messages=history[session.compacted_message_count :],
        )
        updated = await self._repositories.chat.update_memory_state(
            owner_user_id=owner_user_id,
            session_id=session.id,
            context_tokens=tokens,
        )
        return updated or session

    async def set_mode(
        self,
        *,
        owner_user_id: str,
        session: ChatSessionRecord,
        mode: ChatMemoryMode,
        history: list[ChatMessageRecord],
        system_prompt: str,
        trace_context: AgentTraceContext | None = None,
    ) -> ChatSessionRecord:
        updated = await self._repositories.chat.update_memory_state(
            owner_user_id=owner_user_id,
            session_id=session.id,
            memory_mode=mode,
        )
        current = updated or session
        if mode == "manual":
            return await self.compact(
                owner_user_id=owner_user_id,
                session=current,
                history=history,
                system_prompt=system_prompt,
                trace_context=trace_context,
            )
        return await self.refresh_usage(
            owner_user_id=owner_user_id,
            session=current,
            history=history,
            system_prompt=system_prompt,
        )

    async def compact(
        self,
        *,
        owner_user_id: str,
        session: ChatSessionRecord,
        history: list[ChatMessageRecord],
        system_prompt: str,
        trace_context: AgentTraceContext | None = None,
    ) -> ChatSessionRecord:
        uncompressed = history[session.compacted_message_count :]
        if not uncompressed:
            return await self.refresh_usage(
                owner_user_id=owner_user_id,
                session=session,
                history=history,
                system_prompt=system_prompt,
            )
        return await self._compact_messages(
            owner_user_id=owner_user_id,
            session=session,
            messages=uncompressed,
            all_history=history,
            system_prompt=system_prompt,
            trace_context=trace_context,
            parent_span_id=None,
        )

    async def _compact_messages(
        self,
        *,
        owner_user_id: str,
        session: ChatSessionRecord,
        messages: list[ChatMessageRecord],
        all_history: list[ChatMessageRecord],
        system_prompt: str,
        trace_context: AgentTraceContext | None,
        parent_span_id: str | None,
    ) -> ChatSessionRecord:
        attempted_at = datetime.now(timezone.utc)
        running = await self._repositories.chat.update_memory_state(
            owner_user_id=owner_user_id,
            session_id=session.id,
            memory_status="running",
            last_memory_attempt_at=attempted_at,
            clear_memory_error=True,
        )
        current_session = running or session
        compact_span_id = await self._start_span(
            trace_context,
            kind="memory",
            name="chat.memory.compact",
            parent_span_id=parent_span_id,
            attributes={
                "messageCount": len(messages),
                "maxAttempts": self.compression_max_attempts,
                "timeoutSeconds": self.compression_timeout_seconds,
            },
        )
        current_snapshot = legacy_or_structured_snapshot(
            current_session.memory_snapshot,
            current_session.memory_summary,
        )
        prompt = memory_snapshot_prompt(current=current_snapshot, messages=messages)
        last_error: Exception | None = None
        for attempt_number in range(1, self.compression_max_attempts + 1):
            attempt_span_id = await self._start_span(
                trace_context,
                kind="attempt",
                name="chat.memory.compact.attempt",
                parent_span_id=compact_span_id,
                attributes={
                    "attemptNumber": attempt_number,
                    "maxAttempts": self.compression_max_attempts,
                },
            )
            try:
                response = await asyncio.wait_for(
                    self._llm_provider.create_chat_model().ainvoke(prompt),
                    timeout=self.compression_timeout_seconds,
                )
                raw_snapshot = _extract_model_text(response).strip()
                snapshot = parse_memory_snapshot(raw_snapshot)
                validation_span_id = await self._start_span(
                    trace_context,
                    kind="memory",
                    name="chat.memory.validate",
                    parent_span_id=compact_span_id,
                    attributes={"schemaVersion": snapshot.schema_version},
                )
                try:
                    validate_memory_snapshot(snapshot, all_history)
                except Exception as exc:
                    validation_code = (
                        exc.reason_code
                        if isinstance(exc, MemorySnapshotValidationError)
                        else "unexpected_validation_error"
                    )
                    await self._finalize_span(
                        trace_context,
                        validation_span_id,
                        status="failed",
                        summary="Memory snapshot validation failed",
                        attributes={
                            "errorCategory": exc.__class__.__name__,
                            "validationCode": validation_code,
                        },
                    )
                    raise
                await self._finalize_span(
                    trace_context,
                    validation_span_id,
                    status="succeeded",
                    summary="Memory snapshot validated",
                    attributes={
                        "activeConstraintCount": len(snapshot.active_constraints),
                        "supersededFactCount": len(snapshot.superseded_facts),
                    },
                )
                summary = snapshot.narrative_summary()
                compacted_count = session.compacted_message_count + len(messages)
                tokens = estimate_context_tokens(
                    system_prompt=system_prompt,
                    memory_summary=summary,
                    messages=[],
                )
                updated = await self._repositories.chat.update_memory_state(
                    owner_user_id=owner_user_id,
                    session_id=session.id,
                    memory_summary=summary,
                    compacted_message_count=compacted_count,
                    context_tokens=tokens,
                    last_compacted_at=datetime.now(timezone.utc),
                    memory_snapshot=snapshot.to_json_dict(),
                    memory_version=session.memory_version + 1,
                    memory_status="succeeded",
                    last_memory_attempt_at=attempted_at,
                    clear_memory_error=True,
                )
                await self._finalize_span(
                    trace_context,
                    attempt_span_id,
                    status="succeeded",
                    summary="Memory compaction attempt succeeded",
                    attributes={"attemptNumber": attempt_number},
                )
                await self._finalize_span(
                    trace_context,
                    compact_span_id,
                    status="succeeded",
                    summary="Chat memory compacted",
                    attributes={
                        "attemptCount": attempt_number,
                        "memoryVersion": session.memory_version + 1,
                    },
                )
                return updated or current_session
            except (asyncio.TimeoutError, MemorySnapshotValidationError) as exc:
                last_error = exc
                failure_code = (
                    exc.reason_code
                    if isinstance(exc, MemorySnapshotValidationError)
                    else "timeout"
                )
                await self._finalize_span(
                    trace_context,
                    attempt_span_id,
                    status="failed",
                    summary="Memory compaction attempt failed",
                    attributes={
                        "attemptNumber": attempt_number,
                        "errorCategory": exc.__class__.__name__,
                        "failureCode": failure_code,
                    },
                )
            except Exception as exc:
                last_error = exc
                await self._finalize_span(
                    trace_context,
                    attempt_span_id,
                    status="failed",
                    summary="Memory compaction attempt failed",
                    attributes={
                        "attemptNumber": attempt_number,
                        "errorCategory": exc.__class__.__name__,
                    },
                )
                break

        error_category = (
            last_error.__class__.__name__ if last_error is not None else "UnknownError"
        )
        await self._repositories.chat.update_memory_state(
            owner_user_id=owner_user_id,
            session_id=session.id,
            memory_status="failed",
            memory_error_category=error_category,
            last_memory_attempt_at=attempted_at,
        )
        await self._finalize_span(
            trace_context,
            compact_span_id,
            status="failed",
            summary="Chat memory compaction failed",
            attributes={"errorCategory": error_category},
        )
        raise ChatMemoryPreparationError(error_category)

    async def _start_span(
        self,
        context: AgentTraceContext | None,
        *,
        kind: str,
        name: str,
        parent_span_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> str | None:
        if context is None or self._trace_service is None:
            return None
        return await self._trace_service.start_span(
            context,
            kind=kind,
            name=name,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )

    async def _finalize_span(
        self,
        context: AgentTraceContext | None,
        span_id: str | None,
        *,
        status: str,
        summary: str,
        attributes: dict[str, object] | None = None,
    ) -> None:
        if context is None or span_id is None or self._trace_service is None:
            return
        await self._trace_service.finalize_span(
            context,
            span_id=span_id,
            status=status,
            summary=summary,
            attributes=attributes,
        )


def estimate_context_tokens(
    *,
    system_prompt: str,
    memory_summary: str | None,
    messages: list[ChatMessageRecord],
) -> int:
    values: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if memory_summary:
        values.append({"role": "system", "content": _memory_instruction(memory_summary)})
    values.extend(
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"}
    )
    return int(count_tokens_approximately(cast(Any, values)))


def memory_payload(
    session: ChatSessionRecord,
    context_window_tokens: int,
) -> dict[str, object]:
    snapshot = legacy_or_structured_snapshot(
        session.memory_snapshot,
        session.memory_summary,
    )
    return {
        "mode": session.memory_mode,
        "contextTokens": session.context_tokens,
        "contextWindowTokens": context_window_tokens,
        "contextUsagePercent": _usage_percent(
            session.context_tokens,
            context_window_tokens,
        ),
        "compactedMessageCount": session.compacted_message_count,
        "lastCompactedAt": (
            session.last_compacted_at.isoformat()
            if session.last_compacted_at is not None
            else None
        ),
        "canCompact": session.context_tokens > 0,
        "version": session.memory_version,
        "status": session.memory_status,
        "errorCategory": session.memory_error_category,
        "lastAttemptAt": (
            session.last_memory_attempt_at.isoformat()
            if session.last_memory_attempt_at is not None
            else None
        ),
        "snapshot": snapshot.to_json_dict(),
    }


def _usage_percent(tokens: int, window: int) -> float:
    return round(min(100.0, tokens / window * 100), 1)


def _memory_instruction(summary: str) -> str:
    return (
        "以下是通过来源校验的对话记忆。仅将当前有效约束、决策、偏好和未完成事项"
        f"作为上下文；不得恢复已被覆盖的旧事实：\n{summary}"
    )


def _prompt_with_memory(system_prompt: str, summary: str | None) -> str:
    return (
        f"{system_prompt}\n\n{_memory_instruction(summary)}"
        if summary
        else system_prompt
    )


def _extract_model_text(value: object) -> str:
    content = getattr(value, "content", value)
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence) and not isinstance(content, (str, bytes)):
        parts: list[str] = []
        for item in cast(Sequence[object], content):
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                text = cast(Mapping[object, object], item).get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""
