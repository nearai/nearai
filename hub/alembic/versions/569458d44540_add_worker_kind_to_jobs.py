"""Add worker kind to jobs.

Revision ID: 569458d44540
Revises: 69282cae1700
Create Date: 2024-11-08 22:42:09.389676

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "569458d44540"
down_revision: Union[str, None] = "69282cae1700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("worker_kind", sa.String(length=50), nullable=False, default="any"))


def downgrade() -> None:
    op.drop_column("jobs", "worker_kind")
