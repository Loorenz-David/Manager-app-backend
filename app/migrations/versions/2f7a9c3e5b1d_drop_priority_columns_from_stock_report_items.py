"""drop_priority_columns_from_stock_report_items

`priority` and `priority_order` moved to `stock_report_item_snapshots` in
11e1d0d47686; every code reference left the row in the same change. The owner ruled
no backfill (2026-09-26): existing row priorities are not carried into a first
version, so this drop discards them deliberately.

Kept as its own revision so a rollback of the drop does not have to undo the table
creation (30_migrations "Removing a column").

Revision ID: 2f7a9c3e5b1d
Revises: 11e1d0d47686
Create Date: 2026-09-26 11:25:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2f7a9c3e5b1d"
down_revision: Union[str, None] = "11e1d0d47686"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "ix_stock_report_items_workspace_priority_order",
        table_name="stock_report_items",
    )
    op.drop_column("stock_report_items", "priority_order")
    op.drop_column("stock_report_items", "priority")


def downgrade() -> None:
    op.add_column(
        "stock_report_items",
        sa.Column(
            "priority",
            postgresql.ENUM(
                "high",
                "medium",
                "low",
                name="stock_report_priority_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "stock_report_items",
        sa.Column("priority_order", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_stock_report_items_workspace_priority_order",
        "stock_report_items",
        ["workspace_id", "priority", "priority_order"],
        unique=False,
    )
