"""create users table.

Revision ID: 433258af63ec
Revises: 1debe4dbbce1
Create Date: 2025-03-13 12:26:48.714509

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "433258af63ec"
down_revision: Union[str, None] = "1debe4dbbce1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
            comment="Unique, immutable, internal user ID",
        ),
        sa.Column(
            "namespace",
            sa.String(64),
            index=True,
            comment="Unique, human-readable, public user ID (used for display and urls)",
        ),
        sa.Column(
            "near_account_id",
            sa.String(64),
            comment="Unique NEAR account ID linked to this account via signed messaged login",
        ),
        sa.Column(
            "email",
            sa.String(255),
            comment="Unique email linked to this account via social login (google/github)",
        ),
        sa.Column(
            "avatar_url",
            sa.Text,
        ),
        sa.Column(
            "is_anonymous",
            sa.Boolean,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, comment="UTC timestamp"),
    )


def downgrade() -> None:
    op.drop_table("users")
