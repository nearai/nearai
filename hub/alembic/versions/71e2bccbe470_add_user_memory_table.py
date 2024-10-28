"""add user memory table.

Revision ID: 71e2bccbe470
Revises: 212e5ca48274
Create Date: 2024-10-25 16:11:21.155877

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71e2bccbe470"
down_revision: Union[str, None] = "212e5ca48274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_memory",
        sa.Column("account_id", sa.String(length=64), primary_key=True),
        sa.Column("vector_store_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_memory")
