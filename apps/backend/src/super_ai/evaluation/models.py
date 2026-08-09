"""Validated definitions and results shared by API, service, and CLI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

ExecutionType = Literal["chat", "aiops"]
RuleKind = Literal[
    "contains_all",
    "excludes_all",
    "required_tools",
    "required_context_sources",
    "excluded_context_sources",
    "min_references",
    "max_context_tokens",
    "max_duration_ms",
    "max_tool_calls",
    "evidence_cautious",
    "trace_succeeded",
    "memory_contains_active",
    "memory_excludes_active",
    "memory_no_ungrounded",
    "memory_compaction_succeeded",
    "no_exact_duplicate",
    "max_memory_duration_ms",
]


class EvaluationRule(BaseModel):
    """One deterministic and explainable assertion."""

    model_config = ConfigDict(extra="forbid")

    kind: RuleKind
    values: list[str] = Field(default_factory=list, max_length=20)
    threshold: int | None = Field(default=None, ge=0)
    description: str = Field(default="", max_length=240)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        value_kinds = {
            "contains_all",
            "excludes_all",
            "required_tools",
            "required_context_sources",
            "excluded_context_sources",
            "memory_contains_active",
            "memory_excludes_active",
        }
        threshold_kinds = {
            "min_references",
            "max_duration_ms",
            "max_tool_calls",
            "max_context_tokens",
            "max_memory_duration_ms",
        }
        if self.kind in value_kinds and not self.values:
            raise ValueError(f"{self.kind} requires at least one value")
        if self.kind in threshold_kinds and self.threshold is None:
            raise ValueError(f"{self.kind} requires threshold")
        if self.kind not in value_kinds and self.values:
            raise ValueError(f"{self.kind} does not accept values")
        if self.kind not in threshold_kinds and self.threshold is not None:
            raise ValueError(f"{self.kind} does not accept threshold")
        return self


class EvaluationGate(BaseModel):
    """Release gate evaluated from aggregate run metrics."""

    model_config = ConfigDict(extra="forbid")

    min_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    min_average_score: float = Field(default=1.0, ge=0.0, le=1.0)
    max_duration_regression_percent: float | None = Field(default=None, ge=0.0)


class EvaluationCaseDefinition(BaseModel):
    """Immutable case definition stored in a versioned dataset."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    execution_type: ExecutionType
    input_summary: str = Field(min_length=1, max_length=500)
    rules: list[EvaluationRule] = Field(min_length=1, max_length=20)


class EvaluationObservation(BaseModel):
    """Safe facts derived from an owner-scoped P1 Agent Trace."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    execution_type: ExecutionType
    output_text: str
    tool_names: list[str] = Field(default_factory=list)
    reference_count: int = Field(default=0, ge=0)
    context_source_names: list[str] = Field(default_factory=list)
    context_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    trace_status: str
    memory_active_values: list[str] = Field(default_factory=list)
    memory_superseded_values: list[str] = Field(default_factory=list)
    memory_ungrounded_count: int = Field(default=0, ge=0)
    memory_status: str | None = None
    memory_duration_ms: int | None = Field(default=None, ge=0)


class RuleCheck(BaseModel):
    """Explainable outcome of one rule without raw tool payloads."""

    kind: RuleKind
    passed: bool
    expected: str
    actual: str


class EvaluationScore(BaseModel):
    """Deterministic score for one case."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    output_summary: str = Field(max_length=500)
    metrics: dict[str, int | str | None]
    checks: list[RuleCheck]


class GateEvaluation(BaseModel):
    """Aggregate release-gate decision."""

    status: Literal["passed", "failed"]
    failures: list[str]
