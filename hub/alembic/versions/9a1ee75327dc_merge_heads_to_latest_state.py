"""Merge heads to latest state.

Revision ID: 9a1ee75327dc
Revises: 1debe4dbbce1, 3dc05346cbff
Create Date: 2025-03-24 12:40:20.592699

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9a1ee75327dc'
down_revision: Union[str, None] = ('1debe4dbbce1', '3dc05346cbff')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
