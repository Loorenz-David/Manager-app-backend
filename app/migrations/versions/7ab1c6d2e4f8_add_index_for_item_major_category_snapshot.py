"""add_index_for_item_major_category_snapshot

Revision ID: 7ab1c6d2e4f8
Revises: 0f935423c845
Create Date: 2026-06-06 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7ab1c6d2e4f8"
down_revision: Union[str, None] = "0f935423c845"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_items_workspace_item_major_category_snapshot",
        "items",
        ["workspace_id", "item_major_category_snapshot"],
        unique=False,
        postgresql_where=sa.text("item_major_category_snapshot IS NOT NULL AND is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_items_workspace_item_major_category_snapshot", table_name="items")
