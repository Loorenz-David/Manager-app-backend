"""Payload for item-cost result recomputation tasks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemCostResultPayload:
    """Only the identities needed to re-resolve the current task state."""

    workspace_id: str
    task_id: str
