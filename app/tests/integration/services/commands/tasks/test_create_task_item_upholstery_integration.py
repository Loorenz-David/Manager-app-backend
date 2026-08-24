from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
    ItemStateEnum,
)
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


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


async def _seed_workspace_user_item(db_session) -> tuple[Workspace, User, Item]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    item = Item(
        workspace_id=workspace.client_id,
        article_number=f"ART-{suffix}",
        state=ItemStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(item)
    await db_session.flush()
    return workspace, user, item


async def _disable_event_dispatch(monkeypatch) -> None:
    async def _noop_dispatch(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", _noop_dispatch)


@pytest.mark.integration
async def test_task_creation_reuses_existing_deferred_item_upholstery(db_session, monkeypatch):
    workspace, user, item = await _seed_workspace_user_item(db_session)
    await _disable_event_dispatch(monkeypatch)

    current = ItemUpholstery(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        source=ItemUpholsterySourceEnum.INTERNAL,
        amount_meters="2.500",
        created_by_id=user.client_id,
    )
    db_session.add(current)
    await db_session.flush()

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": TaskTypeEnum.INTERNAL,
                "item": {"article_number": item.article_number},
                "item_upholstery": {
                    "source": ItemUpholsterySourceEnum.INTERNAL,
                    "amount_meters": "3.000",
                },
            },
        )
    )

    rows = (
        await db_session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.item_id == item.client_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].client_id == current.client_id
    assert rows[0].amount_meters == Decimal("3.000")


@pytest.mark.integration
async def test_task_creation_reuses_current_context_and_updates_requirement_quantity(
    db_session,
    monkeypatch,
):
    workspace, user, item = await _seed_workspace_user_item(db_session)
    await _disable_event_dispatch(monkeypatch)

    current = ItemUpholstery(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        source=ItemUpholsterySourceEnum.CUSTOMER,
        amount_meters="2.500",
        created_by_id=user.client_id,
    )
    db_session.add(current)
    await db_session.flush()
    requirement = ItemUpholsteryRequirement(
        workspace_id=workspace.client_id,
        item_upholstery_id=current.client_id,
        amount_meters="2.500",
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=ItemUpholsteryRequirementStateEnum.AVAILABLE,
        created_by_id=user.client_id,
    )
    db_session.add(requirement)
    await db_session.flush()
    current.active_requirement_id = requirement.client_id
    await db_session.flush()

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": TaskTypeEnum.INTERNAL,
                "item": {"article_number": item.article_number},
                "item_upholstery": {
                    "source": ItemUpholsterySourceEnum.CUSTOMER,
                    "amount_meters": "3.000",
                },
            },
        )
    )

    await db_session.refresh(current)
    await db_session.refresh(requirement)
    assert current.amount_meters == Decimal("3.000")
    assert requirement.amount_meters == Decimal("3.000")


@pytest.mark.integration
@pytest.mark.parametrize(
    "terminal_state",
    [
        ItemUpholsteryRequirementStateEnum.COMPLETED,
        ItemUpholsteryRequirementStateEnum.FAILED,
    ],
)
async def test_task_creation_archives_terminal_context_and_creates_new_one(
    db_session,
    monkeypatch,
    terminal_state,
):
    workspace, user, item = await _seed_workspace_user_item(db_session)
    await _disable_event_dispatch(monkeypatch)

    current = ItemUpholstery(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        source=ItemUpholsterySourceEnum.CUSTOMER,
        amount_meters="2.500",
        created_by_id=user.client_id,
    )
    db_session.add(current)
    await db_session.flush()
    requirement = ItemUpholsteryRequirement(
        workspace_id=workspace.client_id,
        item_upholstery_id=current.client_id,
        amount_meters="2.500",
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=terminal_state,
        created_by_id=user.client_id,
    )
    db_session.add(requirement)
    await db_session.flush()
    current.active_requirement_id = requirement.client_id
    await db_session.flush()

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": TaskTypeEnum.INTERNAL,
                "item": {"article_number": item.article_number},
                "item_upholstery": {
                    "source": ItemUpholsterySourceEnum.INTERNAL,
                    "amount_meters": "3.000",
                },
            },
        )
    )

    await db_session.refresh(current)
    rows = (
        await db_session.execute(
            select(ItemUpholstery)
            .where(ItemUpholstery.item_id == item.client_id)
            .order_by(ItemUpholstery.created_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert current.is_deleted is True
    assert rows[1].client_id != current.client_id
    assert rows[1].is_deleted is False
