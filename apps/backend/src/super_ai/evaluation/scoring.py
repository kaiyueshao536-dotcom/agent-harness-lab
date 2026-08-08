"""Pure deterministic scoring functions used by runtime and offline CLI."""

from __future__ import annotations

import re
from collections.abc import Sequence

from super_ai.evaluation.models import (
    EvaluationGate,
    EvaluationObservation,
    EvaluationRule,
    EvaluationScore,
    GateEvaluation,
    RuleCheck,
)

_CREDENTIAL_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]+|AKID[A-Za-z0-9]+)")
_NAMED_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[-_ ]?key|authorization|credential|password|secret|token)"
    r"\s*[:=]\s*[^\s,;]+"
)
_ZERO_RESULT_PATTERNS = (
    re.compile(r"recordcount\s*(?:为|=|:|：)?\s*0", re.IGNORECASE),
    re.compile(r"(?:未返回|未匹配到|没有匹配到).{0,12}(?:可解析)?日志"),
    re.compile(r"no matching (?:parseable )?(?:records|logs)", re.IGNORECASE),
)
_CAUTIOUS_PATTERNS = (
    re.compile(r"证据不足"),
    re.compile(r"无法确认(?:原因|根因)?"),
    re.compile(r"cannot confirm", re.IGNORECASE),
)
_OVERCLAIM_PATTERNS = (
    re.compile(r"(?:表明|证明|说明).{0,18}(?:采集链路|日志链路).{0,8}(?:异常|故障)"),
    re.compile(r"(?:表明|证明|说明).{0,18}(?:topic|主题).{0,8}(?:无数据|没有数据)", re.IGNORECASE),
    re.compile(r"(?:采集链路|日志链路)(?:存在|发生|出现)?(?:异常|故障)"),
)


def score_case(
    rules: Sequence[EvaluationRule], observation: EvaluationObservation
) -> EvaluationScore:
    """Evaluate equal-weight rules against facts derived from one trace."""
    checks = [_evaluate_rule(rule, observation) for rule in rules]
    passed_count = sum(1 for check in checks if check.passed)
    score = passed_count / len(checks) if checks else 0.0
    return EvaluationScore(
        passed=bool(checks) and passed_count == len(checks),
        score=round(score, 6),
        output_summary=_safe_summary(observation.output_text),
        metrics={
            "durationMs": observation.duration_ms,
            "toolCallCount": len(observation.tool_names),
            "referenceCount": observation.reference_count,
            "contextSourceCount": len(observation.context_source_names),
            "contextTokens": observation.context_tokens,
            "traceStatus": observation.trace_status,
        },
        checks=checks,
    )


def evaluate_gate(
    gate: EvaluationGate,
    *,
    pass_rate: float,
    average_score: float,
    duration_regression_percent: float | None,
) -> GateEvaluation:
    """Return a stable release-gate decision and human-readable failures."""
    failures: list[str] = []
    if pass_rate < gate.min_pass_rate:
        failures.append(
            f"pass rate {pass_rate:.2%} is below {gate.min_pass_rate:.2%}"
        )
    if average_score < gate.min_average_score:
        failures.append(
            f"average score {average_score:.2%} is below {gate.min_average_score:.2%}"
        )
    limit = gate.max_duration_regression_percent
    if limit is not None and duration_regression_percent is not None:
        if duration_regression_percent > limit:
            failures.append(
                f"duration regression {duration_regression_percent:.2f}% exceeds {limit:.2f}%"
            )
    return GateEvaluation(status="failed" if failures else "passed", failures=failures)


def _evaluate_rule(rule: EvaluationRule, observation: EvaluationObservation) -> RuleCheck:
    output = observation.output_text.casefold()
    tools = {name.casefold() for name in observation.tool_names}
    context_sources = {name.casefold() for name in observation.context_source_names}
    values = [value.casefold() for value in rule.values]
    if rule.kind == "contains_all":
        missing = [
            raw for raw, value in zip(rule.values, values, strict=True) if value not in output
        ]
        return _check(rule, not missing, ", ".join(rule.values), f"missing={missing}")
    if rule.kind == "excludes_all":
        found = [raw for raw, value in zip(rule.values, values, strict=True) if value in output]
        return _check(rule, not found, ", ".join(rule.values), f"found={found}")
    if rule.kind == "required_tools":
        missing = [
            raw for raw, value in zip(rule.values, values, strict=True) if value not in tools
        ]
        return _check(rule, not missing, ", ".join(rule.values), f"missing={missing}")
    if rule.kind == "required_context_sources":
        missing = [
            raw
            for raw, value in zip(rule.values, values, strict=True)
            if value not in context_sources
        ]
        return _check(rule, not missing, ", ".join(rule.values), f"missing={missing}")
    if rule.kind == "excluded_context_sources":
        found = [
            raw
            for raw, value in zip(rule.values, values, strict=True)
            if value in context_sources
        ]
        return _check(rule, not found, ", ".join(rule.values), f"found={found}")
    if rule.kind == "min_references":
        threshold = _threshold(rule)
        return _check(
            rule,
            observation.reference_count >= threshold,
            f">={threshold}",
            str(observation.reference_count),
        )
    if rule.kind == "max_duration_ms":
        threshold = _threshold(rule)
        actual = observation.duration_ms
        return _check(
            rule,
            actual is not None and actual <= threshold,
            f"<={threshold}",
            str(actual),
        )
    if rule.kind == "max_tool_calls":
        threshold = _threshold(rule)
        count = len(observation.tool_names)
        return _check(rule, count <= threshold, f"<={threshold}", str(count))
    if rule.kind == "max_context_tokens":
        threshold = _threshold(rule)
        actual = observation.context_tokens
        return _check(
            rule,
            actual is not None and actual <= threshold,
            f"<={threshold}",
            str(actual),
        )
    if rule.kind == "evidence_cautious":
        zero_result = any(
            pattern.search(observation.output_text) for pattern in _ZERO_RESULT_PATTERNS
        )
        cautious = any(pattern.search(observation.output_text) for pattern in _CAUTIOUS_PATTERNS)
        overclaims = [
            match.group(0)
            for pattern in _OVERCLAIM_PATTERNS
            if (match := pattern.search(observation.output_text)) is not None
        ]
        passed = not zero_result or (cautious and not overclaims)
        return _check(
            rule,
            passed,
            "zero-result reports state uncertainty and avoid causal claims",
            f"zeroResult={zero_result}; cautious={cautious}; overclaims={overclaims}",
        )
    return _check(
        rule,
        observation.trace_status == "succeeded",
        "succeeded",
        observation.trace_status,
    )


def _check(rule: EvaluationRule, passed: bool, expected: str, actual: str) -> RuleCheck:
    return RuleCheck(kind=rule.kind, passed=passed, expected=expected, actual=actual)


def _threshold(rule: EvaluationRule) -> int:
    if rule.threshold is None:
        raise ValueError(f"{rule.kind} has no threshold")
    return rule.threshold


def _safe_summary(value: str) -> str:
    normalized = " ".join(value.split())
    redacted = _CREDENTIAL_PATTERN.sub("[redacted]", normalized)
    redacted = _NAMED_SECRET_PATTERN.sub(
        lambda match: f"{match.group(1)}=[redacted]", redacted
    )
    return redacted[:500]
