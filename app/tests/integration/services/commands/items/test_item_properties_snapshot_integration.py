"""properties reaches the item through every creation path, and re-snapshots only on change.

Three write paths carry it: create_item, create_task's template-only branch
(create_item_in_session), and find_or_create_item — which both creates and, on a
match, re-snapshots. The signature is always derived from the blob, so these tests
assert the derived value rather than a hard-coded hash.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.create_item import create_item
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


PROPS = {"wood": "oak", "carving": {"back": "heavy", "legs": "none"}}
OTHER_PROPS = {"wood": "walnut", "carving": {"back": "heavy", "legs": "none"}}


def _ctx(session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=session,
    )


async def _seed(db_session) -> tuple[Workspace, User]:
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


async def _seed_preorder_template(db_session, workspace, user) -> None:
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )


def _silence_events(monkeypatch) -> None:
    async def _noop(_events):
        return None

    # find_or_create_item dispatches nothing of its own, so there is no bus to silence there.
    for module in (
        "beyo_manager.services.commands.items.create_item",
        "beyo_manager.services.commands.tasks.create_task",
    ):
        monkeypatch.setattr(f"{module}.event_bus.dispatch", _noop)


async def _load(db_session, item_id: str) -> Item:
    return await db_session.scalar(select(Item).where(Item.client_id == item_id))


@pytest.mark.integration
async def test_create_item_snapshots_properties_signature_and_time(db_session, monkeypatch):
    workspace, user = await _seed(db_session)
    _silence_events(monkeypatch)
    before = datetime.now(timezone.utc)

    result = await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"article_number": "ART-P1", "properties": PROPS},
        )
    )

    item = await _load(db_session, result["client_id"])
    assert item.properties == PROPS
    assert item.properties_signature == compute_properties_signature(PROPS)
    assert item.properties_snapshot_at >= before


@pytest.mark.integration
@pytest.mark.parametrize("payload", [{}, None])
async def test_create_item_with_an_empty_payload_leaves_the_columns_null(
    db_session, monkeypatch, payload
):
    workspace, user = await _seed(db_session)
    _silence_events(monkeypatch)

    result = await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"article_number": f"ART-EMPTY-{uuid4().hex[:6]}", "properties": payload},
        )
    )

    item = await _load(db_session, result["client_id"])
    assert item.properties is None
    assert item.properties_signature is None
    assert item.properties_snapshot_at is None


@pytest.mark.integration
async def test_create_task_template_only_branch_snapshots_properties(db_session, monkeypatch):
    """No article_number and no sku: the item is created by create_item_in_session."""
    workspace, user = await _seed(db_session)
    await _seed_preorder_template(db_session, workspace, user)
    _silence_events(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Template-only item",
                "item": {"properties": PROPS},
            },
        )
    )

    item = await _load(db_session, result["item_id"])
    assert item.sku == "PRE-1"
    assert item.properties == PROPS
    assert item.properties_signature == compute_properties_signature(PROPS)
    assert item.properties_snapshot_at is not None


@pytest.mark.integration
async def test_create_task_find_or_create_branch_snapshots_a_new_item(db_session, monkeypatch):
    workspace, user = await _seed(db_session)
    await _seed_preorder_template(db_session, workspace, user)
    _silence_events(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "New item by article number",
                "item": {"article_number": "ART-P2", "properties": PROPS},
            },
        )
    )

    item = await _load(db_session, result["item_id"])
    assert item.properties == PROPS
    assert item.properties_signature == compute_properties_signature(PROPS)


@pytest.mark.integration
async def test_linking_an_existing_item_with_a_new_profile_resnapshots_it(db_session, monkeypatch):
    workspace, user = await _seed(db_session)
    await _seed_preorder_template(db_session, workspace, user)
    _silence_events(monkeypatch)
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    existing = Item(
        workspace_id=workspace.client_id,
        article_number="ART-LINK-1",
        created_by_id=user.client_id,
        properties=PROPS,
        properties_signature=compute_properties_signature(PROPS),
        properties_snapshot_at=established,
    )
    db_session.add(existing)
    await db_session.flush()

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Link with a changed profile",
                "item": {"article_number": "ART-LINK-1", "properties": OTHER_PROPS},
            },
        )
    )

    assert result["item_id"] == existing.client_id
    item = await _load(db_session, existing.client_id)
    assert item.properties == OTHER_PROPS
    assert item.properties_signature == compute_properties_signature(OTHER_PROPS)
    assert item.properties_snapshot_at > established


@pytest.mark.integration
async def test_linking_with_the_same_profile_does_not_bump_the_snapshot_time(db_session, monkeypatch):
    """Key order differs but the profile does not, so nothing is written."""
    workspace, user = await _seed(db_session)
    await _seed_preorder_template(db_session, workspace, user)
    _silence_events(monkeypatch)
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    existing = Item(
        workspace_id=workspace.client_id,
        article_number="ART-LINK-2",
        created_by_id=user.client_id,
        properties=PROPS,
        properties_signature=compute_properties_signature(PROPS),
        properties_snapshot_at=established,
    )
    db_session.add(existing)
    await db_session.flush()

    reordered = {"carving": {"legs": "none", "back": "heavy"}, "wood": "oak"}
    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": "pre_order",
                "title": "Link with the same profile",
                "item": {"article_number": "ART-LINK-2", "properties": reordered},
            },
        )
    )

    item = await _load(db_session, existing.client_id)
    assert item.properties_snapshot_at == established


@pytest.mark.integration
@pytest.mark.parametrize("payload", [{}, None, "absent"])
async def test_linking_with_an_empty_payload_never_wipes_an_existing_profile(
    db_session, monkeypatch, payload
):
    """A frontend that always serializes the whole item must not clear the profile."""
    workspace, user = await _seed(db_session)
    _silence_events(monkeypatch)
    established = datetime(2026, 8, 1, tzinfo=timezone.utc)
    article_number = f"ART-KEEP-{uuid4().hex[:6]}"
    existing = Item(
        workspace_id=workspace.client_id,
        article_number=article_number,
        created_by_id=user.client_id,
        properties=PROPS,
        properties_signature=compute_properties_signature(PROPS),
        properties_snapshot_at=established,
    )
    db_session.add(existing)
    await db_session.flush()

    incoming = {"article_number": article_number, "designer": "Someone"}
    if payload != "absent":
        incoming["properties"] = payload

    result = await find_or_create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data=incoming,
        )
    )

    assert result["was_created"] is False
    item = await _load(db_session, existing.client_id)
    assert item.designer == "Someone"
    assert item.properties == PROPS
    assert item.properties_signature == compute_properties_signature(PROPS)
    assert item.properties_snapshot_at == established


@pytest.mark.integration
async def test_linking_an_unsnapshotted_item_establishes_its_first_profile(db_session, monkeypatch):
    workspace, user = await _seed(db_session)
    _silence_events(monkeypatch)
    article_number = f"ART-FIRST-{uuid4().hex[:6]}"
    existing = Item(
        workspace_id=workspace.client_id,
        article_number=article_number,
        created_by_id=user.client_id,
    )
    db_session.add(existing)
    await db_session.flush()

    await find_or_create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"article_number": article_number, "properties": PROPS},
        )
    )

    item = await _load(db_session, existing.client_id)
    assert item.properties == PROPS
    assert item.properties_signature == compute_properties_signature(PROPS)
    assert item.properties_snapshot_at is not None
