"""create messages.

Revision ID: ad509423386a
Revises: cdbbab203e9e
Create Date: 2024-10-04 11:59:28.985445

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad509423386a"
down_revision: Union[str, None] = "cdbbab203e9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("object", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("thread_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("incomplete_details", sa.JSON, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("incomplete_at", sa.DateTime, nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.JSON, nullable=False),
        sa.Column("assistant_id", sa.String(length=255), nullable=True),
        sa.Column("run_id", sa.String(length=255), nullable=True),
        sa.Column("attachments", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
    )

    # Create an index on thread_id for faster queries
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_thread_id", table_name="messages")
    op.drop_table("messages")
