from __future__ import annotations

from super_ai.aiops.context_quality import estimate_text_tokens, select_sop_context
from super_ai.retrieval import KnowledgeRetrievalHit


def test_context_selector_prioritizes_alert_and_service_and_excludes_conflict() -> None:
    selection = select_sop_context(
        [
            _hit(
                "search-es-timeout-sop.md",
                "Search recovery",
                alert_name="SearchEsTimeoutHigh",
                service="search-service",
                score=0.99,
            ),
            _hit(
                "payment-circuit-open-sop.md",
                "Circuit recovery",
                alert_name="PaymentCircuitOpen",
                service="payment-service",
                score=0.70,
            ),
            _hit(
                "payment-timeout-sop.md",
                "Payment timeout recovery",
                alert_name="PaymentGatewayTimeoutHigh",
                service="payment-service",
                score=0.92,
            ),
        ],
        alert={"labels": {"alertname": "PaymentGatewayTimeoutHigh", "service": "payment-service"}},
    )

    assert selection.selected_sources == [
        "payment-timeout-sop.md",
        "payment-circuit-open-sop.md",
    ]
    excluded = next(item for item in selection.candidates if item.hit.source.startswith("search"))
    assert excluded.affinity == "metadata-conflict"
    assert excluded.decision == "excluded"
    assert excluded.prompt_content is None


def test_context_selector_keeps_generic_sop_but_does_not_claim_exact_match() -> None:
    selection = select_sop_context(
        [_hit("legacy-sop.md", "Generic recovery", score=0.8)],
        alert={"service": "payment-service"},
    )

    assert selection.selected_sources == ["legacy-sop.md"]
    assert selection.candidates[0].affinity == "generic"
    assert "通用" in selection.candidates[0].reason


def test_context_selector_truncates_first_source_and_excludes_later_budget_overflow() -> None:
    long_content = "支付超时处理步骤。" * 400
    token_limit = 80
    selection = select_sop_context(
        [
            _hit("primary.md", long_content, service="payment-service", score=0.9),
            _hit("secondary.md", "secondary", service="payment-service", score=0.8),
        ],
        alert={"service": "payment-service"},
        token_limit=token_limit,
    )

    assert selection.selected_sources == ["primary.md"]
    assert selection.truncated is True
    assert selection.used_tokens <= token_limit
    assert estimate_text_tokens(selection.selected_hits[0].content) <= token_limit
    secondary = next(item for item in selection.candidates if item.hit.source == "secondary.md")
    assert secondary.decision == "excluded"
    assert "预算" in secondary.reason


def test_context_selector_rejects_invalid_limits() -> None:
    hit = _hit("one.md", "content", score=1.0)
    for kwargs in ({"token_limit": 0}, {"source_limit": 0}):
        try:
            select_sop_context([hit], alert={}, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid context limits must be rejected")


def _hit(
    source: str,
    content: str,
    *,
    score: float,
    alert_name: str | None = None,
    service: str | None = None,
) -> KnowledgeRetrievalHit:
    metadata: dict[str, object] = {"knowledgeType": "sop"}
    if alert_name is not None:
        metadata["alertName"] = alert_name
    if service is not None:
        metadata["service"] = service
    return KnowledgeRetrievalHit(
        chunk_id=f"chunk-{source}",
        document_id=f"doc-{source}",
        knowledge_base_id="kb-user",
        owner_user_id="user",
        tenant_id="user",
        content=content,
        source=source,
        metadata=metadata,
        score=score,
        rerank_score=score,
    )
