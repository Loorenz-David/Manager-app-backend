"""create_shopify_product_sync_items_table

Revision ID: e1b2c3d4e5f6
Revises: d4f8a1b2c3e4
Create Date: 2026-07-09 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1b2c3d4e5f6"
down_revision: Union[str, None] = "d4f8a1b2c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    operation_enum = postgresql.ENUM(
        "create",
        "update",
        name="shopify_product_sync_operation_enum",
        create_type=False,
    )
    status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "succeeded",
        "failed",
        name="shopify_product_sync_item_status_enum",
        create_type=False,
    )
    operation_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shopify_product_sync_items",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("shop_integration_id", sa.String(length=64), nullable=False),
        sa.Column("frontend_client_id", sa.String(length=255), nullable=False),
        sa.Column("requested_operation", operation_enum, nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("normalized_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("shopify_product_id", sa.String(length=255), nullable=True),
        sa.Column("shopify_variant_id", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shop_integration_id"], ["shopify_shop_integrations.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(
        "ix_shopify_product_sync_items_workspace_id",
        "shopify_product_sync_items",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_product_sync_items_shop_integration_id",
        "shopify_product_sync_items",
        ["shop_integration_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_product_sync_items_created_by_id",
        "shopify_product_sync_items",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_product_sync_items_status",
        "shopify_product_sync_items",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_product_sync_items_workspace_status",
        "shopify_product_sync_items",
        ["workspace_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_product_sync_items_shop_integration_status",
        "shopify_product_sync_items",
        ["shop_integration_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shopify_product_sync_items_shop_integration_status", table_name="shopify_product_sync_items")
    op.drop_index("ix_shopify_product_sync_items_workspace_status", table_name="shopify_product_sync_items")
    op.drop_index("ix_shopify_product_sync_items_status", table_name="shopify_product_sync_items")
    op.drop_index("ix_shopify_product_sync_items_created_by_id", table_name="shopify_product_sync_items")
    op.drop_index("ix_shopify_product_sync_items_shop_integration_id", table_name="shopify_product_sync_items")
    op.drop_index("ix_shopify_product_sync_items_workspace_id", table_name="shopify_product_sync_items")
    op.drop_table("shopify_product_sync_items")
    postgresql.ENUM(name="shopify_product_sync_item_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="shopify_product_sync_operation_enum").drop(op.get_bind(), checkfirst=True)
