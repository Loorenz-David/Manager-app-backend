"""The item-zone push create_task emits must snapshot the item's *final* identifiers.

The push payload is frozen as JSON when the execution task row is created, so anything
create_task writes to the item afterwards — notably the template-backfilled sku — never
reaches the location tracker unless the enqueue is ordered after that write.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.items.update_item import update_item
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


def _capture_pushes(monkeypatch) -> list[dict]:
    """Intercept the execution-task row so we see the payload exactly as the worker would."""
    payloads: list[dict] = []

    async def _create_instant_task(**kwargs):
        payloads.append(kwargs["payload"])
        return type("_Task", (), {"client_id": f"tsk_{len(payloads)}"})()

    monkeypatch.setattr(
        "beyo_manager.services.commands.location_tracker.enqueue_item_zone_push.create_instant_task",
        _create_instant_task,
    )
    return payloads


async def _seed_preorder_template(db_session, workspace, user) -> None:
    await create_sku_template(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"task_type": "pre_order", "prefix": "PRE"},
        )
    )


@pytest.mark.integration
async def test_zone_push_carries_the_backfilled_sku_for_a_newly_created_item(db_session, monkeypatch):
    """The regression this ordering fix exists for: article_number in, sku minted after."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)
    payloads = _capture_pushes(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-Z", "item_zone": "Shelf A"},
            },
        )
    )

    assert result["item_sku"] == "PRE-1"
    assert len(payloads) == 1
    assert payloads[0]["changes"] == [
        {
            "position": "Shelf A",
            "item_targets": [
                {"article_number": "ART-Z", "sku": "PRE-1", "needs_fixing": False}
            ],
            "username": "tester",
        }
    ]
    assert payloads[0]["requested_by_user_id"] == user.client_id


@pytest.mark.integration
async def test_zone_push_for_an_existing_item_carries_its_stored_sku(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)
    existing_item = Item(
        workspace_id=workspace.client_id,
        article_number="ART-EXISTING",
        sku="MANUAL-SKU-1",
        created_by_id=user.client_id,
    )
    db_session.add(existing_item)
    await db_session.flush()
    payloads = _capture_pushes(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order re-using an item",
                "item": {"article_number": "ART-EXISTING", "item_zone": "Shelf B"},
            },
        )
    )

    assert result["item_id"] == existing_item.client_id
    assert len(payloads) == 1
    assert payloads[0]["changes"][0]["position"] == "Shelf B"
    assert payloads[0]["changes"][0]["item_targets"] == [
        {"article_number": "ART-EXISTING", "sku": "MANUAL-SKU-1", "needs_fixing": False}
    ]


@pytest.mark.integration
async def test_zone_push_for_a_template_only_item_carries_the_template_sku(db_session, monkeypatch):
    """The create_item_in_session branch resolves its sku up front and pushes exactly once."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)
    payloads = _capture_pushes(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order with no identifier",
                "item": {"item_zone": "Shelf C"},
            },
        )
    )

    assert result["item_sku"] == "PRE-1"
    assert len(payloads) == 1
    assert payloads[0]["changes"] == [
        {
            "position": "Shelf C",
            "item_targets": [{"sku": "PRE-1", "needs_fixing": False}],
            "username": "tester",
        }
    ]


@pytest.mark.integration
async def test_return_task_flags_needs_fixing_at_creation(db_session, monkeypatch):
    """create_task must decide from the task in hand — its TaskItem row does not exist yet."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    payloads = _capture_pushes(monkeypatch)

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "Damaged chair returned",
                "item": {"article_number": "ART-RET", "item_zone": "Shelf D"},
            },
        )
    )

    assert len(payloads) == 1
    assert payloads[0]["changes"][0]["item_targets"][0]["needs_fixing"] is True


