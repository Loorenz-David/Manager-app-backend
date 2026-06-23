"""add_allows_batch_working_to_sections_and_steps

Revision ID: 26d4b7f0c3aa
Revises: 71df9b8c4a2e
Create Date: 2026-06-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "26d4b7f0c3aa"
down_revision: Union[str, Sequence[str], None] = "71df9b8c4a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "working_sections",
        sa.Column(
            "allows_batch_working",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "task_steps",
        sa.Column(
            "allows_batch_working",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("task_steps", "allows_batch_working")
    op.drop_column("working_sections", "allows_batch_working")
