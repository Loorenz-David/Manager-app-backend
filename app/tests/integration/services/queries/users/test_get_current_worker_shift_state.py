import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_current_worker_shift_state import (
    get_current_worker_shift_state,
)
from tests.fixtures.phase2_row_factories import adopt_or_create_role, create_test_workspace


async def _seed_user(db_session, label: str) -> User:
    suffix = uuid4().hex
    user = User(
        username=f"{label}-{suffix}",
        email=f"{label}-{suffix}@example.com",
        password="test-password-hash",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_workspace_worker(db_session, label: str = "current-worker") -> tuple[Workspace, User]:
    workspace = await create_test_workspace(db_session, "current-worker-workspace")
    worker = await _seed_user(db_session, label)
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


def _ctx(
    db_session,
    workspace: Workspace,
    actor: User,
    role_name: str,
    *,
    requested_user_id: str | None = None,
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace.client_id,
            "user_id": actor.client_id,
            "role_name": role_name,
        },
        incoming_data={},
        query_params={"user_id": requested_user_id},
        session=db_session,
    )


async def _seed_pause_reason(
    db_session,
    workspace: Workspace,
    actor: User,
    *,
    image_url: str | None = None,
) -> PauseReason:
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Current reason {uuid4().hex}",
        image_url=image_url,
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=actor.client_id,
    )
    db_session.add(reason)
    await db_session.flush()
    return reason


async def _seed_open_shift(
    db_session,
    workspace: Workspace,
    worker: User,
    *,
    state: UserShiftStateEnum,
    reason: str | None = None,
) -> tuple[datetime, datetime]:
    shift_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    state_entered_at = shift_started_at + timedelta(minutes=10)
    db_session.add_all(
        [
            UserShiftStateRecord(
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                state=UserShiftStateEnum.STARTED_SHIFT,
                entered_at=shift_started_at,
                exited_at=shift_started_at,
                changed_by_id=worker.client_id,
                reason=None,
                manually_recorded=False,
            ),
            UserShiftStateRecord(
                workspace_id=workspace.client_id,
                user_id=worker.client_id,
                state=state,
                entered_at=state_entered_at,
                exited_at=None,
                changed_by_id=worker.client_id,
                reason=reason,
                manually_recorded=False,
            ),
        ]
    )
    await db_session.flush()
    return shift_started_at, state_entered_at


