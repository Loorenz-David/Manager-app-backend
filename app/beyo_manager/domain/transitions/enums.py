import enum


class TransitionReasonEnum(enum.Enum):
    """Code-owned vocabulary for state transitions that the system controls (T1).

    Persisted as a constrained string, never resolved through a database lookup — that
    is the whole point: a mandatory state-machine transition must not depend on a
    workspace-editable `pause_reasons` row existing.

    Lives in its own domain because the column spans two of them
    (`step_state_records` in tasks, `user_shift_state_records` in users), so neither
    owns it. `models/` may import `domain/<domain>/enums.py` — this module holds the
    enum ONLY, so it stays importable from the model layer. Label resolution lives in
    the sibling `labels.py`, which read paths import and models never do.
    """

    SHIFT_ENDED = "shift_ended"
    OTHER_TASK_PRIORITY = "other_task_priority"
    WORKER_DECLARED_STATE = "worker_declared_state"
