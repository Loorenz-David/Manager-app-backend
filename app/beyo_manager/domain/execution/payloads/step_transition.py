"""Payload for step state transition events processed by analytics worker."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StepTransitionPayload:
    """Immutable payload for step state transition events.
    
    All fields are JSON-serialisable (strings, not datetime objects).
    Time values are ISO 8601 formatted strings.
    """
    step_id: str
    task_id: str
    workspace_id: str
    closing_record_id: str      # client_id of the StepStateRecord being closed (exited_at set)
    closing_state: str          # the state of the record being closed (old state)
    new_state: str              # the state being entered
    assigned_worker_id: str | None
    working_section_id: str
    working_section_name_snapshot: str | None  # section name at time of transition
    entered_at: str             # ISO 8601 string of the closing record's entered_at
    exited_at: str              # ISO 8601 string of the closing record's exited_at (now)
    step_task_id: str           # same as task_id — included for worker convenience
