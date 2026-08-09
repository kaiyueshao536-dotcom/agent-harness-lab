from __future__ import annotations

from datetime import datetime, timezone

import pytest

from super_ai.chat.memory_models import (
    ChatMemorySnapshot,
    MemorySnapshotValidationError,
    validate_memory_snapshot,
)
from super_ai.memory.repositories import ChatMessageRecord


def test_structured_memory_accepts_explicit_override_and_rejects_inference() -> None:
    messages = [
        _message("old", "超时阈值=30s"),
        _message("new", "以超时阈值=5s为准"),
    ]
    valid = ChatMemorySnapshot.model_validate(
        {
            "schemaVersion": 1,
            "activeConstraints": [
                {"key": "超时阈值", "value": "超时阈值=5s", "sourceMessageId": "new"}
            ],
            "supersededFacts": [
                {
                    "key": "超时阈值",
                    "value": "超时阈值=30s",
                    "sourceMessageId": "old",
                    "supersededByMessageId": "new",
                }
            ],
            "decisions": [],
            "preferences": [],
            "openTasks": [],
            "evidenceRefs": [{"messageId": "new"}],
        }
    )
    inferred = valid.model_copy(
        update={
            "active_constraints": [
                valid.active_constraints[0].model_copy(update={"value": "超时阈值=1s"})
            ]
        }
    )

    assert validate_memory_snapshot(valid, messages) == valid
    with pytest.raises(MemorySnapshotValidationError, match="not grounded"):
        validate_memory_snapshot(inferred, messages)


def test_structured_memory_rejects_cross_session_source() -> None:
    source = _message("foreign", "部署区域=ap-guangzhou", session_id="other")
    local = _message("local", "继续执行")
    snapshot = ChatMemorySnapshot.model_validate(
        {
            "activeConstraints": [
                {
                    "key": "部署区域",
                    "value": "部署区域=ap-guangzhou",
                    "sourceMessageId": "foreign",
                }
            ]
        }
    )

    with pytest.raises(MemorySnapshotValidationError, match="mixed scope"):
        validate_memory_snapshot(snapshot, [local, source])


def test_structured_memory_normalizes_string_evidence_refs() -> None:
    snapshot = ChatMemorySnapshot.model_validate(
        {
            "activeConstraints": [],
            "evidenceRefs": ["message-1"],
        }
    )

    assert snapshot.evidence_refs[0].message_id == "message-1"


def _message(
    message_id: str,
    content: str,
    *,
    session_id: str = "chat-1",
) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=message_id,
        owner_user_id="user-a",
        session_id=session_id,
        role="user",
        content=content,
        metadata={},
        created_at=datetime.now(timezone.utc),
    )
