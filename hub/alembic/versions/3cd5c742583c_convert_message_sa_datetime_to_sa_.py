"""Convert Message sa.DateTime to sa.Timestamp.

Revision ID: 3cd5c742583c
Revises: 26e1e353eb58
Create Date: 2025-02-05 14:13:17.636820

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "3cd5c742583c"
down_revision: Union[str, None] = "26e1e353eb58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("created_at_temp", mysql.TIMESTAMP(fsp=6), server_default=sa.func.now()))
    op.execute("UPDATE messages SET created_at_temp = created_at")
    op.drop_column("messages", "created_at")
    op.add_column("messages", sa.Column("created_at", mysql.TIMESTAMP(fsp=6), server_default=sa.func.now()))
    op.execute("UPDATE messages SET created_at = created_at_temp")
    op.drop_column("messages", "created_at_temp")


def downgrade() -> None:
    op.add_column("messages", sa.Column("created_at_temp", sa.DateTime, server_default=sa.func.now()))
    op.execute("UPDATE messages SET created_at_temp = created_at")
    op.drop_column("messages", "created_at")
    op.add_column("messages", sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    op.execute("UPDATE messages SET created_at = created_at_temp")
    op.drop_column("messages", "created_at_temp")
