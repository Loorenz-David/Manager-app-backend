"""add_process_step_transition_task_type

Revision ID: f1aff3910fd5
Revises: c0f4f2747d9b
Create Date: 2026-05-18 18:30:00.606579
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f1aff3910fd5'
down_revision: Union[str, None] = 'c0f4f2747d9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add process_step_transition to task_type_enum
    op.execute("ALTER TYPE task_type_enum ADD VALUE 'process_step_transition'")


def downgrade() -> None:
    # Note: PostgreSQL does not allow removing enum values, so downgrade is a no-op
    # If needed, the enum would need to be recreated from scratch
    pass
