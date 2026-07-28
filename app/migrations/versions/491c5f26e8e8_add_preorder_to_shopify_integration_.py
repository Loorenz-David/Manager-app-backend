"""add_preorder_to_shopify_integration_event_type

Revision ID: 491c5f26e8e8
Revises: 6851be0af6f7
Create Date: 2026-07-27 20:39:42.320769
"""
from typing import Sequence, Union

from alembic import op


revision: str = '491c5f26e8e8'
down_revision: Union[str, None] = '6851be0af6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE shopify_integration_event_type_enum "
        "ADD VALUE IF NOT EXISTS 'preorder'"
    )


def downgrade() -> None:
    # PostgreSQL enum values are intentionally retained on downgrade.
    pass
