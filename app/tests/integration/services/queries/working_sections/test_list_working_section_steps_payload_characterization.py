from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.list_working_section_steps import (
    list_working_section_steps,
)


_STEP_KEYS = {
    "assigned_worker_display_name_snapshot",
    "assigned_worker_id",
    "cases_summary",
    "closed_at",
    "completed_dependencies",
    "created_at",
    "created_by",
    "client_id",
    "dependency_working_sections",
    "is_reassigned",
    "item",
    "item_images",
    "last_state_record",
    "readiness_status",
    "ready_by_at",
    "recorded_time_marked_wrong",
    "sequence_order",
    "state",
    "task",
    "task_id",
    "total_cost_minor",
    "total_dependencies",
    "total_ended_shift_count",
    "total_ended_shift_seconds",
    "total_issues_count",
    "total_issues_resolved_count",
    "total_pause_count",
    "total_pause_seconds",
    "total_working_count",
    "total_working_seconds",
    "updated_at",
    "updated_by",
    "upholstery_group_image_url",
    "upholstery_group_inventory",
    "upholstery_group_key",
    "upholstery_group_upholstery_id",
    "working_section_id",
    "working_section_name_snapshot",
}

_LAST_STATE_RECORD_KEYS = {
    "description",
    "entered_at",
    "exited_at",
    "first_started_at",
    "last_action_by",
    "pause_reason",
    "state",
}

_TASK_KEYS = {
    "assortment",
    "client_id",
    "item_location",
    "priority",
    "ready_by_at",
    "return_method",
    "return_source",
    "scheduled_end_at",
    "scheduled_start_at",
    "state",
    "task_type",
}

_ITEM_KEYS = {
    "article_number",
    "client_id",
    "item_category_id",
    "item_position",
    "item_zone",
    "quantity",
    "sku",
    "state",
    "upholstery_requirement",
}


def _ctx(db_session, *, workspace_id: str, user_id: str, working_section_id: str, group_by_upholstery: bool) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "worker",
            "username": "tester",
        },
        incoming_data={"working_section_id": working_section_id},
        query_params={"group_by_upholstery": str(group_by_upholstery).lower()},
        session=db_session,
    )


async def _seed_step(db_session) -> tuple[Workspace, User, WorkingSection, Upholstery]:
    suffix = uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    section = WorkingSection(
        client_id=f"wsec_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Section {suffix}",
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=user.client_id,
    )
    item = Item(
        client_id=f"itm_{suffix}",
        workspace_id=workspace.client_id,
        article_number=f"article-{suffix}",
        sku=f"sku-{suffix}",
        created_by_id=user.client_id,
    )
    step = TaskStep(
        client_id=f"tsp_{suffix}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.PENDING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        created_by_id=user.client_id,
        created_at=now,
    )
    task_item = TaskItem(
        client_id=f"tim_{suffix}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        role=TaskItemRoleEnum.PRIMARY,
        created_by_id=user.client_id,
    )
    db_session.add_all([section, task, item, step, task_item])
    await db_session.flush()

    # The primary item carries an upholstery so the three upholstery_group_* columns
    # resolve to real values under group_by_upholstery=true. Without this the grouped
    # and ungrouped runs are indistinguishable — both all-null — and the parametrization
    # would only prove the keys exist, not that their values are computed and carried.
    upholstery = Upholstery(
        client_id=f"uph_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Linen {suffix}",
        image_url=f"https://example.com/{suffix}.webp",
        created_by_id=user.client_id,
    )
    db_session.add(upholstery)
    await db_session.flush()

    item_upholstery = ItemUpholstery(
        client_id=f"iup_{suffix}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        upholstery_id=upholstery.client_id,
        name=f"Linen {suffix}",
        source=ItemUpholsterySourceEnum.INTERNAL,
        created_by_id=user.client_id,
    )
    db_session.add(item_upholstery)
    await db_session.flush()

    state_record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.PENDING,
        entered_at=now,
        created_at=now,
        created_by_id=user.client_id,
    )
    db_session.add(state_record)
    await db_session.flush()
    step.latest_state_record_id = state_record.client_id
    await db_session.flush()
    return workspace, user, section, upholstery


