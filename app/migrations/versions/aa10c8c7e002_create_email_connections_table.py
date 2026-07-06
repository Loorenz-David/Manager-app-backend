"""create_email_connections_table

Revision ID: aa10c8c7e002
Revises: aa10c8c7e001
Create Date: 2026-07-04 13:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "aa10c8c7e002"
down_revision: Union[str, None] = "aa10c8c7e001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_connections",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("email_address", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("smtp_host", sa.String(length=255), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_security", sa.String(length=16), nullable=False),
        sa.Column("smtp_username", sa.String(length=255), nullable=False),
        sa.Column("smtp_password_encrypted", sa.String(length=512), nullable=False),
        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False),
        sa.Column("imap_security", sa.String(length=16), nullable=False),
        sa.Column("imap_username", sa.String(length=255), nullable=False),
        sa.Column("imap_password_encrypted", sa.String(length=512), nullable=False),
        sa.Column("inbox_folder", sa.String(length=128), server_default="INBOX", nullable=False),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.client_id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"]),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(op.f("ix_email_connections_owner_user_id"), "email_connections", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_email_connections_status"), "email_connections", ["status"], unique=False)
    op.create_index(op.f("ix_email_connections_workspace_id"), "email_connections", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_connections_workspace_id"), table_name="email_connections")
    op.drop_index(op.f("ix_email_connections_status"), table_name="email_connections")
    op.drop_index(op.f("ix_email_connections_owner_user_id"), table_name="email_connections")
    op.drop_table("email_connections")
