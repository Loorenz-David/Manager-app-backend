from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.app_update_presentations.create_presentation import (
    create_presentation,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations.list_presentations import (
    list_presentations,
)


def _identity(workspace_id, user_id):
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role_name": "manager",
        "app_scope": "manager",
        "username": "tester",
    }


def _ctx(db_session, workspace, user, incoming=None, query_params=None):
    return ServiceContext(
        identity=_identity(workspace.client_id, user.client_id),
        incoming_data=incoming or {},
        query_params=query_params or {},
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


async def _draft(db_session, workspace, user, *, title="Deck") -> str:
    return (await create_presentation(_ctx(db_session, workspace, user, {"title": title})))[
        "presentation"
    ]["client_id"]


async def _add_slide(db_session, presentation_id, sequence_order, *, is_deleted=False) -> str:
    slide = AppUpdatePresentationSlide(
        presentation_id=presentation_id,
        sequence_order=sequence_order,
        is_deleted=is_deleted,
        deleted_at=datetime.now(timezone.utc) if is_deleted else None,
    )
    db_session.add(slide)
    await db_session.flush()
    return slide.client_id


async def _add_media(
    db_session,
    slide_id,
    sequence_order,
    media_type,
    *,
    storage_key="k.bin",
    poster_storage_key=None,
    fallback_storage_key=None,
    is_deleted=False,
) -> str:
    media = AppUpdateSlideMedia(
        slide_id=slide_id,
        sequence_order=sequence_order,
        media_type=media_type,
        storage_key=storage_key,
        poster_storage_key=poster_storage_key,
        fallback_storage_key=fallback_storage_key,
        is_looping=False,
        is_deleted=is_deleted,
        deleted_at=datetime.now(timezone.utc) if is_deleted else None,
    )
    db_session.add(media)
    await db_session.flush()
    return media.client_id


def _item(result, presentation_id):
    items = result["app_update_presentations_pagination"]["items"]
    return next(i for i in items if i["client_id"] == presentation_id)


@pytest.mark.integration
async def test_slide_count_media_kinds_and_image_cover(db_session):
    workspace, user = await _seed(db_session)
    pid = await _draft(db_session, workspace, user)
    s1 = await _add_slide(db_session, pid, 1)
    s2 = await _add_slide(db_session, pid, 2)
    await _add_media(db_session, s1, 1, SlideMediaTypeEnum.IMAGE, storage_key="cover.png")
    await _add_media(db_session, s2, 1, SlideMediaTypeEnum.VIDEO, storage_key="clip.mp4")

    item = _item(await list_presentations(_ctx(db_session, workspace, user)), pid)
    assert item["slide_count"] == 2
    assert item["media_kinds"] == ["image", "video"]
    assert item["cover_url"] is not None  # resolved from the first slide's image


@pytest.mark.integration
async def test_cover_prefers_video_poster_then_falls_through(db_session):
    workspace, user = await _seed(db_session)
    pid = await _draft(db_session, workspace, user)
    s1 = await _add_slide(db_session, pid, 1)
    # First media is a video WITH a poster -> cover uses the poster.
    await _add_media(
        db_session, s1, 1, SlideMediaTypeEnum.VIDEO,
        storage_key="a.mp4", poster_storage_key="a_poster.png",
    )
    item = _item(await list_presentations(_ctx(db_session, workspace, user)), pid)
    assert item["cover_url"] is not None
    assert item["media_kinds"] == ["video"]


@pytest.mark.integration
async def test_cover_skips_unusable_video_to_next_image(db_session):
    workspace, user = await _seed(db_session)
    pid = await _draft(db_session, workspace, user)
    s1 = await _add_slide(db_session, pid, 1)
    # Video with no poster and no fallback -> not usable as cover.
    await _add_media(db_session, s1, 1, SlideMediaTypeEnum.VIDEO, storage_key="b.mp4")
    # A later image -> becomes the cover.
    await _add_media(db_session, s1, 2, SlideMediaTypeEnum.IMAGE, storage_key="later.png")

    item = _item(await list_presentations(_ctx(db_session, workspace, user)), pid)
    assert item["media_kinds"] == ["video", "image"]
    assert item["cover_url"] is not None  # the later image


@pytest.mark.integration
async def test_no_media_yields_null_cover_and_empty_kinds(db_session):
    workspace, user = await _seed(db_session)
    pid = await _draft(db_session, workspace, user)
    await _add_slide(db_session, pid, 1)
    await _add_slide(db_session, pid, 2)

    item = _item(await list_presentations(_ctx(db_session, workspace, user)), pid)
    assert item["slide_count"] == 2
    assert item["media_kinds"] == []
    assert item["cover_url"] is None


@pytest.mark.integration
async def test_soft_deleted_slides_and_media_excluded(db_session):
    workspace, user = await _seed(db_session)
    pid = await _draft(db_session, workspace, user)
    s1 = await _add_slide(db_session, pid, 1)
    await _add_slide(db_session, pid, 2, is_deleted=True)  # excluded from count
    await _add_media(db_session, s1, 1, SlideMediaTypeEnum.IMAGE, storage_key="live.png")
    await _add_media(
        db_session, s1, 2, SlideMediaTypeEnum.VIDEO, storage_key="dead.mp4", is_deleted=True
    )

    item = _item(await list_presentations(_ctx(db_session, workspace, user)), pid)
    assert item["slide_count"] == 1
    assert item["media_kinds"] == ["image"]  # deleted video excluded


@pytest.mark.integration
async def test_list_cards_have_no_per_row_n_plus_one(db_session):
    from sqlalchemy import event as sa_event

    from beyo_manager.models import database as db_module

    workspace, user = await _seed(db_session)
    for n in range(4):
        pid = await _draft(db_session, workspace, user, title=f"Deck {n}")
        s = await _add_slide(db_session, pid, 1)
        await _add_media(db_session, s, 1, SlideMediaTypeEnum.IMAGE, storage_key=f"c{n}.png")

    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_module._engine  # populated by now (init_db ran via the db_session chain)
    sa_event.listen(engine.sync_engine, "before_cursor_execute", _record)
    try:
        result = await list_presentations(_ctx(db_session, workspace, user))
    finally:
        sa_event.remove(engine.sync_engine, "before_cursor_execute", _record)

    assert len(result["app_update_presentations_pagination"]["items"]) == 4
    # 1 (presentations page) + 1 (slides) + 1 (media selectin) — constant, not per-row.
    assert len(statements) <= 4, (
        f"expected a constant, batched query count; got {len(statements)}: {statements}"
    )
