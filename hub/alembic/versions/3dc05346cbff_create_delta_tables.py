"""create delta tables.

Revision ID: 3dc05346cbff
Revises: 212e5ca48274
Create Date: 2024-10-14 21:33:45.820809
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "3dc05346cbff"
down_revision: Union[str, None] = "212e5ca48274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "deltas",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("object", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("content", sa.JSON, nullable=True),
        sa.Column("step_details", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("filename", sa.String(length=4096), nullable=True),
    )

def downgrade() -> None:
    op.drop_table("deltas")
