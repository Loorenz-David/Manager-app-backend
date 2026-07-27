from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.app_update_presentations.create_presentation import (
    create_presentation,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation_version import (
    create_presentation_version,
)
from beyo_manager.services.commands.app_update_presentations.publish_presentation import (
    publish_presentation,
)
from beyo_manager.services.commands.app_update_slide_composition.replace_slide_composition import (
    replace_slide_composition,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.commands.app_update_slides.update_slide import update_slide
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations.get_presentation import (
    get_presentation,
)


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


async def _draft_with_slide(db_session, workspace, user, *, title=None, description=None):
    pid = (
        await create_presentation(_ctx(db_session, workspace, user, {"title": "Comp"}))
    )["presentation"]["client_id"]
    slide_body = {"presentation_id": pid}
    if title:
        slide_body["title"] = title
    if description:
        slide_body["description"] = description
    slides = (await create_slide(_ctx(db_session, workspace, user, slide_body)))[
        "presentation"
    ]["slides"]
    return pid, slides[-1]["client_id"]


async def _add_media_row(db_session, slide_id, *, key="app_update/x.png") -> str:
    media = AppUpdateSlideMedia(
        slide_id=slide_id,
        sequence_order=1,
        media_type=SlideMediaTypeEnum.IMAGE,
        storage_key=key,
        is_looping=False,
    )
    db_session.add(media)
    await db_session.flush()
    return media.client_id


def _find_slide(presentation: dict, slide_id: str) -> dict:
    return next(s for s in presentation["slides"] if s["client_id"] == slide_id)


@pytest.mark.integration
async def test_text_only_timed_composition(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)

    result = await replace_slide_composition(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": pid,
                "slide_id": slide_id,
                "playback_mode": "timed",
                "duration_ms": 8000,
                "background_color": "#102A43CC",
                "elements": [
                    {"element_type": "text", "text_content": "A faster workflow", "start_ms": 0, "end_ms": 3000},
                    {"element_type": "text", "text_content": "Fewer taps", "start_ms": 3000, "end_ms": 6000},
                    {"element_type": "text", "text_content": "More control", "start_ms": 6000, "end_ms": 8000},
                ],
            },
        )
    )
    slide = _find_slide(result["presentation"], slide_id)
    assert slide["playback_mode"] == "timed"
    assert slide["duration_ms"] == 8000
    assert slide["composition_schema_version"] == 1
    assert slide["background_color"] == "#102A43CC"
    assert [e["element_type"] for e in slide["elements"]] == ["text", "text", "text"]
    assert slide["elements"][0]["text_content"] == "A faster workflow"


@pytest.mark.integration
async def test_media_element_references_media(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)
    media_id = await _add_media_row(db_session, slide_id)

    result = await replace_slide_composition(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": pid,
                "slide_id": slide_id,
                "playback_mode": "media_driven",
                "elements": [
                    {"element_type": "media", "media_id": media_id, "start_ms": 0, "layer_index": 0},
                    {"element_type": "text", "text_content": "Caption", "start_ms": 1000, "layer_index": 10},
                ],
            },
        )
    )
    slide = _find_slide(result["presentation"], slide_id)
    media_element = slide["elements"][0]
    assert media_element["element_type"] == "media"
    assert media_element["media"]["client_id"] == media_id
    assert media_element["media"]["media_url"] is not None


@pytest.mark.integration
async def test_media_must_belong_to_slide(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_a = await _draft_with_slide(db_session, workspace, user)
    slides = (
        await create_slide(_ctx(db_session, workspace, user, {"presentation_id": pid}))
    )["presentation"]["slides"]
    slide_b = slides[-1]["client_id"]
    foreign_media = await _add_media_row(db_session, slide_b)

    with pytest.raises(ValidationError):
        await replace_slide_composition(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_a,
                    "playback_mode": "manual",
                    "elements": [{"element_type": "media", "media_id": foreign_media}],
                },
            )
        )


@pytest.mark.integration
async def test_create_slide_background_color_round_trips(db_session):
    workspace, user = await _seed(db_session)
    pid = (await create_presentation(_ctx(db_session, workspace, user, {"title": "Color"})))['presentation']["client_id"]

    result = await create_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": pid, "background_color": "#FFAA00"},
        )
    )
    slide = result["presentation"]["slides"][0]
    assert slide["background_color"] == "#FFAA00"


