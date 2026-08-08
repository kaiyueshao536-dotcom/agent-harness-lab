from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from alembic import command
from alembic.config import Config

from super_ai.api.app import create_app
from super_ai.evaluation.cli import run_cli
from super_ai.evaluation.models import (
    EvaluationCaseDefinition,
    EvaluationGate,
    EvaluationObservation,
    EvaluationRule,
)
from super_ai.evaluation.scoring import evaluate_gate, score_case
from super_ai.evaluation.service import EvaluationHarnessService
from super_ai.memory.database import create_memory_engine, create_memory_session_factory
from super_ai.memory.evaluation_sqlite import EvaluationDatasetVersionConflict
from super_ai.memory.repositories import EvaluationCaseDraft, EvaluationCaseResultDraft
from super_ai.memory.sqlite import create_sqlite_memory_repositories


def test_scoring_is_deterministic_explainable_and_limits_output_summary() -> None:
    rules = [
        EvaluationRule(kind="trace_succeeded"),
        EvaluationRule(kind="contains_all", values=["root cause"]),
        EvaluationRule(kind="excludes_all", values=["password"]),
        EvaluationRule(kind="required_tools", values=["SearchLog"]),
        EvaluationRule(kind="min_references", threshold=1),
        EvaluationRule(kind="max_duration_ms", threshold=2000),
        EvaluationRule(kind="max_tool_calls", threshold=2),
    ]
    observation = EvaluationObservation(
        trace_id="trace-1",
        execution_type="aiops",
        output_text=(
            "Root cause "
            + "api"
            + "Key=top-secret "
            + "sk-"
            + "secretvalue "
            + "safe " * 200
        ),
        tool_names=["SearchLog"],
        reference_count=2,
        duration_ms=1200,
        trace_status="succeeded",
    )

    first = score_case(rules, observation)
    second = score_case(rules, observation)

    assert first == second
    assert first.passed is True
    assert first.score == 1.0
    assert len(first.output_summary) == 500
    assert "top-secret" not in first.output_summary
    assert "sk-" + "secretvalue" not in first.output_summary
    assert "[redacted]" in first.output_summary
    assert all(check.passed for check in first.checks)
    assert "safe safe safe" not in str(first.checks)


def test_evidence_cautious_rule_rejects_zero_result_overclaim() -> None:
    rule = EvaluationRule(kind="evidence_cautious")
    cautious = EvaluationObservation(
        trace_id="trace-cautious",
        execution_type="aiops",
        output_text=(
            "SearchLog 当前查询未匹配到可解析日志；证据不足，无法确认原因。"
        ),
        tool_names=["SearchLog"],
        duration_ms=100,
        trace_status="succeeded",
    )
    overclaim = cautious.model_copy(
        update={
            "trace_id": "trace-overclaim",
            "output_text": (
                "SearchLog recordCount 为 0，这表明日志采集链路存在异常。"
            ),
        }
    )

    passed = score_case([rule], cautious)
    failed = score_case([rule], overclaim)

    assert passed.passed is True
    assert failed.passed is False
    assert failed.checks[0].kind == "evidence_cautious"
    assert "overclaims=[" in failed.checks[0].actual
    assert "采集链路存在异常" in failed.checks[0].actual