@pytest.mark.integration
@pytest.mark.parametrize("group_by_upholstery", [False, True])
async def test_list_working_section_steps_payload_key_sets_are_stable(db_session, group_by_upholstery):
    workspace, user, section, upholstery = await _seed_step(db_session)

    result = await list_working_section_steps(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            working_section_id=section.client_id,
            group_by_upholstery=group_by_upholstery,
        )
    )

    assert set(result["steps_pagination"]) == {"items", "limit", "offset", "has_more"}
    assert len(result["steps_pagination"]["items"]) == 1

    item = result["steps_pagination"]["items"][0]
    assert set(item) == _STEP_KEYS
    assert set(item["last_state_record"]) == _LAST_STATE_RECORD_KEYS
    assert set(item["task"]) == _TASK_KEYS
    assert set(item["item"]) == _ITEM_KEYS

    # The upholstery_group_* values, not merely their keys. These are the columns the
    # extraction receives as separate arguments, so a builder that accepts the maps and
    # never reads them would still satisfy a key-set-only assertion.
    if group_by_upholstery:
        assert item["upholstery_group_key"] == upholstery.name
        assert item["upholstery_group_image_url"] == upholstery.image_url
        assert item["upholstery_group_upholstery_id"] == upholstery.client_id
    else:
        assert item["upholstery_group_key"] is None
        assert item["upholstery_group_image_url"] is None
        assert item["upholstery_group_upholstery_id"] is None
    # No UpholsteryInventory is seeded, so the inventory lookup finds nothing either way.
    assert item["upholstery_group_inventory"] is None

    pause_reason = item["last_state_record"]["pause_reason"]
    if pause_reason is not None:
        assert set(pause_reason) == {
            "client_id",
            "created_at",
            "created_by_id",
            "description",
            "image_url",
            "is_system_managed",
            "name",
            "pause_type",
            "requires_description",
            "slug",
            "updated_at",
            "updated_by_id",
        }

def _filter_ctx(db_session, *, workspace_id: str, user_id: str, working_section_id: str, record_step_state: str) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "worker",
            "username": "tester",
        },
        incoming_data={"working_section_id": working_section_id},
        query_params={"record_step_state": record_step_state, "readiness_statuses": "ready"},
        session=db_session,
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "record_step_state",
    [
        # The workers app's `DEFAULT_STATE_FILTERS`, verbatim as of 2026-08-01.
        "pending,working,paused,ended_shift",
        # Alone, so the alias is the only thing that can match the row.
        "ended_shift",
    ],
)
async def test_retired_ended_shift_filter_value_selects_paused_steps(db_session, record_step_state):
    """A client still sending `ended_shift` gets the paused steps, not a 500.

    `2645b4327b17` removed the member from `task_step_state_enum` while
    `HANDOFF_TO_FRONTEND_remove_pause_reason_transition_20260801` explicitly told the frontend to
    leave read-side `ended_shift` handling alone until a later handoff — which is why the shipped
    workers app still sends it and every steps list 500s with
    `InvalidTextRepresentationError: invalid input value for enum task_step_state_enum`.

    Run against the database on purpose: the defect is that the string reaches Postgres, and only
    a real bind proves it no longer does.
    """
    workspace, user, section, _ = await _seed_step(db_session)

    step = (
        await db_session.execute(
            select(TaskStep).where(TaskStep.working_section_id == section.client_id)
        )
    ).scalar_one()
    step.state = TaskStepStateEnum.PAUSED
    await db_session.flush()

    result = await list_working_section_steps(
        _filter_ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            working_section_id=section.client_id,
            record_step_state=record_step_state,
        )
    )

    items = result["steps_pagination"]["items"]
    assert [i["client_id"] for i in items] == [step.client_id]
    assert items[0]["state"] == TaskStepStateEnum.PAUSED.value


@pytest.mark.integration
async def test_unknown_state_filter_value_is_a_domain_error_not_a_driver_crash(db_session):
    """A typo must not become an unfiltered list, and must not become a 500 either."""
    workspace, user, section, _ = await _seed_step(db_session)

    with pytest.raises(ValidationError) as exc:
        await list_working_section_steps(
            _filter_ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                working_section_id=section.client_id,
                record_step_state="pending,not_a_state",
            )
        )
    assert "not_a_state" in str(exc.value)
