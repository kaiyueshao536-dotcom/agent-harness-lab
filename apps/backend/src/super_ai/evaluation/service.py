"""Application service for immutable, trace-backed Agent evaluations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast
from uuid import uuid4

from super_ai.chat.memory_models import (
    MemorySnapshotValidationError,
    legacy_or_structured_snapshot,
    validate_memory_snapshot,
)
from super_ai.evaluation.models import (
    EvaluationCaseDefinition,
    EvaluationGate,
    EvaluationObservation,
    EvaluationRule,
    ExecutionType,
)
from super_ai.evaluation.scoring import evaluate_gate, score_case
from super_ai.memory.repositories import (
    EvaluationCaseDraft,
    EvaluationCaseResultDraft,
    EvaluationDatasetRecord,
    EvaluationRunRecord,
    JsonDict,
    MemoryRepositories,
)


class EvaluationNotFoundError(LookupError):
    """Requested owner-scoped evaluation artifact was not found."""


class EvaluationBindingError(ValueError):
    """Trace bindings do not exactly cover the dataset or have the wrong type."""


class EvaluationHarnessService:
    """Create datasets and replay real P1 traces through deterministic rules."""

    def __init__(self, repositories: MemoryRepositories) -> None:
        if repositories.evaluations is None:
            raise ValueError("Evaluation repository is required.")
        if repositories.agent_traces is None:
            raise ValueError("Agent trace repository is required.")
        self._repositories = repositories
        self._evaluations = repositories.evaluations
        self._traces = repositories.agent_traces

    async def create_dataset(
        self,
        *,
        owner_user_id: str,
        name: str,
        version: str,
        description: str,
        gate: EvaluationGate,
        cases: Sequence[EvaluationCaseDefinition],
    ) -> EvaluationDatasetRecord:
        if not cases:
            raise ValueError("An evaluation dataset requires at least one case.")
        if len(cases) > 100:
            raise ValueError("An evaluation dataset supports at most 100 cases.")
        drafts = [
            EvaluationCaseDraft(
                id=f"eval_case_{uuid4().hex}",
                sequence=sequence,
                name=case.name,
                execution_type=case.execution_type,
                input_summary=case.input_summary,
                rules=[cast(JsonDict, rule.model_dump(mode="json")) for rule in case.rules],
            )
            for sequence, case in enumerate(cases, start=1)
        ]
        return await self._evaluations.create_dataset(
            owner_user_id=owner_user_id,
            dataset_id=f"eval_dataset_{uuid4().hex}",
            name=name,
            version=version,
            description=description,
            gate=cast(JsonDict, gate.model_dump(mode="json")),
            cases=drafts,
        )

    async def run(
        self,
        *,
        owner_user_id: str,
        dataset_id: str,
        candidate_label: str,
        trace_bindings: Mapping[str, str],
        baseline_run_id: str | None = None,
    ) -> EvaluationRunRecord:
        dataset = await self._evaluations.get_dataset(
            owner_user_id=owner_user_id, dataset_id=dataset_id
        )
        if dataset is None:
            raise EvaluationNotFoundError("Evaluation dataset not found.")
        cases = await self._evaluations.list_cases(
            owner_user_id=owner_user_id, dataset_id=dataset_id
        )
        expected_ids = {case.id for case in cases}
        if set(trace_bindings) != expected_ids:
            missing = sorted(expected_ids - set(trace_bindings))
            extra = sorted(set(trace_bindings) - expected_ids)
            raise EvaluationBindingError(
                f"Trace bindings must cover every case; missing={missing}, extra={extra}"
            )

        baseline = await self._load_baseline(
            owner_user_id=owner_user_id,
            dataset_id=dataset_id,
            baseline_run_id=baseline_run_id,
        )
        result_drafts: list[EvaluationCaseResultDraft] = []
        for case in cases:
            observation = await self._resolve_observation(
                owner_user_id=owner_user_id,
                trace_id=trace_bindings[case.id],
                expected_execution_type=case.execution_type,
            )
            rules = [EvaluationRule.model_validate(rule) for rule in case.rules]
            scored = score_case(rules, observation)
            result_drafts.append(
                EvaluationCaseResultDraft(
                    id=f"eval_result_{uuid4().hex}",
                    case_id=case.id,
                    sequence=case.sequence,
                    trace_id=observation.trace_id,
                    status="passed" if scored.passed else "failed",
                    score=scored.score,
                    output_summary=scored.output_summary,
                    metrics=cast(JsonDict, scored.metrics),
                    checks=[
                        cast(JsonDict, check.model_dump(mode="json"))
                        for check in scored.checks
                    ],
                )
            )

        pass_rate = _average(
            [1.0 if result.status == "passed" else 0.0 for result in result_drafts]
        )
        average_score = _average([result.score for result in result_drafts])
        durations = [
            float(value)
            for result in result_drafts
            if isinstance((value := result.metrics.get("durationMs")), int)
        ]
        average_duration_ms = _average(durations) if durations else None
        total_tool_calls = sum(
            int(value)
            for result in result_drafts
            if isinstance((value := result.metrics.get("toolCallCount")), int)
        )
        baseline_delta = _baseline_delta(
            baseline,
            pass_rate=pass_rate,
            average_score=average_score,
            average_duration_ms=average_duration_ms,
            total_tool_calls=total_tool_calls,
        )
        duration_regression = baseline_delta.get("durationPercent")
        gate = EvaluationGate.model_validate(dataset.gate)
        gate_result = evaluate_gate(
            gate,
            pass_rate=pass_rate,
            average_score=average_score,
            duration_regression_percent=(
                float(duration_regression)
                if isinstance(duration_regression, (int, float))
                else None
            ),
        )
        return await self._evaluations.create_run(
            owner_user_id=owner_user_id,
            run_id=f"eval_run_{uuid4().hex}",
            dataset_id=dataset_id,
            candidate_label=candidate_label,
            baseline_run_id=baseline_run_id,
            gate_status=gate_result.status,
            pass_rate=pass_rate,
            average_score=average_score,
            average_duration_ms=average_duration_ms,
            total_tool_calls=total_tool_calls,
            baseline_delta=baseline_delta,
            gate_failures=gate_result.failures,
            results=result_drafts,
        )

    async def _load_baseline(
        self,
        *,
        owner_user_id: str,
        dataset_id: str,
        baseline_run_id: str | None,
    ) -> EvaluationRunRecord | None:
        if baseline_run_id is None:
            return None
        baseline = await self._evaluations.get_run(
            owner_user_id=owner_user_id, run_id=baseline_run_id
        )
        if baseline is None or baseline.dataset_id != dataset_id:
            raise EvaluationBindingError("Baseline run must belong to the same owned dataset.")
        return baseline

    async def _resolve_observation(
        self,
        *,
        owner_user_id: str,
        trace_id: str,
        expected_execution_type: str,
    ) -> EvaluationObservation:
        trace = await self._traces.get_trace(owner_user_id=owner_user_id, trace_id=trace_id)
        if trace is None:
            raise EvaluationNotFoundError("Evaluation Trace not found.")
        if trace.execution_type != expected_execution_type:
            raise EvaluationBindingError(
                f"Trace '{trace_id}' is {trace.execution_type}, expected {expected_execution_type}."
            )
        spans = await self._traces.list_spans(owner_user_id=owner_user_id, trace_id=trace_id)
        tool_names = [span.name for span in spans if span.kind == "tool"]
        context_source_names: list[str] = []
        context_tokens: int | None = None
        memory_active_values: list[str] = []
        memory_superseded_values: list[str] = []
        memory_ungrounded_count = 0
        memory_status: str | None = None
        memory_duration_ms: int | None = None
        if trace.execution_type == "chat":
            output_text, reference_count = await self._resolve_chat_output(
                owner_user_id=owner_user_id,
                session_id=trace.resource_id,
                trace_id=trace_id,
            )
            (
                memory_active_values,
                memory_superseded_values,
                memory_ungrounded_count,
                memory_status,
            ) = await self._resolve_chat_memory(
                owner_user_id=owner_user_id,
                session_id=trace.resource_id,
            )
            memory_span = next(
                (span for span in spans if span.name == "chat.memory.prepare"),
                None,
            )
            memory_duration_ms = memory_span.duration_ms if memory_span is not None else None
        else:
            output_text, reference_count = await self._resolve_aiops_output(
                owner_user_id=owner_user_id,
                task_id=trace.resource_id,
            )
            context_source_names, context_tokens = await self._resolve_aiops_context(
                owner_user_id=owner_user_id,
                task_id=trace.resource_id,
            )
        return EvaluationObservation(
            trace_id=trace.id,
            execution_type=cast(ExecutionType, trace.execution_type),
            output_text=output_text,
            tool_names=tool_names,
            reference_count=reference_count,
            context_source_names=context_source_names,
            context_tokens=context_tokens,
            duration_ms=trace.duration_ms,
            trace_status=trace.status,
            memory_active_values=memory_active_values,
            memory_superseded_values=memory_superseded_values,
            memory_ungrounded_count=memory_ungrounded_count,
            memory_status=memory_status,
            memory_duration_ms=memory_duration_ms,
        )

    async def _resolve_chat_memory(
        self,
        *,
        owner_user_id: str,
        session_id: str,
    ) -> tuple[list[str], list[str], int, str | None]:
        session = await self._repositories.chat.get_session(
            owner_user_id=owner_user_id,
            session_id=session_id,
        )
        if session is None:
            raise EvaluationBindingError("Chat session is unavailable.")
        messages = await self._repositories.chat.list_messages(
            owner_user_id=owner_user_id,
            session_id=session_id,
        )
        snapshot = legacy_or_structured_snapshot(
            session.memory_snapshot,
            session.memory_summary,
        )
        ungrounded_count = 0
        try:
            validate_memory_snapshot(snapshot, messages)
        except MemorySnapshotValidationError:
            ungrounded_count = 1
        active = [f"{item.key}={item.value}" for item in snapshot.active_constraints]
        superseded = [f"{item.key}={item.value}" for item in snapshot.superseded_facts]
        return active, superseded, ungrounded_count, session.memory_status

    async def _resolve_chat_output(
        self, *, owner_user_id: str, session_id: str, trace_id: str
    ) -> tuple[str, int]:
        messages = await self._repositories.chat.list_messages(
            owner_user_id=owner_user_id, session_id=session_id
        )
        matches = [
            message
            for message in messages
            if message.role == "assistant" and message.metadata.get("traceId") == trace_id
        ]
        if not matches:
            raise EvaluationBindingError(f"Trace '{trace_id}' has no persisted assistant output.")
        message = matches[-1]
        citations = message.metadata.get("citations")
        count = len(cast(list[object], citations)) if isinstance(citations, list) else 0
        return message.content, count

    async def _resolve_aiops_output(
        self, *, owner_user_id: str, task_id: str
    ) -> tuple[str, int]:
        reports = await self._repositories.diagnostics.list_reports(
            owner_user_id=owner_user_id, task_id=task_id
        )
        if not reports:
            raise EvaluationBindingError(f"Diagnostic task '{task_id}' has no persisted report.")
        evidence = await self._repositories.diagnostics.list_evidence(
            owner_user_id=owner_user_id, task_id=task_id
        )
        return reports[-1].content, len(evidence)

    async def _resolve_aiops_context(
        self, *, owner_user_id: str, task_id: str
    ) -> tuple[list[str], int | None]:
        """Read safe P4 context facts from the latest persisted Planner snapshot."""
        steps = await self._repositories.diagnostics.list_steps(
            owner_user_id=owner_user_id,
            task_id=task_id,
        )
        for step in reversed(steps):
            if step.phase != "planner":
                continue
            raw_snapshot = step.payload.get("retrievalContext")
            if not isinstance(raw_snapshot, Mapping):
                continue
            snapshot = cast(Mapping[str, object], raw_snapshot)
            raw_selected = snapshot.get("selected")
            source_names: list[str] = []
            if isinstance(raw_selected, list):
                for raw_source in cast(list[object], raw_selected):
                    if not isinstance(raw_source, Mapping):
                        continue
                    source = cast(Mapping[str, object], raw_source).get("source")
                    if isinstance(source, str) and source.strip():
                        source_names.append(source.strip())
            raw_budget = snapshot.get("budget")
            if not isinstance(raw_budget, Mapping):
                return source_names, None
            used_tokens = cast(Mapping[str, object], raw_budget).get("usedTokens")
            return source_names, used_tokens if isinstance(used_tokens, int) else None
        return [], None


def _average(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _baseline_delta(
    baseline: EvaluationRunRecord | None,
    *,
    pass_rate: float,
    average_score: float,
    average_duration_ms: float | None,
    total_tool_calls: int,
) -> JsonDict:
    if baseline is None:
        return {}
    duration_percent: float | None = None
    if average_duration_ms is not None and baseline.average_duration_ms not in (None, 0):
        duration_percent = round(
            (average_duration_ms - baseline.average_duration_ms)
            / baseline.average_duration_ms
            * 100,
            4,
        )
    return {
        "passRatePoints": round((pass_rate - baseline.pass_rate) * 100, 4),
        "averageScorePoints": round((average_score - baseline.average_score) * 100, 4),
        "durationPercent": duration_percent,
        "toolCallCount": total_tool_calls - baseline.total_tool_calls,
    }
