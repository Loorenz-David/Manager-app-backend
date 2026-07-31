"""retire_system_pause_reason_machinery

System transitions no longer resolve a `pause_reasons` row, so the machinery that served them
retires here (system_transition_reasons phase 4). Four independent changes:

1. `uq_pause_reasons_slug` is scoped to `(workspace_id, slug)`. It was **globally** unique, which
   meant a slug could exist in exactly one workspace database-wide — so bootstrapping a second
   workspace raised IntegrityError and only one workspace ever received the default catalog. This
   is a supporting change, not the architectural fix; the fix is that nothing resolves by slug.

2. `pause_other_task_priority` is soft-deleted. Auto-pause on task switch carries
   `transition_reason = other_task_priority` with no catalog reference, so the row is a picker entry
   nobody selects and nothing resolves. Phase 3 nulled every reference to it; this migration
   re-asserts that before deleting.

   `pause_ended_shift` is deliberately NOT deleted — a worker legitimately picks it from the pause
   sheet, and `list_pause_reasons` filters `is_deleted`, so deleting it would remove that option.
   `pause_case_created` is already soft-deleted and keeps its 7 historical references.

3. `is_system_managed` is cleared to `false` everywhere. The column and its serialized field stay
   because the published schema declares them required, but nothing reads them for behaviour: the
   delete guard is gone.

4. A CHECK constraint on `step_state_records` makes T2 true by construction — a row may carry a
   transition reason or a catalog reference, never both.

   It is deliberately NOT applied to `user_shift_state_records`. A declaration-sourced segment there
   carries `worker_declared_state` AND the catalog reason the worker chose, by design; both facts
   are true and both are wanted.

Reversible. `downgrade` restores the global index, un-deletes the row, and drops the constraint. It
does NOT restore `is_system_managed = true` on the two rows that carried it: that flag is inert, and
restoring it would re-arm a delete guard that no longer exists.

Compliance for the constraint was verified against the production copy before it was written:
`SELECT count(*) FROM step_state_records WHERE transition_reason IS NOT NULL AND pause_reason_id IS
NOT NULL` returned 0.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b4e7a1c93f28'
down_revision: Union[str, None] = '97b60e06d42a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RETIRED_SLUG = 'pause_other_task_priority'
_CHECK_NAME = 'ck_step_state_records_transition_xor_catalog'


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Scope the slug index to the workspace.
    op.drop_index('uq_pause_reasons_slug', table_name='pause_reasons')
    op.create_index(
        'uq_pause_reasons_slug', 'pause_reasons', ['workspace_id', 'slug'], unique=True
    )

    # 2. Retire `pause_other_task_priority` — but refuse if anything still references it.
    #    Phase 3 nulled every reference; if that is not true here, this database is not in the
    #    state this migration expects and deleting the row would strand live data.
    remaining = bind.execute(
        sa.text(
            """
            SELECT
              (SELECT count(*) FROM step_state_records s
                 JOIN pause_reasons p ON p.client_id = s.pause_reason_id
                WHERE p.slug = :slug)
            + (SELECT count(*) FROM user_shift_state_records u
                 JOIN pause_reasons p ON p.client_id = u.reason
                WHERE p.slug = :slug)
            + (SELECT count(*) FROM user_declared_state_records d
                 JOIN pause_reasons p ON p.client_id = d.pause_reason_id
                WHERE p.slug = :slug)
            """
        ),
        {"slug": _RETIRED_SLUG},
    ).scalar_one()
    if remaining:
        raise RuntimeError(
            f"Refusing to retire '{_RETIRED_SLUG}': {remaining} rows still reference it. "
            "Phase 3's backfill (97b60e06d42a) has not been applied to this database."
        )

    op.execute(
        sa.text(
            """
            UPDATE pause_reasons
               SET is_deleted = true,
                   deleted_at = COALESCE(deleted_at, now())
             WHERE slug = :slug
               AND is_deleted = false
            """
        ).bindparams(slug=_RETIRED_SLUG)
    )

    # 3. The flag is inert from here on.
    op.execute("UPDATE pause_reasons SET is_system_managed = false WHERE is_system_managed = true")

    # 4. Mutual exclusion, on the source table only.
    op.create_check_constraint(
        _CHECK_NAME,
        'step_state_records',
        'transition_reason IS NULL OR pause_reason_id IS NULL',
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK_NAME, 'step_state_records', type_='check')

    op.execute(
        sa.text(
            """
            UPDATE pause_reasons
               SET is_deleted = false,
                   deleted_at = NULL
             WHERE slug = :slug
            """
        ).bindparams(slug=_RETIRED_SLUG)
    )

    # `is_system_managed` is intentionally not restored — see the module docstring.

    op.drop_index('uq_pause_reasons_slug', table_name='pause_reasons')
    op.create_index('uq_pause_reasons_slug', 'pause_reasons', ['slug'], unique=True)
