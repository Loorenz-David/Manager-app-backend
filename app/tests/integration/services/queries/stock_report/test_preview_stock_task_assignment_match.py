from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum as S
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.services.queries.stock_report.preview_stock_task_assignment_match import (
    preview_stock_task_assignment_match,
)
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
_UNSET = object()


async def _make_row(db_session, seeded, *, criteria=None, category=None):
    criteria = criteria or {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=(category or seeded.categories[0]).client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=10,
    )
    db_session.add(row)
    await db_session.flush()
    return row


def _entry(row, task, item, *, override=False):
    return {
        "stock_report_item_id": row if isinstance(row, str) else row.client_id,
        "task_id": task if isinstance(task, str) else task.client_id,
        "item_id": item if isinstance(item, str) else item.client_id,
        "override_property_mismatch": override,
    }


async def _preview(db_session, seeded, row, **body):
    return await preview_stock_task_assignment_match(
        make_ctx(
            db_session,
            seeded,
            role_name="worker",
            incoming_data={**body, "client_id": row.client_id},
        )
    )


def _body(seeded, *, task_id=_UNSET, article_number=_UNSET, **overrides):
    body = {
        "task_id": seeded.task.client_id if task_id is _UNSET else task_id,
        "article_number": (
            seeded.item.article_number if article_number is _UNSET else article_number
        ),
        "sku": None,
        "item_category_id": seeded.categories[0].client_id,
        "properties": dict(seeded.item.properties),
        "quantity": seeded.item.quantity,
    }
    body.update(overrides)
    return body


async def _create(db_session, seeded, row):
    result = await create_stock_task_assignments(
        make_ctx(
            db_session,
            seeded,
            role_name="worker",
            user=seeded.worker,
            incoming_data={
                "entries": [_entry(row, seeded.task, seeded.item)],
            },
        )
    )
    return await db_session.get(
        StockTaskAssignment, result["stock_task_assignments"][0]["client_id"]
    )


