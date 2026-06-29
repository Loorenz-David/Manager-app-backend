"""add_workspace_role_name_enum

Revision ID: 71df9b8c4a2e
Revises: 7e1c3b4a9d2f
Create Date: 2026-06-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "71df9b8c4a2e"
down_revision: Union[str, None] = "7e1c3b4a9d2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Legacy branch bridge:
    # the workspace-role enum work was superseded by the merged specialization branch
    # that production already has as 7e1c3b4a9d2f. Keep this revision as a no-op so
    # later branch children (26d4 -> 4f2 -> a3) can apply cleanly on top of that head.
    pass


def downgrade() -> None:
    pass
