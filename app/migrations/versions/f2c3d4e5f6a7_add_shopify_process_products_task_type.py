"""add_shopify_process_products_task_type

Revision ID: f2c3d4e5f6a7
Revises: e1b2c3d4e5f6
Create Date: 2026-07-09 18:31:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f2c3d4e5f6a7"
down_revision: Union[str, None] = "e1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_process_products'")


def downgrade() -> None:
    pass
