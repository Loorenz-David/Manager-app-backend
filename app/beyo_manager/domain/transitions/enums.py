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
    # A case was raised on the task, so the system stopped its working steps. The worker
    # does not pick this from the pause sheet — which is exactly why it is a member here
    # and not a revived `pause_case_created` catalog row. *Which* kind of case it was is
    # carried by the record's `description`, following the task-switch precedent
    # ("started working with {article_number}"): this vocabulary names the class of thing
    # that happened, the description names the instance.
    CASE_CREATED = "case_created"
    # A manager forced a task to READY, so the system skipped its still-open steps
    # (`force_task_ready`). The worker never picks this — it is not on the pause sheet —
    # which is what makes it a member here. It types every synthetic close so analytics
    # can tell an administrative closure from work that actually happened; the free-text
    # justification rides on the record's `description`, following the precedent above.
    #
    # Unlike every member above it, this one is never written to a PAUSED record — it
    # lands on the SKIPPED records the force closes produce. It still carries a
    # `labels.py` entry, because the step serializer resolves through that map for any
    # record without a catalog row; see the note there.
    FORCED_READY = "forced_ready"
