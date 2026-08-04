from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


def _ctx(session, *, workspace_id: str, user_id: str, role_name: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": role_name,
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, User]:
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


async def _disable_event_dispatch(monkeypatch) -> None:
    async def _noop_dispatch(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", _noop_dispatch)


@pytest.mark.integration
async def test_create_task_allocates_sku_from_template_gaplessly(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    first = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-1"},
            },
        )
    )
    second = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order table",
                "item": {"article_number": "ART-2"},
            },
        )
    )

    assert first["item_sku"] == "PRE-1"
    assert second["item_sku"] == "PRE-2"
    item_one = await db_session.get(Item, first["item_id"])
    item_two = await db_session.get(Item, second["item_id"])
    assert item_one.sku == "PRE-1"
    assert item_two.sku == "PRE-2"


@pytest.mark.integration
async def test_create_task_does_not_overwrite_sku_on_existing_item_match(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )
    existing_item = Item(
        workspace_id=workspace.client_id,
        article_number="ART-EXISTING",
        sku="MANUAL-SKU-1",
        created_by_id=user.client_id,
    )
    db_session.add(existing_item)
    await db_session.flush()

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order re-using an item",
                "item": {"article_number": "ART-EXISTING"},
            },
        )
    )

    assert result["item_id"] == existing_item.client_id
    assert result["item_sku"] == "MANUAL-SKU-1"
    template = await db_session.scalar(
        select(SkuTemplate).where(SkuTemplate.workspace_id == workspace.client_id)
    )
    assert template.last_scalar == 0


@pytest.mark.integration
async def test_create_task_leaves_sku_none_when_task_type_has_no_template(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "internal",
                "title": "Internal task",
                "item": {"article_number": "ART-NO-TEMPLATE"},
            },
        )
    )

    assert result["item_sku"] is None
    item = await db_session.get(Item, result["item_id"])
    assert item.sku is None


@pytest.mark.integration
async def test_create_task_creates_item_from_template_alone_when_no_identifier_given(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )

    first = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {},
            },
        )
    )
    second = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order table",
                "item": {},
            },
        )
    )

    assert first["item_sku"] == "PRE-1"
    assert second["item_sku"] == "PRE-2"
    item_one = await db_session.get(Item, first["item_id"])
    item_two = await db_session.get(Item, second["item_id"])
    assert item_one.sku == "PRE-1"
    assert item_one.article_number is None
    assert item_two.sku == "PRE-2"


@pytest.mark.integration
async def test_create_task_errors_when_no_identifier_and_no_template(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    with pytest.raises(NotFound):
        await create_task(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                role_name="manager",
                incoming_data={
                    "task_type": "internal",
                    "title": "Internal task with no way to identify its item",
                    "item": {},
                },
            )
        )

    item_count = await db_session.scalar(
        select(func.count()).select_from(Item).where(Item.workspace_id == workspace.client_id)
    )
    assert item_count == 0