@pytest.mark.integration
async def test_later_zone_move_resolves_needs_fixing_from_the_open_return_task(db_session, monkeypatch):
    """update_item has no task in hand, so the flag comes from the item's live task links."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    created = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "Damaged chair returned",
                "item": {"article_number": "ART-RET-2", "item_zone": "Shelf A"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    await update_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"client_id": created["item_id"], "item_zone": "Shelf B"},
        )
    )

    assert len(payloads) == 1
    assert payloads[0]["changes"][0]["position"] == "Shelf B"
    assert payloads[0]["changes"][0]["item_targets"][0]["needs_fixing"] is True


@pytest.mark.integration
async def test_zone_move_on_a_non_return_item_is_not_flagged(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)

    created = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-PO", "item_zone": "Shelf A"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    await update_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"client_id": created["item_id"], "item_zone": "Shelf B"},
        )
    )

    assert len(payloads) == 1
    assert payloads[0]["changes"][0]["item_targets"][0]["needs_fixing"] is False


@pytest.mark.integration
async def test_repeated_zone_value_does_not_push_again(db_session, monkeypatch):
    """Case F: the tracker hears about a zone once, not once per request that mentions it."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    created = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "Damaged chair returned",
                "item": {"article_number": "ART-SAME", "item_zone": "Shelf A"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    for zone in ("Shelf A", "  Shelf A  "):
        await update_item(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                role_name="manager",
                incoming_data={"client_id": created["item_id"], "item_zone": zone},
            )
        )

    assert payloads == []

    await update_item(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={"client_id": created["item_id"], "item_zone": "Shelf B"},
        )
    )

    assert len(payloads) == 1


@pytest.mark.integration
async def test_return_task_on_an_unmoved_item_still_flags_needs_fixing(db_session, monkeypatch):
    """The item came back damaged whether or not it moved — the zone-change gate must not eat it.

    This is the real-world shape: the item is already sitting where the tracker last saw it, so
    find_or_create_item defers nothing and create_task has to enqueue the flag itself.
    """
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "First return",
                "item": {"article_number": "ART-UNMOVED", "item_zone": "R31"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "Second return, same zone",
                "item": {"article_number": "ART-UNMOVED", "item_zone": "R31"},
            },
        )
    )

    assert len(payloads) == 1
    assert payloads[0]["changes"] == [
        {
            "position": "R31",
            "item_targets": [{"article_number": "ART-UNMOVED", "needs_fixing": True}],
            "username": "tester",
        }
    ]


@pytest.mark.integration
async def test_return_task_on_an_unmoved_item_pushes_once_not_twice(db_session, monkeypatch):
    """A return task that *does* move the item gets one push carrying the flag, not two."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "First return",
                "item": {"article_number": "ART-MOVED", "item_zone": "R31"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "return",
                "title": "Second return, new zone",
                "item": {"article_number": "ART-MOVED", "item_zone": "R32"},
            },
        )
    )

    assert len(payloads) == 1
    assert payloads[0]["changes"][0]["position"] == "R32"
    assert payloads[0]["changes"][0]["item_targets"][0]["needs_fixing"] is True


@pytest.mark.integration
async def test_non_return_task_on_an_unmoved_item_pushes_nothing(db_session, monkeypatch):
    """Only return tasks earn an unconditional push — everything else stays zone-change driven."""
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order chair",
                "item": {"article_number": "ART-PO-SAME", "item_zone": "Shelf A"},
            },
        )
    )

    payloads = _capture_pushes(monkeypatch)
    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Second pre-order, same zone",
                "item": {"article_number": "ART-PO-SAME", "item_zone": "Shelf A"},
            },
        )
    )

    assert payloads == []


@pytest.mark.integration
async def test_no_zone_push_when_the_item_carries_no_zone(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    await _seed_preorder_template(db_session, workspace, user)
    payloads = _capture_pushes(monkeypatch)

    await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            role_name="manager",
            incoming_data={
                "task_type": "pre_order",
                "title": "Pre-order with no zone",
                "item": {"article_number": "ART-NO-ZONE"},
            },
        )
    )

    assert payloads == []
