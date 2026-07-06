"""add_send_email_messages_task_type

Revision ID: a4f9c2d7e6b1
Revises: f6e7d8c9b0a1
Create Date: 2026-07-06 10:05:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a4f9c2d7e6b1"
down_revision: Union[str, None] = "f6e7d8c9b0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'send_email_messages'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'send_email_messages' remains in task_type_enum on downgrade.
    pass
