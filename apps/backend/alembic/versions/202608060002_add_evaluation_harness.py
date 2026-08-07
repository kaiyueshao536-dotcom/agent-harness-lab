"""add Agent evaluation harness

Revision ID: 202608060002
Revises: 202608060001
Create Date: 2026-08-06 22:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "202608060002"
down_revision: str | None = "202608060001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("gate", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "owner_user_id",
            "name",
            "version",
            name="uq_evaluation_datasets_owner_name_version",
        ),
    )
    op.create_index(
        "ix_evaluation_datasets_owner_user_id", "evaluation_datasets", ["owner_user_id"]
    )
    op.create_index(
        "ix_evaluation_datasets_owner_created",
        "evaluation_datasets",
        ["owner_user_id", "created_at"],
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=80),
            sa.ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("execution_type", sa.String(length=40), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_id", "sequence", name="uq_evaluation_cases_sequence"),
    )
    op.create_index("ix_evaluation_cases_dataset_id", "evaluation_cases", ["dataset_id"])
    op.create_index(
        "ix_evaluation_cases_owner_user_id", "evaluation_cases", ["owner_user_id"]
    )
    op.create_index(
        "ix_evaluation_cases_owner_dataset_sequence",
        "evaluation_cases",
        ["owner_user_id", "dataset_id", "sequence"],
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=80),
            sa.ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("candidate_label", sa.String(length=160), nullable=False),
        sa.Column(
            "baseline_run_id",
            sa.String(length=80),
            sa.ForeignKey("evaluation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("gate_status", sa.String(length=40), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.Column("average_duration_ms", sa.Float(), nullable=True),
        sa.Column("total_tool_calls", sa.Integer(), nullable=False),
        sa.Column("baseline_delta", sa.JSON(), nullable=False),
        sa.Column("gate_failures", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evaluation_runs_dataset_id", "evaluation_runs", ["dataset_id"])
    op.create_index(
        "ix_evaluation_runs_owner_user_id", "evaluation_runs", ["owner_user_id"]
    )
    op.create_index(
        "ix_evaluation_runs_baseline_run_id", "evaluation_runs", ["baseline_run_id"]
    )
    op.create_index(
        "ix_evaluation_runs_owner_created",
        "evaluation_runs",
        ["owner_user_id", "created_at"],
    )
    op.create_index(
        "ix_evaluation_runs_owner_dataset_created",
        "evaluation_runs",
        ["owner_user_id", "dataset_id", "created_at"],
    )

    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=80),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            sa.String(length=80),
            sa.ForeignKey("evaluation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "trace_id",
            sa.String(length=80),
            sa.ForeignKey("agent_traces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "case_id", name="uq_evaluation_case_results_run_case"),
    )
    op.create_index(
        "ix_evaluation_case_results_run_id", "evaluation_case_results", ["run_id"]
    )
    op.create_index(
        "ix_evaluation_case_results_case_id", "evaluation_case_results", ["case_id"]
    )
    op.create_index(
        "ix_evaluation_case_results_owner_user_id",
        "evaluation_case_results",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_evaluation_case_results_trace_id", "evaluation_case_results", ["trace_id"]
    )
    op.create_index(
        "ix_evaluation_case_results_owner_run_sequence",
        "evaluation_case_results",
        ["owner_user_id", "run_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_datasets")
