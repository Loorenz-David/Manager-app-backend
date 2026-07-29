from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models import Base
from beyo_manager.models.tables.users.user_declared_state_record import UserDeclaredStateRecord


async def _seed_dependencies(db_session: AsyncSession) -> tuple[str, str, str, str, str]:
    suffix = uuid4().hex
    user_id = f"usr_declared_{suffix}"
    first_workspace_id = f"ws_declared_a_{suffix}"
    second_workspace_id = f"ws_declared_b_{suffix}"
    first_reason_id = f"par_declared_a_{suffix}"
    second_reason_id = f"par_declared_b_{suffix}"

    await db_session.execute(
        insert(Base.metadata.tables["users"]).values(
            client_id=user_id,
            username=f"declared_{suffix}",
            email=f"declared_{suffix}@example.test",
            password="not-used",
        )
    )
    await db_session.execute(
        insert(Base.metadata.tables["workspaces"]),
        [
            {"client_id": first_workspace_id, "name": f"Declared A {suffix}"},
            {"client_id": second_workspace_id, "name": f"Declared B {suffix}"},
        ],
    )
    await db_session.execute(
        insert(Base.metadata.tables["pause_reasons"]),
        [
            {
                "client_id": first_reason_id,
                "workspace_id": first_workspace_id,
                "name": f"Declared A {suffix}",
                "pause_type": PauseTypeEnum.PERSONAL,
            },
            {
                "client_id": second_reason_id,
                "workspace_id": second_workspace_id,
                "name": f"Declared B {suffix}",
                "pause_type": PauseTypeEnum.PERSONAL,
            },
        ],
    )
    await db_session.flush()

    return user_id, first_workspace_id, second_workspace_id, first_reason_id, second_reason_id


def _open_record(
    *,
    user_id: str,
    workspace_id: str,
    pause_reason_id: str,
    entered_at: datetime,
) -> UserDeclaredStateRecord:
    return UserDeclaredStateRecord(
        user_id=user_id,
        workspace_id=workspace_id,
        pause_reason_id=pause_reason_id,
        entered_at=entered_at,
        created_by_id=user_id,
    )


@pytest.mark.integration
async def test_rejects_second_open_row_for_same_user_and_workspace(db_session: AsyncSession) -> None:
    user_id, workspace_id, _, pause_reason_id, _ = await _seed_dependencies(db_session)
    entered_at = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    db_session.add(
        _open_record(
            user_id=user_id,
            workspace_id=workspace_id,
            pause_reason_id=pause_reason_id,
            entered_at=entered_at,
        )
    )
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                _open_record(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    pause_reason_id=pause_reason_id,
                    entered_at=entered_at + timedelta(minutes=5),
                )
            )
            await db_session.flush()


@pytest.mark.integration
async def test_allows_open_rows_for_same_user_in_different_workspaces(db_session: AsyncSession) -> None:
    user_id, first_workspace_id, second_workspace_id, first_reason_id, second_reason_id = (
        await _seed_dependencies(db_session)
    )
    entered_at = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _open_record(
                user_id=user_id,
                workspace_id=first_workspace_id,
                pause_reason_id=first_reason_id,
                entered_at=entered_at,
            ),
            _open_record(
                user_id=user_id,
                workspace_id=second_workspace_id,
                pause_reason_id=second_reason_id,
                entered_at=entered_at,
            ),
        ]
    )
    await db_session.flush()

    count = await db_session.scalar(
        select(func.count()).select_from(UserDeclaredStateRecord).where(
            UserDeclaredStateRecord.user_id == user_id,
            UserDeclaredStateRecord.exited_at.is_(None),
        )
    )
    assert count == 2


@pytest.mark.integration
async def test_rejects_exit_before_entry(db_session: AsyncSession) -> None:
    user_id, workspace_id, _, pause_reason_id, _ = await _seed_dependencies(db_session)
    entered_at = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                UserDeclaredStateRecord(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    pause_reason_id=pause_reason_id,
                    entered_at=entered_at,
                    exited_at=entered_at - timedelta(seconds=1),
                    created_by_id=user_id,
                )
            )
            await db_session.flush()


@pytest.mark.integration
async def test_allows_new_open_row_after_previous_row_is_closed(db_session: AsyncSession) -> None:
    user_id, workspace_id, _, pause_reason_id, _ = await _seed_dependencies(db_session)
    entered_at = datetime(2026, 7, 29, 8, tzinfo=timezone.utc)
    first_record = _open_record(
        user_id=user_id,
        workspace_id=workspace_id,
        pause_reason_id=pause_reason_id,
        entered_at=entered_at,
    )
    db_session.add(first_record)
    await db_session.flush()

    first_record.exited_at = entered_at + timedelta(minutes=5)
    await db_session.flush()
    second_record = _open_record(
        user_id=user_id,
        workspace_id=workspace_id,
        pause_reason_id=pause_reason_id,
        entered_at=entered_at + timedelta(minutes=5),
    )
    db_session.add(second_record)
    await db_session.flush()

    open_record_id = await db_session.scalar(
        select(UserDeclaredStateRecord.client_id).where(
            UserDeclaredStateRecord.user_id == user_id,
            UserDeclaredStateRecord.workspace_id == workspace_id,
            UserDeclaredStateRecord.exited_at.is_(None),
        )
    )
    assert open_record_id == second_record.client_id