@pytest.mark.integration
async def test_update_slide_background_color_sets_and_clears(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)

    updated = await update_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": pid,
                "slide_id": slide_id,
                "background_color": "#102A43CC",
            },
        )
    )
    assert _find_slide(updated["presentation"], slide_id)["background_color"] == "#102A43CC"

    cleared = await update_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": pid, "slide_id": slide_id, "background_color": None},
        )
    )
    assert _find_slide(cleared["presentation"], slide_id)["background_color"] is None


@pytest.mark.integration
async def test_slide_background_color_rejects_invalid_values(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)

    with pytest.raises(ValidationError):
        await create_slide(
            _ctx(
                db_session,
                workspace,
                user,
                {"presentation_id": pid, "background_color": "#FFF"},
            )
        )

    with pytest.raises(ValidationError):
        await update_slide(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_id,
                    "background_color": "red",
                },
            )
        )


@pytest.mark.integration
async def test_update_slide_background_color_rejected_on_published(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(
        db_session, workspace, user, title="Published slide"
    )
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": pid}))

    with pytest.raises(ConflictError):
        await update_slide(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_id,
                    "background_color": "#FFAA00",
                },
            )
        )


@pytest.mark.integration
async def test_composition_rejects_invalid_background_color(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)

    with pytest.raises(ValidationError):
        await replace_slide_composition(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_id,
                    "playback_mode": "manual",
                    "background_color": "#GGGGGG",
                    "elements": [],
                },
            )
        )


@pytest.mark.integration
async def test_composition_replace_is_atomic(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)

    def _replace(n):
        return replace_slide_composition(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_id,
                    "playback_mode": "manual",
                    "elements": [
                        {"element_type": "text", "text_content": f"t{i}"} for i in range(n)
                    ],
                },
            )
        )

    await _replace(3)
    await _replace(1)

    rows = (
        await db_session.execute(
            select(AppUpdateSlideElement).where(
                AppUpdateSlideElement.slide_id == slide_id
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.integration
async def test_composition_rejected_on_published(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)
    await replace_slide_composition(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": pid,
                "slide_id": slide_id,
                "playback_mode": "manual",
                "elements": [{"element_type": "text", "text_content": "hi"}],
            },
        )
    )
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": pid}))

    with pytest.raises(ConflictError):
        await replace_slide_composition(
            _ctx(
                db_session,
                workspace,
                user,
                {
                    "presentation_id": pid,
                    "slide_id": slide_id,
                    "playback_mode": "manual",
                    "elements": [{"element_type": "text", "text_content": "changed"}],
                },
            )
        )


@pytest.mark.integration
async def test_legacy_slide_serializes_synthesized_elements(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(
        db_session, workspace, user, title="Legacy title", description="Legacy body"
    )
    await _add_media_row(db_session, slide_id)

    result = await get_presentation(_ctx(db_session, workspace, user, {"client_id": pid}))
    slide = _find_slide(result["presentation"], slide_id)

    # No real elements -> adapter synthesizes: 1 media + title + description.
    assert slide["background_color"] is None
    assert [e["element_type"] for e in slide["elements"]] == ["media", "text", "text"]
    assert all(e["client_id"] is None for e in slide["elements"])
    assert slide["elements"][1]["text_content"] == "Legacy title"


@pytest.mark.integration
async def test_new_version_copies_elements_with_remapped_media(db_session):
    workspace, user = await _seed(db_session)
    pid, slide_id = await _draft_with_slide(db_session, workspace, user)
    media_id = await _add_media_row(db_session, slide_id)
    await replace_slide_composition(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": pid,
                "slide_id": slide_id,
                "playback_mode": "media_driven",
                "background_color": "#123456",
                "elements": [{"element_type": "media", "media_id": media_id}],
            },
        )
    )
    await publish_presentation(_ctx(db_session, workspace, user, {"client_id": pid}))

    v2 = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": pid})
    )
    v2_slide = v2["presentation"]["slides"][0]
    assert v2_slide["background_color"] == "#123456"
    copied_media_element = next(
        e for e in v2_slide["elements"] if e["element_type"] == "media"
    )
    # The copied element points at a NEW media row on the new version, not the old one.
    assert copied_media_element["media"]["client_id"] != media_id
    assert copied_media_element["media"]["client_id"].startswith("aupm_")
