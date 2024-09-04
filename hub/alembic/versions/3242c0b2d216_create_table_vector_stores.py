"""create_table_vector_stores.

Revision ID: 3242c0b2d216
Revises: dbeaf5dc234c
Create Date: 2024-08-22 10:29:50.522409

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3242c0b2d216"
down_revision: Union[str, None] = "dbeaf5dc234c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vector_stores",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("file_ids", sa.JSON, nullable=False),
        sa.Column("expires_after", sa.JSON, nullable=False),
        sa.Column("chunking_strategy", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("embedding_model", sa.String(255), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
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
    op.create_index("idx_vector_stores_account_id", "vector_stores", ["account_id"])


def downgrade() -> None:
    # Remove the index first
    op.drop_index("idx_vector_stores_account_id", table_name="vector_stores")

    # Then drop the table
    op.drop_table("vector_stores")
