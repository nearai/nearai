"""run_mode.

Revision ID: e8c084b2232b
Revises: fbadc7651c13
Create Date: 2025-02-14 15:39:46.888615

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8c084b2232b"
down_revision: Union[str, None] = "fbadc7651c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("run_mode", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "run_mode")
