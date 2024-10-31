"""create runs.

Revision ID: ed386550be0f
Revises: ad509423386a
Create Date: 2024-10-08 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed386550be0f"
down_revision: Union[str, None] = "ad509423386a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("object", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("assistant_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("cancelled_at", sa.DateTime, nullable=True),
        sa.Column("failed_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("last_error", sa.JSON, nullable=True),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("tools", sa.JSON, nullable=True),
        sa.Column("file_ids", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("usage", sa.JSON, nullable=True),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("top_p", sa.Float, nullable=True),
        sa.Column("max_prompt_tokens", sa.Integer, nullable=True),
        sa.Column("max_completion_tokens", sa.Integer, nullable=True),
        sa.Column("truncation_strategy", sa.JSON, nullable=True),
        sa.Column("response_format", sa.String(length=50), nullable=True),
        sa.Column("tool_choice", sa.String(length=50), nullable=True),
        sa.Column("parallel_tool_calls", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "required_action", sa.JSON, nullable=True
        ),  # https://platform.openai.com/docs/assistants/tools/function-calling/step-3-initiate-a-run
    )


def downgrade() -> None:
    op.drop_table("runs")
