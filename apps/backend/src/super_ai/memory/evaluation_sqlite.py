"""SQLite persistence for owner-scoped Agent evaluation artifacts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from super_ai.memory.models import (
    AgentTraceModel,
    EvaluationCaseModel,
    EvaluationCaseResultModel,
    EvaluationDatasetModel,
    EvaluationRunModel,
    utc_now,
)
from super_ai.memory.repositories import (
    EvaluationCaseDraft,
    EvaluationCaseRecord,
    EvaluationCaseResultDraft,
    EvaluationCaseResultRecord,
    EvaluationDatasetRecord,
    EvaluationRunRecord,
    JsonDict,
)


class EvaluationDatasetVersionConflict(ValueError):
    """Raised when an owner reuses a dataset name and version."""


class SQLiteEvaluationRepository:
    """Persist immutable datasets and completed evaluation runs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_dataset(
        self,
        *,
        owner_user_id: str,
        dataset_id: str,
        name: str,
        version: str,
        description: str,
        gate: JsonDict,
        cases: list[EvaluationCaseDraft],
        created_at: datetime | None = None,
    ) -> EvaluationDatasetRecord:
        timestamp = created_at or utc_now()
        row = EvaluationDatasetModel(
            id=dataset_id,
            owner_user_id=owner_user_id,
            name=name,
            version=version,
            description=description,
            gate=gate,
            created_at=timestamp,
        )
        case_rows = [
            EvaluationCaseModel(
                id=case.id,
                dataset_id=dataset_id,
                owner_user_id=owner_user_id,
                sequence=case.sequence,
                name=case.name,
                execution_type=case.execution_type,
                input_summary=case.input_summary,
                rules=case.rules,
                created_at=timestamp,
            )
            for case in cases
        ]
        async with self._session_factory() as session:
            session.add(row)
            session.add_all(case_rows)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise EvaluationDatasetVersionConflict(
                    f"Dataset '{name}' version '{version}' already exists."
                ) from exc
        return _dataset_record(row)

    async def get_dataset(
        self, *, owner_user_id: str, dataset_id: str
    ) -> EvaluationDatasetRecord | None:
        stmt = select(EvaluationDatasetModel).where(
            EvaluationDatasetModel.id == dataset_id,
            EvaluationDatasetModel.owner_user_id == owner_user_id,
        )
        async with self._session_factory() as session:
            row = (await session.scalars(stmt)).one_or_none()
        return _dataset_record(row) if row is not None else None

    async def list_datasets(self, *, owner_user_id: str) -> list[EvaluationDatasetRecord]:
        stmt = (
            select(EvaluationDatasetModel)
            .where(EvaluationDatasetModel.owner_user_id == owner_user_id)
            .order_by(EvaluationDatasetModel.created_at.desc(), EvaluationDatasetModel.id.desc())
        )
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_dataset_record(row) for row in rows]

    async def list_cases(
        self, *, owner_user_id: str, dataset_id: str
    ) -> list[EvaluationCaseRecord]:
        stmt = (
            select(EvaluationCaseModel)
            .where(
                EvaluationCaseModel.owner_user_id == owner_user_id,
                EvaluationCaseModel.dataset_id == dataset_id,
            )
            .order_by(EvaluationCaseModel.sequence.asc(), EvaluationCaseModel.id.asc())
        )
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_case_record(row) for row in rows]

    async def create_run(
        self,
        *,
        owner_user_id: str,
        run_id: str,
        dataset_id: str,
        candidate_label: str,
        baseline_run_id: str | None,
        gate_status: str,
        pass_rate: float,
        average_score: float,
        average_duration_ms: float | None,
        total_tool_calls: int,
        baseline_delta: JsonDict,
        gate_failures: list[str],
        results: list[EvaluationCaseResultDraft],
        created_at: datetime | None = None,
    ) -> EvaluationRunRecord:
        timestamp = created_at or utc_now()
        row = EvaluationRunModel(
            id=run_id,
            dataset_id=dataset_id,
            owner_user_id=owner_user_id,
            candidate_label=candidate_label,
            baseline_run_id=baseline_run_id,
            status="completed",
            gate_status=gate_status,
            pass_rate=pass_rate,
            average_score=average_score,
            average_duration_ms=average_duration_ms,
            total_tool_calls=total_tool_calls,
            baseline_delta=baseline_delta,
            gate_failures=gate_failures,
            failure_reason=None,
            created_at=timestamp,
            completed_at=timestamp,
        )
        result_rows = [
            EvaluationCaseResultModel(
                id=result.id,
                run_id=run_id,
                case_id=result.case_id,
                owner_user_id=owner_user_id,
                sequence=result.sequence,
                trace_id=result.trace_id,
                status=result.status,
                score=result.score,
                output_summary=result.output_summary,
                metrics=result.metrics,
                checks=result.checks,
                created_at=timestamp,
            )
            for result in results
        ]
        async with self._session_factory() as session:
            owned_dataset = await session.scalar(
                select(EvaluationDatasetModel).where(
                    EvaluationDatasetModel.id == dataset_id,
                    EvaluationDatasetModel.owner_user_id == owner_user_id,
                )
            )
            if owned_dataset is None:
                raise ValueError("Owned evaluation dataset does not exist.")
            if baseline_run_id is not None:
                baseline = await session.scalar(
                    select(EvaluationRunModel).where(
                        EvaluationRunModel.id == baseline_run_id,
                        EvaluationRunModel.owner_user_id == owner_user_id,
                        EvaluationRunModel.dataset_id == dataset_id,
                    )
                )
                if baseline is None:
                    raise ValueError("Owned baseline evaluation run does not exist.")
            case_ids = {result.case_id for result in results}
            owned_case_ids = set(
                (
                    await session.scalars(
                        select(EvaluationCaseModel.id).where(
                            EvaluationCaseModel.id.in_(case_ids),
                            EvaluationCaseModel.dataset_id == dataset_id,
                            EvaluationCaseModel.owner_user_id == owner_user_id,
                        )
                    )
                ).all()
            )
            if owned_case_ids != case_ids:
                raise ValueError("Evaluation results reference a case outside the owned dataset.")
            trace_ids = {result.trace_id for result in results}
            owned_trace_ids = set(
                (
                    await session.scalars(
                        select(AgentTraceModel.id).where(
                            AgentTraceModel.id.in_(trace_ids),
                            AgentTraceModel.owner_user_id == owner_user_id,
                        )
                    )
                ).all()
            )
            if owned_trace_ids != trace_ids:
                raise ValueError("Evaluation results reference a Trace outside the owner scope.")
            session.add(row)
            session.add_all(result_rows)
            await session.commit()
        return _run_record(row)

    async def get_run(
        self, *, owner_user_id: str, run_id: str
    ) -> EvaluationRunRecord | None:
        stmt = select(EvaluationRunModel).where(
            EvaluationRunModel.id == run_id,
            EvaluationRunModel.owner_user_id == owner_user_id,
        )
        async with self._session_factory() as session:
            row = (await session.scalars(stmt)).one_or_none()
        return _run_record(row) if row is not None else None

    async def list_runs(
        self, *, owner_user_id: str, dataset_id: str | None = None
    ) -> list[EvaluationRunRecord]:
        stmt = select(EvaluationRunModel).where(
            EvaluationRunModel.owner_user_id == owner_user_id
        )
        if dataset_id is not None:
            stmt = stmt.where(EvaluationRunModel.dataset_id == dataset_id)
        stmt = stmt.order_by(EvaluationRunModel.created_at.desc(), EvaluationRunModel.id.desc())
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_run_record(row) for row in rows]

    async def list_results(
        self, *, owner_user_id: str, run_id: str
    ) -> list[EvaluationCaseResultRecord]:
        stmt = (
            select(EvaluationCaseResultModel)
            .where(
                EvaluationCaseResultModel.owner_user_id == owner_user_id,
                EvaluationCaseResultModel.run_id == run_id,
            )
            .order_by(
                EvaluationCaseResultModel.sequence.asc(),
                EvaluationCaseResultModel.id.asc(),
            )
        )
        async with self._session_factory() as session:
            rows = list((await session.scalars(stmt)).all())
        return [_result_record(row) for row in rows]


