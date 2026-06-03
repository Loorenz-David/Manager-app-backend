"""add_pending_step_completion_scheduler_and_task_types

Revision ID: f4a1c9d8e2b0
Revises: e5b7c1a0d2f3
Create Date: 2026-06-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4a1c9d8e2b0"
down_revision: Union[str, None] = "e5b7c1a0d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE delayed_scheduler_type_enum ADD VALUE IF NOT EXISTS 'pending_step_completion'"
    )
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'delayed_step_completion'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
