"""add_ready_by_at_to_task_steps

Revision ID: 4f2e9a7b6c1d
Revises: 26d4b7f0c3aa
Create Date: 2026-06-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f2e9a7b6c1d"
down_revision: Union[str, Sequence[str], None] = "26d4b7f0c3aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("task_steps", sa.Column("ready_by_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("task_steps", "ready_by_at")