def _dataset_record(row: EvaluationDatasetModel) -> EvaluationDatasetRecord:
    return EvaluationDatasetRecord(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        version=row.version,
        description=row.description,
        gate=dict(row.gate),
        created_at=_ensure_utc(row.created_at),
    )


def _case_record(row: EvaluationCaseModel) -> EvaluationCaseRecord:
    return EvaluationCaseRecord(
        id=row.id,
        dataset_id=row.dataset_id,
        owner_user_id=row.owner_user_id,
        sequence=row.sequence,
        name=row.name,
        execution_type=row.execution_type,
        input_summary=row.input_summary,
        rules=[dict(rule) for rule in row.rules],
        created_at=_ensure_utc(row.created_at),
    )


def _run_record(row: EvaluationRunModel) -> EvaluationRunRecord:
    return EvaluationRunRecord(
        id=row.id,
        dataset_id=row.dataset_id,
        owner_user_id=row.owner_user_id,
        candidate_label=row.candidate_label,
        baseline_run_id=row.baseline_run_id,
        status=row.status,
        gate_status=row.gate_status,
        pass_rate=row.pass_rate,
        average_score=row.average_score,
        average_duration_ms=row.average_duration_ms,
        total_tool_calls=row.total_tool_calls,
        baseline_delta=dict(row.baseline_delta),
        gate_failures=list(row.gate_failures),
        failure_reason=row.failure_reason,
        created_at=_ensure_utc(row.created_at),
        completed_at=_ensure_utc_optional(row.completed_at),
    )


def _result_record(row: EvaluationCaseResultModel) -> EvaluationCaseResultRecord:
    return EvaluationCaseResultRecord(
        id=row.id,
        run_id=row.run_id,
        case_id=row.case_id,
        owner_user_id=row.owner_user_id,
        sequence=row.sequence,
        trace_id=row.trace_id,
        status=row.status,
        score=row.score,
        output_summary=row.output_summary,
        metrics=dict(row.metrics),
        checks=[dict(check) for check in row.checks],
        created_at=_ensure_utc(row.created_at),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ensure_utc_optional(value: datetime | None) -> datetime | None:
    return _ensure_utc(value) if value is not None else None
