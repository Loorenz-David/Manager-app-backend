"""Shared helper: propagate a section's `allows_batch_working` onto its open steps.

`task_steps.allows_batch_working` is a snapshot copied from the section at step
creation (`create_task`, `add_task_steps`), and it — not the section column — is
what every enforcement point actually reads:

  - `transition_step_state`            the one-active-step auto-pause guard
  - `_step_transition_core`            the same guard, shared by every other driver
  - `_user_working_record`             the conflict lookup itself filters on it
  - `transition_step_state_batch`      rejects non-batch steps outright
  - `get_user_last_active_step_record` decides whether the resume card is a batch card

The section column, by contrast, is only a template for new steps plus the flag
the workers app renders its batch UI from. So whenever a writer flips the section
column without re-stamping the existing steps, the UI (section-driven) and the
backend (step-driven) disagree for those steps, permanently — a section can read
"not batchable" while its steps keep escaping the one-active-step rule.

Every writer of `WorkingSection.allows_batch_working` on an *existing* section must
therefore call this: `edit_working_section` and the bootstrap re-seed. The creation
paths do not, having no steps yet.

TERMINAL STEPS ARE DELIBERATELY EXCLUDED. On a closed step the flag is not drift,
it is the historical record of the rule the step was worked under, and analytics
reads it as exactly that: `averaged_time` selects it as `is_batchable` and the
`concurrency` sweep divides a batchable interval's time across its overlaps while
giving a non-batch interval its full duration undivided. Re-stamping closed steps
would silently rewrite past worked-time attribution.
"""

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.models.tables.tasks.task_step import TaskStep


async def sync_step_batch_flag_for_section_in_session(
    session: AsyncSession,
    workspace_id: str,
    section_id: str,
    allows_batch_working: bool,
) -> int:
    """Re-stamp the section's non-terminal steps with `allows_batch_working`.

    Returns the number of steps corrected. Idempotent: the predicate excludes steps
    that already carry the target value, so a second call updates zero rows.

    Does not commit — the caller owns the transaction.
    """
    result = await session.execute(
        update(TaskStep)
        .where(
            TaskStep.workspace_id == workspace_id,
            TaskStep.working_section_id == section_id,
            TaskStep.is_deleted.is_(False),
            TaskStep.state.not_in(TERMINAL_STEP_STATES),
            TaskStep.allows_batch_working.is_(not allows_batch_working),
        )
        .values(allows_batch_working=allows_batch_working)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0
