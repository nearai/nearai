"""Add hub_secrets.

Revision ID: 47779d2b93f2
Revises: 03f8ea1f734d
Create Date: 2024-09-18 11:19:36.644411

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47779d2b93f2"
down_revision: Union[str, None] = "03f8ea1f734d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_secrets",
        sa.Column("owner_namespace", sa.String(255), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("owner_namespace", "namespace", "name", "version", "key"),
        sa.Index("ix_owner_namespace", "owner_namespace"),
    )


def downgrade() -> None:
    op.drop_table("hub_secrets")
