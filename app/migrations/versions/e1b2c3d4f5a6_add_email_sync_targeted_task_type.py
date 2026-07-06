"""add_email_sync_targeted_task_type

Revision ID: e1b2c3d4f5a6
Revises: e7a1c4d9b2f0
Create Date: 2026-07-06 08:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e1b2c3d4f5a6"
down_revision: Union[str, None] = "e7a1c4d9b2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'email_sync_targeted'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'email_sync_targeted' remains in task_type_enum on downgrade.
    pass
