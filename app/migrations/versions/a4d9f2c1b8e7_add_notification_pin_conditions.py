"""add notification pin conditions

Revision ID: a4d9f2c1b8e7
Revises: 6787eabf4c32
Create Date: 2026-06-19 13:20:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a4d9f2c1b8e7"
down_revision: Union[str, None] = "6787eabf4c32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_pins",
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "notification_pins",
        sa.Column("fire_once", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("notification_pins", "fire_once")
    op.drop_column("notification_pins", "conditions")
