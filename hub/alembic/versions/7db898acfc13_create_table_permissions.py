"""Create table permissions.

Revision ID: 7db898acfc13
Revises: a8c4e998f8bd
Create Date: 2024-10-23 12:11:19.859286

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7db898acfc13"
down_revision: Union[str, None] = "a8c4e998f8bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("permission", sa.String(255), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("permissions")
