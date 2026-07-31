"""drop_transition_reason_backfill_journal

Drops the journal written by `97b60e06d42a`, which recorded exactly which 270 rows that migration
rewrote (228 on `step_state_records`, 42 on `user_shift_state_records`).

**Applying this migration makes `97b60e06d42a` permanently irreversible.** Post-cutover writers
produce rows shape-identical to backfilled ones, so once the journal is gone no predicate can
identify "the backfilled rows" again. `97b60e06d42a.downgrade()` reads this table; without it that
downgrade cannot restore anything.

That is why it is a separate revision rather than part of `b4e7a1c93f28`. It is applied **last**,
after the retirement work is verified — and per the phase 4 plan's stated default ("keep it"), it is
deliberately **not** applied before the phase has been independently reviewed. If the review finds
the backfill needs reverting, the journal is precisely what is required.

Row count at the time this revision was written: **270** — 228 `step_state_records`,
42 `user_shift_state_records`. Recorded here because the record of what was rewritten has to
outlive the table itself.

`downgrade` recreates the table's structure but **cannot** recreate its contents. It is provided so
the revision graph stays walkable, not because it restores anything. An empty journal makes
`97b60e06d42a.downgrade()` a no-op rather than an error — which is honest, but is not a recovery.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f3d2e60a17'
down_revision: Union[str, None] = 'b4e7a1c93f28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_JOURNAL = 'transition_reason_backfill_journal'


def upgrade() -> None:
    op.execute(f'DROP TABLE IF EXISTS {_JOURNAL}')


def downgrade() -> None:
    # Structure only. The 270 rows it held are not recoverable from here.
    op.create_table(
        _JOURNAL,
        sa.Column('table_name', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('previous_pause_reason_id', sa.String(length=64), nullable=True),
    )
