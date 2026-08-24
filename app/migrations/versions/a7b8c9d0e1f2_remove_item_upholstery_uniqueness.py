"""remove optional item upholstery uniqueness enforcement

Revision ID: a7b8c9d0e1f2
Revises: a6b7c8d9e0f1
Create Date: 2026-08-24 16:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A database may have applied the former e5 revision before it was made
    # non-blocking. Remove that optional constraint without touching data.
    op.execute(
        "DROP INDEX IF EXISTS uix_item_upholsteries_current_workspace_item"
    )


def downgrade() -> None:
    # The uniqueness rule is intentionally maintained only by the optional
    # cleanup workflow, so downgrading must not recreate it.
    pass
