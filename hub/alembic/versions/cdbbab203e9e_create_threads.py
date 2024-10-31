"""create threads.

Revision ID: cdbbab203e9e
Revises: 47779d2b93f2
Create Date: 2024-10-04 11:58:08.023891

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cdbbab203e9e"
down_revision: Union[str, None] = "47779d2b93f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "threads",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("object", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("tool_resources", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("threads")