@pytest.mark.parametrize(
    "case, expected",
    [
        ("task_deleted", "task_not_found"),
        ("category", "category_mismatch"),
        ("not_primary", "item_not_task_primary"),
    ],
)
async def test_preview_refusal_reason_matches_create(db_session, case, expected):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    body = _body(seeded)
    if case == "task_deleted":
        seeded.task.is_deleted = True
    elif case == "category":
        seeded.item.item_category_id = seeded.categories[1].client_id
        body["item_category_id"] = seeded.categories[1].client_id
    else:
        task_item = await db_session.scalar(
            select(TaskItem).where(TaskItem.task_id == seeded.task.client_id)
        )
        task_item.role = TaskItemRoleEnum.RELATED
    await db_session.flush()

    preview_result = await _preview(db_session, seeded, row, **body)
    with pytest.raises(StockAssignmentRefused) as exc_info:
        await create_stock_task_assignments(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={"entries": [_entry(row, seeded.task, seeded.item)]},
            )
        )
    assert exc_info.value.details[0]["reason"] == expected
    assert preview_result["refusal_reason"] == expected
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_evaluator_returns_nine_results_and_first_failure(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _preview(db_session, seeded, row, **_body(seeded))
    assert [check["check"] for check in result["checks"]] == [
        "stock_report_item_not_found",
        "task_not_found",
        "item_not_found",
        "item_not_task_primary",
        "already_processed_by_scanner",
        "task_failed_or_cancelled",
        "item_already_assigned",
        "item_has_no_category",
        "category_mismatch",
    ]
    assert all(check["result"] == "pass" for check in result["checks"])
    assert set(result) == {
        "can_proceed",
        "override_required",
        "refusal_reason",
        "property_failures",
        "matched_item_client_id",
        "values_source",
        "checks",
    }
    assert result["can_proceed"] is True
    assert result["override_required"] is False
    assert result["refusal_reason"] is None
    assert result["property_failures"] == []
    assert result["matched_item_client_id"] == seeded.item.client_id
    assert result["values_source"] == "stored"
    assert (
        next(
            check
            for check in result["checks"]
            if check["check"] == "item_already_assigned"
        )["advisory"]
        is True
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_does_not_write_or_change_counters(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _preview(db_session, seeded, row, **_body(seeded))
    assert (
        await db_session.scalar(
            select(StockTaskAssignment).where(
                StockTaskAssignment.stock_report_item_id == row.client_id
            )
        )
        is None
    )
    refreshed_row = await db_session.get(StockReportItem, row.client_id)
    refreshed_task = await db_session.get(Task, seeded.task.client_id)
    assert (
        refreshed_row.quantity_in_queue,
        refreshed_row.quantity_in_progress,
        refreshed_row.quantity_awaiting,
    ) == (0, 0, 0)
    assert refreshed_task.is_stock_assignment is False
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_reports_advisory_active_assignment_without_blocking(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create(db_session, seeded, row)
    result = await _preview(db_session, seeded, row, **_body(seeded))
    check = next(
        item for item in result["checks"] if item["check"] == "item_already_assigned"
    )
    assert check == {
        "check": "item_already_assigned",
        "result": "fail",
        "advisory": True,
    }
    assert result["can_proceed"] is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_refusal_reason_includes_advisory_failure(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    await _create(db_session, seeded, row)
    result = await _preview(db_session, seeded, row, **_body(seeded))
    assert result["refusal_reason"] == "item_already_assigned"
    assert result["can_proceed"] is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    "body",
    [{"article_number": "SR-does-not-exist"}, {"article_number": None, "sku": None}],
)
async def test_preview_unresolved_identifier_is_not_found_error(db_session, body):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _preview(
        db_session,
        seeded,
        row,
        **_body(seeded, **body, properties={}, quantity=1),
    )
    assert result["matched_item_client_id"] is None
    assert result["property_failures"] == [
        {
            "key": "wood_group",
            "reason": "missing_on_item",
            "accepted_values": ["teak"],
            "item_values": [],
        }
    ]
    assert result["override_required"] is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_quantity_is_matched_from_supplied_candidate(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded, criteria={"quantity": ["4"]})
    matching = await _preview(
        db_session,
        seeded,
        row,
        **_body(seeded, article_number=None, quantity=4, properties={}),
    )
    failing = await _preview(
        db_session,
        seeded,
        row,
        **_body(seeded, article_number=None, quantity=7, properties={}),
    )
    assert matching["property_failures"] == []
    assert matching["override_required"] is False
    assert failing["property_failures"] == [
        {
            "key": "quantity",
            "reason": "value_not_accepted",
            "accepted_values": ["4"],
            "item_values": ["7"],
        }
    ]
    assert failing["override_required"] is True
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    "body",
    [{"article_number": "SR-does-not-exist"}, {"article_number": None, "sku": None}],
)
async def test_preview_unresolved_item_marks_item_checks_not_evaluated(
    db_session, body
):
    # C3(e), corrected round 2, 2026-09-21: the four ITEM-DEPENDENT checks (need a
    # persisted item to mean anything) read not_evaluated. item_has_no_category and
    # category_mismatch are NOT in this set any more -- they are computable from the
    # supplied item_category_id and must be evaluated (C3(g) pins that they are).
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _preview(db_session, seeded, row, **_body(seeded, **body))
    by_name = {check["check"]: check for check in result["checks"]}
    for name in (
        "item_not_found",
        "item_not_task_primary",
        "already_processed_by_scanner",
        "item_already_assigned",
    ):
        assert by_name[name]["result"] == "not_evaluated"
    for name in ("item_has_no_category", "category_mismatch"):
        assert by_name[name]["result"] == "pass"
    assert result["refusal_reason"] is None
    assert result["can_proceed"] is True
    assert result["values_source"] == "supplied"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_uses_stored_values_when_identifier_resolves(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _preview(
        db_session,
        seeded,
        row,
        **_body(
            seeded,
            item_category_id=seeded.categories[1].client_id,
            properties={"wood_type": "Oak"},
            quantity=7,
        ),
    )
    assert result["property_failures"] == []
    assert result["can_proceed"] is True
    assert result["matched_item_client_id"] == seeded.item.client_id
    assert result["values_source"] == "stored"
    assert (
        next(
            check for check in result["checks"] if check["check"] == "category_mismatch"
        )["result"]
        == "pass"
    )
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_failure_values_match_create_for_the_stored_item(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(
        db_session,
        seeded,
        criteria={"upholstery": ["foam"], "wood_group": ["light"]},
    )
    preview_result = await _preview(
        db_session,
        seeded,
        row,
        **_body(
            seeded,
            properties={"upholstery": "Foam", "wood_type": "Oak"},
            quantity=99,
        ),
    )

    assert preview_result["values_source"] == "stored"
    assert preview_result["property_failures"] == [
        {
            "key": "upholstery",
            "reason": "value_not_accepted",
            "accepted_values": ["foam"],
            "item_values": ["down"],
        },
        {
            "key": "wood_group",
            "reason": "value_not_accepted",
            "accepted_values": ["light"],
            "item_values": ["teak"],
        },
    ]

    with pytest.raises(StockAssignmentPropertyMismatch) as excinfo:
        await create_stock_task_assignments(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={
                    "entries": [_entry(row, seeded.task, seeded.item)],
                },
            )
        )
    assert excinfo.value.details[0]["failures"] == preview_result["property_failures"]
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize("path_case", ["absent", "deleted", "foreign"])
async def test_preview_requires_live_row_in_request_workspace(db_session, path_case):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    if path_case == "absent":
        row_id = "sri-does-not-exist"
    elif path_case == "deleted":
        row.is_deleted = True
        await db_session.flush()
        row_id = row.client_id
    else:
        foreign = await seed_stock_report_workspace(db_session)
        foreign_row = await _make_row(db_session, foreign)
        row_id = foreign_row.client_id
    with pytest.raises(NotFound):
        await preview_stock_task_assignment_match(
            make_ctx(
                db_session,
                seeded,
                role_name="worker",
                incoming_data={**_body(seeded), "client_id": row_id},
            )
        )


@pytest.mark.parametrize(
    "body",
    [
        {"quantity": None, "_remove_quantity": True},
        {"sku": "SKU-live"},
    ],
)
async def test_preview_rejects_malformed_body(db_session, body):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    incoming = _body(seeded)
    if body.pop("_remove_quantity", False):
        incoming.pop("quantity")
    else:
        incoming["sku"] = body["sku"]
    with pytest.raises(ValidationError):
        await _preview(db_session, seeded, row, **incoming)


@pytest.mark.parametrize("item_case", ["soft_deleted", "foreign"])
async def test_preview_ignores_deleted_or_foreign_candidate_item(db_session, item_case):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    if item_case == "soft_deleted":
        seeded.item.is_deleted = True
        article_number = seeded.item.article_number
    else:
        foreign = await seed_stock_report_workspace(db_session)
        article_number = foreign.item.article_number
    await db_session.flush()
    result = await _preview(
        db_session,
        seeded,
        row,
        **_body(seeded, article_number=article_number, properties={}, quantity=1),
    )
    assert result["matched_item_client_id"] is None
    assert result["property_failures"] == [
        {
            "key": "wood_group",
            "reason": "missing_on_item",
            "accepted_values": ["teak"],
            "item_values": [],
        }
    ]
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


@pytest.mark.parametrize(
    "category_override, expect_category_mismatch, expect_item_has_no_category, "
    "expect_can_proceed, expect_refusal_reason",
    [
        pytest.param("same", "pass", "pass", True, None, id="own_category"),
        pytest.param(
            "other", "fail", "pass", False, "category_mismatch", id="different_category"
        ),
    ],
)
async def test_preview_supplied_category_takes_effect_with_no_item(
    db_session,
    category_override,
    expect_category_mismatch,
    expect_item_has_no_category,
    expect_can_proceed,
    expect_refusal_reason,
):
    # C3(g), owner ruling round 2, 2026-09-21 (case (iii) withdrawn on the owner's
    # round-3 ruling): with no item resolving, the supplied item_category_id must reach
    # category_mismatch exactly as the supplied properties/quantity already reach the
    # property checks (C3(c)/C3(d)). item_category_id is REQUIRED -- every Item must have
    # a category -- so item_has_no_category cannot fail on this branch and reads pass in
    # both cases; it stays asserted to pin that it is evaluated, not skipped.
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    if category_override == "same":
        item_category_id = seeded.categories[0].client_id
    else:
        item_category_id = seeded.categories[1].client_id
    result = await _preview(
        db_session,
        seeded,
        row,
        **_body(
            seeded,
            article_number=None,
            sku=None,
            item_category_id=item_category_id,
        ),
    )
    by_name = {check["check"]: check for check in result["checks"]}
    assert by_name["category_mismatch"]["result"] == expect_category_mismatch
    assert by_name["item_has_no_category"]["result"] == expect_item_has_no_category
    assert result["can_proceed"] is expect_can_proceed
    assert result["refusal_reason"] == expect_refusal_reason
    assert result["matched_item_client_id"] is None
    assert result["values_source"] == "supplied"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_with_no_task_reports_construction_results(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    result = await _preview(db_session, seeded, row, **_body(seeded, task_id=None))
    by_name = {check["check"]: check for check in result["checks"]}
    for name in (
        "task_not_found",
        "task_failed_or_cancelled",
        "item_not_task_primary",
        "already_processed_by_scanner",
    ):
        assert by_name[name]["result"] == "pass_by_construction"
    assert all(
        check["result"] != "pass"
        for check in by_name.values()
        if check["check"]
        in {
            "task_not_found",
            "task_failed_or_cancelled",
            "item_not_task_primary",
            "already_processed_by_scanner",
        }
    )
    assert result["can_proceed"] is True
    assert result["refusal_reason"] is None
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)


async def test_preview_reports_all_real_task_failures_in_order(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    row = await _make_row(db_session, seeded)
    assignment = await _create(db_session, seeded, row)
    await move_assignment(
        db_session,
        assignment,
        S.AWAITING,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )
    await move_assignment(
        db_session,
        assignment,
        S.RESOLVED,
        workspace_id=seeded.workspace.client_id,
        actor_user_id=seeded.manager.client_id,
        now=NOW,
        trigger="test",
    )
    task_item = await db_session.scalar(
        select(TaskItem).where(TaskItem.task_id == seeded.task.client_id)
    )
    task_item.role = TaskItemRoleEnum.RELATED
    seeded.task.state = TaskStateEnum.CANCELLED
    await db_session.flush()
    result = await _preview(db_session, seeded, row, **_body(seeded))
    by_name = {check["check"]: check for check in result["checks"]}
    assert by_name["item_not_task_primary"]["result"] == "fail"
    assert by_name["already_processed_by_scanner"]["result"] == "fail"
    assert by_name["task_failed_or_cancelled"]["result"] == "fail"
    assert by_name["item_already_assigned"]["result"] == "pass"
    assert result["can_proceed"] is False
    assert result["refusal_reason"] == "item_not_task_primary"
    await assert_stock_report_clean(db_session, seeded.workspace.client_id)
