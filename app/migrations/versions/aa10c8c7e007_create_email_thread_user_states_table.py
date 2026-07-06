"""create_email_thread_user_states_table

Revision ID: aa10c8c7e007
Revises: aa10c8c7e006
Create Date: 2026-07-04 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "aa10c8c7e007"
down_revision: Union[str, None] = "aa10c8c7e006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_thread_user_states",
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("muted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["email_threads.client_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.client_id"]),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("thread_id", "user_id", name="uq_email_thread_user_state"),
    )
    op.create_index("ix_email_thread_user_states_thread_id", "email_thread_user_states", ["thread_id"], unique=False)
    op.create_index("ix_email_thread_user_states_user_id", "email_thread_user_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_email_thread_user_states_user_id", table_name="email_thread_user_states")
    op.drop_index("ix_email_thread_user_states_thread_id", table_name="email_thread_user_states")
    op.drop_table("email_thread_user_states")
