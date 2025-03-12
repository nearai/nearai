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
down_revision: Union[str, None] = "3cd5c742583c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("threads", sa.Column("parent_id", sa.String(length=50), nullable=True))
    op.add_column("threads", sa.Column("child_thread_ids", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("threads", "parent_id")
    op.drop_column("threads", "child_thread_ids")
