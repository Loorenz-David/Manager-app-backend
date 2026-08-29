"""Integration criteria for the phase-2 item-aware typical-times statement."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from beyo_manager.domain.item_economics.budget_division import TYPICAL_MIN_SAMPLE_SIZE
from beyo_manager.domain.item_economics.typical_filters import TypicalFilterSpec
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    get_working_section_typical_times,
    typical_times_statement,
)
from tests.integration.services.queries.working_sections._narrowing_seed import collect_measurement_matrix


NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)


@dataclass
class _Seed:
    workspace: Workspace
    user: User
    section: WorkingSection


async def _seed_base(db_session, *, sections: int = 1) -> tuple[_Seed, list[WorkingSection]]:
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_narrow_{token}", name=f"Narrow {token}")
    user = User(
        client_id=f"usr_narrow_{token}",
        username=f"narrow_{token}",
        email=f"narrow_{token}@example.com",
        password="secret",
    )
    working_sections = [
        WorkingSection(
            client_id=f"wsec_narrow_{token}_{index}",
            workspace_id=workspace.client_id,
            name=f"Narrow {token} {index}",
            is_deleted=index == sections - 1 and sections > 1,
        )
        for index in range(sections)
    ]
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all(working_sections)
    await db_session.flush()
    return _Seed(workspace, user, working_sections[0]), working_sections


async def _category(db_session, seed: _Seed, suffix: str, major: ItemMajorCategoryEnum) -> ItemCategory:
    category = ItemCategory(
        client_id=f"itc_{seed.workspace.client_id}_{suffix}",
        workspace_id=seed.workspace.client_id,
        name=f"Category {suffix} {seed.workspace.client_id}",
        major_category=major,
        created_by_id=seed.user.client_id,
    )
    db_session.add(category)
    await db_session.flush()
    return category


async def _item(
    db_session,
    seed: _Seed,
    suffix: str,
    *,
    category: ItemCategory | None = None,
    designer: str | None = None,
    width: int | None = 70,
    height: int | None = 70,
    depth: int | None = 70,
    upholstery: bool = True,
    deleted: bool = False,
    properties_signature: str | None = None,
) -> Item:
    item = Item(
        client_id=f"itm_{seed.workspace.client_id}_{suffix}",
        workspace_id=seed.workspace.client_id,
        item_category_id=category.client_id if category else None,
        state=ItemStateEnum.READY,
        designer=designer,
        width_in_cm=width,
        height_in_cm=height,
        depth_in_cm=depth,
        can_have_upholstery=upholstery,
        is_deleted=deleted,
        properties_signature=properties_signature,
        created_by_id=seed.user.client_id,
    )
    db_session.add(item)
    await db_session.flush()
    return item


async def _task(
    db_session,
    seed: _Seed,
    suffix: str,
    *,
    seconds: int = 100,
    section: WorkingSection | None = None,
    primary: Item | None = None,
    related: list[Item] | None = None,
    removed_primary: Item | None = None,
    step_count: int = 1,
    step_state: TaskStepStateEnum = TaskStepStateEnum.COMPLETED,
    step_deleted: bool = False,
    step_marked_wrong: bool = False,
    closed_at: datetime | None = NOW - timedelta(days=1),
) -> Task:
    section = section or seed.section
    task = Task(
        client_id=f"tsk_{seed.workspace.client_id}_{suffix}",
        workspace_id=seed.workspace.client_id,
        task_scalar_id=abs(hash(suffix)) % 1000000,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=seed.user.client_id,
    )
    db_session.add(task)
    await db_session.flush()
    if primary is not None:
        db_session.add(
            TaskItem(
                client_id=f"tim_{seed.workspace.client_id}_{suffix}_primary",
                workspace_id=seed.workspace.client_id,
                task_id=task.client_id,
                item_id=primary.client_id,
                role=TaskItemRoleEnum.PRIMARY,
                created_by_id=seed.user.client_id,
            )
        )
    if removed_primary is not None:
        db_session.add(
            TaskItem(
                client_id=f"tim_{seed.workspace.client_id}_{suffix}_removed",
                workspace_id=seed.workspace.client_id,
                task_id=task.client_id,
                item_id=removed_primary.client_id,
                role=TaskItemRoleEnum.PRIMARY,
                removed_at=NOW - timedelta(days=1),
                created_by_id=seed.user.client_id,
            )
        )
    for index, item in enumerate(related or []):
        db_session.add(
            TaskItem(
                client_id=f"tim_{seed.workspace.client_id}_{suffix}_related_{index}",
                workspace_id=seed.workspace.client_id,
                task_id=task.client_id,
                item_id=item.client_id,
                role=TaskItemRoleEnum.RELATED,
                created_by_id=seed.user.client_id,
            )
        )
    await db_session.flush()
    db_session.add_all(
        [
            TaskStep(
                client_id=f"tsp_{seed.workspace.client_id}_{suffix}_{index}",
                workspace_id=seed.workspace.client_id,
                task_id=task.client_id,
                working_section_id=section.client_id,
                working_section_name_snapshot=section.name,
                state=step_state,
                readiness_status=TaskStepReadinessStatusEnum.READY,
                total_dependencies=0,
                completed_dependencies=0,
                total_working_seconds=seconds,
                recorded_time_marked_wrong=step_marked_wrong,
                is_deleted=step_deleted,
                closed_at=closed_at,
                created_by_id=seed.user.client_id,
            )
            for index in range(step_count)
        ]
    )
    await db_session.flush()
    return task


def _rows(result):
    return list(result)


@pytest.mark.integration
async def test_k_shape_is_keyed_by_spec_count_and_non_narrowing_k1_is_seven_columns(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "chair", ItemMajorCategoryEnum.SEAT)
    item = await _item(db_session, seed, "chair", category=chair)
    for index, seconds in enumerate([10, 20, 30, 40, 50]):
        await _task(db_session, seed, f"one-{index}", primary=item, seconds=seconds)

    no_specs = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))).all())
    empty_spec = _rows(
        (await db_session.execute(
            typical_times_statement(seed.workspace.client_id, specs=(TypicalFilterSpec(),), now=NOW)
        )).all()
    )
    narrowing = _rows(
        (await db_session.execute(
            typical_times_statement(
                seed.workspace.client_id,
                specs=(TypicalFilterSpec(item_category_ids=frozenset({chair.client_id})),),
                now=NOW,
            )
        )).all()
    )

    assert no_specs[0]._fields == (
        "client_id", "name", "sample_count", "typical_worker_seconds",
        "typical_unit_worker_seconds",
    )
    assert empty_spec[0]._fields == (
        "client_id", "name", "spec_index", "narrowed_sample_count", "narrowed_typical_worker_seconds",
        "narrowed_typical_unit_worker_seconds",
        "section_sample_count", "section_typical_worker_seconds",
        "section_typical_unit_worker_seconds",
        "properties_sample_count", "properties_typical_worker_seconds",
        "properties_typical_unit_worker_seconds",
    )
    assert narrowing[0]._fields == empty_spec[0]._fields
    assert (empty_spec[0].narrowed_sample_count, empty_spec[0].section_sample_count) == (5, 5)
    assert empty_spec[0].narrowed_typical_worker_seconds == 30
    assert empty_spec[0].section_typical_worker_seconds == 30
    # Quantity-one seeds: the per-unit twins agree with the raw medians.
    assert float(empty_spec[0].narrowed_typical_unit_worker_seconds) == 30.0
    assert float(empty_spec[0].section_typical_unit_worker_seconds) == 30.0
    assert float(no_specs[0].typical_unit_worker_seconds) == 30.0


@pytest.mark.integration
async def test_cardinality_is_section_cross_spec_total_and_history_less_sections_are_materialized(db_session):
    seed, sections = await _seed_base(db_session, sections=4)
    sections[3].is_deleted = True
    await db_session.flush()
    chair = await _category(db_session, seed, "card", ItemMajorCategoryEnum.SEAT)
    item = await _item(db_session, seed, "card", category=chair)
    for index in range(1):
        await _task(db_session, seed, f"card_{index}", section=sections[index], primary=item)

    specs = (
        TypicalFilterSpec(item_category_ids=frozenset({chair.client_id})),
        TypicalFilterSpec(designers=frozenset({"Aalto"})),
    )
    rows = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW))).all())

    assert len(rows) == 6
    assert {(row.client_id, row.spec_index) for row in rows} == {
        (sections[index].client_id, spec_index) for index in range(3) for spec_index in range(2)
    }
    empty_rows = [row for row in rows if row.client_id in {sections[1].client_id, sections[2].client_id}]
    assert all(row.narrowed_sample_count == 0 and row.section_sample_count == 0 for row in empty_rows)
    assert all(row.narrowed_typical_worker_seconds is None and row.section_typical_worker_seconds is None for row in empty_rows)


@pytest.mark.integration
async def test_spec_index_preserves_input_order_and_section_population_is_constant(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "order-chair", ItemMajorCategoryEnum.SEAT)
    table = await _category(db_session, seed, "order-table", ItemMajorCategoryEnum.WOOD)
    chair_item = await _item(db_session, seed, "order-chair", category=chair)
    table_item = await _item(db_session, seed, "order-table", category=table)
    for index in range(6):
        await _task(db_session, seed, f"chair_{index}", primary=chair_item, seconds=10 + index * 7)
    for index in range(2):
        await _task(db_session, seed, f"table_{index}", primary=table_item, seconds=52 + index * 7)
    for index in range(12):
        await _task(db_session, seed, f"other_{index}", seconds=66 + index * 7)
    await _task(db_session, seed, "wrong", seconds=200, step_marked_wrong=True)
    await _task(db_session, seed, "deleted", seconds=201, step_deleted=True)
    await _task(db_session, seed, "pending", seconds=202, step_state=TaskStepStateEnum.PENDING)
    await _task(db_session, seed, "outside-window", seconds=203, closed_at=NOW - timedelta(days=91))

    specs = (
        TypicalFilterSpec(item_category_ids=frozenset({chair.client_id})),
        TypicalFilterSpec(item_category_ids=frozenset({table.client_id})),
    )
    rows = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW))).all())
    by_index = {row.spec_index: row for row in rows}
    base = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))).all())[0]
    assert set(by_index) == {0, 1}
    assert by_index[0].narrowed_sample_count == 6
    assert by_index[1].narrowed_sample_count == 2
    assert all(row.section_sample_count == 20 for row in rows)
    assert all(row.section_typical_worker_seconds == 76 for row in rows)
    assert base.sample_count == 20
    assert base.typical_worker_seconds == 76
    assert all(row.section_sample_count == base.sample_count for row in rows)


@pytest.mark.integration
async def test_each_spec_index_selects_its_own_narrowed_typical(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "value-chair", ItemMajorCategoryEnum.SEAT)
    table = await _category(db_session, seed, "value-table", ItemMajorCategoryEnum.WOOD)
    chair_item = await _item(db_session, seed, "value-chair", category=chair)
    table_item = await _item(db_session, seed, "value-table", category=table)
    for index, seconds in enumerate([10, 20, 30, 40, 50]):
        await _task(db_session, seed, f"value-chair-{index}", primary=chair_item, seconds=seconds)
    for index, seconds in enumerate([60, 70, 80, 90, 100]):
        await _task(db_session, seed, f"value-table-{index}", primary=table_item, seconds=seconds)

    specs = (
        TypicalFilterSpec(item_category_ids=frozenset({chair.client_id})),
        TypicalFilterSpec(item_category_ids=frozenset({table.client_id})),
    )
    rows = {
        row.spec_index: row
        for row in _rows((await db_session.execute(
            typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW)
        )).all())
    }

    assert rows[0].narrowed_sample_count == 5
    assert rows[1].narrowed_sample_count == 5
    assert rows[0].narrowed_typical_worker_seconds == 30
    assert rows[1].narrowed_typical_worker_seconds == 80


@pytest.mark.integration
async def test_narrowed_threshold_uses_its_own_count(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "threshold", ItemMajorCategoryEnum.SEAT)
    item = await _item(db_session, seed, "threshold", category=chair)
    plain = await _item(db_session, seed, "threshold-plain", category=None)
    for index in range(70):
        await _task(db_session, seed, f"threshold_{index}", primary=item if index < 2 else plain, seconds=100 + index)

    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id}))
    row = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())[0]
    assert row.narrowed_sample_count == 2
    assert row.narrowed_typical_worker_seconds is None
    assert isinstance(row.section_typical_worker_seconds, int)


@pytest.mark.integration
@pytest.mark.parametrize("narrowed_count, expected_typical", [(TYPICAL_MIN_SAMPLE_SIZE, "present"), (TYPICAL_MIN_SAMPLE_SIZE - 1, "absent")])
async def test_narrowed_threshold_includes_exact_floor_and_excludes_one_below(db_session, narrowed_count, expected_typical):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, f"floor-{narrowed_count}", ItemMajorCategoryEnum.SEAT)
    chair_item = await _item(db_session, seed, f"floor-chair-{narrowed_count}", category=chair)
    plain = await _item(db_session, seed, f"floor-plain-{narrowed_count}", category=None)
    for index in range(10):
        await _task(
            db_session,
            seed,
            f"floor-{narrowed_count}-{index}",
            primary=chair_item if index < narrowed_count else plain,
            seconds=100 + index,
        )
    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id}))
    row = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())[0]
    assert row.narrowed_sample_count == narrowed_count
    assert (row.narrowed_typical_worker_seconds is not None) is (expected_typical == "present")


@pytest.mark.integration
async def test_primary_less_tasks_stay_in_section_population_and_not_narrowed(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "primaryless", ItemMajorCategoryEnum.SEAT)
    item = await _item(db_session, seed, "primaryless", category=chair)
    for index in range(5):
        await _task(db_session, seed, f"primaryless_{index}", primary=item if index else None)
    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id}))
    rows = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())
    no_spec = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))).all())[0]
    assert rows[0].section_sample_count == 5
    assert rows[0].narrowed_sample_count == 4
    assert no_spec.sample_count == 5


@pytest.mark.integration
async def test_removed_primary_is_still_section_population_and_not_narrowed(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "removed-primaryless", ItemMajorCategoryEnum.SEAT)
    active = await _item(db_session, seed, "removed-primaryless-active", category=chair)
    removed = await _item(db_session, seed, "removed-primaryless-removed", category=chair)
    await _task(db_session, seed, "removed-primaryless-0", removed_primary=removed)
    for index in range(1, 5):
        await _task(db_session, seed, f"removed-primaryless-{index}", primary=active)

    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id}))
    rows = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())
    no_spec = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))).all())[0]
    assert rows[0].section_sample_count == 5
    assert rows[0].narrowed_sample_count == 4
    assert no_spec.sample_count == 5


@pytest.mark.integration
async def test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "fanout-chair", ItemMajorCategoryEnum.SEAT)
    wood = await _category(db_session, seed, "fanout-wood", ItemMajorCategoryEnum.WOOD)
    primary = await _item(db_session, seed, "fanout-primary", category=chair)
    secondary_a = await _item(db_session, seed, "fanout-secondary-a", category=chair)
    secondary_b = await _item(db_session, seed, "fanout-secondary-b", category=chair)
    secondary_wood = await _item(db_session, seed, "fanout-secondary-wood", category=wood)
    for index in range(5):
        await _task(db_session, seed, f"fanout_{index}", primary=primary, related=[secondary_a, secondary_b], seconds=100)
    await _task(db_session, seed, "fanout-other", primary=primary, related=[secondary_wood], seconds=100)
    specs = (
        TypicalFilterSpec(item_category_ids=frozenset({chair.client_id})),
        TypicalFilterSpec(item_category_ids=frozenset({wood.client_id})),
    )
    rows = {row.spec_index: row for row in _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW))).all())}
    assert rows[0].narrowed_sample_count == 6
    assert rows[1].narrowed_sample_count == 0


@pytest.mark.integration
async def test_removed_primary_does_not_change_group_sum_and_no_spec_is_a_control(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "removed", ItemMajorCategoryEnum.SEAT)
    active = await _item(db_session, seed, "removed-active", category=chair)
    removed = await _item(db_session, seed, "removed-old", category=chair)
    for index in range(5):
        await _task(db_session, seed, f"removed-{index}", primary=active, removed_primary=removed, seconds=100)
    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id}))
    no_spec = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))).all())[0]
    with_spec = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())[0]
    assert (no_spec.sample_count, no_spec.typical_worker_seconds) == (5, 100)
    assert (with_spec.section_sample_count, with_spec.section_typical_worker_seconds) == (5, 100)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "spec", "inside", "outside"),
    [
        ("category", "item_category_ids", "category", "other-category"),
        ("major", "major_categories", "seat", "wood"),
        ("width", "width_cm", "width-in", "width-out"),
        ("height", "height_cm", "height-in", "height-out"),
        ("depth", "depth_cm", "depth-in", "depth-out"),
        ("upholstery-false", "can_have_upholstery", "upholstery-false", "upholstery-true"),
        ("upholstery-true", "can_have_upholstery", "upholstery-true", "upholstery-false"),
        ("designer", "designers", "designer-in", "designer-out"),
        ("recorded-width", "width_cm", "recorded-width", "null-width"),
    ],
)
async def test_each_item_field_and_null_unknown_row_is_an_exact_population_count(
    db_session, field, spec, inside, outside
):
    seed, _ = await _seed_base(db_session)
    seat = await _category(db_session, seed, f"{field}-seat", ItemMajorCategoryEnum.SEAT)
    wood = await _category(db_session, seed, f"{field}-wood", ItemMajorCategoryEnum.WOOD)
    for index in range(5):
        if field == "category":
            in_item = await _item(db_session, seed, f"{inside}-{index}", category=seat)
            out_category = wood if index < 4 else None
            out_item = await _item(db_session, seed, f"{outside}-{index}", category=out_category)
            filter_spec = TypicalFilterSpec(item_category_ids=frozenset({seat.client_id}))
        elif field == "major":
            in_item = await _item(db_session, seed, f"{inside}-{index}", category=seat)
            out_item = await _item(db_session, seed, f"{outside}-{index}", category=wood)
            filter_spec = TypicalFilterSpec(major_categories=frozenset({ItemMajorCategoryEnum.SEAT}))
        elif field == "width":
            in_item = await _item(db_session, seed, f"{inside}-{index}", width=60 if index == 0 else 80)
            out_item = await _item(db_session, seed, f"{outside}-{index}", width=59 if index == 0 else 81)
            filter_spec = TypicalFilterSpec(width_cm=(60, 80))
        elif field == "height":
            in_item = await _item(db_session, seed, f"{inside}-{index}", height=70)
            out_item = await _item(db_session, seed, f"{outside}-{index}", height=None)
            filter_spec = TypicalFilterSpec(height_cm=(60, 80))
        elif field == "depth":
            in_item = await _item(db_session, seed, f"{inside}-{index}", depth=70)
            out_item = await _item(db_session, seed, f"{outside}-{index}", depth=None)
            filter_spec = TypicalFilterSpec(depth_cm=(60, 80))
        elif field.startswith("upholstery"):
            expected_upholstery = field.endswith("true")
            in_item = await _item(db_session, seed, f"{inside}-{index}", upholstery=expected_upholstery)
            out_item = await _item(db_session, seed, f"{outside}-{index}", upholstery=not expected_upholstery)
            filter_spec = TypicalFilterSpec(can_have_upholstery=expected_upholstery)
        elif field == "designer":
            in_item = await _item(db_session, seed, f"{inside}-{index}", designer="Aalto")
            out_item = await _item(db_session, seed, f"{outside}-{index}", designer=None if index == 0 else "Eames")
            filter_spec = TypicalFilterSpec(designers=frozenset({"Aalto"}))
        else:
            in_item = await _item(db_session, seed, f"{inside}-{index}", width=70)
            out_item = await _item(db_session, seed, f"{outside}-{index}", width=None)
            filter_spec = TypicalFilterSpec(width_cm=(None, None))
        await _task(db_session, seed, f"{field}-in-{index}", primary=in_item)
        await _task(db_session, seed, f"{field}-out-{index}", primary=out_item)

    if field in {"category", "major"}:
        null_item = await _item(db_session, seed, f"{field}-null", category=None)
        await _task(db_session, seed, f"{field}-null", primary=null_item)
    if field == "width":
        null_width_item = await _item(db_session, seed, f"{field}-null", width=None)
        await _task(db_session, seed, f"{field}-null", primary=null_width_item)

    row = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(filter_spec,), now=NOW))).all())[0]
    assert row.narrowed_sample_count == 5


@pytest.mark.integration
async def test_field_predicates_are_and_across_fields_and_or_within_category_collection(db_session):
    seed, _ = await _seed_base(db_session)
    chair = await _category(db_session, seed, "and-chair", ItemMajorCategoryEnum.SEAT)
    stool = await _category(db_session, seed, "and-stool", ItemMajorCategoryEnum.SEAT)
    sofa = await _category(db_session, seed, "and-sofa", ItemMajorCategoryEnum.WOOD)
    for index in range(5):
        for suffix, category, width in (("chair", chair, 70), ("stool", stool, 70), ("wide", chair, 90), ("sofa", sofa, 70)):
            item = await _item(db_session, seed, f"and-{suffix}-{index}", category=category, width=width)
            await _task(db_session, seed, f"and-{suffix}-{index}", primary=item)
    spec = TypicalFilterSpec(item_category_ids=frozenset({chair.client_id, stool.client_id}), width_cm=(60, 80))
    row = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())[0]
    assert row.narrowed_sample_count == 10


@pytest.mark.integration
async def test_zero_lower_bound_is_a_real_range_value(db_session):
    seed, _ = await _seed_base(db_session)
    for index in range(5):
        in_item = await _item(db_session, seed, f"zero-in-{index}", width=0)
        out_item = await _item(db_session, seed, f"zero-out-{index}", width=None)
        await _task(db_session, seed, f"zero-in-{index}", primary=in_item)
        await _task(db_session, seed, f"zero-out-{index}", primary=out_item)
    spec = TypicalFilterSpec(width_cm=(0, 0))
    row = _rows((await db_session.execute(typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW))).all())[0]
    assert row.narrowed_sample_count == 5


@pytest.mark.integration
async def test_item_category_join_is_emitted_exactly_when_major_category_is_needed(db_session):
    seed, _ = await _seed_base(db_session)
    no_major = (TypicalFilterSpec(item_category_ids=frozenset({"chair"})), TypicalFilterSpec(width_cm=(60, 80)))
    one_major = (TypicalFilterSpec(item_category_ids=frozenset({"chair"})), TypicalFilterSpec(major_categories=frozenset({ItemMajorCategoryEnum.SEAT})))
    both_major = (TypicalFilterSpec(major_categories=frozenset({ItemMajorCategoryEnum.SEAT})), TypicalFilterSpec(major_categories=frozenset({ItemMajorCategoryEnum.WOOD})))
    for specs, expected in ((no_major, 0), (one_major, 1), (both_major, 1)):
        sql = str(typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW).compile())
        assert sql.count("LEFT OUTER JOIN item_categories") == expected


@pytest.mark.integration
async def test_service_no_spec_payload_is_explicitly_unchanged(db_session):
    seed, _ = await _seed_base(db_session)
    for index, seconds in enumerate([600, 1000, 1200, 6000, 7000]):
        await _task(db_session, seed, f"payload-{index}", seconds=seconds)
    ctx = ServiceContext(
        identity={"workspace_id": seed.workspace.client_id, "user_id": seed.user.client_id, "role_name": "worker"},
        incoming_data={},
        query_params={},
        session=db_session,
    )
    payload = await get_working_section_typical_times(ctx)
    assert payload == {
        "typical_times": [
            {
                "working_section_id": seed.section.client_id,
                "section_name": seed.section.name,
                "typical_worker_seconds": 1200,
                "sample_count": 5,
                "method": "median_completed_section_totals",
                "window_days": 90,
                "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
            }
        ]
    }


@pytest.mark.integration
async def test_unit_medians_normalize_by_primary_quantity_and_clamp_legacy_zero(db_session):
    """Mixed historical quantities discriminate the per-unit twins from the raw medians.

    Five same-category tasks: seconds (1000, 2000, 3000, 4000, 5000) at quantities
    (1, 2, 1, 4, 0). Raw median stays 3000. Per-unit samples are
    (1000, 1000, 3000, 1000, 5000) — the zero quantity clamps to one — so the unit
    median is 1000, not 3000 and not 3000/q for any q.
    """
    seed, _ = await _seed_base(db_session)
    category = await _category(db_session, seed, "unitq", ItemMajorCategoryEnum.SEAT)
    for index, (seconds, quantity) in enumerate(
        [(1000, 1), (2000, 2), (3000, 1), (4000, 4), (5000, 0)]
    ):
        item = await _item(db_session, seed, f"unitq-{index}", category=category)
        item.quantity = quantity
        await _task(db_session, seed, f"unitq-{index}", primary=item, seconds=seconds)
    await db_session.flush()

    spec = TypicalFilterSpec(item_category_ids=frozenset({category.client_id}))
    spec_rows = (
        await db_session.execute(
            typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW)
        )
    ).all()
    row = next(r for r in spec_rows if r.client_id == seed.section.client_id)
    assert row.narrowed_sample_count == 5
    assert row.narrowed_typical_worker_seconds == 3000
    assert row.section_typical_worker_seconds == 3000
    assert float(row.narrowed_typical_unit_worker_seconds) == 1000.0
    assert float(row.section_typical_unit_worker_seconds) == 1000.0

    no_spec_rows = (
        await db_session.execute(typical_times_statement(seed.workspace.client_id, now=NOW))
    ).all()
    no_spec_row = next(r for r in no_spec_rows if r.client_id == seed.section.client_id)
    assert no_spec_row.typical_worker_seconds == 3000
    assert float(no_spec_row.typical_unit_worker_seconds) == 1000.0


@pytest.mark.integration
async def test_properties_tier_narrows_within_the_category_and_gates_on_its_own_count(db_session):
    """Same category, two signature cohorts: the properties median must discriminate.

    Signature "sig-oak" history is (100, 200, 300, 400, 500); signature "sig-teak"
    history is (1000, 1100, 1200, 1300, 1400); one legacy NULL-signature task at
    9000. The category tier pools all eleven; the properties tier for a
    "sig-oak" spec must answer 300 from exactly five samples — proving the
    NULL-signature and other-signature rows are outside the tier.
    """
    seed, _ = await _seed_base(db_session)
    category = await _category(db_session, seed, "props", ItemMajorCategoryEnum.SEAT)
    for index, seconds in enumerate([100, 200, 300, 400, 500]):
        item = await _item(db_session, seed, f"props-oak-{index}", category=category, properties_signature="sig-oak")
        await _task(db_session, seed, f"props-oak-{index}", primary=item, seconds=seconds)
    for index, seconds in enumerate([1000, 1100, 1200, 1300, 1400]):
        item = await _item(db_session, seed, f"props-teak-{index}", category=category, properties_signature="sig-teak")
        await _task(db_session, seed, f"props-teak-{index}", primary=item, seconds=seconds)
    legacy = await _item(db_session, seed, "props-legacy", category=category, properties_signature=None)
    await _task(db_session, seed, "props-legacy", primary=legacy, seconds=9000)

    specs = (
        TypicalFilterSpec(item_category_ids=frozenset({category.client_id}), properties_signature="sig-oak"),
        TypicalFilterSpec(item_category_ids=frozenset({category.client_id})),
    )
    rows = {
        row.spec_index: row
        for row in (await db_session.execute(
            typical_times_statement(seed.workspace.client_id, specs=specs, now=NOW)
        )).all()
        if row.client_id == seed.section.client_id
    }

    oak = rows[0]
    assert oak.properties_sample_count == 5
    assert oak.properties_typical_worker_seconds == 300
    assert float(oak.properties_typical_unit_worker_seconds) == 300.0
    # The category tier on the same row still pools all eleven samples
    # (sorted middle of 100..500, 1000..1400, 9000 is 1000).
    assert oak.narrowed_sample_count == 11
    assert oak.narrowed_typical_worker_seconds == 1000

    # A signature-less spec has no properties tier at all.
    bare = rows[1]
    assert bare.properties_sample_count == 0
    assert bare.properties_typical_worker_seconds is None
    assert bare.properties_typical_unit_worker_seconds is None


@pytest.mark.integration
async def test_properties_tier_below_gate_yields_null_but_keeps_its_count(db_session):
    seed, _ = await _seed_base(db_session)
    category = await _category(db_session, seed, "props-gate", ItemMajorCategoryEnum.SEAT)
    for index in range(TYPICAL_MIN_SAMPLE_SIZE - 1):
        item = await _item(db_session, seed, f"props-gate-{index}", category=category, properties_signature="sig-few")
        await _task(db_session, seed, f"props-gate-{index}", primary=item, seconds=100 + index)
    filler = await _item(db_session, seed, "props-gate-filler", category=category)
    await _task(db_session, seed, "props-gate-filler", primary=filler, seconds=999)

    spec = TypicalFilterSpec(item_category_ids=frozenset({category.client_id}), properties_signature="sig-few")
    row = next(
        r
        for r in (await db_session.execute(
            typical_times_statement(seed.workspace.client_id, specs=(spec,), now=NOW)
        )).all()
        if r.client_id == seed.section.client_id
    )
    assert row.properties_sample_count == TYPICAL_MIN_SAMPLE_SIZE - 1
    assert row.properties_typical_worker_seconds is None
    assert row.narrowed_sample_count == TYPICAL_MIN_SAMPLE_SIZE
    assert row.narrowed_typical_worker_seconds is not None


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_TYPICAL_COST_MEASUREMENTS") != "1",
    reason="cost matrix is an explicit measurement run",
)
async def test_cost_matrix_harness_is_reproducible(db_session, capsys):
    rows = await collect_measurement_matrix(db_session)
    print(rows)
    assert len(rows) == 11
