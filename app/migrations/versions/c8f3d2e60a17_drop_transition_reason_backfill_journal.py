"""drop_transition_reason_backfill_journal

Drops the journal written by `97b60e06d42a`, which recorded exactly which 270 rows that migration
rewrote (228 on `step_state_records`, 42 on `user_shift_state_records`).

**Applying this migration makes `97b60e06d42a` permanently irreversible.** Post-cutover writers
produce rows shape-identical to backfilled ones, so once the journal is gone no predicate can
identify "the backfilled rows" again. `97b60e06d42a.downgrade()` reads this table; without it that
downgrade cannot restore anything.

## Why this runs unguarded

An earlier revision of this migration refused unless `ALLOW_DROP_BACKFILL_JOURNAL=yes` was set. That
guard was removed after weighing what the journal actually protects.

Every row it holds shares the **same** `previous_pause_reason_id` — the backfill migrated references
to exactly one catalog row, so the column carries no per-row information. The journal's entire
content is *a list of which row ids were touched*, and its only use is reversing the backfill. If
that reversal were ever wanted, it would be wanted for all rows carrying
`transition_reason = 'other_task_priority'`, which is derivable without this table.

Against that, the guard raised inside `alembic upgrade head`, which in this repository's deploy
workflow runs **before** `systemctl restart`. A refusal there left the new schema applied, the new
code pulled but not running, and services never restarted — a worse outcome than the one it was
protecting against.

Rollback for this deploy is an RDS snapshot, which restores everything rather than one migration's
row rewrites.

## Row count at the time this revision was written

**270** — 228 `step_state_records`, 42 `user_shift_state_records`. Recorded here because the record
of what was rewritten has to outlive the table itself. `upgrade()` also prints the live count before
dropping, so the deploy log carries the number as it actually was.

`downgrade` recreates the table's structure but **cannot** recreate its contents. It exists so the
revision graph stays walkable, not because it restores anything.
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
    bind = op.get_bind()
    held = bind.execute(sa.text(f'SELECT count(*) FROM {_JOURNAL}')).scalar_one()
    print(f"[{revision}] dropping {_JOURNAL}, which held {held} rows")

    op.execute(f'DROP TABLE IF EXISTS {_JOURNAL}')


def downgrade() -> None:
    # Structure only. The rows it held are not recoverable from here.
    op.create_table(
        _JOURNAL,
        sa.Column('table_name', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('previous_pause_reason_id', sa.String(length=64), nullable=True),
    )
