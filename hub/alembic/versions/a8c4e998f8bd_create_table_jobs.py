"""Create table jobs.

Revision ID: a8c4e998f8bd
Revises: 71e2bccbe470
Create Date: 2024-10-23 11:32:24.054255

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c4e998f8bd"
down_revision: Union[str, None] = "71e2bccbe470"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("registry_path", sa.String(255), nullable=False),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(255), nullable=False),
        sa.Column("worker_id", sa.String(255), nullable=True),
        sa.Column("info", sa.JSON),
        sa.Column("result", sa.JSON),
    )


def downgrade() -> None:
    op.drop_table("jobs")
