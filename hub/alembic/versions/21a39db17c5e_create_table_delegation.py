"""Create table delegation.

Revision ID: 21a39db17c5e
Revises: 7db898acfc13
Create Date: 2024-11-02 15:36:51.052100

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21a39db17c5e"
down_revision: Union[str, None] = "7db898acfc13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "delegation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("original_account_id", sa.String(255), nullable=False),
        sa.Column("delegation_account_id", sa.String(255), nullable=False),
        # If it is null it means that the delegation is permanent
        sa.Column("expires_at", sa.TIMESTAMP, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("delegation")
