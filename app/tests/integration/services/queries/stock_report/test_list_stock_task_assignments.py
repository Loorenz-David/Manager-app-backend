"""Plan 13 — `GET /api/v1/stock-report/items/{client_id}/assignments` (master plan
§6.5; intention §9, §9B ruling 2, §14F F10).

Assignments come from `CR`; terminal states are reached with phase 4's
`move_assignment`, never with `PR` (plan 13 §6).

This file exercises one representative case per code path; row-by-row transcription
and mutation arming belong to the tester (see the implementer handoff).
"""

import itertools
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.images.enums import (
    ImageLinkEntityTypeEnum,
    ImageSourceTypeEnum,
    ImageStorageProviderEnum,
)
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.queries.stock_report.list_stock_task_assignments import (
    list_stock_task_assignments,
)
from tests.helpers.stock_report import make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
# C4(a)'s two `created_at` values: one earlier row, and one shared value that
# leaves `client_id` as the only separator of the remaining pair.
EARLY = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
LATE = datetime(2026, 9, 21, 11, 0, 0, tzinfo=timezone.utc)
CRITERIA = {"wood_group": ["teak"]}

ASSIGNMENT_KEYS = {
    "client_id",
    "state",
    "stock_report_item_id",
    "task_id",
    "item_id",
    "quantity",
    "property_mismatch_overridden",
    "credited_history_record_id",
    "created_at",
    "created_by_id",
    "updated_at",
    "updated_by_id",
    "item",
    "task",
}
ITEM_KEYS = {
    "client_id",
    "article_number",
    "sku",
    "quantity",
    "item_category_snapshot",
    "item_major_category_snapshot",
    "item_images",
}
# `serialize_image_light`'s shape (`bm/domain/images/serializers.py:49`) — the
# element type C4(b) names for `item_images`.
IMAGE_LIGHT_KEYS = {
    "client_id",
    "image_url",
    "width_px",
    "height_px",
    "file_size_bytes",
}
TASK_KEYS = {
    "client_id",
    "task_type",
    "priority",
    "state",
    "title",
    "return_source",
    "ready_by_at",
    "return_method",
    "created_at",
    "updated_at",
    "closed_at",
    "completed_at",
}

_scalar_ids = itertools.count(2)


async def _make_row(session, seeded, *, criteria=None):
    criteria = CRITERIA if criteria is None else criteria
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    session.add(row)
    await session.flush()
    return row


