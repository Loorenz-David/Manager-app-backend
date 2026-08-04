from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.create_item import create_item
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace_user_and_template(db_session) -> tuple[Workspace, User]:
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

    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )
    return workspace, user


@pytest.mark.integration
async def test_create_item_allocates_sku_from_template(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user_and_template(db_session)

    async def _fake_dispatch(events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.items.create_item.event_bus.dispatch", _fake_dispatch)

    first = await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"sku_template_task_type": TaskTypeEnum.PRE_ORDER},
        )
    )
    second = await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"sku_template_task_type": TaskTypeEnum.PRE_ORDER},
        )
    )

    item_one = await db_session.get(Item, first["client_id"])
    item_two = await db_session.get(Item, second["client_id"])
    assert item_one.sku == "PRE-1"
    assert item_two.sku == "PRE-2"


@pytest.mark.integration
async def test_create_item_manual_sku_does_not_consume_template_counter(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user_and_template(db_session)

    async def _fake_dispatch(events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.items.create_item.event_bus.dispatch", _fake_dispatch)

    await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"sku": "CUSTOM-1", "sku_template_task_type": TaskTypeEnum.PRE_ORDER},
        )
    )

    template = await db_session.scalar(
        select(SkuTemplate).where(
            SkuTemplate.workspace_id == workspace.client_id,
            SkuTemplate.task_type == TaskTypeEnum.PRE_ORDER,
        )
    )
    assert template.last_scalar == 0


@pytest.mark.integration
async def test_create_item_rolls_back_scalar_when_transaction_fails(db_session, monkeypatch):
    """A failure that happens *after* the scalar is allocated (e.g. a bad nested
    upholstery reference) must roll the increment back with everything else —
    proving the counter doesn't leak on partial failures, unlike a DB sequence.

    Uses a dedicated session (like a real request would get from get_db()) so
    maybe_begin owns and rolls back its own transaction, instead of running as a
    subordinate inside the test fixture's ambient autobegun transaction.
    """
    workspace, user = await _seed_workspace_user_and_template(db_session)
    await db_session.commit()

    async def _fake_dispatch(events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.items.create_item.event_bus.dispatch", _fake_dispatch)

    from beyo_manager.models.database import _session_factory

    failing_session = _session_factory()
    try:
        with pytest.raises(NotFound):
            await create_item(
                _ctx(
                    failing_session,
                    workspace_id=workspace.client_id,
                    user_id=user.client_id,
                    incoming_data={
                        "sku_template_task_type": TaskTypeEnum.PRE_ORDER,
                        "item_upholstery": {"source": "internal", "upholstery_id": "uph_missing"},
                    },
                )
            )
    finally:
        await failing_session.close()

    template = await db_session.scalar(
        select(SkuTemplate).where(
            SkuTemplate.workspace_id == workspace.client_id,
            SkuTemplate.task_type == TaskTypeEnum.PRE_ORDER,
        )
    )
    assert template.last_scalar == 0

    result = await create_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"sku_template_task_type": TaskTypeEnum.PRE_ORDER},
        )
    )
    item = await db_session.get(Item, result["client_id"])
    assert item.sku == "PRE-1"


@pytest.mark.integration
async def test_create_item_requires_sku_source(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user_and_template(db_session)

    async def _fake_dispatch(events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.items.create_item.event_bus.dispatch", _fake_dispatch)

    with pytest.raises(ValidationError):
        await create_item(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={},
            )
        )
