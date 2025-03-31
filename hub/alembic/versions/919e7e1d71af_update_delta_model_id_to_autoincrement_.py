"""Update Delta model id to autoincrement integer and remove metadata in favor of specific fields.

Revision ID: 919e7e1d71af
Revises: 9a1ee75327dc
Create Date: 2025-03-24 12:43:51.123099

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "919e7e1d71af"
down_revision: Union[str, None] = "9a1ee75327dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a new table (temporary) with the updated schema.
    op.create_table(
        "deltas_new",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("object", sa.String(length=50), nullable=False, server_default="thread.message.delta"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("run_id", sa.String(length=255), nullable=True),
        sa.Column("thread_id", sa.String(length=255), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
    )
    # Create indexes on the new columns as required.
    op.create_index("ix_deltas_run_id", "deltas_new", ["run_id"])
    op.create_index("ix_deltas_thread_id", "deltas_new", ["thread_id"])
    op.create_index("ix_deltas_message_id", "deltas_new", ["message_id"])

    # Copy data from the old table into the new table.
    # Only the columns common to both schemas are migrated.
    op.execute("""
        INSERT INTO deltas_new (object, created_at, content)
        SELECT object, created_at, content FROM deltas
    """)
    # Drop the old table.
    op.drop_table("deltas")
    # Rename the new table to the original name.
    op.rename_table("deltas_new", "deltas")


def downgrade() -> None:
    # Recreate the old table schema.
    op.create_table(
        "deltas_old",
        sa.Column("id", sa.String(30), primary_key=True),
        sa.Column("object", sa.String(), nullable=False, server_default="thread.message.delta"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("step_details", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("filename", sa.String(), nullable=True),
    )
    # Migrate data back from the current table.
    # Since the old primary key and extra columns were dropped, we generate a new id;
    # data for step_details, metadata, and filename cannot be recovered (set as NULL).
    op.execute("""
        INSERT INTO deltas_old (id, object, created_at, content, step_details, metadata, filename)
        SELECT CONCAT('delta_', LPAD(CAST(id AS CHAR), 24, '0')), object, created_at, content, NULL, NULL, NULL
        FROM deltas
    """)
    op.drop_table("deltas")
    op.rename_table("deltas_old", "deltas")