def test_offline_cli_uses_gate_exit_codes(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    pass_fixture = repository_root / "evals" / "fixtures" / "p2-smoke-pass.json"
    fail_fixture = repository_root / "evals" / "fixtures" / "p2-smoke-fail.json"
    report = tmp_path / "report.json"

    assert run_cli([str(pass_fixture), "--output", str(report)]) == 0
    assert '"gateStatus": "passed"' in report.read_text(encoding="utf-8")
    assert run_cli([str(fail_fixture), "--output", str(report)]) == 1
    assert '"gateStatus": "failed"' in report.read_text(encoding="utf-8")
    invalid_fixture = tmp_path / "invalid.json"
    invalid_fixture.write_text(
        '{"name":"invalid","gate":{},"cases":[{"name":"bad",'
        '"rules":[{"kind":"python_eval"}],"observation":{}}]}',
        encoding="utf-8",
    )
    assert run_cli([str(invalid_fixture), "--output", str(report)]) == 2


def test_p3_recovery_fixture_is_secretless_deterministic_and_passes(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    fixture = repository_root / "evals" / "fixtures" / "p3-tool-recovery-pass.json"
    report_a = tmp_path / "p3-report-a.json"
    report_b = tmp_path / "p3-report-b.json"

    raw_fixture = fixture.read_text(encoding="utf-8")
    assert "api_key" not in raw_fixture.casefold()
    assert "authorization" not in raw_fixture.casefold()
    assert "password" not in raw_fixture.casefold()
    assert '"secret"' not in raw_fixture.casefold()
    assert run_cli([str(fixture), "--output", str(report_a)]) == 0
    assert run_cli([str(fixture), "--output", str(report_b)]) == 0
    assert report_a.read_text(encoding="utf-8") == report_b.read_text(encoding="utf-8")


def test_p3_report_evidence_fixture_passes_offline_cli(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    fixture = repository_root / "evals" / "fixtures" / "p3-report-evidence-pass.json"
    report = tmp_path / "p3-report-evidence.json"

    assert run_cli([str(fixture), "--output", str(report)]) == 0
    payload = report.read_text(encoding="utf-8")
    assert '"gateStatus": "passed"' in payload
    assert '"kind": "evidence_cautious"' in payload


def test_duration_regression_fails_baseline_gate() -> None:
    result = evaluate_gate(
        EvaluationGate(
            min_pass_rate=1,
            min_average_score=1,
            max_duration_regression_percent=10,
        ),
        pass_rate=1,
        average_score=1,
        duration_regression_percent=15,
    )

    assert result.status == "failed"
    assert result.failures == ["duration regression 15.00% exceeds 10.00%"]


@pytest.mark.asyncio
async def test_repository_keeps_versions_immutable_and_owner_scoped(
    migrated_database_url: str,
) -> None:
    engine = create_memory_engine(migrated_database_url)
    repositories = create_sqlite_memory_repositories(create_memory_session_factory(engine))
    repository = repositories.evaluations
    assert repository is not None
    case = EvaluationCaseDraft(
        id="case-1",
        sequence=1,
        name="case",
        execution_type="chat",
        input_summary="summary",
        rules=[{"kind": "trace_succeeded", "values": [], "threshold": None}],
    )
    try:
        created = await repository.create_dataset(
            owner_user_id="owner-a",
            dataset_id="dataset-a",
            name="core",
            version="v1",
            description="",
            gate={"min_pass_rate": 1.0, "min_average_score": 1.0},
            cases=[case],
        )
        with pytest.raises(EvaluationDatasetVersionConflict):
            await repository.create_dataset(
                owner_user_id="owner-a",
                dataset_id="dataset-conflict",
                name="core",
                version="v1",
                description="changed",
                gate={},
                cases=[case],
            )
        hidden = await repository.get_dataset(
            owner_user_id="owner-b", dataset_id=created.id
        )
        own_cases = await repository.list_cases(
            owner_user_id="owner-a", dataset_id=created.id
        )
        trace_repository = repositories.agent_traces
        assert trace_repository is not None
        await trace_repository.create_trace(
            owner_user_id="owner-b",
            trace_id="owner-b-trace",
            execution_type="chat",
            resource_type="chat_session",
            resource_id="owner-b-session",
        )
        with pytest.raises(ValueError, match="Trace outside the owner scope"):
            await repository.create_run(
                owner_user_id="owner-a",
                run_id="cross-owner-run",
                dataset_id=created.id,
                candidate_label="invalid",
                baseline_run_id=None,
                gate_status="failed",
                pass_rate=0,
                average_score=0,
                average_duration_ms=None,
                total_tool_calls=0,
                baseline_delta={},
                gate_failures=["invalid"],
                results=[
                    EvaluationCaseResultDraft(
                        id="cross-owner-result",
                        case_id="case-1",
                        sequence=1,
                        trace_id="owner-b-trace",
                        status="failed",
                        score=0,
                        output_summary="",
                        metrics={},
                        checks=[],
                    )
                ],
            )
    finally:
        await engine.dispose()

    assert hidden is None
    assert [item.id for item in own_cases] == ["case-1"]


@pytest.mark.asyncio
async def test_aiops_trace_resolves_report_evidence_and_tool_spans(
    migrated_database_url: str,
) -> None:
    engine = create_memory_engine(migrated_database_url)
    repositories = create_sqlite_memory_repositories(create_memory_session_factory(engine))
    trace_repository = repositories.agent_traces
    assert trace_repository is not None
    try:
        await repositories.diagnostics.create_task(
            owner_user_id="aiops-owner",
            task_id="aiops-task",
            status="succeeded",
            query="diagnose latency",
        )
        await repositories.diagnostics.add_report(
            owner_user_id="aiops-owner",
            report_id="aiops-report",
            task_id="aiops-task",
            title="Diagnosis",
            content="The root cause is a saturated connection pool.",
        )
        await repositories.diagnostics.create_evidence(
            owner_user_id="aiops-owner",
            evidence_id="aiops-evidence",
            task_id="aiops-task",
            kind="log",
            source="cls",
            summary="Connection timeout evidence",
        )
        await trace_repository.create_trace(
            owner_user_id="aiops-owner",
            trace_id="aiops-trace",
            execution_type="aiops",
            resource_type="diagnostic_task",
            resource_id="aiops-task",
        )
        await trace_repository.create_span(
            owner_user_id="aiops-owner",
            trace_id="aiops-trace",
            span_id="aiops-tool",
            sequence=1,
            kind="tool",
            name="SearchLog",
        )
        await trace_repository.finalize_trace(
            owner_user_id="aiops-owner",
            trace_id="aiops-trace",
            status="succeeded",
        )
        await trace_repository.create_trace(
            owner_user_id="aiops-owner",
            trace_id="aiops-trace-failed",
            execution_type="aiops",
            resource_type="diagnostic_task",
            resource_id="aiops-task",
        )
        await trace_repository.finalize_trace(
            owner_user_id="aiops-owner",
            trace_id="aiops-trace-failed",
            status="failed",
            error_category="McpClientError",
        )
        service = EvaluationHarnessService(repositories)
        dataset = await service.create_dataset(
            owner_user_id="aiops-owner",
            name="aiops core",
            version="v1",
            description="",
            gate=EvaluationGate(),
            cases=[
                EvaluationCaseDefinition(
                    name="diagnosis",
                    execution_type="aiops",
                    input_summary="diagnose latency",
                    rules=[
                        EvaluationRule(kind="contains_all", values=["root cause"]),
                        EvaluationRule(kind="required_tools", values=["SearchLog"]),
                        EvaluationRule(kind="min_references", threshold=1),
                        EvaluationRule(kind="evidence_cautious"),
                        EvaluationRule(kind="trace_succeeded"),
                    ],
                )
            ],
        )
        evaluation_repository = repositories.evaluations
        assert evaluation_repository is not None
        case = (
            await evaluation_repository.list_cases(
                owner_user_id="aiops-owner", dataset_id=dataset.id
            )
        )[0]
        run = await service.run(
            owner_user_id="aiops-owner",
            dataset_id=dataset.id,
            candidate_label="P2",
            trace_bindings={case.id: "aiops-trace"},
        )
        failed_run = await service.run(
            owner_user_id="aiops-owner",
            dataset_id=dataset.id,
            candidate_label="P3 failed attempt",
            trace_bindings={case.id: "aiops-trace-failed"},
        )
    finally:
        await engine.dispose()

    assert run.gate_status == "passed"
    assert run.pass_rate == 1
    assert run.total_tool_calls == 1
    assert failed_run.gate_status == "failed"
    assert failed_run.pass_rate == 0


@pytest.mark.asyncio
async def test_evaluation_api_runs_real_trace_and_hides_owner_resources(
    migrated_database_url: str,
) -> None:
    app = create_app(database_url=migrated_database_url)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        owner = await _register(client, "eval-owner@example.com")
        other = await _register(client, "eval-other@example.com")
        owner_id = cast(dict[str, str], owner["user"])["id"]
        other_id = cast(dict[str, str], other["user"])["id"]

        engine = create_memory_engine(migrated_database_url)
        repositories = create_sqlite_memory_repositories(create_memory_session_factory(engine))
        trace_repository = repositories.agent_traces
        assert trace_repository is not None
        try:
            await repositories.chat.create_session(
                owner_user_id=owner_id, session_id="eval-session"
            )
            trace = await trace_repository.create_trace(
                owner_user_id=owner_id,
                trace_id="eval-trace",
                execution_type="chat",
                resource_type="chat_session",
                resource_id="eval-session",
            )
            await trace_repository.create_span(
                owner_user_id=owner_id,
                trace_id=trace.id,
                span_id="eval-tool-span",
                sequence=1,
                kind="tool",
                name="knowledge_search",
            )
            await trace_repository.finalize_trace(
                owner_user_id=owner_id,
                trace_id=trace.id,
                status="succeeded",
            )
            await trace_repository.create_trace(
                owner_user_id=other_id,
                trace_id="eval-trace-other-owner",
                execution_type="chat",
                resource_type="chat_session",
                resource_id="other-session",
            )
            await repositories.chat.append_message(
                owner_user_id=owner_id,
                message_id="eval-answer",
                session_id="eval-session",
                role="assistant",
                content="The root cause is documented.",
                metadata={"traceId": trace.id, "citations": [{"id": "citation-1"}]},
            )
            incompatible_trace = await trace_repository.create_trace(
                owner_user_id=owner_id,
                trace_id="eval-trace-aiops",
                execution_type="aiops",
                resource_type="diagnostic_task",
                resource_id="eval-task",
            )
            await trace_repository.finalize_trace(
                owner_user_id=owner_id,
                trace_id=incompatible_trace.id,
                status="succeeded",
            )
        finally:
            await engine.dispose()

        anonymous = await client.get("/evaluations/datasets")
        created = await client.post(
            "/evaluations/datasets",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "name": "core",
                "version": "v1",
                "description": "regression",
                "gate": {"minPassRate": 1, "minAverageScore": 1},
                "cases": [
                    {
                        "name": "grounded answer",
                        "executionType": "chat",
                        "inputSummary": "answer with evidence",
                        "rules": [
                            {"kind": "trace_succeeded"},
                            {"kind": "contains_all", "values": ["root cause"]},
                            {"kind": "required_tools", "values": ["knowledge_search"]},
                            {"kind": "min_references", "threshold": 1},
                        ],
                    }
                ],
            },
        )
        dataset = created.json()["data"]
        case_id = dataset["cases"][0]["id"]
        evaluated = await client.post(
            f"/evaluations/datasets/{dataset['id']}/runs",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "candidateLabel": "P2",
                "traceBindings": {case_id: "eval-trace"},
            },
        )
        baseline_run_id = evaluated.json()["data"]["run"]["id"]
        compared = await client.post(
            f"/evaluations/datasets/{dataset['id']}/runs",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "candidateLabel": "P2 compared",
                "baselineRunId": baseline_run_id,
                "traceBindings": {case_id: "eval-trace"},
            },
        )
        wrong_type = await client.post(
            f"/evaluations/datasets/{dataset['id']}/runs",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "candidateLabel": "wrong type",
                "traceBindings": {case_id: "eval-trace-aiops"},
            },
        )
        cross_owner_trace = await client.post(
            f"/evaluations/datasets/{dataset['id']}/runs",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "candidateLabel": "cross owner",
                "traceBindings": {case_id: "eval-trace-other-owner"},
            },
        )
        second_dataset_response = await client.post(
            "/evaluations/datasets",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "name": "core",
                "version": "v2",
                "description": "baseline boundary",
                "gate": {"minPassRate": 1, "minAverageScore": 1},
                "cases": [
                    {
                        "name": "other version",
                        "executionType": "chat",
                        "inputSummary": "same trace, different dataset",
                        "rules": [{"kind": "trace_succeeded"}],
                    }
                ],
            },
        )
        second_dataset = second_dataset_response.json()["data"]
        wrong_baseline = await client.post(
            f"/evaluations/datasets/{second_dataset['id']}/runs",
            headers=_headers(cast(str, owner["accessToken"])),
            json={
                "candidateLabel": "wrong baseline",
                "baselineRunId": baseline_run_id,
                "traceBindings": {second_dataset["cases"][0]["id"]: "eval-trace"},
            },
        )
        hidden = await client.get(
            f"/evaluations/runs/{evaluated.json()['data']['run']['id']}",
            headers=_headers(cast(str, other["accessToken"])),
        )

    assert anonymous.status_code == 401
    assert created.status_code == 200
    assert evaluated.status_code == 200
    assert evaluated.json()["data"]["run"]["gateStatus"] == "passed"
    assert evaluated.json()["data"]["results"][0]["score"] == 1.0
    assert compared.status_code == 200
    assert compared.json()["data"]["run"]["baselineRunId"] == baseline_run_id
    assert compared.json()["data"]["run"]["baselineDelta"]["passRatePoints"] == 0
    assert wrong_type.status_code == 400
    assert cross_owner_trace.status_code == 404
    assert wrong_baseline.status_code == 400
    assert hidden.status_code == 404


async def _register(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "displayName": "Evaluation User",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json()["data"])


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> str:
    database_path = tmp_path / "evaluation.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    return f"sqlite+aiosqlite:///{database_path}"
