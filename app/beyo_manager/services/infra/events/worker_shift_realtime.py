"""Realtime events for the worker-shifts domain.

**Why these are functions and not `dispatch` calls.** Shift state is written from three
processes, and the payload is not something the caller holds — it is re-read from the database
so it matches `GET /worker-shifts/current` exactly. That read is the reason this module exists;
delivery itself goes through `realtime_push`, which picks the right transport for the process.

**Two events, not one.** Every socket joins both its user room and its workspace room
unconditionally (`sockets/manager.py`), so a workspace broadcast reaches every worker's
device, not just the managers'. The workspace event is therefore a lean signal — no pause
reason, no declaration text — and managers refetch the `/worker-stats` endpoints that already
gate that detail behind `require_roles([ADMIN, MANAGER])`. The full payload goes only to the
room of the worker it describes.

**Never raises.** These are called after the write has committed. A Redis hiccup must not
turn a recorded clock-out into a 500 — the client reconciles on its next fetch.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.services.infra.events.realtime_push import (
    push_to_user,
    push_workspace_event_items,
    push_workspace_refresh,
)
from beyo_manager.services.queries.users.get_current_worker_shift_state import (
    load_current_worker_shift_state,
)


logger = logging.getLogger(__name__)


WORKER_SHIFT_STATE_CHANGED = "worker-shift:state-changed"
WORKER_SHIFT_ROSTER_CHANGED = "worker-shift:roster-changed"
TASK_STEP_STATE_CHANGED = "task:step-state-changed"

# The lean workspace payload. Anything not named here — pause reason, declared state and its
# free-text description — is deliberately withheld from the workspace broadcast.
_ROSTER_FIELDS = ("user_id", "clocked_in", "state", "state_entered_at")


def build_roster_payload(state: dict) -> dict:
    return {field: state.get(field) for field in _ROSTER_FIELDS}


async def emit_worker_shift_state(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> None:
    """Broadcast the worker's shift state. Call after the write has committed.

    The state is re-read rather than assembled from what the caller happens to hold, so the
    payload is exactly what `GET /worker-shifts/current` would return for the same worker.
    The floor app can write it straight into its cache instead of refetching.
    """
    try:
        state = await load_current_worker_shift_state(session, workspace_id, user_id)
        await push_to_user(user_id, WORKER_SHIFT_STATE_CHANGED, state)
        await push_workspace_refresh(
            workspace_id, WORKER_SHIFT_ROSTER_CHANGED, build_roster_payload(state)
        )
    except Exception:
        logger.exception(
            "worker_shift.realtime_emit_failed | workspace_id=%s user_id=%s",
            workspace_id,
            user_id,
        )


async def emit_steps_paused(workspace_id: str, step_ids: list[str]) -> None:
    """Tell the workspace that these steps were paused by something other than their worker.

    Clock-out, declaring a state and raising a case all pause steps server-side. Without this
    the worker's device keeps rendering them as working until something else refetches — and
    the workers app guards its own transitions on that stale cache, so the next action fails.
    Shaped as the item list `task:step-state-changed` already carries so existing listeners
    need no change.
    """
    if not step_ids:
        return
    try:
        await push_workspace_event_items(
            workspace_id,
            TASK_STEP_STATE_CHANGED,
            [
                {"client_id": step_id, "new_state": TaskStepStateEnum.PAUSED.value}
                for step_id in step_ids
            ],
        )
    except Exception:
        logger.exception(
            "worker_shift.realtime_step_emit_failed | workspace_id=%s step_ids=%s",
            workspace_id,
            step_ids,
        )
