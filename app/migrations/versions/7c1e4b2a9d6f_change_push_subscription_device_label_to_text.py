"""change_push_subscription_device_label_to_text

Revision ID: 7c1e4b2a9d6f
Revises: 6b4c2d1e9f7a
Create Date: 2026-07-07 13:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7c1e4b2a9d6f"
down_revision: Union[str, None] = "6b4c2d1e9f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "push_subscriptions",
        "device_label",
        existing_type=sa.String(length=128),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "push_subscriptions",
        "device_label",
        existing_type=sa.Text(),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
