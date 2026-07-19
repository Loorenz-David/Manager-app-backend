"""index step_state_records on (workspace, coalesce(credited,created) user, entered_at)

Supports the per-worker concurrency-averaging sweep, which fetches a worker's
time-bearing records by COALESCE(credited_user_id, created_by_id) over a time window.
Functional index matches that predicate exactly.

Revision ID: a7f3c1e9d240
Revises: b7d9e3f21c04
Create Date: 2026-07-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a7f3c1e9d240'
down_revision: Union[str, None] = 'b7d9e3f21c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_step_state_records_ws_credited_entered"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX {_INDEX} ON step_state_records "
        "(workspace_id, COALESCE(credited_user_id, created_by_id), entered_at)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