@pytest.mark.integration
async def test_current_state_returns_clocked_out_shape_without_write_lock(
    db_session,
    monkeypatch,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    statements = []
    execute = db_session.execute

    async def _recording_execute(statement, *args, **kwargs):
        statements.append(statement)
        return await execute(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", _recording_execute)

    result = await get_current_worker_shift_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    assert result == {
        "user_id": worker.client_id,
        "clocked_in": False,
        "shift_started_at": None,
        "state": None,
        "state_entered_at": None,
        "pause_reason": None,
        "declared_state": None,
    }
    assert statements
    assert all(statement._for_update_arg is None for statement in statements)


@pytest.mark.integration
@pytest.mark.parametrize(
    "state",
    [
        UserShiftStateEnum.IDLE,
        UserShiftStateEnum.WORKING,
        UserShiftStateEnum.IN_PAUSE,
    ],
)
async def test_current_state_serializes_idle_working_and_step_pause(
    db_session,
    state: UserShiftStateEnum,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    pause_reason = (
        await _seed_pause_reason(
            db_session,
            workspace,
            worker,
            image_url="https://example.com/reason.png",
        )
        if state is UserShiftStateEnum.IN_PAUSE
        else None
    )
    shift_started_at, state_entered_at = await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=state,
        reason=pause_reason.client_id if pause_reason else None,
    )

    result = await get_current_worker_shift_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    assert result == {
        "user_id": worker.client_id,
        "clocked_in": True,
        "shift_started_at": shift_started_at.isoformat(),
        "state": state.value,
        "state_entered_at": state_entered_at.isoformat(),
        "pause_reason": (
            {
                "id": pause_reason.client_id,
                "name": pause_reason.name,
                "image_url": pause_reason.image_url,
            }
            if pause_reason
            else None
        ),
        "declared_state": None,
    }


@pytest.mark.integration
async def test_current_state_serializes_open_declared_state(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    pause_reason = await _seed_pause_reason(db_session, workspace, worker)
    shift_started_at, state_entered_at = await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=UserShiftStateEnum.IN_PAUSE,
        reason=pause_reason.client_id,
    )
    declared = UserDeclaredStateRecord(
        workspace_id=workspace.client_id,
        user_id=worker.client_id,
        pause_reason_id=pause_reason.client_id,
        description="Cleaning section B",
        entered_at=state_entered_at,
        exited_at=None,
        created_by_id=worker.client_id,
    )
    db_session.add(declared)
    await db_session.flush()

    result = await get_current_worker_shift_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    assert result == {
        "user_id": worker.client_id,
        "clocked_in": True,
        "shift_started_at": shift_started_at.isoformat(),
        "state": "in_pause",
        "state_entered_at": state_entered_at.isoformat(),
        "pause_reason": {
            "id": pause_reason.client_id,
            "name": pause_reason.name,
            "image_url": pause_reason.image_url,
        },
        "declared_state": {
            "id": declared.client_id,
            "pause_reason": {
                "id": pause_reason.client_id,
                "name": pause_reason.name,
                "image_url": pause_reason.image_url,
            },
            "description": "Cleaning section B",
            "entered_at": state_entered_at.isoformat(),
        },
    }


@pytest.mark.integration
async def test_current_state_serializes_legacy_free_text_reason(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    shift_started_at, state_entered_at = await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=UserShiftStateEnum.IN_PAUSE,
        reason="legacy meeting",
    )

    result = await get_current_worker_shift_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    assert result == {
        "user_id": worker.client_id,
        "clocked_in": True,
        "shift_started_at": shift_started_at.isoformat(),
        "state": "in_pause",
        "state_entered_at": state_entered_at.isoformat(),
        "pause_reason": None,
        "declared_state": None,
        "reason_text": "legacy meeting",
    }


@pytest.mark.integration
async def test_current_state_does_not_expose_unresolvable_pause_reason_id(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=UserShiftStateEnum.IN_PAUSE,
        reason=f"{PauseReason.CLIENT_ID_PREFIX}_missing",
    )

    result = await get_current_worker_shift_state(
        _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
    )

    assert result["pause_reason"] is None
    assert result["reason_text"] is None


@pytest.mark.integration
async def test_current_state_warns_on_unresolvable_pause_reason_id(
    db_session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    unresolvable_reason_id = f"{PauseReason.CLIENT_ID_PREFIX}_missing"
    await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=UserShiftStateEnum.IN_PAUSE,
        reason=unresolvable_reason_id,
    )
    shift_record_id = await db_session.scalar(
        select(UserShiftStateRecord.client_id).where(
            UserShiftStateRecord.workspace_id == workspace.client_id,
            UserShiftStateRecord.user_id == worker.client_id,
            UserShiftStateRecord.exited_at.is_(None),
        )
    )

    with caplog.at_level(logging.WARNING):
        await get_current_worker_shift_state(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )

    warnings = [
        record
        for record in caplog.records
        if record.levelno == logging.WARNING
        and "worker_shift.current_state_unresolved_pause_reason" in record.getMessage()
    ]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert f"workspace_id={workspace.client_id}" in message
    assert f"user_id={worker.client_id}" in message
    assert f"shift_record_id={shift_record_id}" in message
    assert f"pause_reason_id={unresolvable_reason_id}" in message


@pytest.mark.integration
@pytest.mark.parametrize("reason_is_resolvable", [True, False])
async def test_current_state_does_not_warn_for_resolved_or_legacy_reason(
    db_session,
    caplog: pytest.LogCaptureFixture,
    reason_is_resolvable: bool,
) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    if reason_is_resolvable:
        pause_reason = await _seed_pause_reason(db_session, workspace, worker)
        reason = pause_reason.client_id
    else:
        reason = "legacy meeting"
    await _seed_open_shift(
        db_session,
        workspace,
        worker,
        state=UserShiftStateEnum.IN_PAUSE,
        reason=reason,
    )

    with caplog.at_level(logging.WARNING):
        await get_current_worker_shift_state(
            _ctx(db_session, workspace, worker, RoleNameEnum.WORKER.value)
        )

    assert "worker_shift.current_state_unresolved_pause_reason" not in caplog.text


@pytest.mark.integration
async def test_current_state_uses_clock_action_access_matrix(db_session) -> None:
    workspace, worker = await _seed_workspace_worker(db_session)
    _, peer = await _seed_workspace_worker(db_session, "current-peer")
    manager = await _seed_user(db_session, "current-manager")

    manager_result = await get_current_worker_shift_state(
        _ctx(
            db_session,
            workspace,
            manager,
            RoleNameEnum.MANAGER.value,
            requested_user_id=worker.client_id,
        )
    )
    assert manager_result["user_id"] == worker.client_id

    with pytest.raises(PermissionDenied):
        await get_current_worker_shift_state(
            _ctx(db_session, workspace, manager, RoleNameEnum.MANAGER.value)
        )

    with pytest.raises(PermissionDenied):
        await get_current_worker_shift_state(
            _ctx(
                db_session,
                workspace,
                worker,
                RoleNameEnum.WORKER.value,
                requested_user_id=peer.client_id,
            )
        )

    non_member = await _seed_user(db_session, "current-non-member")
    with pytest.raises(NotFound):
        await get_current_worker_shift_state(
            _ctx(
                db_session,
                workspace,
                manager,
                RoleNameEnum.MANAGER.value,
                requested_user_id=non_member.client_id,
            )
        )
