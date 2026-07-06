"""create_email_messages_table

Revision ID: aa10c8c7e006
Revises: aa10c8c7e005
Create Date: 2026-07-04 13:25:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "aa10c8c7e006"
down_revision: Union[str, None] = "aa10c8c7e005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_messages",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("provider_folder", sa.String(length=128), nullable=True),
        sa.Column("provider_uid", sa.String(length=32), nullable=True),
        sa.Column("from_address", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("to_addresses_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cc_addresses_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bcc_addresses_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("body_preview", sa.String(length=300), nullable=True),
        sa.Column("rfc_message_id", sa.String(length=512), nullable=True),
        sa.Column("in_reply_to", sa.String(length=512), nullable=True),
        sa.Column("references_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tracking_token", sa.String(length=128), nullable=True),
        sa.Column("raw_headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sent_or_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["email_connections.client_id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.client_id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"]),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "connection_id",
            "provider_folder",
            "provider_uid",
            name="uq_email_message_provider_uid",
        ),
    )
    op.create_index("ix_email_messages_connection_id", "email_messages", ["connection_id"], unique=False)
    op.create_index("ix_email_messages_direction", "email_messages", ["direction"], unique=False)
    op.create_index("ix_email_messages_rfc_id", "email_messages", ["rfc_message_id"], unique=False)
    op.create_index("ix_email_messages_thread_id", "email_messages", ["thread_id"], unique=False)
    op.create_index("ix_email_messages_thread_time", "email_messages", ["thread_id", "sent_or_received_at"], unique=False)
    op.create_index("ix_email_messages_workspace_id", "email_messages", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_email_messages_workspace_id", table_name="email_messages")
    op.drop_index("ix_email_messages_thread_time", table_name="email_messages")
    op.drop_index("ix_email_messages_thread_id", table_name="email_messages")
    op.drop_index("ix_email_messages_rfc_id", table_name="email_messages")
    op.drop_index("ix_email_messages_direction", table_name="email_messages")
    op.drop_index("ix_email_messages_connection_id", table_name="email_messages")
    op.drop_table("email_messages")
