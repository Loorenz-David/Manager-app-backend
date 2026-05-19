"""add_task_step_latest_state_record_relationship

Revision ID: 8f2c1d4a7b3e
Revises: cf79311a956f
Create Date: 2026-05-18 19:40:00.000000
"""
from typing import Sequence, Union


revision: str = "8f2c1d4a7b3e"
down_revision: Union[str, None] = "cf79311a956f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ORM-only change: the foreign key already exists in the schema.
    # This revision records the model relationship addition in migration history.
    pass


def downgrade() -> None:
    pass