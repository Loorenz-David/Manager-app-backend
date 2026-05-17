"""partial_unique_index_upholstery_inventory

Revision ID: f3c8a1d209e5
Revises: a61def0ca46f
Create Date: 2026-05-16 22:00:00.000000

Replace the hard unique constraint on (workspace_id, upholstery_id) with a
partial unique index so that soft-deleted inventories do not block re-creation
for the same upholstery.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f3c8a1d209e5'
down_revision: Union[str, None] = 'a61def0ca46f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        'uq_upholstery_inventory_workspace_upholstery',
        'upholstery_inventory',
        type_='unique',
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uix_upholstery_inventory_workspace_upholstery_active
        ON upholstery_inventory (workspace_id, upholstery_id)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_index(
        'uix_upholstery_inventory_workspace_upholstery_active',
        table_name='upholstery_inventory',
    )
    op.create_unique_constraint(
        'uq_upholstery_inventory_workspace_upholstery',
        'upholstery_inventory',
        ['workspace_id', 'upholstery_id'],
    )
