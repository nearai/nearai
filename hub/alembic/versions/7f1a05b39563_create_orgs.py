"""Create orgs.

Revision ID: 7f1a05b39563
Revises: 1debe4dbbce1
Create Date: 2025-03-10 16:20:41.667957

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects.mysql import ENUM

# revision identifiers, used by Alembic.
revision: str = "7f1a05b39563"
down_revision: Union[str, None] = "1debe4dbbce1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Step 1: Create organization tables first
    op.create_table(
        "orgs",
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Unique organization identifier (matches registry_entry.namespace)",
        ),
        sa.Column("display_name", sa.String(255), nullable=False, comment="Human-readable organization name"),
        sa.Column("created_by", sa.String(255), nullable=False, comment="NEAR account of the creator"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Organization creation time",
        ),
        sa.Column("meta", mysql.LONGTEXT(), nullable=True, comment="JSON metadata for custom configurations"),
        sa.PrimaryKeyConstraint("name"),
        mysql_collate="utf8mb4_unicode_ci",
        comment="Organizations that can own registry entries",
    )

    op.create_table(
        "org_members",
        sa.Column("org_name", sa.String(255), nullable=False, comment="Reference to orgs.name"),
        sa.Column("member_id", sa.String(255), nullable=False, comment="NEAR account of the member"),
        sa.Column(
            "role",
            ENUM("admin", "maintainer", "member", name="org_roles"),
            nullable=False,
            server_default="member",
            comment="Base role for access control",
        ),
        sa.Column("permissions", mysql.LONGTEXT(), nullable=True, comment="JSON array of granular permissions"),
        sa.Column(
            "joined_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Membership start time",
        ),
        sa.ForeignKeyConstraint(["org_name"], ["orgs.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("org_name", "member_id"),
        mysql_collate="utf8mb4_unicode_ci",
        comment="Organization members and their permissions",
    )

    op.create_table(
        "org_invitations",
        sa.Column("id", sa.String(32), nullable=False, comment="Unique invitation ID"),
        sa.Column("org_name", sa.String(255), nullable=False, comment="Reference to orgs.name"),
        sa.Column("inviter_id", sa.String(255), nullable=False, comment="NEAR account of the inviter"),
        sa.Column("invitee_id", sa.String(255), nullable=False, comment="NEAR account being invited"),
        sa.Column(
            "role", ENUM("admin", "maintainer", "member", name="org_roles"), nullable=False, server_default="member"
        ),
        sa.Column("permissions", mysql.LONGTEXT(), nullable=True, comment="JSON array of permissions to grant"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="Invitation expiration time"),
        sa.Column(
            "status",
            ENUM("pending", "accepted", "revoked", name="invitation_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.ForeignKeyConstraint(["org_name"], ["orgs.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        mysql_collate="utf8mb4_unicode_ci",
        comment="Pending organization invitations",
    )

    # Step 2: Modify main tables using shadow table pattern
    # RegistryEntry modifications
    op.create_table(
        "registry_entry_new",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False, comment="Owner namespace (user or org)"),
        sa.Column(
            "owner_type",
            ENUM("user", "org", name="owner_type"),
            nullable=False,
            server_default="user",
            comment="Type of namespace owner",
        ),
        sa.Column("author", sa.String(255), nullable=True, comment="Original author for org-owned entries"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(255), nullable=False),
        sa.Column("time", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("details", mysql.LONGTEXT(), nullable=True),
        sa.Column("show_entry", sa.Boolean(), nullable=False),
        sa.Index("idx_namespace_owner_type", "namespace", "owner_type", unique=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_collate="utf8mb4_unicode_ci",
    )

    # Copy data with default values
    op.execute("""
        INSERT INTO registry_entry_new
            (id, namespace, owner_type, author, name, version, time,
             description, category, details, show_entry)
        SELECT
            id,
            namespace,
            'user' as owner_type,
            null as author,
            name,
            version,
            time,
            description,
            category,
            details,
            show_entry
        FROM registry_entry
    """)

    # Replace old table
    op.drop_table("registry_entry")
    op.rename_table("registry_entry_new", "registry_entry")

    # Repeat similar pattern for other tables...
    # AgentData modifications
    op.create_table(
        "agent_data_new",
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("owner_type", ENUM("user", "org", name="owner_types"), nullable=False, server_default="user"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", mysql.LONGTEXT(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("namespace", "name", "key"),
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.execute("""
            INSERT INTO agent_data_new
                (namespace, owner_type, name, key, value, created_at, updated_at)
            SELECT
                namespace,
                'user',
                name,
                key,
                value,
                created_at,
                updated_at
            FROM agent_data
        """)

    op.drop_table("agent_data")
    op.rename_table("agent_data_new", "agent_data")


def downgrade():
    # Reverse registry_entry changes
    op.create_table(
        "registry_entry_old",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(255), nullable=False),
        sa.Column("time", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("details", mysql.LONGTEXT(), nullable=True),
        sa.Column("show_entry", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_collate="utf8mb4_unicode_ci",
    )

    op.execute("""
        INSERT INTO registry_entry_old
            (id, namespace, name, version, time, description, category, details, show_entry)
        SELECT
            id,
            namespace,
            name,
            version,
            time,
            description,
            category,
            details,
            show_entry
        FROM registry_entry
    """)

    op.drop_table("registry_entry")
    op.rename_table("registry_entry_old", "registry_entry")

    # Drop organization-related tables
    op.drop_table("org_invitations")
    op.drop_table("org_members")
    op.drop_table("orgs")

    # Drop ENUM types if supported
    op.execute("DROP TYPE IF EXISTS owner_types")
    op.execute("DROP TYPE IF EXISTS org_roles")
    op.execute("DROP TYPE IF EXISTS invitation_status")
