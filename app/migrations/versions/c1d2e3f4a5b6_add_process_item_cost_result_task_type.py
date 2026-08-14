"""add process item cost result task type

Revision ID: c1d2e3f4a5b6
Revises: be9dfe42a035
Create Date: 2026-08-14 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "be9dfe42a035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'process_item_cost_result'"
    )


def downgrade() -> None:
    # PostgreSQL enum labels cannot be removed safely in-place. The label remains
    # on downgrade, following the existing task-type migration precedent.
    pass
