"""Full-loop kiosk flow (declared worker states, phase 6, acceptance 6).

Drives the shop-floor device's whole day against the real database:
floor sign-in (phase 5) -> roster with clock codes (phase 6) -> GET /current ->
clock-in on-behalf -> declare on-behalf -> GET /current -> clock-out (phase 4).

The device never authenticates as the worker: every step below runs under the
floor session's claims, which is exactly what the kiosk holds.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.auth.sign_in_user import sign_in_user
from beyo_manager.services.commands.users.clock_in_worker_shift import clock_in_worker_shift
from beyo_manager.services.commands.users.clock_out_worker_shift import clock_out_worker_shift
from beyo_manager.services.commands.users.declare_worker_state import declare_worker_state
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.users.get_current_worker_shift_state import (
    get_current_worker_shift_state,
)
from beyo_manager.services.queries.users.list_users import list_users


pytestmark = pytest.mark.asyncio

_DEVICE_PASSWORD = "FloorDevice123!"


async def _workspace_role(db_session, workspace: Workspace, role_name: RoleNameEnum) -> WorkspaceRole:
    role = (
        await db_session.execute(select(Role).where(Role.name == role_name))
    ).scalar_one()
    workspace_role = await db_session.scalar(
        select(WorkspaceRole)
        .where(
            WorkspaceRole.workspace_id == workspace.client_id,
            WorkspaceRole.role_id == role.client_id,
            WorkspaceRole.specialization.is_(None),
        )
        .limit(1)
    )
    if workspace_role is None:
        workspace_role = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=role.client_id,
            is_system=True,
        )
        db_session.add(workspace_role)
        await db_session.flush()
    return workspace_role


async def _seed_member(
    db_session,
    workspace: Workspace,
    role_name: RoleNameEnum,
    *,
    label: str,
    password: str | None = None,
) -> User:
    suffix = uuid4().hex
    user = User(
        username=f"{label}-{suffix}",
        email=f"{label}-{suffix}@example.com",
        password=(
            bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if password is not None
            else "test-password-hash"
        ),
    )
    db_session.add(user)
    await db_session.flush()
    workspace_role = await _workspace_role(db_session, workspace, role_name)
    db_session.add(
        WorkspaceMembership(
            user_id=user.client_id,
            workspace_id=workspace.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()
    return user


async def _kiosk_workspace(db_session) -> Workspace:
    """A workspace with a populated pause-reason catalog.

    Clock-out no longer resolves `pause_ended_shift` — it writes
    `transition_reason = shift_ended` with no catalog reference, so this flow would work in a
    workspace with an empty catalog. The catalog is still required for the *declaration* half of
    the loop, where the worker picks a reason, so the fixture keeps selecting a populated
    workspace and the whole loop stays mock-free.

    The `is_system_managed` filter that used to be here is gone: no row carries that flag any
    more. Selecting on it would match nothing and take this fixture's assert with it.
    """
    workspace = await db_session.scalar(
        select(Workspace)
        .join(PauseReason, PauseReason.workspace_id == Workspace.client_id)
        .where(
            PauseReason.slug == "pause_ended_shift",
            PauseReason.is_deleted.is_(False),
        )
        .limit(1)
    )
    assert workspace is not None, "no workspace has a 'pause_ended_shift' reason"
    return workspace


async def _seed_kiosk_workspace(db_session, *, clock_in_code: str | None):
    """Workspace + floor device account (manager) + one worker holding a clock code."""
    workspace = await _kiosk_workspace(db_session)
    device_manager = await _seed_member(
        db_session,
        workspace,
        RoleNameEnum.MANAGER,
        label="kiosk-device",
        password=_DEVICE_PASSWORD,
    )
    worker = await _seed_member(db_session, workspace, RoleNameEnum.WORKER, label="kiosk-worker")
    db_session.add(
        UserWorkProfile(
            user_id=worker.client_id,
            workspace_id=workspace.client_id,
            clock_in_code=clock_in_code,
            created_by_id=device_manager.client_id,
        )
    )
    await db_session.flush()
    return workspace, device_manager, worker


async def _floor_claims(db_session, device_manager: User) -> dict:
    """Sign in exactly as the device does and return the token's real claims."""
    response = await sign_in_user(
        ServiceContext(
            identity={},
            incoming_data={
                "email": device_manager.email,
                "password": _DEVICE_PASSWORD,
                "app_scope": "floor",
            },
            session=db_session,
        )
    )
    claims = jwt.decode(
        response["access_token"],
        settings.jwt_secret_key,
        algorithms=["HS256"],
    )
    # Phase 5 invariants the kiosk depends on: never-expiring, no refresh cookie.
    assert claims["app_scope"] == "floor"
    assert "exp" not in claims
    assert "_refresh_token" not in response
    return claims


def _roster_ctx(db_session, claims: dict, worker: User) -> ServiceContext:
    """The device's roster poll, narrowed to the seeded worker for determinism."""
    return ServiceContext(
        identity=claims,
        incoming_data={},
        session=db_session,
        query_params={
            "q": worker.username,
            "string_filters": "username",
            "role": RoleNameEnum.WORKER.value,
            "working_sections": None,
            "limit": "50",
            "offset": "0",
            "compact": "True",
        },
    )


