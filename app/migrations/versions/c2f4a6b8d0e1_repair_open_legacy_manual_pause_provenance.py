"""Repair open legacy manual-pause provenance.

Revision ID: c2f4a6b8d0e1
Revises: 595e7b840926
Create Date: 2026-07-29 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c2f4a6b8d0e1"
down_revision: str | None = "595e7b840926"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPAIR_STATEMENT = sa.text(
    """
    UPDATE user_shift_state_records
    SET changed_by_id = user_id
    WHERE exited_at IS NULL
      AND state = 'in_pause'
      AND manually_recorded IS TRUE
      AND changed_by_id IS NULL
    """
)


def upgrade() -> None:
    op.execute(REPAIR_STATEMENT)


def downgrade() -> None:
    """No-op: restored actor provenance is not reversible and is safe to retain."""
