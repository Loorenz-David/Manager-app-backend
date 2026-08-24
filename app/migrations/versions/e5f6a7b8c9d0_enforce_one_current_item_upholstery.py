"""enforce one current item upholstery per item

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-24 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicate_rows = connection.execute(
        sa.text(
            """
            SELECT workspace_id, item_id, array_agg(client_id ORDER BY created_at)
            FROM item_upholsteries
            WHERE is_deleted = false
            GROUP BY workspace_id, item_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicate_rows:
        details = "; ".join(
            f"workspace={workspace_id}, item={item_id}, rows={client_ids}"
            for workspace_id, item_id, client_ids in duplicate_rows
        )
        raise RuntimeError(
            "Cannot enforce one current item upholstery per item until duplicate active "
            f"rows are resolved: {details}"
        )

    op.create_index(
        "uix_item_upholsteries_current_workspace_item",
        "item_upholsteries",
        ["workspace_id", "item_id"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index(
        "uix_item_upholsteries_current_workspace_item",
        table_name="item_upholsteries",
    )
