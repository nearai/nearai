"""Create fork table.

Revision ID: 7255ee296766
Revises: e7197522ba61
Create Date: 2024-12-13 09:44:03.353472

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7255ee296766"
down_revision: Union[str, None] = "e7197522ba61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forks",
        sa.Column("category", sa.String(255), primary_key=True),
        sa.Column("from_namespace", sa.String(255), nullable=False),
        sa.Column("from_name", sa.String(255), nullable=False),
        sa.Column("to_namespace", sa.String(255), primary_key=True),
        sa.Column("to_name", sa.String(255), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("forks")
