"""add from run id in run model.

Revision ID: 69282cae1700
Revises: 21a39db17c5e
Create Date: 2024-11-04 23:39:14.339069

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69282cae1700"
down_revision: Union[str, None] = "21a39db17c5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("parent_run_id", sa.String(length=50), nullable=True))
    op.add_column("runs", sa.Column("child_run_ids", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "parent_run_id")
    op.drop_column("runs", "child_run_ids")
