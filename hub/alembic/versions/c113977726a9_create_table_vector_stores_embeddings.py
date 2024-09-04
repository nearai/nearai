"""create_table_embeddings.

Revision ID: c113977726a9
Revises: ed88d0518db4
Create Date: 2024-08-29 08:56:41.993509

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import UserDefinedType

# revision identifiers, used by Alembic.
revision: str = "c113977726a9"
down_revision: Union[str, None] = "ed88d0518db4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class VECTOR(UserDefinedType):
    def __init__(self, length):  # noqa: D107
        self.length = length

    def get_col_spec(self):  # noqa: D102
        return f"VECTOR({self.length})"


def upgrade() -> None:
    # Create vector_store_embeddings table
    op.create_table(
        "vector_store_embeddings",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("vector_store_id", sa.String(64), nullable=False),
        sa.Column("file_id", sa.String(64), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", VECTOR(768), nullable=False),  # Nomic AI dimension in 768.
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index("idx_vector_store_embeddings_vector_store_id", "vector_store_embeddings", ["vector_store_id"])
    op.create_index("idx_vector_store_embeddings_file_id", "vector_store_embeddings", ["file_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_vector_store_embeddings_file_id", table_name="vector_store_embeddings")
    op.drop_index("idx_vector_store_embeddings_vector_store_id", table_name="vector_store_embeddings")

    # Drop vector_store_embeddings table
    op.drop_table("vector_store_embeddings")
