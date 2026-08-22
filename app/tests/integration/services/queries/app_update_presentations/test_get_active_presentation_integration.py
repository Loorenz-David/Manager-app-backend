from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.app_update_presentations.enums import (
    AudienceModeEnum,
    PresentationViewStatusEnum,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_user_target import (
    AppUpdatePresentationUserTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_view import (
    AppUpdatePresentationView,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.app_update_presentation_views.record_presentation_view import (
    record_presentation_view,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation import (
    create_presentation,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation_version import (
    create_presentation_version,
)
from beyo_manager.services.commands.app_update_presentations.publish_presentation import (
    publish_presentation,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations.get_active_presentation import (
    get_active_presentation as get_active,
)
from beyo_manager.services.queries.app_update_presentations.list_whats_new import (
    list_whats_new,
)


def _identity(workspace_id, user_id, *, app_scope="manager"):
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role_name": "manager",
        "app_scope": app_scope,
        "username": "tester",
    }


def _ctx(db_session, workspace, user, incoming):
    return ServiceContext(
        identity=_identity(workspace.client_id, user.client_id),
        incoming_data=incoming,
        session=db_session,
    )


def _active_ctx(db_session, workspace, user, *, app_key="manager", app_scope="manager"):
    return ServiceContext(
        identity=_identity(workspace.client_id, user.client_id, app_scope=app_scope),
        incoming_data={},
        query_params={"app_key": app_key},
        session=db_session,
    )


async def _seed(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_user(db_session, workspace):
    suffix = uuid4().hex[:8]
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_published(db_session, workspace, user, *, title="Update") -> str:
    presentation_id = (
        await create_presentation(_ctx(db_session, workspace, user, {"title": title}))
    )["presentation"]["client_id"]
    await create_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": presentation_id, "title": "Slide", "description": "Body"},
        )
    )
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": presentation_id}))
    return presentation_id


async def _complete(db_session, workspace, user, presentation_id):
    await record_presentation_view(
        ServiceContext(
            identity=_identity(workspace.client_id, user.client_id),
            incoming_data={
                "presentation_id": presentation_id,
                "version": 1,
                "action": "completed",
            },
            session=db_session,
        )
    )


@pytest.mark.integration
async def test_active_returns_published_for_matching_context(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"] is not None
    assert result["presentation"]["client_id"] == presentation_id
    assert result["presentation"]["view_state"]["status"] == "unseen"


@pytest.mark.integration
async def test_app_key_must_match_signed_scope(db_session):
    workspace, user = await _seed(db_session)
    await _create_published(db_session, workspace, user)

    with pytest.raises(ValidationError):
        await get_active(
            _active_ctx(db_session, workspace, user, app_key="worker", app_scope="manager")
        )


@pytest.mark.integration
async def test_completed_presentation_is_excluded(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)
    await _complete(db_session, workspace, user, presentation_id)

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"] is None


@pytest.mark.integration
async def test_highest_priority_wins(db_session):
    workspace, user = await _seed(db_session)
    low_id = await _create_published(db_session, workspace, user, title="Low")
    high_id = await _create_published(db_session, workspace, user, title="High")

    high = (
        await db_session.execute(
            select(AppUpdatePresentation).where(AppUpdatePresentation.client_id == high_id)
        )
    ).scalar_one()
    high.display_priority = 100
    await db_session.flush()

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"]["client_id"] == high_id
    assert low_id != high_id


@pytest.mark.integration
async def test_selected_users_only_targeting(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    presentation = (
        await db_session.execute(
            select(AppUpdatePresentation)
            .options(selectinload(AppUpdatePresentation.user_targets))
            .where(AppUpdatePresentation.client_id == presentation_id)
        )
    ).scalar_one()
    presentation.audience_mode = AudienceModeEnum.SELECTED_USERS_ONLY
    presentation.user_targets.append(
        AppUpdatePresentationUserTarget(
            presentation_id=presentation_id, user_id=user.client_id
        )
    )
    await db_session.flush()

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"]["client_id"] == presentation_id

    other_user = await _seed_user(db_session, workspace)
    other_ctx = ServiceContext(
        identity=_identity(workspace.client_id, other_user.client_id),
        incoming_data={},
        query_params={"app_key": "manager"},
        session=db_session,
    )
    assert (await get_active(other_ctx))["presentation"] is None


@pytest.mark.integration
async def test_shared_acting_users_have_independent_view_state(db_session):
    workspace, user_a = await _seed(db_session)
    user_b = await _seed_user(db_session, workspace)
    presentation_id = await _create_published(db_session, workspace, user_a)

    await _complete(db_session, workspace, user_a, presentation_id)

    a_result = await get_active(_active_ctx(db_session, workspace, user_a))
    b_ctx = ServiceContext(
        identity=_identity(workspace.client_id, user_b.client_id),
        incoming_data={},
        query_params={"app_key": "manager"},
        session=db_session,
    )
    b_result = await get_active(b_ctx)

    assert a_result["presentation"] is None
    assert b_result["presentation"]["client_id"] == presentation_id

    rows = (
        await db_session.execute(
            select(AppUpdatePresentationView).where(
                AppUpdatePresentationView.presentation_id == presentation_id
            )
        )
    ).scalars().all()
    assert {r.acting_user_id for r in rows} == {user_a.client_id}
    assert rows[0].status == PresentationViewStatusEnum.COMPLETED


async def _publish_new_version(db_session, workspace, user, presentation_id) -> str:
    v_next = (
        await create_presentation_version(
            _ctx(db_session, workspace, user, {"client_id": presentation_id})
        )
    )["presentation"]["client_id"]
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": v_next}))
    return v_next


@pytest.mark.integration
async def test_newest_version_wins(db_session):
    workspace, user = await _seed(db_session)
    v1_id = await _create_published(db_session, workspace, user)
    v2_id = await _publish_new_version(db_session, workspace, user, v1_id)

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"]["client_id"] == v2_id
    assert result["presentation"]["version"] == 2


@pytest.mark.integration
async def test_completing_newest_version_does_not_fall_back_to_old(db_session):
    workspace, user = await _seed(db_session)
    v1_id = await _create_published(db_session, workspace, user)
    v2_id = await _publish_new_version(db_session, workspace, user, v1_id)

    # Complete the newest version.
    await record_presentation_view(
        ServiceContext(
            identity=_identity(workspace.client_id, user.client_id),
            incoming_data={"presentation_id": v2_id, "version": 2, "action": "completed"},
            session=db_session,
        )
    )

    result = await get_active(_active_ctx(db_session, workspace, user))
    assert result["presentation"] is None


@pytest.mark.integration
async def test_whats_new_lists_newest_version_per_announcement(db_session):
    workspace, user = await _seed(db_session)
    a1 = await _create_published(db_session, workspace, user, title="A")
    b1 = await _create_published(db_session, workspace, user, title="B")
    a2 = await _publish_new_version(db_session, workspace, user, a1)

    result = await list_whats_new(_active_ctx(db_session, workspace, user))
    items = result["app_update_whats_new_pagination"]["items"]
    ids = {i["client_id"] for i in items}

    # One entry per announcement, and announcement A resolves to its v2.
    assert ids == {a2, b1}
    assert a1 not in ids
