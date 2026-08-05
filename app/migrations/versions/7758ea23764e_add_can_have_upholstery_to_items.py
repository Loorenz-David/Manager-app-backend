"""add can_have_upholstery to items

Whether an item should carry upholstery has so far been inferred purely from its category's
major_category snapshot (item_major_category_snapshot == "seat"). That's too coarse: not every
seat item actually needs upholstery tracked (e.g. a seat sold or repaired frame-only). This flag
lets a specific item opt out, defaulting to true so existing seat-category behavior is unchanged
until an item is explicitly flagged otherwise.

Revision ID: 7758ea23764e
Revises: 2645b4327b17
Create Date: 2026-08-05 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7758ea23764e"
down_revision: Union[str, None] = "2645b4327b17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "can_have_upholstery",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("items", "can_have_upholstery")
