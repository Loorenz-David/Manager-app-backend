"""Realtime events for the worker-shifts write paths.

Every test here patches the push functions inside `worker_shift_realtime` rather than the
socket layer beneath them, so an assertion failure names the event and payload the frontend
would actually receive, not the transport that happened to carry it.

The property worth defending hardest is the **room split**: the worker's own room gets the
full state, the workspace room gets a lean signal. Every socket joins both rooms
unconditionally, so anything put in the workspace payload is visible to every worker on the
floor, not only to managers — and the manager-facing detail it would carry is gated behind
`require_roles([ADMIN, MANAGER])` everywhere else.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.clock_in_worker_shift import clock_in_worker_shift
from beyo_manager.services.commands.users.clock_out_worker_shift import clock_out_worker_shift
from beyo_manager.services.commands.users.close_declared_worker_state import (
    close_declared_worker_state,
)
from beyo_manager.services.commands.users.declare_worker_state import declare_worker_state
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import worker_shift_realtime
from tests.fixtures.phase2_row_factories import adopt_or_create_role, create_test_workspace


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class _Recorder:
    """Captures what each room was sent, in order."""

    def __init__(self) -> None:
        self.user_events: list[tuple[str, str, object]] = []
        self.workspace_events: list[tuple[str, str, object]] = []

    async def to_user(self, user_id: str, event: str, payload) -> None:
        self.user_events.append((user_id, event, payload))

    async def to_workspace(self, workspace_id: str, event: str, payload) -> None:
        self.workspace_events.append((workspace_id, event, payload))

    def user_payload(self, event: str) -> dict:
        matches = [payload for _, name, payload in self.user_events if name == event]
        assert len(matches) == 1, f"expected exactly one {event} to the user room, got {len(matches)}"
        return matches[0]

    def workspace_payload(self, event: str) -> object:
        matches = [payload for _, name, payload in self.workspace_events if name == event]
        assert len(matches) == 1, f"expected exactly one {event} to the workspace, got {len(matches)}"
        return matches[0]

    def workspace_event_names(self) -> list[str]:
        return [name for _, name, _ in self.workspace_events]


@pytest.fixture
def emitted(monkeypatch) -> _Recorder:
    recorder = _Recorder()
    monkeypatch.setattr(worker_shift_realtime, "push_to_user", recorder.to_user)
    monkeypatch.setattr(worker_shift_realtime, "push_workspace_refresh", recorder.to_workspace)
    monkeypatch.setattr(
        worker_shift_realtime, "push_workspace_event_items", recorder.to_workspace
    )
    return recorder


async def _seed_workspace_worker(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex
    workspace = await create_test_workspace(db_session, "shift-realtime")
    worker = User(
        username=f"shift-realtime-{suffix}",
        email=f"shift-realtime-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(worker)
    await db_session.flush()
    worker_role = await adopt_or_create_role(db_session, RoleNameEnum.WORKER)
    workspace_role = await db_session.scalar(
        select(WorkspaceRole).where(
            WorkspaceRole.workspace_id == workspace.client_id,
            WorkspaceRole.role_id == worker_role.client_id,
            WorkspaceRole.specialization.is_(None),
        )
    )
    if workspace_role is None:
        workspace_role = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=worker_role.client_id,
            is_system=True,
        )
        db_session.add(workspace_role)
        await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            user_id=worker.client_id,
            workspace_id=workspace.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return workspace, worker


def _ctx(db_session, workspace, actor, incoming_data: dict | None = None) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": actor.client_id,
            "role_name": RoleNameEnum.WORKER.value,
        },
        incoming_data=incoming_data or {},
        session=db_session,
    )


async def _seed_personal_pause_reason(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    requires_description: bool = False,
) -> PauseReason:
    suffix = uuid4().hex
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Realtime Break {suffix}",
        slug=f"realtime-break-{suffix}",
        pause_type=PauseTypeEnum.PERSONAL,
        requires_description=requires_description,
        created_by_id=worker.client_id,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


async def _seed_working_step(db_session, workspace: Workspace, worker: User) -> TaskStep:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"realtime-section-{suffix}",
        created_by_id=worker.client_id,
    )
    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=worker.client_id,
    )
    db_session.add_all([section, task])
    await db_session.flush()
    step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=TaskStepStateEnum.WORKING,
        working_section_id=section.client_id,
        assigned_worker_id=worker.client_id,
        created_by_id=worker.client_id,
    )
    db_session.add(step)
    await db_session.flush()
    record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        exited_at=None,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def test_clock_in_sends_the_full_state_to_the_worker_and_a_lean_one_to_the_workspace(
    db_session, emitted
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)

    await clock_in_worker_shift(_ctx(db_session, workspace, worker))

    user_id, event, payload = emitted.user_events[0]
    assert user_id == worker.client_id
    assert event == worker_shift_realtime.WORKER_SHIFT_STATE_CHANGED
    # The payload the floor app can write straight into its `GET /current` cache.
    assert payload["clocked_in"] is True
    assert payload["state"] == "idle"
    assert payload["shift_started_at"] is not None
    assert set(payload) >= {"user_id", "clocked_in", "state", "state_entered_at", "pause_reason"}

    workspace_id, event, roster = emitted.workspace_events[0]
    assert workspace_id == workspace.client_id
    assert event == worker_shift_realtime.WORKER_SHIFT_ROSTER_CHANGED
    assert roster == {
        "user_id": worker.client_id,
        "clocked_in": True,
        "state": "idle",
        "state_entered_at": payload["state_entered_at"],
    }


async def test_clock_out_tells_the_workspace_the_shift_ended(db_session, emitted) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    emitted.user_events.clear()
    emitted.workspace_events.clear()

    await clock_out_worker_shift(_ctx(db_session, workspace, worker))

    assert emitted.user_payload(worker_shift_realtime.WORKER_SHIFT_STATE_CHANGED) == {
        "user_id": worker.client_id,
        "clocked_in": False,
        "shift_started_at": None,
        "state": None,
        "state_entered_at": None,
        "pause_reason": None,
        "declared_state": None,
    }
    assert emitted.workspace_payload(worker_shift_realtime.WORKER_SHIFT_ROSTER_CHANGED) == {
        "user_id": worker.client_id,
        "clocked_in": False,
        "state": None,
        "state_entered_at": None,
    }


async def test_a_declarations_description_never_reaches_the_workspace_room(
    db_session, emitted
) -> None:
    """The one payload rule this domain cannot get wrong.

    Every socket in the workspace joins the workspace room, so a description like "doctor
    appointment" put here would be readable by every worker on the floor.
    """
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_personal_pause_reason(
        db_session, workspace, worker, requires_description=True
    )
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    emitted.user_events.clear()
    emitted.workspace_events.clear()

    await declare_worker_state(
        _ctx(
            db_session,
            workspace,
            worker,
            {"pause_reason_id": reason.client_id, "description": "doctor appointment"},
        )
    )

    to_worker = emitted.user_payload(worker_shift_realtime.WORKER_SHIFT_STATE_CHANGED)
    assert to_worker["state"] == "in_pause"
    assert to_worker["declared_state"]["description"] == "doctor appointment"

    roster = emitted.workspace_payload(worker_shift_realtime.WORKER_SHIFT_ROSTER_CHANGED)
    assert set(roster) == {"user_id", "clocked_in", "state", "state_entered_at"}
    assert "doctor appointment" not in str(roster)


async def test_closing_a_declaration_announces_the_return_to_idle(db_session, emitted) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_personal_pause_reason(db_session, workspace, worker)
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    await declare_worker_state(
        _ctx(db_session, workspace, worker, {"pause_reason_id": reason.client_id})
    )
    emitted.user_events.clear()
    emitted.workspace_events.clear()

    await close_declared_worker_state(_ctx(db_session, workspace, worker))

    assert emitted.user_payload(worker_shift_realtime.WORKER_SHIFT_STATE_CHANGED)["state"] == "idle"
    assert (
        emitted.workspace_payload(worker_shift_realtime.WORKER_SHIFT_ROSTER_CHANGED)["state"]
        == "idle"
    )


async def test_clock_out_announces_the_steps_it_force_paused(db_session, emitted) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    step = await _seed_working_step(db_session, workspace, worker)
    emitted.user_events.clear()
    emitted.workspace_events.clear()

    await clock_out_worker_shift(_ctx(db_session, workspace, worker))

    assert emitted.workspace_payload(worker_shift_realtime.TASK_STEP_STATE_CHANGED) == [
        {"client_id": step.client_id, "new_state": "paused"}
    ]


async def test_declaring_announces_the_steps_it_auto_paused(db_session, emitted) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    reason = await _seed_personal_pause_reason(db_session, workspace, worker)
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    step = await _seed_working_step(db_session, workspace, worker)
    emitted.user_events.clear()
    emitted.workspace_events.clear()

    await declare_worker_state(
        _ctx(db_session, workspace, worker, {"pause_reason_id": reason.client_id})
    )

    assert emitted.workspace_payload(worker_shift_realtime.TASK_STEP_STATE_CHANGED) == [
        {"client_id": step.client_id, "new_state": "paused"}
    ]


async def test_no_step_event_when_nothing_was_paused(db_session, emitted) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await clock_in_worker_shift(_ctx(db_session, workspace, worker))
    emitted.workspace_events.clear()

    await clock_out_worker_shift(_ctx(db_session, workspace, worker))

    assert worker_shift_realtime.TASK_STEP_STATE_CHANGED not in emitted.workspace_event_names()


async def test_a_broken_socket_transport_does_not_fail_the_clock_in(
    db_session, monkeypatch, caplog
) -> None:
    """The write is already committed by the time we emit. Losing the broadcast costs the
    client a stale render until its next fetch; raising here would cost the worker a clock-in
    that the database says happened.
    """
    workspace, worker = await _seed_workspace_worker(db_session)

    async def explode(*args, **kwargs):
        raise RuntimeError("redis is down")

    monkeypatch.setattr(worker_shift_realtime, "push_to_user", explode)

    with caplog.at_level("ERROR"):
        result = await clock_in_worker_shift(_ctx(db_session, workspace, worker))

    assert result == {"action": "clock_in", "user_id": worker.client_id}
    assert await db_session.scalar(
        select(UserShiftStateRecord.client_id).where(
            UserShiftStateRecord.workspace_id == workspace.client_id,
            UserShiftStateRecord.user_id == worker.client_id,
            UserShiftStateRecord.exited_at.is_(None),
        )
    )
    assert "worker_shift.realtime_emit_failed" in caplog.text
