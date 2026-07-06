"""add_failed_to_task_customer_coordination_state_enum

Revision ID: e7a1c4d9b2f0
Revises: 8485202cd902
Create Date: 2026-07-05 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e7a1c4d9b2f0"
down_revision: Union[str, None] = "8485202cd902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE task_customer_coordination_state_enum ADD VALUE IF NOT EXISTS 'failed'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'failed' remains in task_customer_coordination_state_enum on downgrade.
    pass
