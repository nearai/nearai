"""create_table_vector_stores_files.

Revision ID: ed88d0518db4
Revises: 3242c0b2d216
Create Date: 2024-08-23 15:05:20.984753

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed88d0518db4"
down_revision: Union[str, None] = "3242c0b2d216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vector_store_files",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("file_uri", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("encoding", sa.String(20), nullable=True),
        sa.Column("embedding_status", sa.String(20)),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp(),
        ),
    )

    # Add index for filtering by account_id
    op.create_index("idx_vector_store_files_account_id", "vector_store_files", ["account_id"])


def downgrade() -> None:
    # Remove the index first
    op.drop_index("idx_vector_store_files_account_id", table_name="vector_store_files")

    # Then drop the table
    op.drop_table("vector_store_files")
