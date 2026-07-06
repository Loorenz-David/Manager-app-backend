"""create_email_sync_states_table

Revision ID: aa10c8c7e003
Revises: aa10c8c7e002
Create Date: 2026-07-04 13:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "aa10c8c7e003"
down_revision: Union[str, None] = "aa10c8c7e002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_sync_states",
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("folder", sa.String(length=128), server_default="INBOX", nullable=False),
        sa.Column("uidvalidity", sa.Integer(), nullable=True),
        sa.Column("last_seen_uid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["email_connections.client_id"]),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("connection_id"),
    )
    op.create_index(op.f("ix_email_sync_states_connection_id"), "email_sync_states", ["connection_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_sync_states_connection_id"), table_name="email_sync_states")
    op.drop_table("email_sync_states")
