"""Agent key value storage.

Revision ID: c5af2948a246
Revises: 7255ee296766
Create Date: 2024-12-20 13:06:55.971788

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5af2948a246"
down_revision: Union[str, None] = "7255ee296766"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_data",
        sa.Column("namespace", sa.String(length=255), primary_key=True),
        sa.Column("name", sa.String(length=255), primary_key=True),
        sa.Column("key", sa.String(length=255), primary_key=True),
        sa.Column("value", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_data")
