"""create run_scheduler table.

Revision ID: 26e1e353eb58
Revises: c5af2948a246
Create Date: 2025-01-13 14:57:15.478166

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "26e1e353eb58"
down_revision: Union[str, None] = "c5af2948a246"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("agent", sa.Text, nullable=False),
        sa.Column("input_message", sa.Text, nullable=False),
        sa.Column("run_params", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("run_at", sa.DateTime, nullable=False, index=True),
        sa.Column("has_run", sa.Boolean, server_default=sa.false(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("scheduled_runs")
