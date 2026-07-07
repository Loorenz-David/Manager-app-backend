"""add_location_tracker_push_locations_task_type

Revision ID: b2c4d6e8f0a1
Revises: 7c1e4b2a9d6f
Create Date: 2026-07-07 16:25:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b2c4d6e8f0a1"
down_revision: Union[str, None] = "7c1e4b2a9d6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'location_tracker_push_locations'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values from an existing type.
    # 'location_tracker_push_locations' remains in task_type_enum on downgrade.
    pass
