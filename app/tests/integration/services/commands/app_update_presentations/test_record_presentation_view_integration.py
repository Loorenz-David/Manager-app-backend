from __future__ import annotations

from uuid import uuid4

import pytest

from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.app_update_presentation_views.record_presentation_view import (
    record_presentation_view,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation import (
    create_presentation,
)
from beyo_manager.services.commands.app_update_presentations.publish_presentation import (
    publish_presentation,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.context import ServiceContext


def _identity(workspace_id, user_id):
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


async def _publish(db_session, workspace, user, *, is_dismissible=True) -> str:
    presentation_id = (
        await create_presentation(
            _ctx(db_session, workspace, user, {"title": "U", "is_dismissible": is_dismissible})
        )
    )["presentation"]["client_id"]
    await create_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": presentation_id, "title": "S", "description": "D"},
        )
    )
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": presentation_id}))
    return presentation_id


def _view(presentation_id, action, **extra):
    return {"presentation_id": presentation_id, "version": 1, "action": action, **extra}


@pytest.mark.integration
async def test_shown_is_idempotent_and_increments_view_count(db_session):
    workspace, user = await _seed(db_session)
    pid = await _publish(db_session, workspace, user)

    first = await record_presentation_view(_ctx(db_session, workspace, user, _view(pid, "shown")))
    second = await record_presentation_view(_ctx(db_session, workspace, user, _view(pid, "shown")))

    assert first["view_state"]["view_count"] == 1
    assert second["view_state"]["view_count"] == 2
    assert second["view_state"]["status"] == "shown"


@pytest.mark.integration
async def test_completion_is_terminal(db_session):
    workspace, user = await _seed(db_session)
    pid = await _publish(db_session, workspace, user)

    await record_presentation_view(_ctx(db_session, workspace, user, _view(pid, "completed")))
    # Repeated completed stays completed.
    again = await record_presentation_view(
        _ctx(db_session, workspace, user, _view(pid, "completed"))
    )
    assert again["view_state"]["status"] == "completed"

    # Completed cannot regress to dismissed.
    with pytest.raises(ConflictError):
        await record_presentation_view(_ctx(db_session, workspace, user, _view(pid, "dismissed")))


@pytest.mark.integration
async def test_dismiss_rejected_when_not_dismissible(db_session):
    workspace, user = await _seed(db_session)
    pid = await _publish(db_session, workspace, user, is_dismissible=False)

    with pytest.raises(ConflictError):
        await record_presentation_view(_ctx(db_session, workspace, user, _view(pid, "dismissed")))


@pytest.mark.integration
async def test_slide_index_validated_against_slide_count(db_session):
    workspace, user = await _seed(db_session)
    pid = await _publish(db_session, workspace, user)  # one slide -> valid index is 0

    with pytest.raises(ValidationError):
        await record_presentation_view(
            _ctx(db_session, workspace, user, _view(pid, "progressed", last_slide_index=5))
        )


@pytest.mark.integration
async def test_version_mismatch_rejected(db_session):
    workspace, user = await _seed(db_session)
    pid = await _publish(db_session, workspace, user)

    with pytest.raises(ValidationError):
        await record_presentation_view(
            _ctx(db_session, workspace, user, {"presentation_id": pid, "version": 99, "action": "shown"})
        )
