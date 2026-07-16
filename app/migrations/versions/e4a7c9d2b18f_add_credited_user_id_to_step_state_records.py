"""add_credited_user_id_to_step_state_records

Revision ID: e4a7c9d2b18f
Revises: c9d382a037e5
Create Date: 2026-07-15 17:40:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e4a7c9d2b18f'
down_revision: Union[str, None] = 'c9d382a037e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, no server_default, no FK: adding the column takes a metadata-only
    # lock (no table rewrite, no FK validation scan) on this high-volume table.
    # Pre-existing rows read as NULL; analytics backfill falls back to
    # created_by_id for those. Going forward the transition core populates it.
    op.add_column(
        'step_state_records',
        sa.Column('credited_user_id', sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('step_state_records', 'credited_user_id')
