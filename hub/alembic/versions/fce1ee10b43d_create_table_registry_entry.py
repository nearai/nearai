"""Create table registry_entry.

Revision ID: fce1ee10b43d
Revises: 854b55665dda
Create Date: 2024-08-14 13:46:21.126581

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fce1ee10b43d"
down_revision: Union[str, None] = "854b55665dda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "registry_entry",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(255, collation="utf8mb4_unicode_ci"), nullable=False),
        sa.Column("time", sa.DateTime, nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("description", sa.String(255, collation="utf8mb4_unicode_ci"), nullable=False),
        sa.Column("details", sa.Text(collation="utf8mb4_unicode_ci"), nullable=True),
        sa.Column("show_entry", sa.Boolean, nullable=False),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    op.drop_table("registry_entry")
