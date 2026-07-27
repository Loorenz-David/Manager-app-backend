from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.app_update_presentations import (
    publish_presentation as publish_module,
)
from beyo_manager.services.commands.app_update_presentations.archive_presentation import (
    archive_presentation,
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
from beyo_manager.services.commands.app_update_presentations.update_presentation import (
    update_presentation,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.context import ServiceContext


def _identity(workspace_id: str, user_id: str) -> dict:
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role_name": "manager",
        "app_scope": "manager",
        "username": "tester",
    }


def _ctx(db_session, workspace, user, incoming):
    return ServiceContext(
        identity=_identity(workspace.client_id, user.client_id),
        incoming_data=incoming,
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


async def _create_draft(db_session, workspace, user, *, title="Update") -> str:
    result = await create_presentation(_ctx(db_session, workspace, user, {"title": title}))
    return result["presentation"]["client_id"]


async def _add_slide(db_session, workspace, user, presentation_id) -> None:
    await create_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": presentation_id, "title": "Slide", "description": "Body"},
        )
    )


async def _create_published(db_session, workspace, user, *, title="Update") -> str:
    presentation_id = await _create_draft(db_session, workspace, user, title=title)
    await _add_slide(db_session, workspace, user, presentation_id)
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": presentation_id}))
    return presentation_id


@pytest.mark.integration
async def test_create_publish_lifecycle(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    row = (
        await db_session.execute(
            select(AppUpdatePresentation).where(
                AppUpdatePresentation.client_id == presentation_id
            )
        )
    ).scalar_one()
    assert row.status == PresentationStatusEnum.PUBLISHED
    assert row.published_at is not None
    assert row.logical_client_id == presentation_id
    assert row.version == 1


@pytest.mark.integration
async def test_category_round_trips_and_copies_to_new_version(db_session):
    workspace, user = await _seed(db_session)
    created = await create_presentation(
        _ctx(db_session, workspace, user, {"title": "Workflow change", "category": "workflow"})
    )
    presentation_id = created["presentation"]["client_id"]
    assert created["presentation"]["category"] == "workflow"

    await _add_slide(db_session, workspace, user, presentation_id)
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": presentation_id}))
    versioned = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    assert versioned["presentation"]["category"] == "workflow"


@pytest.mark.integration
async def test_category_sets_default_display_priority(db_session):
    workspace, user = await _seed(db_session)

    alert = await create_presentation(
        _ctx(db_session, workspace, user, {"title": "Outage", "category": "alert"})
    )
    assert alert["presentation"]["display_priority"] == 300

    news = await create_presentation(
        _ctx(db_session, workspace, user, {"title": "Tip", "category": "news"})
    )
    assert news["presentation"]["display_priority"] == 0

    # No category -> baseline.
    plain = await create_presentation(_ctx(db_session, workspace, user, {"title": "Plain"}))
    assert plain["presentation"]["display_priority"] == 0

    # Explicit priority always wins over the category default.
    override = await create_presentation(
        _ctx(
            db_session,
            workspace,
            user,
            {"title": "Manual", "category": "alert", "display_priority": 5},
        )
    )
    assert override["presentation"]["display_priority"] == 5


@pytest.mark.integration
async def test_publish_empty_draft_rejected(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_draft(db_session, workspace, user)

    with pytest.raises(ValidationError):
        await publish_presentation(
            _ctx(db_session, workspace, user, {"client_id": presentation_id})
        )


@pytest.mark.integration
async def test_published_presentation_is_immutable(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    with pytest.raises(ConflictError):
        await update_presentation(
            _ctx(
                db_session,
                workspace,
                user,
                {"client_id": presentation_id, "title": "New title"},
            )
        )


@pytest.mark.integration
async def test_new_version_copies_slides_as_draft(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    result = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    new = result["presentation"]
    assert new["version"] == 2
    assert new["status"] == "draft"
    assert new["published_at"] is None
    assert len(new["slides"]) == 1
    assert new["client_id"] != presentation_id


@pytest.mark.integration
async def test_publishing_v2_does_not_require_archiving_v1(db_session):
    """Newest-version-wins: v1 and v2 can both be published; v1 is superseded at
    read time, not blocked at publish time."""
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)

    result = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    v2_id = result["presentation"]["client_id"]

    # No ConflictError — publishing v2 while v1 is live is allowed now.
    published = await publish_presentation(
        _ctx(db_session, workspace, user, {"client_id": v2_id})
    )
    assert published["presentation"]["status"] == "published"

    # Both versions remain published rows.
    statuses = (
        await db_session.execute(
            select(AppUpdatePresentation.version, AppUpdatePresentation.status).where(
                AppUpdatePresentation.logical_client_id == presentation_id
            )
        )
    ).all()
    assert {(v, s.value) for v, s in statuses} == {(1, "published"), (2, "published")}


@pytest.mark.integration
async def test_archive_sets_archived(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_draft(db_session, workspace, user)
    await _add_slide(db_session, workspace, user, presentation_id)

    result = await archive_presentation(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    assert result["presentation"]["status"] == "archived"
    assert result["presentation"]["archived_at"] is not None


@pytest.mark.integration
async def test_publish_emits_published_event(db_session, monkeypatch):
    captured: list = []

    async def _fake_dispatch(events):
        captured.extend(events)

    monkeypatch.setattr(publish_module.event_bus, "dispatch", _fake_dispatch)

    workspace, user = await _seed(db_session)
    presentation_id = await _create_draft(db_session, workspace, user)
    await _add_slide(db_session, workspace, user, presentation_id)
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": presentation_id}))

    assert len(captured) == 1
    event = captured[0]
    assert event.event_name == "app_update_presentation:published"
    assert event.workspace_id == workspace.client_id
    assert event.client_id == presentation_id


@pytest.mark.integration
async def test_new_version_slides_are_independent_rows(db_session):
    workspace, user = await _seed(db_session)
    presentation_id = await _create_published(db_session, workspace, user)
    result = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    v2_id = result["presentation"]["client_id"]

    slide_presentation_ids = (
        await db_session.execute(
            select(AppUpdatePresentationSlide.presentation_id).where(
                AppUpdatePresentationSlide.presentation_id.in_([presentation_id, v2_id])
            )
        )
    ).scalars().all()
    assert sorted(slide_presentation_ids) == sorted([presentation_id, v2_id])
