"""Validated, source-grounded Chat memory snapshot models."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from super_ai.memory.repositories import ChatMessageRecord, JsonDict


class MemoryItem(BaseModel):
    """One memory value whose text is grounded in a Chat message."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    source_message_id: str = Field(alias="sourceMessageId", min_length=1, max_length=80)


class SupersededMemoryItem(MemoryItem):
    superseded_by_message_id: str = Field(
        alias="supersededByMessageId", min_length=1, max_length=80
    )


class MemoryEvidenceRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    message_id: str = Field(alias="messageId", min_length=1, max_length=80)


class ChatMemorySnapshot(BaseModel):
    """Persisted structured memory accepted by deterministic validation."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_version: Literal[1] = Field(default=1, alias="schemaVersion")
    active_constraints: list[MemoryItem] = Field(
        default_factory=lambda: list[MemoryItem](), alias="activeConstraints"
    )
    superseded_facts: list[SupersededMemoryItem] = Field(
        default_factory=lambda: list[SupersededMemoryItem](), alias="supersededFacts"
    )
    decisions: list[MemoryItem] = Field(default_factory=lambda: list[MemoryItem]())
    preferences: list[MemoryItem] = Field(default_factory=lambda: list[MemoryItem]())
    open_tasks: list[MemoryItem] = Field(
        default_factory=lambda: list[MemoryItem](), alias="openTasks"
    )
    evidence_refs: list[MemoryEvidenceRef] = Field(
        default_factory=lambda: list[MemoryEvidenceRef](), alias="evidenceRefs"
    )
    legacy_summary: str | None = Field(default=None, alias="legacySummary")

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def normalize_evidence_refs(cls, value: object) -> object:
        """Normalize model shorthand without weakening source validation."""

        if not isinstance(value, list):
            return value
        items = cast(list[object], value)
        normalized: list[object] = []
        for item in items:
            normalized.append({"messageId": item} if isinstance(item, str) else item)
        return normalized

    def to_json_dict(self) -> JsonDict:
        return self.model_dump(by_alias=True, mode="json")

    def narrative_summary(self) -> str:
        sections: list[str] = []
        _append_items(sections, "当前有效约束", self.active_constraints)
        _append_items(sections, "已确认决策", self.decisions)
        _append_items(sections, "用户偏好", self.preferences)
        _append_items(sections, "未完成事项", self.open_tasks)
        if self.legacy_summary:
            sections.append(f"旧版摘要（来源不可追溯）：\n{self.legacy_summary.strip()}")
        return "\n\n".join(sections) or "当前没有可追溯的结构化记忆。"


class MemorySnapshotValidationError(RuntimeError):
    """Raised when a model-proposed snapshot cannot be trusted."""

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def parse_memory_snapshot(value: object) -> ChatMemorySnapshot:
    """Parse a strict snapshot from model text or persisted JSON."""

    if isinstance(value, ChatMemorySnapshot):
        return value
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        raw: object = {str(key): item for key, item in mapping.items()}
    else:
        text = str(value).strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
            if text.startswith("json"):
                text = text[4:].lstrip()
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise MemorySnapshotValidationError(
                "Memory snapshot is not valid JSON.",
                reason_code="invalid_json",
            ) from exc
    try:
        return ChatMemorySnapshot.model_validate(raw)
    except ValidationError as exc:
        first_error = exc.errors(include_url=False, include_context=False)[0]
        error_type = str(first_error.get("type", "unknown")).replace("_", "-")
        location = "-".join(str(part) for part in first_error.get("loc", ()))
        diagnostic = f"invalid_schema:{error_type}"
        if location:
            diagnostic = f"{diagnostic}:{location}"
        raise MemorySnapshotValidationError(
            "Memory snapshot schema is invalid.",
            reason_code=diagnostic,
        ) from exc


def legacy_or_structured_snapshot(
    snapshot: JsonDict | None, legacy_summary: str | None
) -> ChatMemorySnapshot:
    if snapshot is not None:
        return parse_memory_snapshot(snapshot)
    return (
        ChatMemorySnapshot(legacySummary=legacy_summary)
        if legacy_summary
        else ChatMemorySnapshot()
    )


def validate_memory_snapshot(
    snapshot: ChatMemorySnapshot,
    messages: Sequence[ChatMessageRecord],
) -> ChatMemorySnapshot:
    """Verify tenant/session-local sources, exact values, ordering and active-key uniqueness."""

    message_by_id = {message.id: message for message in messages}
    order = {message.id: index for index, message in enumerate(messages)}
    owner_ids = {message.owner_user_id for message in messages}
    session_ids = {message.session_id for message in messages}
    if len(owner_ids) > 1 or len(session_ids) > 1:
        raise MemorySnapshotValidationError(
            "Memory validation received a mixed scope.",
            reason_code="mixed_scope",
        )

    active_keys: set[str] = set()
    for item in snapshot.active_constraints:
        _validate_item(item, message_by_id)
        if item.key in active_keys:
            raise MemorySnapshotValidationError(
                "An active memory key has multiple values.",
                reason_code="duplicate_active_key",
            )
        active_keys.add(item.key)
    for group in (snapshot.decisions, snapshot.preferences, snapshot.open_tasks):
        for item in group:
            _validate_item(item, message_by_id)
    for item in snapshot.superseded_facts:
        _validate_item(item, message_by_id)
        replacement = message_by_id.get(item.superseded_by_message_id)
        if replacement is None:
            raise MemorySnapshotValidationError(
                "A supersession source is inaccessible.",
                reason_code="supersession_source_inaccessible",
            )
        if order[item.superseded_by_message_id] <= order[item.source_message_id]:
            raise MemorySnapshotValidationError(
                "A supersession source is not newer.",
                reason_code="supersession_not_newer",
            )
        if item.key not in active_keys:
            raise MemorySnapshotValidationError(
                "A superseded key has no active replacement.",
                reason_code="superseded_key_without_active_replacement",
            )
    for ref in snapshot.evidence_refs:
        if ref.message_id not in message_by_id:
            raise MemorySnapshotValidationError(
                "A memory evidence source is inaccessible.",
                reason_code="evidence_source_inaccessible",
            )
    return snapshot


def memory_snapshot_prompt(
    *,
    current: ChatMemorySnapshot,
    messages: Sequence[ChatMessageRecord],
) -> str:
    transcript = "\n".join(
        f"[{message.id}] {message.role}: {message.content}" for message in messages
    )
    current_json = json.dumps(current.to_json_dict(), ensure_ascii=False)
    return (
        "你负责提出 Chat 结构化记忆候选。只输出一个 JSON 对象，严禁 Markdown。"
        "必须使用 schemaVersion、activeConstraints、supersededFacts、decisions、preferences、"
        "openTasks、evidenceRefs 字段。每个事实条目必须包含 key、value、sourceMessageId，"
        "evidenceRefs 必须是对象数组，每个对象只包含 messageId，例如 "
        '[{"messageId":"chat_message_xxx"}]。'
        "value 必须是来源消息中逐字连续出现的原文。只有较新消息明确表达修改、覆盖、"
        "废止或以新值为准时，"
        "才可把旧条目移入 supersededFacts，并填写 supersededByMessageId。"
        "不得归纳编号规律，不得补全、改写或推断来源中不存在的值。"
        "保留仍然有效的已有条目，删除已经完成的 open task。\n\n"
        f"已有快照：\n{current_json}\n\n新增可压缩消息：\n{transcript}"
    )


def _validate_item(
    item: MemoryItem, message_by_id: Mapping[str, ChatMessageRecord]
) -> None:
    source = message_by_id.get(item.source_message_id)
    if source is None:
        raise MemorySnapshotValidationError(
            "A memory source is inaccessible.",
            reason_code="memory_source_inaccessible",
        )
    if item.value not in source.content:
        raise MemorySnapshotValidationError(
            "A memory value is not grounded in its source.",
            reason_code="value_not_grounded",
        )


def _append_items(
    output: list[str], title: str, items: Sequence[MemoryItem]
) -> None:
    if not items:
        return
    lines = [f"- {item.key}={item.value}（来源 {item.source_message_id}）" for item in items]
    output.append(f"{title}：\n" + "\n".join(lines))
