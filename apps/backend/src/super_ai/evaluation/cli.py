"""Secretless offline entry point for deterministic evaluation fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from super_ai.evaluation.models import EvaluationGate, EvaluationObservation, EvaluationRule
from super_ai.evaluation.scoring import evaluate_gate, score_case


class OfflineCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    rules: list[EvaluationRule] = Field(min_length=1, max_length=20)
    observation: EvaluationObservation


class OfflineFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    gate: EvaluationGate
    cases: list[OfflineCase] = Field(min_length=1, max_length=100)


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic Agent evaluation fixture.")
    parser.add_argument("fixture", type=Path, help="Path to a strict JSON fixture")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)
    try:
        raw: Any = json.loads(args.fixture.read_text(encoding="utf-8"))
        fixture = OfflineFixture.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Invalid evaluation fixture: {exc}", file=sys.stderr)
        return 2

    case_reports: list[dict[str, object]] = []
    scores: list[float] = []
    passed = 0
    durations: list[int] = []
    for case in fixture.cases:
        score = score_case(case.rules, case.observation)
        scores.append(score.score)
        passed += int(score.passed)
        if case.observation.duration_ms is not None:
            durations.append(case.observation.duration_ms)
        case_reports.append(
            {
                "name": case.name,
                "traceId": case.observation.trace_id,
                "status": "passed" if score.passed else "failed",
                "score": score.score,
                "outputSummary": score.output_summary,
                "metrics": score.metrics,
                "checks": [check.model_dump(mode="json") for check in score.checks],
            }
        )
    pass_rate = passed / len(fixture.cases)
    average_score = sum(scores) / len(scores)
    gate = evaluate_gate(
        fixture.gate,
        pass_rate=pass_rate,
        average_score=average_score,
        duration_regression_percent=None,
    )
    report = {
        "fixture": fixture.name,
        "gateStatus": gate.status,
        "gateFailures": gate.failures,
        "passRate": round(pass_rate, 6),
        "averageScore": round(average_score, 6),
        "averageDurationMs": (
            round(sum(durations) / len(durations), 3) if durations else None
        ),
        "cases": case_reports,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if gate.status == "passed" else 1


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