async def _make_pair(session, seeded):
    suffix = uuid4().hex[:10]
    item = Item(
        client_id=f"itm_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        article_number=f"SR-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=seeded.categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    task = Task(
        client_id=f"tsk_sr_{suffix}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next(_scalar_ids),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    session.add_all([item, task])
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_sr_{suffix}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.flush()
    return item, task


async def _CR(session, seeded, row):
    item, task = await _make_pair(session, seeded)
    ctx = make_ctx(
        session,
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
    return result["stock_task_assignments"][0]


async def _move(session, seeded, assignment_id, target):
    assignment = (
        await session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == assignment_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    await move_assignment(
        session,
        assignment,
        target,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )


async def _GA(
    session,
    seeded,
    client_id,
    *,
    user=None,
    role_name="manager",
    include_resolved=False,
):
    ctx = make_ctx(
        session,
        seeded,
        role_name=role_name,
        user=user,
        incoming_data={"client_id": client_id},
        query_params={"include_resolved": include_resolved},
    )
    return await list_stock_task_assignments(ctx)


async def test_resolved_assignments_are_hidden_by_default_and_opted_into(
    db_session,
):
    """The default list hides exact `resolved`, while the opt-in list retains every
    non-deleted state. `resolved_early` stays visible in both lists."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    a1 = (await _CR(db_session, seeded, row))["client_id"]
    a2 = (await _CR(db_session, seeded, row))["client_id"]
    a3 = (await _CR(db_session, seeded, row))["client_id"]
    a4 = (await _CR(db_session, seeded, row))["client_id"]
    await _move(db_session, seeded, a2, S.AWAITING)
    await _move(db_session, seeded, a2, S.RESOLVED)
    await _move(db_session, seeded, a4, S.RESOLVED_EARLY)
    await db_session.execute(
        text(
            "UPDATE stock_task_assignments SET is_deleted = true "
            "WHERE client_id = :client_id"
        ),
        {"client_id": a3},
    )
    await db_session.flush()

    # `client_id` is a ULID with no monotonic counter (master plan §10), so the
    # three listed ids are bound by **sorting the real ids at runtime**, never by
    # creation order, and `created_at` is then written against that sort (L-14):
    #   * `HI` — the largest `client_id` — is back-dated, so `created_at`
    #     ascending DISAGREES with `client_id` ascending. Ordering by `client_id`
    #     alone yields [LO, MID, HI] and fails here: that is what arms the
    #     `created_at` term of the row's key.
    #   * `LO` and `MID` SHARE one `created_at`, so `client_id` is the only term
    #     the contract leaves to separate them. Measured 2026-09-22: dropping
    #     that term does NOT change this result — the plan is
    #     `Sort(created_at) ← Index Scan(ix_..._stock_report_item_id)`, the
    #     back-dating above is a HOT update so the scan still feeds the sort in
    #     insertion order, and insertion order is `client_id` order because `CR`
    #     mints its ULIDs milliseconds apart. The tiebreaker is a determinism
    #     guarantee this plan absorbs; keep it asserted, but do not read a green
    #     run without it as evidence.
    # The expected list below is constructed explicitly; re-running production's
    # own ORDER BY in the test would mirror the clause instead of pinning it.
    LO, MID, HI = sorted([a1, a2, a4])
    for client_id, created_at in ((HI, EARLY), (MID, LATE), (LO, LATE)):
        await db_session.execute(
            text(
                "UPDATE stock_task_assignments SET created_at = :created_at "
                "WHERE client_id = :client_id"
            ),
            {"created_at": created_at, "client_id": client_id},
        )
    await db_session.flush()

    listed = await _GA(db_session, seeded, row.client_id)

    ids = [element["client_id"] for element in listed["stock_task_assignments"]]
    assert set(ids) == {a1, a4}
    by_id = {
        element["client_id"]: element
        for element in listed["stock_task_assignments"]
    }
    assert by_id[a4]["state"] == "resolved_early"
    assert by_id[a1]["state"] == "in_queue"

    included = await _GA(
        db_session, seeded, row.client_id, include_resolved=True
    )
    included_ids = [
        element["client_id"] for element in included["stock_task_assignments"]
    ]
    assert set(included_ids) == {a1, a2, a4}
    assert included_ids == [HI, LO, MID]
    assert {
        element["client_id"]: element["state"]
        for element in included["stock_task_assignments"]
    }[a2] == "resolved"


async def test_the_element_is_the_fourteen_key_shape_with_its_two_nested_objects(
    db_session,
):
    """C4(b): the element and both nested objects, key for key — including the
    `item_images` element type, asserted against a **linked image** so the clause
    is exercised rather than satisfied by an empty list."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    created = await _CR(db_session, seeded, row)
    image = Image(
        image_url="https://images.example/chair.jpg",
        storage_provider=ImageStorageProviderEnum.EXTERNAL,
        source_type=ImageSourceTypeEnum.EXTERNAL_URL,
        created_by_id=seeded.manager.client_id,
        width_px=800,
        height_px=600,
        file_size_bytes=12345,
    )
    db_session.add(image)
    await db_session.flush()
    db_session.add(
        ImageLink(
            image_id=image.client_id,
            entity_type=ImageLinkEntityTypeEnum.ITEM,
            entity_client_id=created["item_id"],
            display_order=0,
        )
    )
    await db_session.flush()

    listed = await _GA(db_session, seeded, row.client_id)

    element = listed["stock_task_assignments"][0]
    assert set(element) == ASSIGNMENT_KEYS
    assert set(element["item"]) == ITEM_KEYS
    assert set(element["task"]) == TASK_KEYS
    assert [set(entry) for entry in element["item"]["item_images"]] == [
        IMAGE_LIGHT_KEYS
    ]
    assert element["item"]["item_images"][0]["client_id"] == image.client_id


async def test_the_create_and_list_surfaces_return_the_same_key_set(db_session):
    """C6(a): a board renders a freshly created assignment and a reloaded one
    identically, so the two surfaces must agree on the key set."""
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    created = await _CR(db_session, seeded, row)

    listed = await _GA(db_session, seeded, row.client_id)

    element = next(
        candidate
        for candidate in listed["stock_task_assignments"]
        if candidate["client_id"] == created["client_id"]
    )
    assert set(created) == set(element)
    assert set(created["item"]) == set(element["item"])
    assert set(created["task"]) == set(element["task"])


async def test_the_row_lookup_refuses_deleted_absent_and_foreign_rows(db_session):
    """C4(d): `NotFound` each — never an empty array. The foreign row is a
    cross-workspace reference: same category name, same properties."""
    seeded = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session)
    deleted = await _make_row(db_session, seeded)
    foreign_row = await _make_row(db_session, foreign)
    await db_session.execute(
        text(
            "UPDATE stock_report_items SET is_deleted = true "
            "WHERE client_id = :client_id"
        ),
        {"client_id": deleted.client_id},
    )
    await db_session.flush()

    for client_id in (deleted.client_id, "sri_absent", foreign_row.client_id):
        with pytest.raises(NotFound):
            await _GA(db_session, seeded, client_id)


async def test_a_row_with_no_assignments_answers_an_empty_list(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)

    listed = await _GA(db_session, seeded, row.client_id)

    assert listed == {"stock_task_assignments": []}
