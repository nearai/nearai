"""Agent key value storage.

Revision ID: 531422e5c684
Revises: e7197522ba61
Create Date: 2024-12-17 16:41:32.671496

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "531422e5c684"
down_revision: Union[str, None] = "e7197522ba61"
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
