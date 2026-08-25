"""reserve the item upholstery lifecycle migration slot

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-24 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Duplicate cleanup is an explicit data-maintenance operation, not a migration
    # prerequisite. Keep this revision in the chain for databases that already know
    # its revision, but do not inspect or mutate item-upholstery data here.
    pass


def downgrade() -> None:
    # Remove the index if this revision was applied before it became a no-op.
    op.execute(
        "DROP INDEX IF EXISTS uix_item_upholsteries_current_workspace_item"
    )
