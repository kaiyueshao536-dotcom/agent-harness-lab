"""add Chat memory lifecycle state

Revision ID: 202608090001
Revises: 202608060002
Create Date: 2026-08-09 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "202608090001"
down_revision: str | None = "202608060002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.add_column(sa.Column("memory_snapshot", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("memory_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "memory_status", sa.String(length=40), nullable=False, server_default="idle"
            )
        )
        batch_op.add_column(
            sa.Column("memory_error_category", sa.String(length=160), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_memory_attempt_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.drop_column("last_memory_attempt_at")
        batch_op.drop_column("memory_error_category")
        batch_op.drop_column("memory_status")
        batch_op.drop_column("memory_version")
        batch_op.drop_column("memory_snapshot")
