"""add_connecteam_task_type

Revision ID: c9e1f2a3b4c5
Revises: b4074f2e26c4
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c9e1f2a3b4c5"
down_revision: Union[str, None] = "b4074f2e26c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'connecteam_process_time_activity'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass

