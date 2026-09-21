"""Plan 11 C4/C5 — the category guard on both item writers (master plan §6.5
`_category_guard.py`; intention §5B MC-14 "category change refused" / "made exact").

Fixture: F0 with A created through `CR`. One representative row per distinct code
path; row-by-row transcription and mutation arming belong to the tester.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.items.find_or_create_item import find_or_create_item
from beyo_manager.services.commands.items.update_item import update_item
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext
from tests.helpers.stock_report import assert_stock_report_clean, make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

_MESSAGE = "Unassign this item from the stock report before changing its category."


async def _make_row(db_session, seeded, *, criteria=None, quantity_requested=10):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=quantity_requested,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _CR(db_session, seeded, row, task, item):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row.client_id,
                    "task_id": task.client_id,
                    "item_id": item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    return result["stock_task_assignments"][0]["client_id"]


async def _update_item(db_session, seeded, **fields):
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="manager",
        incoming_data={"client_id": seeded.item.client_id, **fields},
    )
    return await update_item(ctx)


async def _fresh_assignment(db_session, client_id):
    return (
        await db_session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# C4 — update_item
# ---------------------------------------------------------------------------


async def test_c4a_changing_category_with_active_assignment_is_refused(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)
    before = await db_session.get(Item, seeded.item.client_id)
    before_category, before_updated_at = before.item_category_id, before.updated_at

    with pytest.raises(ConflictError) as excinfo:
        await _update_item(
            db_session, seeded, item_category_id=seeded.categories[1].client_id
        )
    assert str(excinfo.value) == _MESSAGE

    after = await db_session.get(Item, seeded.item.client_id)
    assert after.item_category_id == before_category
    assert after.updated_at == before_updated_at


async def test_c4c_changing_an_unrelated_field_with_active_assignment_is_allowed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)

    await _update_item(db_session, seeded, designer="x")

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.designer == "x"


async def test_c4f_changing_category_of_a_resolved_only_assignment_is_allowed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.AWAITING, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _update_item(db_session, seeded, item_category_id=seeded.categories[1].client_id)

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[1].client_id


async def test_c4g_changing_category_of_a_soft_deleted_only_assignment_is_allowed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    ctx = make_ctx(
        db_session,
        seeded,
        role_name="worker",
        incoming_data={"client_ids": [assignment_id]},
    )
    from beyo_manager.services.commands.stock_report.delete_stock_task_assignments import (
        delete_stock_task_assignments,
    )

    await delete_stock_task_assignments(ctx)

    await _update_item(db_session, seeded, item_category_id=seeded.categories[1].client_id)

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[1].client_id
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_c4i_changing_category_of_a_resolved_early_only_assignment_is_allowed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment_id = await _CR(db_session, seeded, row, seeded.task, seeded.item)
    assignment = await _fresh_assignment(db_session, assignment_id)
    await move_assignment(
        db_session, assignment, S.RESOLVED_EARLY, workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id, now=NOW, trigger="test",
    )

    await _update_item(db_session, seeded, item_category_id=seeded.categories[1].client_id)

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[1].client_id


# ---------------------------------------------------------------------------
# C5 — find_or_create_item / create_task
# ---------------------------------------------------------------------------


async def _create_task(db_session, seeded, *, item_category_id, article_number=None):
    ctx = ServiceContext(
        identity={
            "workspace_id": seeded.workspace.client_id,
            "user_id": seeded.manager.client_id,
            "role_name": "manager",
        },
        incoming_data={
            "task_type": "internal",
            "item": {
                "article_number": article_number or seeded.item.article_number,
                "item_category_id": item_category_id,
            },
        },
        session=db_session,
    )
    return await create_task(ctx)


async def test_c5a_create_task_naming_a_new_category_for_an_actively_assigned_item_is_refused(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)

    with pytest.raises(ConflictError) as excinfo:
        await _create_task(db_session, seeded, item_category_id=seeded.categories[1].client_id)
    assert str(excinfo.value) == _MESSAGE

    # NOTE: this session has been in one continuously-autobegun transaction since
    # `seed_stock_report_workspace`'s first flush, so `create_task`'s own
    # `maybe_begin` never reaches owner mode here and never gets a chance to roll
    # back — a same-session read would see the flushed-but-uncommitted Task row
    # regardless of whether the real (fresh-session, production) rollback fires.
    # "The whole creation rolls back" is therefore not independently observable at
    # this scope; it is asserted analytically in the intention (§5B, verified: no
    # `begin_nested` wraps the call, no earlier step commits) and is not proven by
    # this test. What this test does prove: the guard fires with the exact message
    # and the item's own category is unaffected.
    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[0].client_id


async def test_c5c_create_task_omitting_category_with_active_assignment_is_allowed(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)

    ctx = ServiceContext(
        identity={
            "workspace_id": seeded.workspace.client_id,
            "user_id": seeded.manager.client_id,
            "role_name": "manager",
        },
        incoming_data={
            "task_type": "internal",
            "item": {"article_number": seeded.item.article_number},
        },
        session=db_session,
    )
    result = await create_task(ctx)
    assert result["client_id"]

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[0].client_id


async def test_c5d_no_assignment_at_all_category_change_through_create_task_behaves_as_today(
    db_session,
):
    seeded = await seed_stock_report_workspace(db_session)

    result = await _create_task(db_session, seeded, item_category_id=seeded.categories[1].client_id)
    assert result["client_id"]

    item = await db_session.get(Item, seeded.item.client_id)
    assert item.item_category_id == seeded.categories[1].client_id


async def test_c5e_find_or_create_item_directly_refuses_with_active_assignment(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _CR(db_session, seeded, row, seeded.task, seeded.item)

    ctx = ServiceContext(
        identity={
            "workspace_id": seeded.workspace.client_id,
            "user_id": seeded.manager.client_id,
            "role_name": "manager",
        },
        incoming_data={
            "article_number": seeded.item.article_number,
            "item_category_id": seeded.categories[1].client_id,
        },
        session=db_session,
    )
    with pytest.raises(ConflictError) as excinfo:
        await find_or_create_item(ctx)
    assert str(excinfo.value) == _MESSAGE
