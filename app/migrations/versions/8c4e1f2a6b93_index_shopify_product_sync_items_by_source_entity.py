"""index_shopify_product_sync_items_by_source_entity

The worker product form now writes to Shopify when it is saved, and reads the
product back before a step is completed. Both look up "the newest sync row for
this item in this shop": sync rows created from the form record
`source_entity_type = 'item'` and `source_entity_id = <item client_id>`, and the
worker uses the stored `shopify_product_id` of that row to update the same
product instead of creating a duplicate. This index serves that lookup.

Hand-written; index only, no data change.

Revision ID: 8c4e1f2a6b93
Revises: 3b8d2f7a9c41
Create Date: 2026-11-09 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "8c4e1f2a6b93"
down_revision: Union[str, Sequence[str], None] = "3b8d2f7a9c41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_shopify_product_sync_items_source_entity_shop",
        "shopify_product_sync_items",
        ["workspace_id", "source_entity_type", "source_entity_id", "shop_integration_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shopify_product_sync_items_source_entity_shop",
        table_name="shopify_product_sync_items",
    )
