from dataclasses import dataclass
from uuid import uuid4

import pytest

from beyo_manager.domain.connecteam.enums import ConnecteamUserMappingStatusEnum as Status
from beyo_manager.domain.connecteam.user_csv_rows import ConnecteamCsvUser
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.connecteam import map_connecteam_user_ids as command_module
from beyo_manager.services.commands.connecteam.map_connecteam_user_ids import (
    map_connecteam_user_ids,
)
from beyo_manager.services.queries.users.get_connecteam_mapping_candidates import (
    InternalConnecteamMappingCandidate,
)


@dataclass
class DryRunSession:
    def in_transaction(self):
        return False


def _user(user_id: int, first: str, last: str = ""):
    return ConnecteamCsvUser(user_id, first, last, user_id + 1)


def _candidate(username: str, profile: str | None, connecteam_id: str | None = None, user: str | None = None):
    return InternalConnecteamMappingCandidate(
        user_id=user or f"usr_{username.lower()}",
        username=username,
        user_work_profile_id=profile,
        workspace_id="ws_test" if profile else None,
        connecteam_user_id=connecteam_id,
    )


@pytest.mark.asyncio
async def test_dry_run_classifies_all_statuses_and_does_not_write(monkeypatch):
    candidates = [
        _candidate("Proposed", "uwp_proposed"),
        _candidate("Already", "uwp_already", "2"),
        _candidate("Different", "uwp_different", "old"),
        _candidate("NoProfile", None),
        _candidate("Ambiguous", "uwp_a"),
        _candidate("Ambiguous", "uwp_b"),
        _candidate("AssignedTarget", "uwp_target"),
        _candidate("AssignedElsewhere", "uwp_elsewhere", "99"),
    ]
    monkeypatch.setattr(command_module, "get_connecteam_mapping_candidates", lambda *args, **kwargs: _async_result(candidates))
    users = [
        _user(1, "Proposed"),
        _user(2, "Already"),
        _user(3, "Different"),
        _user(4, "NoProfile"),
        _user(5, "Ambiguous"),
        _user(6, "Duplicate"),
        _user(7, "duplicate"),
        _user(99, "AssignedTarget"),
        _user(8, "NoMatch"),
        _user(9, "", ""),
    ]

    report = await map_connecteam_user_ids(
        DryRunSession(), csv_users=users, apply=False, workspace_id=None
    )

    statuses = {row.status for row in report.rows}
    assert statuses == {
        Status.PROPOSED,
        Status.ALREADY_MAPPED_SAME_ID,
        Status.EXISTING_DIFFERENT_CONNECTEAM_ID,
        Status.WORK_PROFILE_NOT_FOUND,
        Status.WORK_PROFILE_AMBIGUOUS,
        Status.DUPLICATE_EXTERNAL_FULL_NAME,
        Status.CONNECTEAM_ID_ALREADY_ASSIGNED,
        Status.EXTERNAL_USER_UNMATCHED,
        Status.INVALID_EXTERNAL_NAME,
    }
    assert report.dry_run is True
    assert report.applied is False


async def _async_result(value):
    return value


@pytest.mark.asyncio
async def test_apply_stores_string_id_and_rerun_is_idempotent(db_session):
    suffix = uuid4().hex
    workspace = Workspace(name=f"mapping-test-workspace-{suffix}")
    db_session.add(workspace)
    await db_session.flush()
    worker = User(
        username=f"Mapping{suffix} Worker",
        email=f"mapping-worker-{suffix}@example.com",
        password="hash",
    )
    db_session.add(worker)
    await db_session.flush()
    profile = UserWorkProfile(
        user_id=worker.client_id,
        workspace_id=workspace.client_id,
        created_by_id=worker.client_id,
    )
    db_session.add(profile)
    workspace_id = workspace.client_id
    await db_session.commit()

    csv_user = ConnecteamCsvUser(12345, f"Mapping{suffix}", "Worker", 2)
    first = await map_connecteam_user_ids(
        db_session, csv_users=[csv_user], apply=True, workspace_id=workspace_id
    )
    assert first.rows[0].status is Status.UPDATED
    assert profile.connecteam_user_id == "12345"

    second = await map_connecteam_user_ids(
        db_session, csv_users=[csv_user], apply=False, workspace_id=workspace_id
    )
    assert second.rows[0].status is Status.ALREADY_MAPPED_SAME_ID


@pytest.mark.asyncio
async def test_apply_conflict_aborts_before_write(monkeypatch):
    candidates = [_candidate("Conflict", "uwp_conflict", "old")]
    monkeypatch.setattr(command_module, "get_connecteam_mapping_candidates", lambda *args, **kwargs: _async_result(candidates))
    session = DryRunSession()

    report = await map_connecteam_user_ids(
        session,
        csv_users=[_user(42, "Conflict")],
        apply=True,
        workspace_id=None,
    )

    assert report.identity_conflicts_present is True
    assert report.rows[0].status is Status.EXISTING_DIFFERENT_CONNECTEAM_ID
