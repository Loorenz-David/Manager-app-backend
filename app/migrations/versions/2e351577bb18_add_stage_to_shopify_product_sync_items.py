"""add_stage_to_shopify_product_sync_items

Revision ID: 2e351577bb18
Revises: 491c5f26e8e8
Create Date: 2026-07-27 21:20:04.126318
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '2e351577bb18'
down_revision: Union[str, None] = '491c5f26e8e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    stage_enum = postgresql.ENUM(
        "queued",
        "product_created",
        "variant_configured",
        "inventory_set",
        name="shopify_product_sync_stage_enum",
        create_type=False,
    )
    stage_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "shopify_product_sync_items",
        sa.Column(
            "stage",
            stage_enum,
            server_default="queued",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("shopify_product_sync_items", "stage")
    postgresql.ENUM(
        name="shopify_product_sync_stage_enum",
    ).drop(op.get_bind(), checkfirst=True)
