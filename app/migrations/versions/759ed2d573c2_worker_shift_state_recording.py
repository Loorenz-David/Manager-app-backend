"""worker_shift_state_recording

Revision ID: 759ed2d573c2
Revises: 74f152a8b9d1
Create Date: 2026-07-20 01:27:12.186686
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "759ed2d573c2"
down_revision: Union[str, None] = "74f152a8b9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_shift_state_enum ADD VALUE IF NOT EXISTS 'idle'")
    op.execute(
        "ALTER TYPE recurring_scheduler_type_enum "
        "ADD VALUE IF NOT EXISTS 'auto_clock_out_open_shifts'"
    )
    op.execute(
        "ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'auto_clock_out_open_shifts'"
    )
    op.add_column(
        "user_shift_state_records",
        sa.Column("reason", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "user_shift_state_records",
        sa.Column(
            "manually_recorded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_shift_state_records", "manually_recorded")
    op.drop_column("user_shift_state_records", "reason")
    # PostgreSQL does not support safely removing enum values. The values added
    # in upgrade() intentionally remain present after downgrade.
