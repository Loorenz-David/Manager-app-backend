"""create_email_threads_table

Revision ID: aa10c8c7e005
Revises: aa10c8c7e004
Create Date: 2026-07-04 13:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "aa10c8c7e005"
down_revision: Union[str, None] = "aa10c8c7e004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_threads",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_client_id", sa.String(length=128), nullable=True),
        sa.Column("major_entity_type", sa.String(length=64), nullable=True),
        sa.Column("major_entity_client_id", sa.String(length=128), nullable=True),
        sa.Column("subject_normalized", sa.String(length=512), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_inbound_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["email_connections.client_id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"]),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index("ix_email_threads_connection_id", "email_threads", ["connection_id"], unique=False)
    op.create_index("ix_email_threads_entity", "email_threads", ["entity_type", "entity_client_id"], unique=False)
    op.create_index("ix_email_threads_last_message_at", "email_threads", ["last_message_at"], unique=False)
    op.create_index("ix_email_threads_major_entity", "email_threads", ["major_entity_type", "major_entity_client_id"], unique=False)
    op.create_index("ix_email_threads_workspace_id", "email_threads", ["workspace_id"], unique=False)
    op.create_index("ix_email_threads_entity_type", "email_threads", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_email_threads_entity_type", table_name="email_threads")
    op.drop_index("ix_email_threads_workspace_id", table_name="email_threads")
    op.drop_index("ix_email_threads_major_entity", table_name="email_threads")
    op.drop_index("ix_email_threads_last_message_at", table_name="email_threads")
    op.drop_index("ix_email_threads_entity", table_name="email_threads")
    op.drop_index("ix_email_threads_connection_id", table_name="email_threads")
    op.drop_table("email_threads")
