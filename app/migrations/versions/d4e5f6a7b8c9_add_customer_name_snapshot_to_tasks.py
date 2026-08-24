"""add customer name snapshot to tasks

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-08-24 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("customer_name_snapshot", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE tasks AS t
            SET customer_name_snapshot = c.display_name
            FROM customers AS c
            WHERE t.customer_id = c.client_id
              AND t.workspace_id = c.workspace_id
              AND t.customer_name_snapshot IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("tasks", "customer_name_snapshot")
