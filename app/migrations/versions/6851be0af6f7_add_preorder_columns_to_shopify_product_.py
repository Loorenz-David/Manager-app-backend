"""add_preorder_columns_to_shopify_product_sync_items

Revision ID: 6851be0af6f7
Revises: 0f86759d0bb5
Create Date: 2026-07-27 20:39:27.804674
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '6851be0af6f7'
down_revision: Union[str, None] = '0f86759d0bb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inventory_mode_enum = postgresql.ENUM(
        'add',
        'set',
        name='shopify_inventory_mode_enum',
        create_type=False,
    )
    inventory_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('shopify_product_sync_items', sa.Column('inventory_mode', inventory_mode_enum, server_default='add', nullable=False))
    op.add_column('shopify_product_sync_items', sa.Column('shopify_media_id', sa.String(length=255), nullable=True))
    op.add_column('shopify_product_sync_items', sa.Column('media_status', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('shopify_product_sync_items', 'media_status')
    op.drop_column('shopify_product_sync_items', 'shopify_media_id')
    op.drop_column('shopify_product_sync_items', 'inventory_mode')
    postgresql.ENUM(
        name='shopify_inventory_mode_enum',
    ).drop(op.get_bind(), checkfirst=True)
