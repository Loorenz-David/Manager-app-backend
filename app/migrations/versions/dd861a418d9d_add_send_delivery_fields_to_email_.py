"""add_send_delivery_fields_to_email_messages

Revision ID: dd861a418d9d
Revises: c4b6e2f9a1d3
Create Date: 2026-07-04 17:02:28.814184
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'dd861a418d9d'
down_revision: Union[str, None] = 'c4b6e2f9a1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'send_coordination_email_batch'")
    op.add_column('email_messages', sa.Column('send_attempted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('email_messages', sa.Column('send_error', sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column('email_messages', 'send_error')
    op.drop_column('email_messages', 'send_attempted_at')
    # PostgreSQL does not support removing enum values from an existing type.
    # 'send_coordination_email_batch' remains in task_type_enum on downgrade.
