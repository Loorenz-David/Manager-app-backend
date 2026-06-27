from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.batch_update_item_positions import batch_update_item_positions
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


async def _seed_workspace_user_and_items(db_session) -> tuple[Workspace, User, Item, Item]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    item_one = Item(
        workspace_id=workspace.client_id,
        created_by_id=user.client_id,
        article_number=f"ART-{suffix}-1",
        sku=f"SKU-{suffix}-1",
        item_position="A-01",
    )
    item_two = Item(
        workspace_id=workspace.client_id,
        created_by_id=user.client_id,
        article_number=f"ART-{suffix}-2",
        sku=f"SKU-{suffix}-2",
        item_position="A-02",
    )
    db_session.add_all([workspace, user, item_one, item_two])
    await db_session.flush()
    return workspace, user, item_one, item_two


@pytest.mark.integration
async def test_batch_update_item_positions_updates_all_items_creates_history_and_dispatches_events(
    db_session,
    monkeypatch,
):
    workspace, user, item_one, item_two = await _seed_workspace_user_and_items(db_session)
    dispatched_events = []

    async def _fake_dispatch(events):
        dispatched_events.extend(events)
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.batch_update_item_positions.event_bus.dispatch",
        _fake_dispatch,
    )

    result = await batch_update_item_positions(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "entries": [
                    {"client_id": item_one.client_id, "item_position": "B-07"},
                    {"client_id": item_two.client_id, "item_position": None},
                ]
            },
        )
    )

    await db_session.refresh(item_one)
    await db_session.refresh(item_two)

    history_rows = (
        await db_session.execute(
            select(HistoryRecord, HistoryRecordLink)
            .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
            .where(
                HistoryRecordLink.entity_type == HistoryRecordEntityTypeEnum.ITEM,
                HistoryRecordLink.entity_client_id.in_([item_one.client_id, item_two.client_id]),
                HistoryRecord.change_type == HistoryRecordChangeTypeEnum.UPDATED,
            )
            .order_by(HistoryRecord.created_at.asc())
        )
    ).all()

    assert result == {"updated_ids": [item_one.client_id, item_two.client_id]}
    assert item_one.item_position == "B-07"
    assert item_two.item_position is None
    assert item_one.updated_by_id == user.client_id
    assert item_two.updated_by_id == user.client_id
    assert len(history_rows) == 2
    assert all(record.description is not None for record, _link in history_rows)
    assert [event.event_name for event in dispatched_events] == ["item:updated", "item:updated"]
    assert [event.client_id for event in dispatched_events] == [item_one.client_id, item_two.client_id]


@pytest.mark.integration
async def test_batch_update_item_positions_rolls_back_when_any_item_is_missing(db_session, monkeypatch):
    workspace, user, item_one, item_two = await _seed_workspace_user_and_items(db_session)
    dispatched_events = []
    before_item_one_updated_at = item_one.updated_at
    before_item_two_updated_at = item_two.updated_at

    async def _fake_dispatch(events):
        dispatched_events.extend(events)
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.items.batch_update_item_positions.event_bus.dispatch",
        _fake_dispatch,
    )

    with pytest.raises(NotFound):
        await batch_update_item_positions(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={
                    "entries": [
                        {"client_id": item_one.client_id, "item_position": "B-07"},
                        {"client_id": "itm_missing", "item_position": "C-01"},
                    ]
                },
            )
    )

    await db_session.refresh(item_one)
    await db_session.refresh(item_two)
    history_count = await db_session.scalar(select(func.count()).select_from(HistoryRecord))

    assert item_one.item_position == "A-01"
    assert item_two.item_position == "A-02"
    assert item_one.updated_at == before_item_one_updated_at
    assert item_two.updated_at == before_item_two_updated_at
    assert history_count == 0
    assert dispatched_events == []
