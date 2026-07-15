"""add Shopify inventory adjustment ledger

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-15 08:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shopify_product_sync_items",
        sa.Column("shopify_inventory_item_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "shopify_product_sync_items",
        sa.Column("inventory_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    status_enum = postgresql.ENUM(
        "pending",
        "applied",
        "failed",
        name="shopify_inventory_adjustment_status_enum",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shopify_inventory_adjustments",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("shop_integration_id", sa.String(length=64), nullable=False),
        sa.Column("sync_item_id", sa.String(length=64), nullable=True),
        sa.Column("frontend_client_id", sa.String(length=255), nullable=False),
        sa.Column("shopify_inventory_item_id", sa.String(length=255), nullable=False),
        sa.Column("shopify_location_id", sa.String(length=255), nullable=False),
        sa.Column("requested_delta", sa.Integer(), nullable=False),
        sa.Column("baseline_available", sa.Integer(), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("reference_uri", sa.String(length=255), nullable=False),
        sa.Column("shopify_error_code", sa.String(length=64), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["shop_integration_id"], ["shopify_shop_integrations.client_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["sync_item_id"], ["shopify_product_sync_items.client_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "shop_integration_id",
            "frontend_client_id",
            "shopify_location_id",
            name="uq_shopify_inventory_adjustments_idempotency",
        ),
    )
    op.create_index(
        "ix_shopify_inventory_adjustments_workspace_id",
        "shopify_inventory_adjustments",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_inventory_adjustments_shop_integration_id",
        "shopify_inventory_adjustments",
        ["shop_integration_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_inventory_adjustments_sync_item_id",
        "shopify_inventory_adjustments",
        ["sync_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_inventory_adjustments_status",
        "shopify_inventory_adjustments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_inventory_adjustments_created_by_id",
        "shopify_inventory_adjustments",
        ["created_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shopify_inventory_adjustments_created_by_id", table_name="shopify_inventory_adjustments")
    op.drop_index("ix_shopify_inventory_adjustments_status", table_name="shopify_inventory_adjustments")
    op.drop_index("ix_shopify_inventory_adjustments_sync_item_id", table_name="shopify_inventory_adjustments")
    op.drop_index("ix_shopify_inventory_adjustments_shop_integration_id", table_name="shopify_inventory_adjustments")
    op.drop_index("ix_shopify_inventory_adjustments_workspace_id", table_name="shopify_inventory_adjustments")
    op.drop_table("shopify_inventory_adjustments")
    postgresql.ENUM(name="shopify_inventory_adjustment_status_enum").drop(op.get_bind(), checkfirst=True)
    op.drop_column("shopify_product_sync_items", "inventory_result_json")
    op.drop_column("shopify_product_sync_items", "shopify_inventory_item_id")
