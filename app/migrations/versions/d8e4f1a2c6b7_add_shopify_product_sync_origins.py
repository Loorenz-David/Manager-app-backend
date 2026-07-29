"""add_shopify_product_sync_origins

Revision ID: d8e4f1a2c6b7
Revises: c7f2a9e1b3d4
Create Date: 2026-07-28 18:00:00.000000

Product-sync origin is deliberately VARCHAR rather than a native PostgreSQL
enum. Inventory mode remains for one compatibility release, but all unfinished
work is converted to the absolute ``quantities`` payload contract.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d8e4f1a2c6b7"
down_revision: Union[str, None] = "c7f2a9e1b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shopify_product_sync_items",
        sa.Column(
            "sync_origin",
            sa.String(length=64),
            nullable=False,
            server_default="standard_product_sync",
        ),
    )
    op.add_column(
        "shopify_product_sync_items",
        sa.Column("source_entity_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "shopify_product_sync_items",
        sa.Column("source_entity_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_shopify_product_sync_items_workspace_origin",
        "shopify_product_sync_items",
        ["workspace_id", "sync_origin"],
        unique=False,
    )

    # Events carry the strongest historical signal because the old pre-order
    # helper rewrote its enqueue event in the same transaction. Matching the
    # PRE_ORDER task is a fallback for partially staged historical rows.
    op.execute(
        """
        UPDATE shopify_product_sync_items AS sync_item
        SET
            sync_origin = 'preorder_task',
            source_entity_type = 'task',
            source_entity_id = COALESCE(
                (
                    SELECT event.metadata ->> 'task_id'
                    FROM shopify_integration_events AS event
                    WHERE event.workspace_id = sync_item.workspace_id
                      AND event.event_type = 'preorder'
                      AND (
                          event.metadata ->> 'preorder_operation_id' = sync_item.client_id
                          OR event.metadata ->> 'task_id' = sync_item.frontend_client_id
                      )
                    ORDER BY event.created_at ASC
                    LIMIT 1
                ),
                (
                    SELECT task.client_id
                    FROM tasks AS task
                    WHERE task.workspace_id = sync_item.workspace_id
                      AND task.client_id = sync_item.frontend_client_id
                      AND task.task_type = 'pre_order'
                    LIMIT 1
                )
            )
        WHERE EXISTS (
            SELECT 1
            FROM shopify_integration_events AS event
            WHERE event.workspace_id = sync_item.workspace_id
              AND event.event_type = 'preorder'
              AND (
                  event.metadata ->> 'preorder_operation_id' = sync_item.client_id
                  OR event.metadata ->> 'task_id' = sync_item.frontend_client_id
              )
        )
        OR EXISTS (
            SELECT 1
            FROM tasks AS task
            WHERE task.workspace_id = sync_item.workspace_id
              AND task.client_id = sync_item.frontend_client_id
              AND task.task_type = 'pre_order'
        )
        """
    )

    # A missed legacy job is made canonical in-place. The submitted
    # quantity_to_add is intentionally interpreted as an absolute quantity.
    op.execute(
        """
        UPDATE shopify_product_sync_items
        SET normalized_payload = jsonb_set(
            normalized_payload #- '{inventory,adjustments}',
            '{inventory,quantities}',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'location_id', adjustment -> 'location_id',
                            'quantity', adjustment -> 'quantity_to_add'
                        )
                    )
                    FROM jsonb_array_elements(
                        normalized_payload #> '{inventory,adjustments}'
                    ) AS adjustment
                ),
                '[]'::jsonb
            ),
            true
        )
        WHERE status IN ('pending', 'processing')
          AND stage <> 'inventory_set'
          AND jsonb_typeof(
              normalized_payload #> '{inventory,adjustments}'
          ) = 'array'
          AND normalized_payload #> '{inventory,quantities}' IS NULL
        """
    )
    op.execute(
        """
        UPDATE shopify_product_sync_items
        SET normalized_payload = normalized_payload #- '{inventory,adjustments}'
        WHERE status IN ('pending', 'processing')
          AND stage <> 'inventory_set'
          AND normalized_payload #> '{inventory,quantities}' IS NOT NULL
          AND normalized_payload #> '{inventory,adjustments}' IS NOT NULL
        """
    )

    inventory_mode_enum = postgresql.ENUM(
        "add",
        "set",
        name="shopify_inventory_mode_enum",
        create_type=False,
    )
    op.alter_column(
        "shopify_product_sync_items",
        "inventory_mode",
        existing_type=inventory_mode_enum,
        server_default="set",
        existing_nullable=False,
    )
    op.execute(
        """
        UPDATE shopify_product_sync_items
        SET inventory_mode = 'set'
        WHERE status IN ('pending', 'processing')
          AND stage <> 'inventory_set'
        """
    )


def downgrade() -> None:
    inventory_mode_enum = postgresql.ENUM(
        "add",
        "set",
        name="shopify_inventory_mode_enum",
        create_type=False,
    )
    op.alter_column(
        "shopify_product_sync_items",
        "inventory_mode",
        existing_type=inventory_mode_enum,
        server_default="add",
        existing_nullable=False,
    )
    op.drop_index(
        "ix_shopify_product_sync_items_workspace_origin",
        table_name="shopify_product_sync_items",
    )
    op.drop_column("shopify_product_sync_items", "source_entity_id")
    op.drop_column("shopify_product_sync_items", "source_entity_type")
    op.drop_column("shopify_product_sync_items", "sync_origin")
