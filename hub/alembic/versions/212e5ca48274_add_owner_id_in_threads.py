"""add owner id in threads.

Revision ID: 212e5ca48274
Revises: ed386550be0f
Create Date: 2024-10-23 21:09:32.385961

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "212e5ca48274"
down_revision: Union[str, None] = "ed386550be0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("threads", sa.Column("owner_id", sa.String(255), nullable=False))


def downgrade() -> None:
    op.drop_column("threads", "owner_id")
