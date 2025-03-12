"""Create table logs.

Revision ID: e7197522ba61
Revises: 569458d44540
Create Date: 2024-11-09 14:16:38.242392

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7197522ba61"
down_revision: Union[str, None] = "569458d44540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("target", sa.Text, nullable=False),
        sa.Column("info", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("logs")
