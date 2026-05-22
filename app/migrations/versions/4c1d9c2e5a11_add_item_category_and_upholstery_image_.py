"""add_item_category_and_upholstery_image_link_entity_types

Revision ID: 4c1d9c2e5a11
Revises: 869a18698f34
Create Date: 2026-05-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "4c1d9c2e5a11"
down_revision: Union[str, None] = "869a18698f34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'item_category'"))
    op.execute(text("ALTER TYPE image_link_entity_type_enum ADD VALUE IF NOT EXISTS 'upholstery'"))


def downgrade() -> None:
    # PostgreSQL enums cannot drop individual values safely; leave as no-op.
    pass
