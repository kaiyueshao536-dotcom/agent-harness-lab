"""Deterministic SOP context selection and approximate token budgeting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal, cast

from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import count_tokens_approximately

from super_ai.retrieval import KnowledgeRetrievalHit

ContextAffinity = Literal["alert-match", "service-match", "generic", "metadata-conflict"]
ContextDecision = Literal["selected", "excluded"]

DEFAULT_SOP_CONTEXT_TOKEN_BUDGET = 1_600
DEFAULT_SOP_CONTEXT_SOURCE_LIMIT = 3


@dataclass(frozen=True, slots=True)
class SopContextCandidate:
    """One retrieval candidate plus its safe, explainable selection decision."""

    hit: KnowledgeRetrievalHit
    affinity: ContextAffinity
    decision: ContextDecision
    reason: str
    estimated_tokens: int
    used_tokens: int
    prompt_content: str | None
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class SopContextSelection:
    """Bounded SOP context and the decisions that produced it."""

    candidates: tuple[SopContextCandidate, ...]
    token_limit: int
    used_tokens: int
    source_limit: int

    @property
    def selected_hits(self) -> list[KnowledgeRetrievalHit]:
        return [
            replace(candidate.hit, content=candidate.prompt_content or "")
            for candidate in self.candidates
            if candidate.decision == "selected" and candidate.prompt_content is not None
        ]

    @property
    def selected_sources(self) -> list[str]:
        return [
            candidate.hit.source
            for candidate in self.candidates
            if candidate.decision == "selected"
        ]

    @property
    def truncated(self) -> bool:
        return any(candidate.truncated for candidate in self.candidates)


def select_sop_context(
    hits: Sequence[KnowledgeRetrievalHit],
    *,
    alert: Mapping[str, object],
    token_limit: int = DEFAULT_SOP_CONTEXT_TOKEN_BUDGET,
    source_limit: int = DEFAULT_SOP_CONTEXT_SOURCE_LIMIT,
) -> SopContextSelection:
    """Select routing-compatible SOPs in stable affinity/rerank order."""
    if token_limit < 1:
        raise ValueError("token_limit must be positive")
    if source_limit < 1:
        raise ValueError("source_limit must be positive")

    alert_names, services = _alert_routes(alert)
    ranked = sorted(
        enumerate(hits),
        key=lambda item: (_affinity_rank(_affinity(item[1], alert_names, services)), item[0]),
    )
    decisions: list[SopContextCandidate] = []
    used_tokens = 0
    selected_count = 0
    for _, hit in ranked:
        affinity = _affinity(hit, alert_names, services)
        estimated_tokens = estimate_text_tokens(hit.content)
        if affinity == "metadata-conflict":
            decisions.append(
                _excluded(hit, affinity, "告警或服务 metadata 与当前诊断冲突。", estimated_tokens)
            )
            continue
        if selected_count >= source_limit:
            decisions.append(
                _excluded(hit, affinity, "已达到上下文来源数量上限。", estimated_tokens)
            )
            continue

        remaining = token_limit - used_tokens
        if estimated_tokens <= remaining:
            decisions.append(
                SopContextCandidate(
                    hit=hit,
                    affinity=affinity,
                    decision="selected",
                    reason=_selected_reason(affinity),
                    estimated_tokens=estimated_tokens,
                    used_tokens=estimated_tokens,
                    prompt_content=hit.content,
                )
            )
            used_tokens += estimated_tokens
            selected_count += 1
            continue
        if selected_count == 0 and remaining > 0:
            content = _truncate_to_token_budget(hit.content, remaining)
            content_tokens = estimate_text_tokens(content) if content else 0
            if content:
                decisions.append(
                    SopContextCandidate(
                        hit=hit,
                        affinity=affinity,
                        decision="selected",
                        reason=f"{_selected_reason(affinity)} 正文已按 Token 预算截断。",
                        estimated_tokens=estimated_tokens,
                        used_tokens=content_tokens,
                        prompt_content=content,
                        truncated=True,
                    )
                )
                used_tokens += content_tokens
                selected_count += 1
                continue
        decisions.append(
            _excluded(hit, affinity, "剩余 Token 预算不足。", estimated_tokens)
        )

    return SopContextSelection(
        candidates=tuple(decisions),
        token_limit=token_limit,
        used_tokens=used_tokens,
        source_limit=source_limit,
    )


def estimate_text_tokens(text: str) -> int:
    """Return a deterministic LangChain approximation, not provider billing tokens."""
    if not text:
        return 0
    return int(count_tokens_approximately([HumanMessage(content=text)]))


def _excluded(
    hit: KnowledgeRetrievalHit,
    affinity: ContextAffinity,
    reason: str,
    estimated_tokens: int,
) -> SopContextCandidate:
    return SopContextCandidate(
        hit=hit,
        affinity=affinity,
        decision="excluded",
        reason=reason,
        estimated_tokens=estimated_tokens,
        used_tokens=0,
        prompt_content=None,
    )


def _selected_reason(affinity: ContextAffinity) -> str:
    if affinity == "alert-match":
        return "SOP 告警名称与当前告警一致。"
    if affinity == "service-match":
        return "SOP 服务与当前告警服务一致。"
    return "SOP 缺少路由 metadata，作为通用正式 SOP 候选。"


def _affinity(
    hit: KnowledgeRetrievalHit,
    alert_names: set[str],
    services: set[str],
) -> ContextAffinity:
    metadata = hit.metadata
    hit_alerts = _metadata_values(metadata, "alertName", "alertname", "alert_name")
    hit_services = _metadata_values(metadata, "service", "serviceName", "service_name")
    if alert_names and hit_alerts.intersection(alert_names):
        return "alert-match"
    if services and hit_services.intersection(services):
        return "service-match"
    if hit_alerts or hit_services:
        return "metadata-conflict"
    return "generic"


def _affinity_rank(value: ContextAffinity) -> int:
    return {
        "alert-match": 0,
        "service-match": 1,
        "generic": 2,
        "metadata-conflict": 3,
    }[value]


def _alert_routes(alert: Mapping[str, object]) -> tuple[set[str], set[str]]:
    mappings: list[Mapping[str, object]] = [alert]
    for key in ("labels", "annotations", "context"):
        nested = alert.get(key)
        if isinstance(nested, Mapping):
            mappings.append(cast(Mapping[str, object], nested))
    alert_names: set[str] = set()
    services: set[str] = set()
    for mapping in mappings:
        alert_names.update(
            _metadata_values(mapping, "alertName", "alertname", "alert_name", "name")
        )
        services.update(
            _metadata_values(mapping, "service", "serviceName", "service_name")
        )
    return alert_names, services


def _metadata_values(mapping: Mapping[str, object], *keys: str) -> set[str]:
    normalized_keys = {key.casefold() for key in keys}
    values: set[str] = set()
    for key, raw in mapping.items():
        if str(key).casefold() not in normalized_keys:
            continue
        if isinstance(raw, str) and raw.strip():
            values.add(raw.strip().casefold())
    return values


def _truncate_to_token_budget(text: str, token_limit: int) -> str:
    low = 0
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if estimate_text_tokens(text[:middle]) <= token_limit:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip()
