"""add notification pin major entity

Revision ID: b5e8a7c2d4f1
Revises: a4d9f2c1b8e7
Create Date: 2026-06-20 13:05:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b5e8a7c2d4f1"
down_revision: Union[str, None] = "a4d9f2c1b8e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_pins",
        sa.Column("major_entity_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "notification_pins",
        sa.Column("major_client_entity_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_notification_pins_major_entity",
        "notification_pins",
        ["major_entity_type", "major_client_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_pins_major_entity", table_name="notification_pins")
    op.drop_column("notification_pins", "major_client_entity_id")
    op.drop_column("notification_pins", "major_entity_type")
