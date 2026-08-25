from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.pause_reasons.pause_reason_user_link import (
    PauseReasonUserLink,
)
from beyo_manager.models.tables.pause_reasons.pause_reason_working_section_link import (
    PauseReasonWorkingSectionLink,
)
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import (
    seed_pause_reason_links,
    seed_pause_reasons,
)
from beyo_manager.services.commands.pause_reasons.create_pause_reason import (
    create_pause_reason,
)
from beyo_manager.services.commands.pause_reasons.delete_pause_reason import (
    delete_pause_reason,
)
from beyo_manager.services.commands.pause_reasons.update_pause_reason import (
    update_pause_reason,
)
from beyo_manager.services.context import ServiceContext


async def _seed_identity(db_session):
    suffix = uuid4().hex[:8]
    workspace = await db_session.scalar(select(Workspace).order_by(Workspace.client_id))
    if workspace is None:
        workspace = Workspace(name=f"Pause workspace {suffix}")
        db_session.add(workspace)
        await db_session.flush()
    user = User(
        client_id=f"usr_{suffix}",
        username=f"pause_user_{suffix}",
        email=f"pause_{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    await db_session.flush()
    identity = {"workspace_id": workspace.client_id, "user_id": user.client_id}
    return workspace, ServiceContext(
        identity=identity, incoming_data={}, session=db_session
    )


async def _make_active_member(db_session, workspace, user):
    role = await db_session.scalar(select(Role).where(Role.name == RoleNameEnum.WORKER))
    if role is None:
        role = Role(name=RoleNameEnum.WORKER)
        db_session.add(role)
        await db_session.flush()
    workspace_role = await db_session.scalar(
        select(WorkspaceRole).where(
            WorkspaceRole.workspace_id == workspace.client_id,
            WorkspaceRole.role_id == role.client_id,
            WorkspaceRole.specialization.is_(None),
        )
    )
    if workspace_role is None:
        workspace_role = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=role.client_id,
        )
        db_session.add(workspace_role)
        await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()


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

    # `pause_other_task_priority` is still absent: auto-pause on task switch is a system transition
    # carrying `transition_reason = other_task_priority` with no catalog reference, so seeding a row
    # nobody selects and nothing resolves would leave a picker entry with no meaning.
    # `pause_ended_shift` deliberately stays — a worker picks it. The sixth row is `pause_other`.
    assert len(first) == 12
    assert first == second
    assert first_count == second_count == 12
    assert "pause_other_task_priority" not in first
    assert "pause_ended_shift" in first

    # The catch-all carries the only `requires_description = True` in the seed — its reason text is
    # the row's whole content, so losing that flag would let a worker pause with no explanation.
    other = await db_session.scalar(
        select(PauseReason).where(
            PauseReason.workspace_id == workspace.client_id,
            PauseReason.slug == "pause_other",
        )
    )
    assert other.pause_type is PauseTypeEnum.PERSONAL
    assert other.requires_description is True

    # No seeded row is system-managed any more; the flag is inert published contract.
    seeded_rows = (
        (
            await db_session.execute(
                select(PauseReason).where(
                    PauseReason.workspace_id == workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert all(row.is_system_managed is False for row in seeded_rows)

    # Bootstrap still repairs a drifted field on rerun.
    lunch = next(row for row in seeded_rows if row.slug == "pause_lunch_break")
    original_image = lunch.image_url
    lunch.image_url = "https://example.invalid/drifted.webp"
    await db_session.flush()
    await seed_pause_reasons(db_session, workspace.client_id)
    assert lunch.image_url == original_image

    expected_new_reason_images = {
        "pause_price_tags": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/price-tags.webp",
        "pause_descriptions": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/descriptions.webp",
        "pause_photo_editing": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/photo-editing.webp",
        "pause_moving_furniture": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/moving-furniture.webp",
        "pause_searching_upholstery": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/searching-upholstery.webp",
        "pause_workspace_cleaning": "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/workspace-cleaning.webp",
    }
    for slug, expected_image_url in expected_new_reason_images.items():
        seeded_reason = await db_session.scalar(
            select(PauseReason).where(
                PauseReason.workspace_id == workspace.client_id,
                PauseReason.slug == slug,
            )
        )
        assert seeded_reason.image_url == expected_image_url


@pytest.mark.integration
async def test_seed_pause_reason_links_assigns_requested_workers_and_is_idempotent(
    db_session,
):
    workspace, _ = await _seed_identity(db_session)
    workers = {}
    for worker_name in ("Vitalii", "Nazar", "Roman"):
        worker = User(
            client_id=f"usr_{worker_name.lower()}_{uuid4().hex[:8]}",
            username=worker_name,
            email=f"{worker_name.lower()}_{uuid4().hex[:8]}@example.com",
            password="secret",
        )
        db_session.add(worker)
        await db_session.flush()
        await _make_active_member(db_session, workspace, worker)
        workers[worker_name] = worker.client_id

    pause_reason_ids = await seed_pause_reasons(db_session, workspace.client_id)
    await seed_pause_reason_links(
        db_session,
        workspace.client_id,
        pause_reason_ids,
        workers,
    )
    await seed_pause_reason_links(
        db_session,
        workspace.client_id,
        pause_reason_ids,
        workers,
    )

    rows = (
        await db_session.scalars(
            select(PauseReasonUserLink).where(
                PauseReasonUserLink.workspace_id == workspace.client_id
            )
        )
    ).all()
    links_by_reason = {}
    for row in rows:
        links_by_reason.setdefault(row.pause_reason_id, set()).add(row.user_id)

    assert links_by_reason[pause_reason_ids["pause_price_tags"]] == {
        workers["Vitalii"]
    }
    assert links_by_reason[pause_reason_ids["pause_descriptions"]] == {
        workers["Vitalii"]
    }
    assert links_by_reason[pause_reason_ids["pause_photo_editing"]] == {
        workers["Vitalii"]
    }
    assert links_by_reason[pause_reason_ids["pause_moving_furniture"]] == {
        workers["Vitalii"],
        workers["Nazar"],
    }
    assert links_by_reason[pause_reason_ids["pause_searching_upholstery"]] == {
        workers["Roman"]
    }
    assert pause_reason_ids["pause_workspace_cleaning"] not in links_by_reason


@pytest.mark.integration
async def test_pause_reason_crud_and_no_delete_guard_remains(db_session):
    workspace, ctx = await _seed_identity(db_session)
    ctx.incoming_data = {
        "name": "Typed blocker",
        "pause_type": PauseTypeEnum.BLOCKER.value,
    }

    created = await create_pause_reason(ctx)
    client_id = created["pause_reason"]["client_id"]
    assert created["pause_reason"]["slug"] == f"custom_{client_id}"
    assert created["pause_reason"]["linked_user_ids"] == []
    assert created["pause_reason"]["linked_working_section_ids"] == []

    ctx.incoming_data = {"client_id": client_id, "name": "Typed blocker renamed"}
    updated = await update_pause_reason(ctx)
    assert updated["pause_reason"]["name"] == "Typed blocker renamed"

    ctx.incoming_data = {"client_id": client_id}
    await delete_pause_reason(ctx)
    deleted = await db_session.scalar(
        select(PauseReason).where(PauseReason.client_id == client_id)
    )
    assert deleted.is_deleted is True

    ctx.incoming_data = {
        "name": "Typed blocker renamed",
        "pause_type": PauseTypeEnum.BLOCKER.value,
    }
    recreated = await create_pause_reason(ctx)
    assert recreated["pause_reason"]["client_id"] != client_id

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


@pytest.mark.integration
async def test_pause_reason_link_sets_round_trip_preserve_clear_and_validate(
    db_session,
):
    workspace, ctx = await _seed_identity(db_session)
    user = await db_session.get(User, ctx.user_id)
    await _make_active_member(db_session, workspace, user)
    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"Pause section {uuid4().hex[:8]}",
        created_by_id=user.client_id,
    )
    db_session.add(section)
    await db_session.flush()

    ctx.incoming_data = {
        "name": "Restricted pause",
        "pause_type": PauseTypeEnum.PERSONAL.value,
        "linked_user_ids": [user.client_id, user.client_id],
        "linked_working_section_ids": [section.client_id],
    }
    created = await create_pause_reason(ctx)
    reason_id = created["pause_reason"]["client_id"]
    assert created["pause_reason"]["linked_user_ids"] == [user.client_id]
    assert created["pause_reason"]["linked_working_section_ids"] == [section.client_id]

    ctx.incoming_data = {"client_id": reason_id, "name": "Restricted renamed"}
    preserved = await update_pause_reason(ctx)
    assert preserved["pause_reason"]["linked_user_ids"] == [user.client_id]
    assert preserved["pause_reason"]["linked_working_section_ids"] == [
        section.client_id
    ]

    ctx.incoming_data = {
        "client_id": reason_id,
        "linked_user_ids": [],
        "linked_working_section_ids": [],
    }
    cleared = await update_pause_reason(ctx)
    assert cleared["pause_reason"]["linked_user_ids"] == []
    assert cleared["pause_reason"]["linked_working_section_ids"] == []
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(PauseReasonUserLink)
            .where(PauseReasonUserLink.pause_reason_id == reason_id)
        )
        == 0
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(PauseReasonWorkingSectionLink)
            .where(PauseReasonWorkingSectionLink.pause_reason_id == reason_id)
        )
        == 0
    )

    ctx.incoming_data = {
        "client_id": reason_id,
        "linked_user_ids": ["usr_not_in_workspace"],
    }
    with pytest.raises(ValidationError):
        await update_pause_reason(ctx)
