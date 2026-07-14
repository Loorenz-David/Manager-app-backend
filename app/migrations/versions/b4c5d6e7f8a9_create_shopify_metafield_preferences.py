"""create_shopify_metafield_preferences

Revision ID: b4c5d6e7f8a9
Revises: a3d4e5f6a7b8
Create Date: 2026-07-13 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shopify_metafield_preferences",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("item_category_id", sa.String(length=64), nullable=False),
        sa.Column("shop_integration_id", sa.String(length=64), nullable=False),
        sa.Column("shopify_metafield_definition_id", sa.String(length=255), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_id", sa.String(length=64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["item_category_id"], ["item_categories.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["shop_integration_id"], ["shopify_shop_integrations.client_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.client_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.client_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_index(
        "ix_shopify_metafield_preferences_workspace_id",
        "shopify_metafield_preferences",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_item_category_id",
        "shopify_metafield_preferences",
        ["item_category_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_shop_integration_id",
        "shopify_metafield_preferences",
        ["shop_integration_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_created_by_id",
        "shopify_metafield_preferences",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_updated_by_id",
        "shopify_metafield_preferences",
        ["updated_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_is_deleted",
        "shopify_metafield_preferences",
        ["is_deleted"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_deleted_by_id",
        "shopify_metafield_preferences",
        ["deleted_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_workspace_shop_category",
        "shopify_metafield_preferences",
        ["workspace_id", "shop_integration_id", "item_category_id"],
        unique=False,
    )
    op.create_index(
        "ix_shopify_metafield_preferences_ws_shop_category_creator",
        "shopify_metafield_preferences",
        ["workspace_id", "shop_integration_id", "item_category_id", "created_by_id"],
        unique=False,
    )
    op.create_index(
        "uix_shopify_metafield_preferences_active_scope",
        "shopify_metafield_preferences",
        ["workspace_id", "shop_integration_id", "item_category_id", "shopify_metafield_definition_id"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uix_shopify_metafield_preferences_active_scope", table_name="shopify_metafield_preferences")
    op.drop_index(
        "ix_shopify_metafield_preferences_ws_shop_category_creator",
        table_name="shopify_metafield_preferences",
    )
    op.drop_index(
        "ix_shopify_metafield_preferences_workspace_shop_category",
        table_name="shopify_metafield_preferences",
    )
    op.drop_index("ix_shopify_metafield_preferences_deleted_by_id", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_is_deleted", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_updated_by_id", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_created_by_id", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_shop_integration_id", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_item_category_id", table_name="shopify_metafield_preferences")
    op.drop_index("ix_shopify_metafield_preferences_workspace_id", table_name="shopify_metafield_preferences")
    op.drop_table("shopify_metafield_preferences")
