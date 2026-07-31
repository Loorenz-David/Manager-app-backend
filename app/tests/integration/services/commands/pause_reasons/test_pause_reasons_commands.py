from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import seed_pause_reasons
from beyo_manager.services.commands.pause_reasons.create_pause_reason import create_pause_reason
from beyo_manager.services.commands.pause_reasons.delete_pause_reason import delete_pause_reason
from beyo_manager.services.commands.pause_reasons.update_pause_reason import update_pause_reason
from beyo_manager.services.context import ServiceContext


async def _seed_identity(db_session):
    suffix = uuid4().hex[:8]
    workspace = await db_session.scalar(select(Workspace).order_by(Workspace.client_id))
    user = User(
        client_id=f"usr_{suffix}",
        username=f"pause_user_{suffix}",
        email=f"pause_{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    await db_session.flush()
    identity = {"workspace_id": workspace.client_id, "user_id": user.client_id}
    return workspace, ServiceContext(identity=identity, incoming_data={}, session=db_session)


@pytest.mark.integration
async def test_seed_pause_reasons_is_idempotent(db_session):
    workspace, _ = await _seed_identity(db_session)

    async def _count_for_workspace():
        # is_deleted excluded: a separate migration (fb10ac7fd439) seeds a soft-deleted
        # `pause_case_created` anchor row for legacy-data backfill purposes only — it's not
        # part of what seed_pause_reasons creates/returns and must not be counted here.
        return await db_session.scalar(
            select(func.count())
            .select_from(PauseReason)
            .where(
                PauseReason.workspace_id == workspace.client_id,
                PauseReason.is_deleted.is_(False),
            )
        )

    first = await seed_pause_reasons(db_session, workspace.client_id)
    first_count = await _count_for_workspace()
    second = await seed_pause_reasons(db_session, workspace.client_id)
    second_count = await _count_for_workspace()

    # Five, not six. `pause_other_task_priority` was removed from the seed: auto-pause on task
    # switch is a system transition carrying `transition_reason = other_task_priority` with no
    # catalog reference, so seeding a row nobody selects and nothing resolves would leave a picker
    # entry with no meaning. `pause_ended_shift` deliberately stays — a worker picks it.
    assert len(first) == 5
    assert first == second
    assert first_count == second_count == 5
    assert "pause_other_task_priority" not in first
    assert "pause_ended_shift" in first

    # No seeded row is system-managed any more; the flag is inert published contract.
    seeded_rows = (
        await db_session.execute(
            select(PauseReason).where(PauseReason.workspace_id == workspace.client_id)
        )
    ).scalars().all()
    assert all(row.is_system_managed is False for row in seeded_rows)

    # Bootstrap still repairs a drifted field on rerun.
    lunch = next(row for row in seeded_rows if row.slug == "pause_lunch_break")
    original_image = lunch.image_url
    lunch.image_url = "https://example.invalid/drifted.webp"
    await db_session.flush()
    await seed_pause_reasons(db_session, workspace.client_id)
    assert lunch.image_url == original_image


@pytest.mark.integration
async def test_pause_reason_crud_and_no_delete_guard_remains(db_session):
    workspace, ctx = await _seed_identity(db_session)
    ctx.incoming_data = {"name": "Typed blocker", "pause_type": PauseTypeEnum.BLOCKER.value}

    created = await create_pause_reason(ctx)
    client_id = created["pause_reason"]["client_id"]

    ctx.incoming_data = {"client_id": client_id, "name": "Typed blocker renamed"}
    updated = await update_pause_reason(ctx)
    assert updated["pause_reason"]["name"] == "Typed blocker renamed"

    ctx.incoming_data = {"client_id": client_id}
    await delete_pause_reason(ctx)
    deleted = await db_session.scalar(select(PauseReason).where(PauseReason.client_id == client_id))
    assert deleted.is_deleted is True

    # The system-managed delete guard is gone. It blocked deletion of rows whose behaviour the
    # backend depended on; nothing resolves a pause reason by slug any more, so there is no row
    # left to protect and every row here is workspace data the manager owns outright.
    seeded = await seed_pause_reasons(db_session, workspace.client_id)
    ctx.incoming_data = {"client_id": seeded["pause_ended_shift"]}
    await delete_pause_reason(ctx)

    formerly_protected = await db_session.scalar(
        select(PauseReason).where(PauseReason.client_id == seeded["pause_ended_shift"])
    )
    assert formerly_protected.is_deleted is True
