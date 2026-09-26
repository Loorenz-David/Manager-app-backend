"""Plan 13A — `process_stock_demand_deleted`, the Scanner delete webhook (master
plan §6.5/§6.6; intention §14E, §8B MC-8/MC-9, §4A MC-3/MC-4, §5A MC-1/MC-16,
§7A MC-7, §4B MC-17, §9D MC-19).

Fixture of record (plan 13A §6): rows are created through the demand service (`AD`),
assignments through `CR`, terminal states through phase 4's `move_assignment` or
phase 9's processed webhook; groups are ordered **against** their ordering key by a
procedure that reads the minted `client_id`s back first — a ULID carries no monotonic
counter, so creation order proves nothing (master plan §10). Every non-drift row ends
with `assert_stock_report_clean` and asserts the foreign workspace is untouched.
"""

from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text

from beyo_manager.config import Settings, settings
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.domain.stock_report.enums import (
    StockDemandDeletedOutcomeEnum as O,
    StockReportHistoryRecordTypeEnum,
    StockReportRepairTargetKindEnum,
    StockTaskAssignmentStateEnum as S,
)
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.stock_report import (
    LocationTrackerWebhookAuthError,
    StockDemandDeadlineExceeded,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.reset.reset_app import reset_app
from beyo_manager.services.commands.stock_report import process_stock_demand_deleted as dd_module
from beyo_manager.services.commands.stock_report._move_assignment import move_assignment
from beyo_manager.services.commands.stock_report.apply_stock_demand import (
    apply_stock_demand,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from beyo_manager.services.commands.stock_report.delete_stock_report_item import (
    delete_stock_report_item,
)
from beyo_manager.services.commands.stock_report.process_stock_demand_deleted import (
    process_stock_demand_deleted,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority import (
    set_stock_report_item_priority,
)
from beyo_manager.services.commands.stock_report.set_stock_report_item_priority_order import (
    set_stock_report_item_priority_order,
)
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)
from tests.helpers.statement_listener import (
    count_writes,
    record_statement_calls,
    record_statements,
)
from tests.helpers.stock_report import (
    active_snapshot,
    ensure_active_snapshots,
    latest_snapshot,
    snapshot_id_of,
    snapshot_positions,
    assert_stock_report_clean,
    capture_dispatch,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API_KEY = "test-stock-demand-deleted-key"
NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
DD_SITE = (
    "beyo_manager.services.commands.stock_report.process_stock_demand_deleted.dispatch"
)
CRITERIA = {"wood_group": ["teak"]}
CATEGORY = "Dining Chairs"
TIMEOUT_MS = Settings.model_fields["stock_demand_webhook_timeout_ms"].default

# The four MC-9 tables plus `stock_report_repair_records` (plan 13A §6 "zero writes").
WRITE_TABLES = {
    "stock_report_items",
    "stock_task_assignments",
    "stock_report_history_records",
    "stock_report_repair_records",
    "tasks",
}

_scalar_ids = itertools.count(100)


# ---------------------------------------------------------------------------
# Fixture kit
# ---------------------------------------------------------------------------


@dataclass
class Space:
    """The handles one workspace's seeding needs. W and W' each get one so the
    fixture kit can build the **same shape** in either workspace — C5(e)'s foreign
    control is that shape, not a bare row (review 1, S2)."""

    identity: dict
    workspace_id: str
    category_id: str
    manager_id: str


@dataclass
class Env:
    """Every id is captured as a plain string while the seed's ORM instances are
    live: `session.rollback()` expires them, and a later attribute read would attempt
    IO outside the greenlet context (the phase-12 `_seller` precedent)."""

    session: object
    identity: dict
    workspace_id: str
    foreign_workspace_id: str
    category_id: str
    manager_id: str
    item_id: str
    task_id: str
    foreign_row_id: str
    own: Space
    foreign: Space


@pytest_asyncio.fixture
async def env(db_session, monkeypatch):
    """W with the F0 seed, plus a foreign workspace W' holding the *same* identity
    shape (same category name, same properties). Every row asserts W' untouched."""
    own = await seed_stock_report_workspace(db_session)
    foreign = await seed_stock_report_workspace(db_session)
    foreign_row = StockReportItem(
        workspace_id=foreign.workspace.client_id,
        item_category_id=foreign.categories[0].client_id,
        properties=normalize_stock_criteria(CRITERIA),
        properties_signature=compute_stock_criteria_signature(CRITERIA),
        quantity_requested=10,
    )
    db_session.add(foreign_row)
    await db_session.flush()
    own_space = Space(
        identity=make_ctx(db_session, own).identity,
        workspace_id=own.workspace.client_id,
        category_id=own.categories[0].client_id,
        manager_id=own.manager.client_id,
    )
    foreign_space = Space(
        identity=make_ctx(db_session, foreign).identity,
        workspace_id=foreign.workspace.client_id,
        category_id=foreign.categories[0].client_id,
        manager_id=foreign.manager.client_id,
    )
    env = Env(
        session=db_session,
        identity=own_space.identity,
        workspace_id=own_space.workspace_id,
        foreign_workspace_id=foreign_space.workspace_id,
        category_id=own_space.category_id,
        manager_id=own_space.manager_id,
        item_id=own.item.client_id,
        task_id=own.task.client_id,
        foreign_row_id=foreign_row.client_id,
        own=own_space,
        foreign=foreign_space,
    )
    await db_session.commit()

    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", API_KEY)
    monkeypatch.setattr(
        settings, "location_tracker_webhook_workspace_id", env.workspace_id
    )

    yield env

    await db_session.rollback()
    await purge_stock_report_workspace(db_session, env.workspace_id)
    await purge_stock_report_workspace(db_session, env.foreign_workspace_id)
    await db_session.commit()


async def _assert_foreign_untouched(env: Env) -> None:
    row = (
        await env.session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == env.foreign_row_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert row.is_deleted is False
    assert row.deleted_at is None
    assert row.quantity_requested == 10
    assert (
        row.quantity_in_queue,
        row.quantity_in_progress,
        row.quantity_awaiting,
    ) == (0, 0, 0)


async def _foreign_table_counts(env: Env) -> dict:
    """The foreign workspace's row count in each of the four MC-9 tables."""
    counts = {}
    for model in (
        StockReportItem,
        StockTaskAssignment,
        StockReportHistoryRecord,
        StockReportRepairRecord,
    ):
        counts[model] = await env.session.scalar(
            select(func.count())
            .select_from(model)
            .where(model.workspace_id == env.foreign_workspace_id)
        )
    return counts


async def _settle(env: Env) -> None:
    """Close the read transaction a helper autobegan: the command refuses a session
    that is already in a transaction (X3)."""
    await env.session.commit()


def _entry(index, properties_raw, *, quantity=10, category=CATEGORY):
    return DemandEntry(
        index=index,
        item_category_raw=category,
        properties_raw=properties_raw,
        properties_normalized=normalize_stock_criteria(properties_raw),
        properties_signature=compute_stock_criteria_signature(properties_raw),
        quantity_requested=quantity,
    )


def _space(env: Env, space: Space | None) -> Space:
    return env.own if space is None else space


async def _AD(env: Env, entries, *, space: Space | None = None):
    """The demand service — the fixture's row constructor (plan 13A §6)."""
    return await apply_stock_demand(
        env.session,
        workspace_id=_space(env, space).workspace_id,
        entries=entries,
        now=NOW,
        deadline=time.monotonic() + 60,
        timeout_ms=TIMEOUT_MS,
    )


async def _make_row(
    env: Env, properties_raw=None, *, quantity_requested=10, space: Space | None = None
):
    properties_raw = CRITERIA if properties_raw is None else properties_raw
    result = await _AD(
        env, [_entry(0, properties_raw, quantity=quantity_requested)], space=space
    )
    assert result.events, "AD created no row"
    return result.events[0].client_id


def _dd_body(entries) -> bytes:
    return json.dumps(entries).encode("utf-8")


def _identity_entry(properties_raw=None, *, category=CATEGORY, **extra):
    properties_raw = CRITERIA if properties_raw is None else properties_raw
    return {"itemCategory": category, "properties": properties_raw, **extra}


def _dd_ctx(env: Env, body, *, headers=None):
    return ServiceContext(
        identity={},
        incoming_data={
            "raw_body": body,
            "headers": {"x-api-key": API_KEY} if headers is None else headers,
        },
        session=env.session,
        now=NOW,
    )


async def _DD(env: Env, entries, *, monkeypatch=None, headers=None, body=None):
    captured = (
        capture_dispatch(monkeypatch, DD_SITE) if monkeypatch is not None else None
    )
    body = _dd_body(entries) if body is None else body
    result = await process_stock_demand_deleted(_dd_ctx(env, body, headers=headers))
    return result, captured


async def _make_pair(env: Env, *, quantity, wood_type="Teak", space: Space | None = None):
    """One more (item, task) pair shaped like F0's — a task holds one active PRIMARY
    item and an item holds one active assignment (master plan §6.1b)."""
    target = _space(env, space)
    suffix = uuid4().hex[:10]
    item = Item(
        client_id=f"itm_sr_{suffix}",
        workspace_id=target.workspace_id,
        article_number=f"SR-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=quantity,
        item_category_id=target.category_id,
        properties={"wood_type": wood_type, "upholstery": "Down"},
    )
    task = Task(
        client_id=f"tsk_sr_{suffix}",
        workspace_id=target.workspace_id,
        task_scalar_id=next(_scalar_ids),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=target.manager_id,
    )
    env.session.add_all([item, task])
    await env.session.flush()
    env.session.add(
        TaskItem(
            client_id=f"tim_sr_{suffix}",
            workspace_id=target.workspace_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=target.manager_id,
        )
    )
    await env.session.flush()
    await env.session.commit()
    return item, task


async def _CR(env: Env, row_id, item, task, *, space: Space | None = None):
    ctx = ServiceContext(
        identity={**_space(env, space).identity, "role_name": "worker"},
        session=env.session,
        now=NOW,
        incoming_data={
            "entries": [
                {
                    "stock_report_item_id": row_id,
                    "task_id": task.client_id,
                    "item_id": item.client_id,
                    "override_property_mismatch": False,
                }
            ]
        },
    )
    result = await create_stock_task_assignments(ctx)
    await env.session.commit()
    return result["stock_task_assignments"][0]["client_id"]


async def _fresh_assignment(session, client_id):
    return (
        await session.execute(
            select(StockTaskAssignment)
            .where(StockTaskAssignment.client_id == client_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _move(env: Env, assignment_id, target, *, space: Space | None = None):
    where = _space(env, space)
    assignment = await _fresh_assignment(env.session, assignment_id)
    await move_assignment(
        env.session,
        assignment,
        target,
        workspace_id=where.workspace_id,
        actor_user_id=where.manager_id,
        now=NOW,
        trigger="test",
    )
    await env.session.commit()


async def _assignment_on(
    env: Env,
    row_id,
    *,
    quantity,
    state=None,
    wood_type="Teak",
    space: Space | None = None,
):
    item, task = await _make_pair(
        env, quantity=quantity, wood_type=wood_type, space=space
    )
    assignment_id = await _CR(env, row_id, item, task, space=space)
    if state is not None and state is not S.IN_QUEUE:
        if state is S.RESOLVED:
            await _move(env, assignment_id, S.AWAITING, space=space)
        await _move(env, assignment_id, state, space=space)
    return assignment_id, item, task


async def _fresh_row(session, row_id):
    return (
        await session.execute(
            select(StockReportItem)
            .where(StockReportItem.client_id == row_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _counters(session, row_id):
    return (
        await session.execute(
            select(
                StockReportItem.quantity_in_queue,
                StockReportItem.quantity_in_progress,
                StockReportItem.quantity_awaiting,
            ).where(StockReportItem.client_id == row_id)
        )
    ).one()


async def _orders(session, workspace_id):
    """`row_id -> priority_order` over the live rows' **active snapshots**."""
    return {
        row_id: order
        for row_id, (_priority, order) in (
            await snapshot_positions(session, workspace_id)
        ).items()
    }


async def _goal_record(session, row_id):
    """The **goal** record, i.e. the `quantity_requested_change` one — a row that has
    been through the phase-12 priority commands also carries `priority_change` and
    `priority_order_change` history records (§6.2)."""
    return (
        await session.execute(
            select(StockReportHistoryRecord)
            .where(
                StockReportHistoryRecord.stock_report_item_id == row_id,
                StockReportHistoryRecord.type
                == StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _goal_awaiting(session, row_id):
    return (await _goal_record(session, row_id)).quantity_awaiting


async def _history_records(session, row_id):
    """**Every** history record of the row, keyed by `client_id` — not just the goal
    one. C3(a) promises "every history record … soft-deleted with NULL author", and a
    row that has been through the phase-12 priority commands carries three kinds
    (review 1, S1)."""
    return {
        record.client_id: record
        for record in (
            await session.execute(
                select(StockReportHistoryRecord)
                .where(StockReportHistoryRecord.stock_report_item_id == row_id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    }


async def _seed_group(env: Env, ordered_ids, priority="high", *, space: Space | None = None):
    """Produce a group whose ascending `priority_order` **disagrees** with ascending
    `client_id`, by a procedure and never by assumption (plan 13A §6; L-14).

    `ordered_ids` is the wanted arrangement, position 1 first. The rows are put in
    the group with `set_stock_report_item_priority` (which appends) and then moved
    into place with `set_stock_report_item_priority_order` — both phase-12 commands,
    so the seed runs through shipped code. The disagreement is asserted here, before
    the act under test.
    """
    where = _space(env, space)
    identity = where.identity
    # Positions live on the active item snapshot (2026-09-26): every live row of
    # the space gets one first, through the shipped version command.
    await ensure_active_snapshots(env.session, where.workspace_id, now=NOW)
    await env.session.commit()
    for client_id in ordered_ids:
        await set_stock_report_item_priority(
            ServiceContext(
                identity=identity,
                incoming_data={"client_id": client_id, "priority": priority},
                session=env.session,
                now=NOW,
            )
        )
        await env.session.commit()
    for position, client_id in enumerate(ordered_ids, start=1):
        await set_stock_report_item_priority_order(
            ServiceContext(
                identity=identity,
                incoming_data={"client_id": client_id, "priority_order": position},
                session=env.session,
                now=NOW,
            )
        )
        await env.session.commit()

    orders = await _orders(env.session, where.workspace_id)
    placed = [client_id for client_id in ordered_ids]
    assert [orders[client_id] for client_id in placed] == list(
        range(1, len(placed) + 1)
    )
    assert placed != sorted(placed), (
        "the seeded order agrees with ascending client_id, so a gap close that "
        "renumbered by client_id could not be told from a correct one"
    )
    await _settle(env)


def _group_arrangement(fixed, fillers):
    """Place the `fillers` around the rows whose positions the criterion fixes, so
    that position 1 holds the group's **largest** `client_id` — the disagreement the
    fixture needs (plan 13's `_seed_high_group` precedent)."""
    remaining = sorted(fillers, reverse=True)
    arrangement = []
    for slot in fixed:
        arrangement.append(remaining.pop(0) if slot is None else slot)
    return arrangement


# ---------------------------------------------------------------------------
# C1 — authentication and the body (the rows whose outcome needs a live row)
# ---------------------------------------------------------------------------


async def test_c1a_a_missing_api_key_is_401_and_writes_nothing(env):
    """C1(a): no `x-api-key`, valid body naming R."""
    row_id = await _make_row(env)

    async with record_statements(env.session) as statements:
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await _DD(env, [_identity_entry()], headers={})
    assert str(excinfo.value) == "Unauthorized."
    assert excinfo.value.http_status == 401
    assert count_writes(statements, WRITE_TABLES) == 0

    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c1b_a_wrong_api_key_is_401_and_writes_nothing(env):
    """C1(b): the same refusal on the wrong-key path — a different branch of the
    verifier than C1(a)'s missing header (master plan §9 rule 8)."""
    row_id = await _make_row(env)

    async with record_statements(env.session) as statements:
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await _DD(env, [_identity_entry()], headers={"x-api-key": "wrong"})
    assert str(excinfo.value) == "Unauthorized."
    assert count_writes(statements, WRITE_TABLES) == 0

    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c1c_a_wrong_key_with_an_unparseable_body_is_401_not_422(env):
    """C1(c): MC-8's order — verification happens before parsing, so a request that
    is wrong in both ways answers 401."""
    await _make_row(env)

    with pytest.raises(LocationTrackerWebhookAuthError):
        await _DD(env, None, body=b"not json", headers={"x-api-key": "wrong"})

    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c1i_an_unknown_quantity_requested_key_is_ignored(env):
    """C1(i): `quantityRequested` is an unknown key here — ignored, never validated
    (§14E E2/U7; Scanner v2 §4A.1 "sent anyway, it is ignored")."""
    row_id = await _make_row(env)

    result, _ = await _DD(env, [_identity_entry(quantityRequested=5)])

    assert result == {
        "results": [
            {
                "itemCategory": CATEGORY,
                "properties": CRITERIA,
                "outcome": O.DELETED.value,
            }
        ]
    }
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c1j_two_entries_of_one_identity_are_422_and_delete_nothing(env):
    """C1(j): the duplicate rule runs on the **normalized** signature, so two
    differently spelled property lists collide; nothing is deleted."""
    row_id = await _make_row(env)

    with pytest.raises(ValidationError) as excinfo:
        await _DD(
            env,
            [
                _identity_entry({"wood_group": ["Teak", "Dark"]}),
                _identity_entry({"wood_group": ["dark", "teak"]}),
            ],
        )
    assert "entries 0 and 1" in str(excinfo.value)
    assert excinfo.value.http_status == 422

    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c1k_every_offending_entry_is_named_and_the_good_one_is_not_applied(env):
    """C1(k): entries 0 and 2 are malformed, entry 1 names R. The request is atomic:
    both defects are named and R is still live."""
    row_id = await _make_row(env)

    with pytest.raises(ValidationError) as excinfo:
        await _DD(
            env,
            [
                {"itemCategory": "", "properties": CRITERIA},
                _identity_entry(),
                {"itemCategory": CATEGORY, "properties": "not an object"},
            ],
        )
    message = str(excinfo.value)
    assert "entry 0" in message
    assert "entry 2" in message

    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C2 — find the row with the find-or-create engine
# ---------------------------------------------------------------------------


async def test_c2a_an_exact_identity_is_deleted(env):
    """C2(a): the positive control of C2 — the outcome enum observed carrying its
    positive value, and the row actually gone (L-26)."""
    row_id = await _make_row(env)

    result, _ = await _DD(env, [_identity_entry()])

    assert [entry["outcome"] for entry in result["results"]] == [O.DELETED.value]
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2b_a_case_variant_category_resolves_and_deletes(env):
    """C2(b): MC-8's unique case-insensitive fallback (U6)."""
    row_id = await _make_row(env)

    result, _ = await _DD(env, [_identity_entry(category="dining chairs")])

    assert [entry["outcome"] for entry in result["results"]] == [O.DELETED.value]
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2c_an_ambiguous_case_insensitive_match_resolves_to_nothing(env):
    """C2(c): two categories differing only in case make the fallback ambiguous, and
    an ambiguous category resolves to nothing rather than to whichever row the SELECT
    returned first (MC-8 C14, §14E E7)."""
    row_id = await _make_row(env)
    env.session.add(
        ItemCategory(
            workspace_id=env.workspace_id,
            name="dining chairs",
            major_category=ItemMajorCategoryEnum.SEAT,
        )
    )
    await env.session.flush()
    await _settle(env)

    result, _ = await _DD(env, [_identity_entry(category="DINING CHAIRS")])

    assert [entry["outcome"] for entry in result["results"]] == [
        O.CATEGORY_NOT_FOUND.value
    ]
    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2d_an_unknown_category_does_not_stop_the_other_entries(env):
    """C2(d): §14E E7 — "other entries are still applied", in request order."""
    row_id = await _make_row(env)

    result, _ = await _DD(
        env,
        [
            _identity_entry(category="Serving Trolleys"),
            _identity_entry(),
        ],
    )

    assert [entry["outcome"] for entry in result["results"]] == [
        O.CATEGORY_NOT_FOUND.value,
        O.DELETED.value,
    ]
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2e_properties_are_matched_on_the_normalized_signature(env):
    """C2(e): MC-3 — `["Teak", " TEAK "]` normalizes to R's identity."""
    row_id = await _make_row(env)

    result, _ = await _DD(
        env, [_identity_entry({"wood_group": ["Teak", " TEAK "]})]
    )

    assert [entry["outcome"] for entry in result["results"]] == [O.DELETED.value]
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2f_an_identity_that_exists_only_in_a_foreign_workspace_is_not_found(
    env,
):
    """C2(f): a **cross-workspace reference** (L-16) — the foreign row carries W's own
    category id and W's signature, so the workspace filter in
    `discover_live_rows_by_identity` is the only reason the entry answers
    `not_found`. With a foreign row that also carried a foreign category id, no
    tenancy mutation could ever be observed: the identity tuple would not match.
    """
    cross_row = StockReportItem(
        workspace_id=env.foreign_workspace_id,
        item_category_id=env.category_id,  # W's category, held by W' — the reference
        properties=normalize_stock_criteria(CRITERIA),
        properties_signature=compute_stock_criteria_signature(CRITERIA),
        quantity_requested=7,
    )
    env.session.add(cross_row)
    await env.session.flush()
    cross_row_id = cross_row.client_id
    await _settle(env)

    try:
        result, _ = await _DD(env, [_identity_entry()])

        assert [entry["outcome"] for entry in result["results"]] == [O.NOT_FOUND.value]
        cross = await _fresh_row(env.session, cross_row_id)
        assert cross.is_deleted is False
        assert cross.quantity_requested == 7
        await assert_stock_report_clean(env.session, env.workspace_id)
        await _assert_foreign_untouched(env)
    finally:
        # This row is the one shape the shared purge cannot clean: it lives in W'
        # while referencing W's category, so W's `item_categories` delete would hit
        # the FK's RESTRICT (charter rule 11½ — the test owns what it committed).
        await env.session.rollback()
        await env.session.execute(
            text("DELETE FROM stock_report_items WHERE client_id = :id"),
            {"id": cross_row_id},
        )
        await env.session.commit()


async def test_c2g_an_already_deleted_row_is_not_found(env):
    """C2(g): §14E E7 — what a replay of an already-applied delete reads. The row was
    removed by the user-facing command (plan 13), not by this webhook."""
    row_id = await _make_row(env)
    await delete_stock_report_item(
        ServiceContext(
            identity=env.identity,
            incoming_data={"client_id": row_id},
            session=env.session,
            now=NOW,
        )
    )
    await _settle(env)

    result, _ = await _DD(env, [_identity_entry()])

    assert [entry["outcome"] for entry in result["results"]] == [O.NOT_FOUND.value]
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2h_an_identity_that_was_never_created_creates_nothing(env):
    """C2(h): §14E E4 "nothing is created" — this webhook finds, it never
    find-or-creates."""
    await _make_row(env)
    unknown = {"wood_group": ["dark"]}
    signature = compute_stock_criteria_signature(unknown)

    async with record_statements(env.session) as statements:
        result, captured = await _DD(
            env, [_identity_entry(unknown)], monkeypatch=None
        )
    inserts = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith("INSERT")
        and "stock_report_items" in statement
    ]
    assert inserts == []
    assert [entry["outcome"] for entry in result["results"]] == [O.NOT_FOUND.value]

    live = (
        await env.session.execute(
            select(StockReportItem.client_id).where(
                StockReportItem.workspace_id == env.workspace_id,
                StockReportItem.properties_signature == signature,
                StockReportItem.is_deleted.is_(False),
            )
        )
    ).all()
    assert live == []
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c2h_emits_no_created_event(env, monkeypatch):
    """C2(h), event half: the same entry dispatches nothing at all."""
    await _make_row(env)

    _result, captured = await _DD(
        env, [_identity_entry({"wood_group": ["dark"]})], monkeypatch=monkeypatch
    )

    assert captured == []
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C3 — the cascade, every assignment state, the group and the events
# ---------------------------------------------------------------------------


async def _seed_six_assignment_row(
    env: Env, *, space: Space | None = None, properties=None, wood_type="Teak"
):
    """C3(a)'s fixture: R in the `high` group as R2 of `A1 R2 C3`, with **six**
    assignments, one per member of the state enum (§14E E5 "any state", enumerated
    and never sampled).

    `space` builds the same shape in the foreign workspace — C5(e)'s control is this
    shape in W', not a bare row (review 1, S2). `properties` and `wood_type` only
    name W''s row: the `env` fixture already holds W''s cross-workspace reference row
    at the default identity (C2(f)), the demand service will not mint a second live
    row for an identity that already exists, and MC-12 requires each assignment's
    item to match its row's criteria.
    """
    row_id = await _make_row(env, properties, space=space)
    prefix = "oak" if properties is None else "elm"
    fillers = [
        await _make_row(env, {"wood_group": [f"{prefix}{index}"]}, space=space)
        for index in range(2)
    ]
    await _seed_group(
        env, _group_arrangement([None, row_id, None], fillers), space=space
    )

    assignments = {}
    for label, quantity, state in (
        ("A1", 2, S.AWAITING),
        ("A2", 3, S.RESOLVED),
        ("A3", 1, S.IN_QUEUE),
        ("A4", 5, S.RESOLVED_EARLY),
        ("A5", 4, S.FAILED),
        ("A6", 3, S.IN_PROGRESS),
    ):
        assignment_id, item, task = await _assignment_on(
            env,
            row_id,
            quantity=quantity,
            state=state,
            wood_type=wood_type,
            space=space,
        )
        assignments[label] = (assignment_id, item, task)
    await _settle(env)
    return row_id, fillers, assignments


async def test_c3a_every_assignment_state_is_removed_and_only_awaiting_is_uncredited(
    env,
):
    """C3(a): six assignments, one per state. All six are soft-deleted with NULL
    authorship (MC-17), only A1's awaiting credit leaves the goal, the counters end
    at zero and every task's flag clears."""
    row_id, _fillers, assignments = await _seed_six_assignment_row(env)

    assert await _counters(env.session, row_id) == (1, 3, 2)
    assert await _goal_awaiting(env.session, row_id) == 10
    history_before = await _history_records(env.session, row_id)
    # "Every X" needs a fixture with more than one X and an assertion that counts
    # them (review 1, S1). The fixture gives R **two** kinds, not the three review 1
    # named: `_seed_group` appends the rows in the wanted order, so every row is
    # already at its wanted position when `set_stock_report_item_priority_order`
    # runs and no `priority_order_change` record is written. Both kinds are asserted
    # by identity below, so the type-narrowing mutant reddens on the second one.
    assert {record.type for record in history_before.values()} == {
        StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_CHANGE,
        StockReportHistoryRecordTypeEnum.PRIORITY_CHANGE,
    }
    assert len(history_before) == 2
    assert all(record.is_deleted is False for record in history_before.values())
    stamps_before = {}
    for label, (assignment_id, _item, _task) in assignments.items():
        assignment = await _fresh_assignment(env.session, assignment_id)
        stamps_before[label] = (assignment.updated_at, assignment.updated_by_id)
    await _settle(env)

    result, _ = await _DD(env, [_identity_entry()])

    assert [entry["outcome"] for entry in result["results"]] == [O.DELETED.value]
    for label, (assignment_id, _item, task) in assignments.items():
        assignment = await _fresh_assignment(env.session, assignment_id)
        assert assignment.is_deleted is True, label
        assert assignment.deleted_at == NOW, label
        assert assignment.deleted_by_id is None, label
        # MC-17: a Scanner-caused removal records no one and touches no `updated_*`.
        assert (
            assignment.updated_at,
            assignment.updated_by_id,
        ) == stamps_before[label], label
        refreshed_task = await _fresh_task(env.session, task.client_id)
        assert refreshed_task.is_stock_assignment is False, label

    assert await _goal_awaiting(env.session, row_id) == 8
    history_after = await _history_records(env.session, row_id)
    assert set(history_after) == set(history_before)
    assert len(history_after) == len(history_before)
    for record in history_after.values():
        assert record.is_deleted is True, record.type
        assert record.deleted_at == NOW, record.type
        assert record.deleted_by_id is None, record.type

    row = await _fresh_row(env.session, row_id)
    assert row.is_deleted is True
    assert row.deleted_at == NOW
    assert row.updated_at == NOW
    assert row.deleted_by_id is None
    assert row.updated_by_id is None
    assert await _counters(env.session, row_id) == (0, 0, 0)

    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def _fresh_task(session, task_id):
    return (
        await session.execute(
            select(Task)
            .where(Task.client_id == task_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def _task_snapshot(session, task_id):
    task = await _fresh_task(session, task_id)
    steps = (
        await session.execute(
            text(
                "SELECT count(*) FROM task_steps WHERE task_id = :task_id"
            ),
            {"task_id": task_id},
        )
    ).scalar_one()
    return (
        task.state,
        task.updated_at,
        task.updated_by_id,
        task.is_deleted,
        steps,
    )


async def _item_snapshot(session, item_id):
    item = (
        await session.execute(
            select(Item)
            .where(Item.client_id == item_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    return (item.is_deleted, item.updated_at, item.item_category_id)


async def test_c3b_tasks_task_steps_and_items_are_never_touched(env, monkeypatch):
    """C3(b): §14E E5 — every recorded task and item value is byte-identical after
    the cascade, and no task event is dispatched."""
    row_id, _fillers, assignments = await _seed_six_assignment_row(env)

    before_tasks = {
        label: await _task_snapshot(env.session, task.client_id)
        for label, (_assignment_id, _item, task) in assignments.items()
    }
    before_items = {
        label: await _item_snapshot(env.session, item.client_id)
        for label, (_assignment_id, item, _task) in assignments.items()
    }
    await _settle(env)

    _result, captured = await _DD(env, [_identity_entry()], monkeypatch=monkeypatch)

    for label, (_assignment_id, item, task) in assignments.items():
        assert await _task_snapshot(env.session, task.client_id) == before_tasks[label]
        assert await _item_snapshot(env.session, item.client_id) == before_items[label]
    assert [
        event.event_name
        for event in captured
        if event.event_name.startswith("task")
    ] == []
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c3c_the_group_closes_its_gap_and_the_deleted_row_keeps_its_own_order(
    env,
):
    """C3(c): MC-7 row 10 — `high` = `A1 R2 C3` becomes `A1 C2`, and R's deleted row
    keeps `priority high`, `priority_order 2`."""
    row_id, fillers, _assignments = await _seed_six_assignment_row(env)
    arrangement = _group_arrangement([None, row_id, None], fillers)
    A, C = arrangement[0], arrangement[2]

    await _DD(env, [_identity_entry()])

    orders = await _orders(env.session, env.workspace_id)
    assert orders[A] == 1
    assert orders[C] == 2
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    # R's snapshot is closed with the row and keeps the position it held.
    deleted = await latest_snapshot(env.session, row_id)
    assert deleted.closed_at is not None
    assert deleted.priority.value == "high"
    assert deleted.priority_order == 2
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c3d_the_coalesced_event_list_is_exactly_these_events(env, monkeypatch):
    """C3(d): §14E E12 / MC-19 "Row deletion". The list is asserted as a **multiset
    with per-name counts** — the cascade emits assignment events in ascending
    `client_id`, which is not the fixture's A1…A6 order — and the six assignment
    events are asserted as a `{client_id: state}` mapping, never by list position.
    No `:updated` for R, although `remove_assignment` built three of them.
    """
    row_id, fillers, assignments = await _seed_six_assignment_row(env)
    arrangement = _group_arrangement([None, row_id, None], fillers)
    C = arrangement[2]

    _result, captured = await _DD(env, [_identity_entry()], monkeypatch=monkeypatch)

    names = [event.event_name for event in captured]
    assert sorted(names) == sorted(
        ["stock_report_item:deleted"]
        + ["stock_task_assignment:deleted"] * 6
        + ["stock_report_item_snapshot:updated"]
    )
    assert all(event.workspace_id == env.workspace_id for event in captured)

    states_by_assignment = {
        event.client_id: event.extra["state"]
        for event in captured
        if event.event_name == "stock_task_assignment:deleted"
    }
    assert states_by_assignment == {
        assignments["A1"][0]: S.AWAITING.value,
        assignments["A2"][0]: S.RESOLVED.value,
        assignments["A3"][0]: S.IN_QUEUE.value,
        assignments["A4"][0]: S.RESOLVED_EARLY.value,
        assignments["A5"][0]: S.FAILED.value,
        assignments["A6"][0]: S.IN_PROGRESS.value,
    }

    updated = [
        event
        for event in captured
        if event.event_name == "stock_report_item_snapshot:updated"
    ]
    assert [event.client_id for event in updated] == [
        await snapshot_id_of(env.session, C)
    ]
    assert updated[0].extra["stock_report_item_id"] == C
    assert updated[0].extra["priority_order"] == 2
    deleted_rows = [
        event.client_id
        for event in captured
        if event.event_name == "stock_report_item:deleted"
    ]
    assert deleted_rows == [row_id]
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c3e_a_later_demand_for_the_same_identity_creates_a_fresh_row(env):
    """C3(e): §14E E10 / MC-4 — a soft-deleted row is outside the live-identity
    predicate, so the next demand creates a **new** row rather than reviving it."""
    row_id, _fillers, _assignments = await _seed_six_assignment_row(env)
    await _DD(env, [_identity_entry()])

    result = await _AD(env, [_entry(0, CRITERIA, quantity=6)])

    assert [event.event_name for event in result.events] == [
        "stock_report_item:created"
    ]
    new_row_id = result.events[0].client_id
    assert new_row_id != row_id
    new_row = await _fresh_row(env.session, new_row_id)
    assert new_row.quantity_requested == 6
    # A fresh row has no snapshot at all until the next version is opened.
    assert await active_snapshot(env.session, new_row_id) is None
    assert (
        new_row.quantity_in_queue,
        new_row.quantity_in_progress,
        new_row.quantity_awaiting,
    ) == (0, 0, 0)
    assignments = (
        await env.session.execute(
            select(StockTaskAssignment.client_id).where(
                StockTaskAssignment.stock_report_item_id == new_row_id
            )
        )
    ).all()
    assert assignments == []
    goals = (
        await env.session.execute(
            select(
                StockReportHistoryRecord.quantity_requested,
                StockReportHistoryRecord.quantity_awaiting,
            ).where(StockReportHistoryRecord.stock_report_item_id == new_row_id)
        )
    ).all()
    assert goals == [(6, 0)]
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C4 — the replay instrument (MC-9)
# ---------------------------------------------------------------------------


async def test_c4a_a_replay_is_not_found_and_writes_nothing(env, monkeypatch):
    """C4(a): §14E E8 / MC-9 — the second delivery reads `not_found`, issues zero
    writes over the five tables and dispatches nothing."""
    row_id = await _make_row(env)
    await _DD(env, [_identity_entry()])
    assert (await _fresh_row(env.session, row_id)).is_deleted is True
    await _settle(env)

    async with record_statements(env.session) as statements:
        result, captured = await _DD(env, [_identity_entry()], monkeypatch=monkeypatch)

    assert [entry["outcome"] for entry in result["results"]] == [O.NOT_FOUND.value]
    assert count_writes(statements, WRITE_TABLES) == 0
    assert captured == []
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c4b_a_replay_after_an_inline_self_heal_leaves_the_one_record(
    env, monkeypatch
):
    """C4(b), §14E carried question (4): the first delivery self-heals a wrong
    counter while deleting (one repair record, `inline:stock_demand_deleted`, NULL
    author); the replay writes nothing and leaves **still exactly one** record."""
    row_id = await _make_row(env)
    assignment_id, _item, _task = await _assignment_on(env, row_id, quantity=1)
    await env.session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :id"
        ),
        {"id": row_id},
    )
    await _settle(env)

    result, _ = await _DD(env, [_identity_entry()])
    assert [entry["outcome"] for entry in result["results"]] == [O.DELETED.value]
    assert (await _fresh_assignment(env.session, assignment_id)).is_deleted is True

    records = (
        (
            await env.session.execute(
                select(StockReportRepairRecord).where(
                    StockReportRepairRecord.workspace_id == env.workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    record = records[0]
    assert record.target_kind is StockReportRepairTargetKindEnum.STOCK_REPORT_ITEM
    assert record.target_client_id == row_id
    assert record.field == "quantity_in_queue"
    assert record.stored_value == "0"
    assert record.recomputed_value == "0"
    assert record.trigger == "inline:stock_demand_deleted"
    assert record.created_by_id is None
    await _settle(env)

    async with record_statements(env.session) as statements:
        replay, captured = await _DD(env, [_identity_entry()], monkeypatch=monkeypatch)

    assert [entry["outcome"] for entry in replay["results"]] == [O.NOT_FOUND.value]
    assert count_writes(statements, WRITE_TABLES) == 0
    assert captured == []
    assert (
        await env.session.scalar(
            select(func.count())
            .select_from(StockReportRepairRecord)
            .where(StockReportRepairRecord.workspace_id == env.workspace_id)
        )
        == 1
    )
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C5 — several rows, several groups, the statement bound, the check, the reset
# ---------------------------------------------------------------------------


async def test_c5b_two_rows_of_one_group_each_close_their_own_gap(env, monkeypatch):
    """C5(b), §14E carried question (2): `high` = `A1 R2 C3 D4`; deleting R then C
    leaves `A1 D2`, and C's own deleted row keeps the `priority_order 2` it was
    shifted to by R's cascade before its own deletion.

    It also **measures** Q2's promise under `record_statements`: one advisory lock and
    exactly one `FOR UPDATE` per lock class whatever the number of candidate rows
    (master plan §9 rule 7, sixth authorized use).

    **Which identity is R is decided from the minted ids, never from creation order**
    (review 1, B1; the `test_c5c` pattern). The cascade loop runs ascending
    `client_id`, so "C was shifted 3 → 2 by R's cascade **before** its own deletion"
    holds only when R's id sorts first; a ULID carries no monotonic counter, so two
    `_make_row` calls decide nothing (master plan §10). R therefore takes position 2
    and C position 3 by `sorted()` over the two minted ids, the premise is asserted
    before the act, and C stays a candidate *after* another candidate in the group so
    the shift clause survives.
    """
    # Each candidate carries its own MC-12-matching wood type, because which
    # identity plays R is decided below from the ids and not from this order.
    candidates = {}
    for properties, wood_type in (
        ({"wood_group": ["teak"]}, "Teak"),
        ({"wood_group": ["light"]}, "Oak"),
    ):
        candidates[await _make_row(env, properties)] = (properties, wood_type)
    row_r, row_c = sorted(candidates)
    assert row_r < row_c, "the cascade loop must reach R before C"
    fillers = [
        await _make_row(env, {"wood_group": [f"ash{index}"]}) for index in range(2)
    ]
    arrangement = _group_arrangement([None, row_r, row_c, None], fillers)
    A, D = arrangement[0], arrangement[3]
    await _seed_group(env, arrangement)

    a_r, _item_r, _task_r = await _assignment_on(
        env, row_r, quantity=1, wood_type=candidates[row_r][1]
    )
    a_c, _item_c, _task_c = await _assignment_on(
        env, row_c, quantity=2, wood_type=candidates[row_c][1]
    )
    await _settle(env)

    async with record_statements(env.session) as statements:
        result, captured = await _DD(
            env,
            [
                _identity_entry(candidates[row_r][0]),
                _identity_entry(candidates[row_c][0]),
            ],
            monkeypatch=monkeypatch,
        )

    assert [entry["outcome"] for entry in result["results"]] == [
        O.DELETED.value,
        O.DELETED.value,
    ]
    orders = await _orders(env.session, env.workspace_id)
    assert orders[A] == 1
    assert orders[D] == 2
    assert (await latest_snapshot(env.session, row_r)).priority_order == 2
    assert (await latest_snapshot(env.session, row_c)).priority_order == 2
    assert (await _fresh_assignment(env.session, a_r)).is_deleted is True
    assert (await _fresh_assignment(env.session, a_c)).is_deleted is True

    names = [event.event_name for event in captured]
    assert sorted(names) == sorted(
        [
            "stock_report_item:deleted",
            "stock_report_item:deleted",
            "stock_task_assignment:deleted",
            "stock_task_assignment:deleted",
            "stock_report_item_snapshot:updated",
        ]
    )
    updated = [
        event
        for event in captured
        if event.event_name == "stock_report_item_snapshot:updated"
    ]
    assert [event.client_id for event in updated] == [
        await snapshot_id_of(env.session, D)
    ]
    assert updated[0].extra["priority_order"] == 2

    upper = [statement.upper() for statement in statements]
    assert sum("PG_ADVISORY_XACT_LOCK" in statement for statement in upper) == 1
    assert (
        sum(
            "FOR UPDATE" in statement and " TASKS" in statement
            for statement in upper
        )
        == 1
    )
    assert (
        sum(
            "FOR UPDATE" in statement and "STOCK_REPORT_ITEMS" in statement
            for statement in upper
        )
        == 1
    )
    assert (
        sum(
            "FOR UPDATE" in statement and "STOCK_TASK_ASSIGNMENTS" in statement
            for statement in upper
        )
        == 1
    )
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c5c_two_groups_with_a_miss_between_stay_dense_and_in_request_order(env):
    """C5(c), carried question (2) across groups: `high` = `A1 R2 C3 D4`,
    `low` = `X1 Y2`; `DD([R, <never created>, X])` answers in request order and both
    groups end dense."""
    row_r = await _make_row(env)
    row_c = await _make_row(env, {"wood_group": ["light"]})
    high_fillers = [
        await _make_row(env, {"wood_group": [f"ash{index}"]}) for index in range(2)
    ]
    high = _group_arrangement([None, row_r, row_c, None], high_fillers)
    A, D = high[0], high[3]
    await _seed_group(env, high)

    # `low` = `X1 Y2`: X must hold position 1 or its gap close is unobservable (Y
    # would end at 1 either way). Which row is X is decided **after** the ids are
    # minted, so position 1 also holds the group's larger `client_id` and the
    # disagreement `_seed_group` asserts still holds.
    low_properties = {
        await _make_row(env, properties): properties
        for properties in ({"wood_group": ["birch"]}, {"wood_group": ["cedar"]})
    }
    row_x, row_y = sorted(low_properties, reverse=True)
    await _seed_group(env, [row_x, row_y], priority="low")

    result, _ = await _DD(
        env,
        [
            _identity_entry(),
            _identity_entry({"wood_group": ["walnut"]}),
            _identity_entry(low_properties[row_x]),
        ],
    )

    assert [entry["outcome"] for entry in result["results"]] == [
        O.DELETED.value,
        O.NOT_FOUND.value,
        O.DELETED.value,
    ]
    orders = await _orders(env.session, env.workspace_id)
    assert orders[A] == 1
    assert orders[row_c] == 2
    assert orders[D] == 3
    assert orders[row_y] == 1
    assert sorted(
        order for client_id, order in orders.items() if client_id in (A, row_c, D)
    ) == [1, 2, 3]
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


@pytest.mark.parametrize("entry_count", [3, 30])
async def test_c5d_the_find_step_is_set_based_for_all_not_found(env, entry_count):
    """C5(d), carried question (3): the *all `not_found`* shape issues **exactly 5**
    statements — `set_config`, the workspace check, the advisory lock,
    `resolve_categories_for_entries`, `discover_live_rows_by_identity` — identically
    at 3 entries and at 30, and writes nothing."""
    entries = [
        _identity_entry({"wood_group": [f"never{index}"]})
        for index in range(entry_count)
    ]

    async with record_statements(env.session) as statements:
        result, _ = await _DD(env, entries)

    assert [entry["outcome"] for entry in result["results"]] == [
        O.NOT_FOUND.value
    ] * entry_count
    assert len(statements) == 5, statements
    assert count_writes(statements, WRITE_TABLES) == 0
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


@pytest.mark.parametrize("entry_count", [3, 30])
async def test_c5d_the_find_step_is_set_based_for_all_category_not_found(
    env, entry_count
):
    """C5(d), the second shape: with no entry resolving a category, discovery
    executes nothing at all and the count is **exactly 4**, again identical at 3 and
    at 30 entries."""
    entries = [
        _identity_entry({"wood_group": ["teak"]}, category=f"Unknown {index}")
        for index in range(entry_count)
    ]

    async with record_statements(env.session) as statements:
        result, _ = await _DD(env, entries)

    assert [entry["outcome"] for entry in result["results"]] == [
        O.CATEGORY_NOT_FOUND.value
    ] * entry_count
    assert len(statements) == 4, statements
    assert count_writes(statements, WRITE_TABLES) == 0
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c5e_the_consistency_check_stays_empty_in_both_workspaces(env):
    """C5(e), carried question (5): after C3(a)'s deletion the MC-20 check returns
    `[]` for W — every task flag false, the group dense, no counter divergence and
    the soft-deleted goal consistent with its kept credits — and `[]` for a foreign
    workspace holding **the same shape**, whose row is still live.

    W' is seeded with the cell's shape, not a bare row (review 1, S2): the same row
    through `AD`, the same `A1 R2 C3` group through the phase-12 commands and the
    same six assignments through `CR` plus the state moves. Only its `wood_group`
    values differ, because the `env` fixture's cross-workspace reference row (C2(f))
    already occupies the default identity in W' and `AD` mints no second live row for
    an identity that exists. Every clause below is therefore asserted against a W'
    that *could* diverge: a group whose density a leaking gap close would break,
    counters a leaking cascade would zero, six task flags a leaking recompute would
    clear, and a goal record a leaking credit would move.
    """
    row_id, _fillers, _assignments = await _seed_six_assignment_row(env)
    foreign_row_id, _foreign_fillers, foreign_assignments = (
        await _seed_six_assignment_row(
            env,
            space=env.foreign,
            properties={"wood_group": ["light"]},
            wood_type="Birch",
        )
    )
    foreign_before = {
        "counters": await _counters(env.session, foreign_row_id),
        "goal": await _goal_awaiting(env.session, foreign_row_id),
        "orders": await _orders(env.session, env.foreign_workspace_id),
    }
    await _settle(env)

    await _DD(env, [_identity_entry()])

    assert await compute_stock_report_divergences(env.session, env.workspace_id) == []
    assert (
        await compute_stock_report_divergences(env.session, env.foreign_workspace_id)
        == []
    )
    for workspace_id in (env.workspace_id, env.foreign_workspace_id):
        assert (
            await env.session.scalar(
                select(func.count())
                .select_from(StockReportRepairRecord)
                .where(StockReportRepairRecord.workspace_id == workspace_id)
            )
            == 0
        )
    goal = await _goal_record(env.session, row_id)
    assert goal.quantity_awaiting == 8

    # W' is untouched in every part of the shape, not only in its bare row.
    foreign_row = await _fresh_row(env.session, foreign_row_id)
    assert foreign_row.is_deleted is False
    assert await _counters(env.session, foreign_row_id) == foreign_before["counters"]
    assert await _goal_awaiting(env.session, foreign_row_id) == foreign_before["goal"]
    assert (
        await _orders(env.session, env.foreign_workspace_id) == foreign_before["orders"]
    )
    for label, (assignment_id, _item, task) in foreign_assignments.items():
        assert (
            await _fresh_assignment(env.session, assignment_id)
        ).is_deleted is False, label
        assert (
            await _fresh_task(env.session, task.client_id)
        ).is_stock_assignment is True, label
    for record in (await _history_records(env.session, foreign_row_id)).values():
        assert record.is_deleted is False, record.type
    await _assert_foreign_untouched(env)


async def test_c5f_the_workspace_reset_still_clears_everything(env, monkeypatch):
    """C5(f), carried question (6): after a Scanner deletion has left a soft-deleted
    row, soft-deleted assignments and history, and one repair record, `reset_app`
    returns and every stock-report table is empty for W while the foreign workspace
    is untouched."""
    row_id = await _make_row(env)
    await _assignment_on(env, row_id, quantity=1)
    await env.session.execute(
        text(
            "UPDATE stock_report_items SET quantity_in_queue = 0 WHERE client_id = :id"
        ),
        {"id": row_id},
    )
    await _settle(env)
    await _DD(env, [_identity_entry()])

    foreign_before = await _foreign_table_counts(env)
    await _settle(env)

    reset_ctx = ServiceContext(
        identity=env.identity,
        incoming_data={"delete_orphan_bootstrap_users": False},
        session=env.session,
        now=NOW,
    )
    capture_dispatch(
        monkeypatch, "beyo_manager.services.commands.reset.reset_app.dispatch"
    )
    await reset_app(reset_ctx)

    for model in (
        StockReportItem,
        StockTaskAssignment,
        StockReportHistoryRecord,
        StockReportRepairRecord,
    ):
        assert (
            await env.session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.workspace_id == env.workspace_id)
            )
            == 0
        )
    assert (
        await env.session.scalar(
            select(Workspace.client_id).where(
                Workspace.client_id == env.workspace_id
            )
        )
        is None
    )
    # "the foreign counts unchanged" — all four MC-9 tables, not just the items one
    # (review 1, N3). Three of the four are 0 in this fixture: the foreign workspace
    # holds one bare row and nothing else, so `stock_report_items` (1 → 1) is the
    # only count here that could move.
    assert await _foreign_table_counts(env) == foreign_before
    assert foreign_before[StockReportItem] == 1
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C6 — the MC-9 limits and the deadline
# ---------------------------------------------------------------------------


async def test_c6a_the_first_statement_sets_both_limits_from_the_default(env):
    """C6(a): §14E E9 / MC-9 (i) — `set_config` is the **first** statement of the
    request and carries the configured default in both parameters (charter rule 13:
    the default is read from the field, never typed)."""
    await _make_row(env)

    async with record_statement_calls(env.session) as calls:
        await _DD(env, [_identity_entry()])

    statement, parameters = calls[0]
    assert "set_config" in statement
    assert "statement_timeout" in statement
    assert "lock_timeout" in statement
    assert list(parameters) == [str(TIMEOUT_MS), str(TIMEOUT_MS)]
    # §6's standing close, which this row was missing (review 1, N2).
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


async def test_c6b_the_deadline_is_checked_before_the_commit(env, monkeypatch):
    """C6(b): §14E E9 (P39) / MC-9 (iii) — the deadline check is the last action
    inside the transaction, so nothing is committed when it fires."""
    row_id = await _make_row(env)
    assignment_id, _item, _task = await _assignment_on(env, row_id, quantity=1)
    await _settle(env)

    clock = iter([0.0, 10.0**9])
    monkeypatch.setattr(
        dd_module, "time", SimpleNamespace(monotonic=lambda: next(clock))
    )

    with pytest.raises(StockDemandDeadlineExceeded) as excinfo:
        await _DD(env, [_identity_entry()])
    assert excinfo.value.http_status == 503

    assert (await _fresh_row(env.session, row_id)).is_deleted is False
    assert (await _fresh_assignment(env.session, assignment_id)).is_deleted is False
    assert (
        await env.session.scalar(
            select(func.count())
            .select_from(StockReportRepairRecord)
            .where(StockReportRepairRecord.workspace_id == env.workspace_id)
        )
        == 0
    )
    # §6's standing close, which this row was missing (review 1, N2).
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)


# ---------------------------------------------------------------------------
# C7 — the response envelope
# ---------------------------------------------------------------------------


async def test_c7b_every_result_echoes_the_entry_byte_for_byte(env):
    """C7(b): §14E E7 / Scanner v2 §4A.3 — `itemCategory` and `properties` come back
    exactly as received, never normalized and never replaced by the resolved
    category's own name."""
    await _make_row(env)
    sent_properties = {"wood_group": ["Teak", " TEAK "]}

    result, _ = await _DD(
        env,
        [
            _identity_entry(sent_properties, category="dining chairs"),
            _identity_entry(category="Serving Trolleys"),
            _identity_entry({"wood_group": ["dark"]}),
        ],
    )

    assert result["results"] == [
        {
            "itemCategory": "dining chairs",
            "properties": {"wood_group": ["Teak", " TEAK "]},
            "outcome": O.DELETED.value,
        },
        {
            "itemCategory": "Serving Trolleys",
            "properties": CRITERIA,
            "outcome": O.CATEGORY_NOT_FOUND.value,
        },
        {
            "itemCategory": CATEGORY,
            "properties": {"wood_group": ["dark"]},
            "outcome": O.NOT_FOUND.value,
        },
    ]
    for entry in result["results"]:
        assert set(entry) == {"itemCategory", "properties", "outcome"}
    await assert_stock_report_clean(env.session, env.workspace_id)
    await _assert_foreign_untouched(env)
