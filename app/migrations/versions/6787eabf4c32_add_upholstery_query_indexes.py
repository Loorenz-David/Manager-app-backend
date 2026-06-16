"""add upholstery query indexes

Revision ID: 6787eabf4c32
Revises: 38491ecd2b90
Create Date: 2026-06-16 18:25:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "6787eabf4c32"
down_revision: Union[str, None] = "38491ecd2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholstery_requirements_workspace_state "
        "ON item_upholstery_requirements (workspace_id, state)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholstery_requirements_workspace_inventory_id "
        "ON item_upholstery_requirements (workspace_id, upholstery_inventory_id)"
    )
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_item_upholsteries_workspace_upholstery_id "
        "ON item_upholsteries (workspace_id, upholstery_id)"
    )


def downgrade() -> None:
    op.execute("COMMIT")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholstery_requirements_workspace_state")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholstery_requirements_workspace_inventory_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_item_upholsteries_workspace_upholstery_id")
