"""add_shopify_execution_task_types

Revision ID: c3f7a9d2e4b1
Revises: 677ed7131bb2
Create Date: 2026-07-09 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3f7a9d2e4b1"
down_revision: Union[str, None] = "677ed7131bb2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_process_webhook'")
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_sync_webhooks_for_shop'")
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_remove_webhooks_for_shop'")
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'shopify_reconcile_shop'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # The Shopify task types remain in task_type_enum on downgrade.
    pass
