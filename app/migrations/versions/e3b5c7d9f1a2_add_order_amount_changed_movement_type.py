"""add_order_amount_changed_movement_type

An upholstery order's amount can now be edited after it was placed
(`update_upholstery_order_amount`); the inventory ledger records that as its own
movement kind. Additive enum value only.

Hand-written.

Revision ID: e3b5c7d9f1a2
Revises: d7e2a9c4b1f6
Create Date: 2026-11-16 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e3b5c7d9f1a2"
down_revision: Union[str, None] = "d7e2a9c4b1f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE upholstery_inventory_movement_type_enum "
        "ADD VALUE IF NOT EXISTS 'order_amount_changed'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'order_amount_changed' remains in upholstery_inventory_movement_type_enum on downgrade.
    pass
