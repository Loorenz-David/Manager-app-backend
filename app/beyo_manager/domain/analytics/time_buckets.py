"""The analytics time-bucket key for a step-state record.

Six consumers bucket a worker's time on one string, and every one of them expects the same
three keys: ``working``, ``paused``, ``ended_shift``. That third key is a **derived label,
not a step state** — it means *the system stopped this step because the shift ended and
nobody said why*. A step a worker paused for a stated reason is an ordinary pause, whatever
the reason happens to be named.

The rule lives here, once, because it is applied in two places that must not drift: the SQL
select in `services/queries/analytics/averaged_time.py` (which builds the equivalent `CASE`
over the same constants) and the clock-out rebuild in
`services/commands/users/_reconstruct_shift_middle.py`.
"""

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum

# Deliberately a bare string, not an enum member: this label outlives the step state that
# once carried the same name, and nothing here may depend on that member existing.
ENDED_SHIFT_BUCKET = "ended_shift"


def bucket_for(state_value: str, transition_reason: str | None) -> str:
    """The bucket a record counts toward, from its state and its typed transition.

    A pause the system wrote at clock-out is the unattributed off-shift bucket; anything
    else counts as itself.
    """
    if (
        state_value == TaskStepStateEnum.PAUSED.value
        and transition_reason == TransitionReasonEnum.SHIFT_ENDED.value
    ):
        return ENDED_SHIFT_BUCKET
    return state_value
