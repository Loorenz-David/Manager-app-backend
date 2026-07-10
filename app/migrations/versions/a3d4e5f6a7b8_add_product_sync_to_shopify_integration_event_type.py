"""add_product_sync_to_shopify_integration_event_type

Revision ID: a3d4e5f6a7b8
Revises: f2c3d4e5f6a7
Create Date: 2026-07-09 18:32:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a3d4e5f6a7b8"
down_revision: Union[str, None] = "f2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE shopify_integration_event_type_enum ADD VALUE IF NOT EXISTS 'product_sync'")


def downgrade() -> None:
    pass
