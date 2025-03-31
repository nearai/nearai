"""create delta tables.

Revision ID: 3dc05346cbff
Revises: 212e5ca48274
Create Date: 2024-10-14 21:33:45.820809
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3dc05346cbff"
down_revision: Union[str, None] = "fc7a0b228355"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deltas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("object", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("content", sa.JSON, nullable=True),
        sa.Column("step_details", sa.JSON, nullable=True),
        sa.Column("filename", sa.String(length=4096), nullable=True),
        sa.Column("run_id", sa.String(length=255), nullable=True),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
    )

    op.create_index("ix_deltas_run_id", "deltas", ["run_id"])
    op.create_index("ix_deltas_thread_id", "deltas", ["thread_id"])
    op.create_index("ix_deltas_message_id", "deltas", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_deltas_run_id", table_name="deltas")
    op.drop_index("ix_deltas_thread_id", table_name="deltas")
    op.drop_index("ix_deltas_message_id", table_name="deltas")

    op.drop_table("deltas")
