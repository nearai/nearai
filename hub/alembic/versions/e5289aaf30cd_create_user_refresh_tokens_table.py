"""create user refresh tokens table.

Revision ID: e5289aaf30cd
Revises: 433258af63ec
Create Date: 2025-03-14 10:09:08.658476

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5289aaf30cd"
down_revision: Union[str, None] = "433258af63ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_refresh_tokens",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, comment="UTC timestamp"),
    )


def downgrade() -> None:
    op.drop_table("user_refresh_tokens")