def _current_ctx(db_session, claims: dict, worker: User) -> ServiceContext:
    return ServiceContext(
        identity=claims,
        incoming_data={},
        session=db_session,
        query_params={"user_id": worker.client_id},
    )


def _action_ctx(db_session, claims: dict, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity=claims,
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_open_working_step(db_session, workspace: Workspace, worker: User) -> TaskStep:
    suffix = uuid4().hex
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"kiosk-section-{suffix}",
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
        entered_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        exited_at=None,
        created_by_id=worker.client_id,
        credited_user_id=worker.client_id,
    )
    db_session.add(record)
    await db_session.flush()
    step.latest_state_record_id = record.client_id
    await db_session.flush()
    return step


async def test_kiosk_full_loop_from_floor_sign_in_to_clock_out(db_session) -> None:
    code = uuid4().hex[:8]
    workspace, device_manager, worker = await _seed_kiosk_workspace(
        db_session, clock_in_code=code
    )
    reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Cleaning {uuid4().hex}",
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=device_manager.client_id,
    )
    db_session.add(reason)
    await db_session.flush()
    await _seed_open_working_step(db_session, workspace, worker)

    # 1. Device signs in once under the floor scope.
    claims = await _floor_claims(db_session, device_manager)

    # 2. Device polls the roster and matches the typed code locally (no identify endpoint).
    roster = await list_users(_roster_ctx(db_session, claims, worker))
    matched = [item for item in roster["users"] if item.get("clock_in_code") == code]
    assert len(matched) == 1, roster["users"]
    assert matched[0]["client_id"] == worker.client_id
    assert matched[0]["email"] == worker.email

    # 3. Cache decides *who*; state always comes fresh from the server.
    before = await get_current_worker_shift_state(_current_ctx(db_session, claims, worker))
    assert before == {
        "user_id": worker.client_id,
        "clocked_in": False,
        "shift_started_at": None,
        "state": None,
        "state_entered_at": None,
        "pause_reason": None,
        "declared_state": None,
    }

    # 4. Clock in on behalf of the confirmed worker.
    clock_in_result = await clock_in_worker_shift(
        _action_ctx(db_session, claims, {"user_id": worker.client_id})
    )
    assert clock_in_result == {"action": "clock_in", "user_id": worker.client_id}
    assert "analytics" not in clock_in_result

    after_clock_in = await get_current_worker_shift_state(
        _current_ctx(db_session, claims, worker)
    )
    assert after_clock_in["clocked_in"] is True
    assert after_clock_in["state"] == UserShiftStateEnum.IDLE.value
    assert after_clock_in["declared_state"] is None

    # 5. Declare a state on behalf; the worker's open working step is auto-paused (D5).
    declare_result = await declare_worker_state(
        _action_ctx(
            db_session,
            claims,
            {"user_id": worker.client_id, "pause_reason_id": reason.client_id},
        )
    )
    assert declare_result["shift_state"] == UserShiftStateEnum.IN_PAUSE.value
    assert declare_result["paused_steps"] == 1
    assert declare_result["declared_state"]["pause_reason"]["id"] == reason.client_id

    declared_view = await get_current_worker_shift_state(
        _current_ctx(db_session, claims, worker)
    )
    assert declared_view["state"] == UserShiftStateEnum.IN_PAUSE.value
    assert declared_view["pause_reason"]["id"] == reason.client_id
    assert declared_view["declared_state"]["id"] == declare_result["declared_state"]["id"]

    # 6. Clock out. transitioned_steps is 0 *because* the declaration already paused
    #    the only working step — the same story on both sides of the seam.
    clock_out_result = await clock_out_worker_shift(
        _action_ctx(db_session, claims, {"user_id": worker.client_id})
    )
    assert clock_out_result == {
        "action": "clock_out",
        "user_id": worker.client_id,
        "transitioned_steps": 0,
        "analytics": None,
        "_clock_out_at": clock_out_result["_clock_out_at"],
    }

    closed = await get_current_worker_shift_state(_current_ctx(db_session, claims, worker))
    assert closed["clocked_in"] is False


async def test_kiosk_clock_out_reports_working_steps_it_force_closed(db_session) -> None:
    workspace, device_manager, worker = await _seed_kiosk_workspace(
        db_session, clock_in_code=uuid4().hex[:8]
    )
    claims = await _floor_claims(db_session, device_manager)

    await clock_in_worker_shift(
        _action_ctx(db_session, claims, {"user_id": worker.client_id})
    )
    await _seed_open_working_step(db_session, workspace, worker)

    clock_out_result = await clock_out_worker_shift(
        _action_ctx(db_session, claims, {"user_id": worker.client_id})
    )

    assert clock_out_result["transitioned_steps"] == 1
    assert clock_out_result["analytics"] is None


async def test_kiosk_roster_matches_worker_without_a_clock_code_by_email(db_session) -> None:
    """Rollout needs no backfill: email matching works while clock_in_code is NULL."""
    _, device_manager, worker = await _seed_kiosk_workspace(db_session, clock_in_code=None)
    claims = await _floor_claims(db_session, device_manager)

    roster = await list_users(_roster_ctx(db_session, claims, worker))

    item = next(i for i in roster["users"] if i["client_id"] == worker.client_id)
    assert item["clock_in_code"] is None
    assert item["email"] == worker.email
