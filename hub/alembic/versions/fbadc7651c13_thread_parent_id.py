"""Thread parent_id.

Revision ID: fbadc7651c13
Revises: 26e1e353eb58
Create Date: 2025-01-30 22:10:25.268797

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fbadc7651c13"
down_revision: Union[str, None] = "26e1e353eb58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("thread", sa.Column("parent_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("thread", "parent_id")
