"""Sequence-order semantics for slides and slide media.

Soft-deleted rows keep their historical ``sequence_order`` but release the slot:
uniqueness is enforced by a partial index over ``is_deleted = false`` only, and
the active set is kept contiguous at 1..N. Before that, deleting the only media
on a slide and adding another raised
``duplicate key value violates unique constraint
"uq_app_update_slide_media_slide_sequence"`` in production.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
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
from beyo_manager.services.commands.app_update_presentations.create_presentation_version import (
    create_presentation_version,
)
from beyo_manager.services.commands.app_update_presentations.publish_presentation import (
    publish_presentation,
)
from beyo_manager.services.commands.app_update_slide_media import add_slide_media as add_module
from beyo_manager.services.commands.app_update_slide_media.add_slide_media import (
    add_slide_media,
)
from beyo_manager.services.commands.app_update_slide_media.delete_slide_media import (
    delete_slide_media,
)
from beyo_manager.services.commands.app_update_slide_media.reorder_slide_media import (
    reorder_slide_media,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.commands.app_update_slides.delete_slide import delete_slide
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


class _StubStorage:
    """head_object always finds the object — these tests exercise sequencing."""

    def head_object(self, key: str) -> dict:
        return {"content_length": 1024, "content_type": "image/png", "last_modified": None}


@pytest.fixture(autouse=True)
def stub_storage(monkeypatch):
    monkeypatch.setattr(add_module, "get_storage_client", lambda: _StubStorage())


async def _draft_with_slide(db_session, workspace, user):
    presentation = await create_presentation(
        _ctx(db_session, workspace, user, {"title": "Update"})
    )
    presentation_id = presentation["presentation"]["client_id"]
    result = await create_slide(
        _ctx(db_session, workspace, user, {"presentation_id": presentation_id, "title": "S"})
    )
    slide_id = result["presentation"]["slides"][0]["client_id"]
    return presentation_id, slide_id


async def _add_media(db_session, workspace, user, presentation_id, slide_id, *, key):
    result = await add_slide_media(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "media_type": SlideMediaTypeEnum.IMAGE,
                "storage_key": key,
            },
        )
    )
    return result["presentation"]


async def _media_rows(db_session, slide_id):
    result = await db_session.execute(
        select(AppUpdateSlideMedia)
        .where(AppUpdateSlideMedia.slide_id == slide_id)
        .order_by(AppUpdateSlideMedia.sequence_order)
    )
    return result.scalars().all()


async def _active_media_orders(db_session, slide_id):
    return [m.sequence_order for m in await _media_rows(db_session, slide_id) if not m.is_deleted]


@pytest.mark.integration
async def test_media_can_be_added_after_the_only_media_is_deleted(db_session):
    """The exact production failure: delete the only media, add another."""
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)

    first = await _add_media(
        db_session, workspace, user, presentation_id, slide_id, key="a.png"
    )
    media_id = first["slides"][0]["media"][0]["client_id"]

    await delete_slide_media(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "media_id": media_id,
            },
        )
    )

    await _add_media(db_session, workspace, user, presentation_id, slide_id, key="b.png")

    rows = await _media_rows(db_session, slide_id)
    active = [m for m in rows if not m.is_deleted]
    deleted = [m for m in rows if m.is_deleted]
    assert [m.sequence_order for m in active] == [1]
    assert active[0].storage_key == "b.png"
    # The deleted row keeps its historical value and simply stops reserving it.
    assert [m.sequence_order for m in deleted] == [1]


@pytest.mark.integration
async def test_slide_can_be_created_after_the_only_slide_is_deleted(db_session):
    """Same defect one level up: slides use the same allocate-then-insert path."""
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)

    await delete_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": presentation_id, "slide_id": slide_id},
        )
    )
    await create_slide(
        _ctx(db_session, workspace, user, {"presentation_id": presentation_id, "title": "S2"})
    )

    result = await db_session.execute(
        select(AppUpdatePresentationSlide).where(
            AppUpdatePresentationSlide.presentation_id == presentation_id,
            AppUpdatePresentationSlide.is_deleted.is_(False),
        )
    )
    slides = result.scalars().all()
    assert [s.sequence_order for s in slides] == [1]
    assert slides[0].title == "S2"


@pytest.mark.integration
async def test_delete_compacts_surviving_media_to_contiguous_range(db_session):
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)

    for key in ("a.png", "b.png", "c.png"):
        latest = await _add_media(
            db_session, workspace, user, presentation_id, slide_id, key=key
        )
    media = latest["slides"][0]["media"]
    assert [m["sequence_order"] for m in media] == [1, 2, 3]
    first_media_id = media[0]["client_id"]

    await delete_slide_media(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "media_id": first_media_id,
            },
        )
    )

    assert await _active_media_orders(db_session, slide_id) == [1, 2]
    survivors = [m for m in await _media_rows(db_session, slide_id) if not m.is_deleted]
    assert [m.storage_key for m in survivors] == ["b.png", "c.png"]


@pytest.mark.integration
async def test_reorder_succeeds_with_a_deleted_row_holding_a_low_sequence(db_session):
    """Reorder renumbers active rows down onto values deleted rows still carry."""
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)

    for key in ("a.png", "b.png", "c.png"):
        latest = await _add_media(
            db_session, workspace, user, presentation_id, slide_id, key=key
        )
    media_ids = [m["client_id"] for m in latest["slides"][0]["media"]]

    # Delete the last one, then reorder the survivors so one of them must take
    # a sequence value that is still stored on a soft-deleted row.
    await delete_slide_media(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "media_id": media_ids[0],
            },
        )
    )

    survivors = [m for m in await _media_rows(db_session, slide_id) if not m.is_deleted]
    reversed_ids = [m.client_id for m in reversed(survivors)]
    result = await reorder_slide_media(
        _ctx(
            db_session,
            workspace,
            user,
            {
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "ordered_media_ids": reversed_ids,
            },
        )
    )

    ordered = result["presentation"]["slides"][0]["media"]
    assert [m["sequence_order"] for m in ordered] == [1, 2]
    assert [m["client_id"] for m in ordered] == reversed_ids


@pytest.mark.integration
async def test_publish_succeeds_with_soft_deleted_slide_and_media(db_session):
    """Publish compacts active rows to 1..N; deleted rows must not block it."""
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)
    await _add_media(db_session, workspace, user, presentation_id, slide_id, key="a.png")

    second = await create_slide(
        _ctx(db_session, workspace, user, {"presentation_id": presentation_id, "title": "S2"})
    )
    second_slide_id = second["presentation"]["slides"][1]["client_id"]
    await _add_media(
        db_session, workspace, user, presentation_id, second_slide_id, key="b.png"
    )

    # Remove the first slide (and its media) so the survivor has to move to 1.
    await delete_slide(
        _ctx(
            db_session,
            workspace,
            user,
            {"presentation_id": presentation_id, "slide_id": slide_id},
        )
    )

    result = await publish_presentation(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    slides = result["presentation"]["slides"]
    assert [s["sequence_order"] for s in slides] == [1]
    assert [m["sequence_order"] for m in slides[0]["media"]] == [1]


@pytest.mark.integration
async def test_concurrent_adds_to_one_slide_get_distinct_sequences(db_session):
    """Two overlapping adds must not both allocate the same sequence_order.

    Needs two real connections: the guard is a FOR UPDATE row lock on the slide,
    which is invisible within a single session. The setup is committed so the
    second connection can see it, then removed explicitly.
    """
    from beyo_manager.models.database import _session_factory

    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)
    await db_session.commit()

    async def _add(key: str) -> None:
        async with _session_factory() as session:
            await add_slide_media(
                ServiceContext(
                    identity=_identity(workspace.client_id, user.client_id),
                    incoming_data={
                        "presentation_id": presentation_id,
                        "slide_id": slide_id,
                        "media_type": SlideMediaTypeEnum.IMAGE,
                        "storage_key": key,
                    },
                    session=session,
                )
            )

    try:
        import asyncio

        await asyncio.gather(_add("concurrent_a.png"), _add("concurrent_b.png"))

        async with _session_factory() as verify:
            result = await verify.execute(
                select(AppUpdateSlideMedia)
                .where(AppUpdateSlideMedia.slide_id == slide_id)
                .order_by(AppUpdateSlideMedia.sequence_order)
            )
            rows = result.scalars().all()
        assert [r.sequence_order for r in rows] == [1, 2]
        assert len({r.storage_key for r in rows}) == 2
    finally:
        async with _session_factory() as cleanup:
            await cleanup.execute(
                AppUpdateSlideMedia.__table__.delete().where(
                    AppUpdateSlideMedia.slide_id == slide_id
                )
            )
            await cleanup.execute(
                AppUpdatePresentationSlide.__table__.delete().where(
                    AppUpdatePresentationSlide.presentation_id == presentation_id
                )
            )
            await cleanup.execute(
                AppUpdatePresentation.__table__.delete().where(
                    AppUpdatePresentation.client_id == presentation_id
                )
            )
            await cleanup.execute(
                User.__table__.delete().where(User.client_id == user.client_id)
            )
            await cleanup.execute(
                Workspace.__table__.delete().where(
                    Workspace.client_id == workspace.client_id
                )
            )
            await cleanup.commit()


@pytest.mark.integration
async def test_new_version_copy_is_contiguous_from_one(db_session):
    """A copy must not inherit gaps left in the source by an earlier delete."""
    workspace, user = await _seed(db_session)
    presentation_id, slide_id = await _draft_with_slide(db_session, workspace, user)

    for key in ("a.png", "b.png"):
        await _add_media(db_session, workspace, user, presentation_id, slide_id, key=key)

    # Force a gap directly, bypassing the compaction delete_slide_media applies.
    rows = await _media_rows(db_session, slide_id)
    rows[0].is_deleted = True
    rows[1].sequence_order = 7
    await db_session.flush()

    result = await create_presentation_version(
        _ctx(db_session, workspace, user, {"client_id": presentation_id})
    )
    copied = result["presentation"]["slides"][0]["media"]
    assert [m["sequence_order"] for m in copied] == [1]
    assert copied[0]["client_id"] != rows[1].client_id
