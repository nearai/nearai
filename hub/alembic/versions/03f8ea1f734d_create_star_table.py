"""Create star table.

Revision ID: 03f8ea1f734d
Revises: c113977726a9
Create Date: 2024-09-12 20:28:29.742770

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03f8ea1f734d"
down_revision: Union[str, None] = "c113977726a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stars",
        sa.Column("account_id", sa.String(255), primary_key=True),
        sa.Column("namespace", sa.String(255), primary_key=True),
        sa.Column("name", sa.String(255), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("stars")
