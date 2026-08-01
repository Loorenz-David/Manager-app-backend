"""drop_transition_reason_backfill_journal

Drops the journal written by `97b60e06d42a`, which recorded exactly which 270 rows that migration
rewrote (228 on `step_state_records`, 42 on `user_shift_state_records`).

**Applying this migration makes `97b60e06d42a` permanently irreversible.** Post-cutover writers
produce rows shape-identical to backfilled ones, so once the journal is gone no predicate can
identify "the backfilled rows" again. `97b60e06d42a.downgrade()` reads this table; without it that
downgrade cannot restore anything.

## Why this refuses to run by default

Being a separate revision is **not** enough protection, and this is not hypothetical: during phase
4 the author ran a routine `alembic upgrade head` to restore state after an unrelated test, `head`
had moved to include this revision, and the journal was dropped without anyone deciding to drop it.
It was recoverable only because that database had no post-cutover traffic, so the backfilled rows
were still exactly the rows carrying `transition_reason = 'other_task_priority'`. **On a database
with live traffic the two populations are indistinguishable and the reconstruction is impossible.**

So `upgrade()` refuses unless `ALLOW_DROP_BACKFILL_JOURNAL=yes` is set in the environment. An
unqualified `upgrade head` stops here with an explanation instead of destroying the record. Refusing
is the safe failure: a deploy that halts is recoverable, a journal that is gone is not.

Set the variable only when the retirement has been reviewed **and** phase 3's backfill has been
verified on the target database — not merely on a copy of it.

    ALLOW_DROP_BACKFILL_JOURNAL=yes alembic upgrade head

## Row count at the time this revision was written

**270** — 228 `step_state_records`, 42 `user_shift_state_records`. Recorded here because the record
of what was rewritten has to outlive the table itself. `upgrade()` also prints the live count before
dropping, so the deploy log carries the number as it actually was.

`downgrade` recreates the table's structure but **cannot** recreate its contents. It exists so the
revision graph stays walkable, not because it restores anything.
"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f3d2e60a17'
down_revision: Union[str, None] = 'b4e7a1c93f28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_JOURNAL = 'transition_reason_backfill_journal'
_ACK_ENV = 'ALLOW_DROP_BACKFILL_JOURNAL'


def upgrade() -> None:
    if os.environ.get(_ACK_ENV) != 'yes':
        raise RuntimeError(
            f"Refusing to drop `{_JOURNAL}` without an explicit acknowledgement.\n"
            f"\n"
            f"This table is the only record of which rows migration 97b60e06d42a rewrote, and "
            f"dropping it makes that backfill permanently irreversible — post-cutover rows are "
            f"shape-identical to backfilled ones, so nothing can tell them apart afterwards.\n"
            f"\n"
            f"If you reached this from a plain `alembic upgrade head`, that is exactly what this "
            f"guard is for: nothing is broken, and no decision has been lost. Upgrade to "
            f"`b4e7a1c93f28` instead to apply the retirement without dropping the journal.\n"
            f"\n"
            f"When the retirement has been reviewed AND phase 3's backfill is verified on THIS "
            f"database (not a copy), re-run with:\n"
            f"\n"
            f"    {_ACK_ENV}=yes alembic upgrade head\n"
        )

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
