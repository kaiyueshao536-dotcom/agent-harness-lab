"""add unified Agent traces

Revision ID: 202608060001
Revises: 202607110007
Create Date: 2026-08-06 21:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "202608060001"
down_revision: str | None = "202607110007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column("execution_type", sa.String(length=40), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_category", sa.String(length=160), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_traces_owner_user_id", "agent_traces", ["owner_user_id"])
    op.create_index(
        "ix_agent_traces_owner_started", "agent_traces", ["owner_user_id", "started_at"]
    )
    op.create_index(
        "ix_agent_traces_owner_resource_started",
        "agent_traces",
        ["owner_user_id", "resource_type", "resource_id", "started_at"],
    )
    op.create_index(
        "ix_agent_traces_owner_status_started",
        "agent_traces",
        ["owner_user_id", "status", "started_at"],
    )
    op.create_table(
        "agent_trace_spans",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=80), nullable=False),
        sa.Column(
            "trace_id",
            sa.String(length=80),
            sa.ForeignKey("agent_traces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_span_id",
            sa.String(length=80),
            sa.ForeignKey("agent_trace_spans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_id", sa.String(length=160), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("trace_id", "sequence", name="uq_agent_trace_spans_trace_sequence"),
    )
    op.create_index(
        "ix_agent_trace_spans_owner_user_id", "agent_trace_spans", ["owner_user_id"]
    )
    op.create_index("ix_agent_trace_spans_trace_id", "agent_trace_spans", ["trace_id"])
    op.create_index(
        "ix_agent_trace_spans_owner_trace_sequence",
        "agent_trace_spans",
        ["owner_user_id", "trace_id", "sequence"],
    )
    op.create_index(
        "ix_agent_trace_spans_trace_external",
        "agent_trace_spans",
        ["trace_id", "external_id"],
    )


def downgrade() -> None:
    op.drop_table("agent_trace_spans")
    op.drop_table("agent_traces")
