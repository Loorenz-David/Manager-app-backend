"""Repair open legacy manual-pause provenance.

Precondition (review finding J1): this repair is sound ONLY while `user_declared_state_records`
has no writers — at this revision, every `manually_recorded = TRUE` shift row is legacy by
construction. From Phase 3 on, the reconcile writes declaration projections with the same flags
(`manually_recorded = TRUE`, `changed_by_id = NULL`); a re-run then would stamp those rows too —
inert (nothing reads `changed_by_id` for stickiness after Phase 3 removes the carve-out), but do
not re-run this migration's body outside its original position in the chain.

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
