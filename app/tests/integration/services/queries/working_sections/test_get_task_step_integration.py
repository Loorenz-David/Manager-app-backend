from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.items.enums import ItemUpholsterySourceEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.upholstery.upholstery import Upholstery
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_task_step import get_task_step
from beyo_manager.services.queries.working_sections.list_working_section_steps import (
    list_working_section_steps,
)

_GROUP_KEYS = {
    "upholstery_group_key",
    "upholstery_group_image_url",
    "upholstery_group_upholstery_id",
    "upholstery_group_inventory",
}


class _Seed:
    def __init__(self, workspace, user, section, task, item, step, upholstery):
        self.workspace = workspace
        self.user = user
        self.section = section
        self.task = task
        self.item = item
        self.step = step
        self.upholstery = upholstery


async def _seed(db_session, *, with_upholstery: bool = True) -> _Seed:
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
        state=TaskStepStateEnum.WORKING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        assigned_worker_id=user.client_id,
        created_by_id=user.client_id,
        created_at=now,
        total_cost_minor=4321,
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

    upholstery = None
    if with_upholstery:
        # The three upholstery_group_* columns only resolve to non-null values when
        # the primary item carries an upholstery. Without one, the grouped and the
        # ungrouped list item are indistinguishable and the parity assertions below
        # would prove nothing about where those values come from.
        upholstery = Upholstery(
            client_id=f"uph_{suffix}",
            workspace_id=workspace.client_id,
            name=f"Linen {suffix}",
            image_url=f"https://example.com/{suffix}.webp",
            created_by_id=user.client_id,
        )
        db_session.add(upholstery)
        await db_session.flush()

        db_session.add(
            ItemUpholstery(
                client_id=f"iup_{suffix}",
                workspace_id=workspace.client_id,
                item_id=item.client_id,
                upholstery_id=upholstery.client_id,
                name=f"Linen {suffix}",
                source=ItemUpholsterySourceEnum.INTERNAL,
                created_by_id=user.client_id,
            )
        )
        await db_session.flush()

    state_record = StepStateRecord(
        workspace_id=workspace.client_id,
        step_id=step.client_id,
        state=TaskStepStateEnum.WORKING,
        entered_at=now,
        created_at=now,
        created_by_id=user.client_id,
    )
    db_session.add(state_record)
    await db_session.flush()
    step.latest_state_record_id = state_record.client_id
    await db_session.flush()

    return _Seed(workspace, user, section, task, item, step, upholstery)


def _ctx(
    db_session,
    *,
    workspace_id: str,
    user_id: str,
    incoming_data: dict,
    query_params: dict | None = None,
    role_name: str = "worker",
) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": role_name,
            "username": "tester",
        },
        incoming_data=incoming_data,
        query_params=query_params or {},
        session=db_session,
    )


async def _single(db_session, seed: _Seed, *, user_id: str | None = None, role_name: str = "worker") -> dict:
    result = await get_task_step(
        _ctx(
            db_session,
            workspace_id=seed.workspace.client_id,
            user_id=user_id or seed.user.client_id,
            incoming_data={"step_id": seed.step.client_id},
            role_name=role_name,
        )
    )
    return result["step"]


async def _list_item(
    db_session, seed: _Seed, *, group_by_upholstery: bool, user_id: str | None = None, role_name: str = "worker"
) -> dict:
    result = await list_working_section_steps(
        _ctx(
            db_session,
            workspace_id=seed.workspace.client_id,
            user_id=user_id or seed.user.client_id,
            incoming_data={"working_section_id": seed.section.client_id},
            query_params={"group_by_upholstery": str(group_by_upholstery).lower()},
            role_name=role_name,
        )
    )
    items = result["steps_pagination"]["items"]
    assert len(items) == 1
    return items[0]


@pytest.mark.integration
@pytest.mark.parametrize("role_name", ["worker", "manager", "admin"])
async def test_single_step_payload_is_identical_to_the_grouped_list_item(db_session, role_name):
    """The contract the frontend validates against: one step fetched alone parses
    with the same schema, and carries the same values, as that step inside a list
    page. Asserting the whole dict — not a key set — is what catches a field the
    list computes in batch and a single-step path quietly leaves out."""
    seed = await _seed(db_session)

    single = await _single(db_session, seed, role_name=role_name)
    listed = await _list_item(db_session, seed, group_by_upholstery=True, role_name=role_name)

    assert single == listed
    # The role gate travels with the payload rather than being re-derived here.
    assert ("total_cost_minor" in single) is (role_name in {"manager", "admin"})


@pytest.mark.integration
async def test_group_columns_are_resolved_even_though_no_grouping_was_requested(db_session):
    """Deliberate, documented divergence from an *ungrouped* list page.

    The three upholstery_group_* values are properties of the step's own primary
    item, so this route resolves them unconditionally: the frontend feeds one
    per-step cache entry from every fetch, and a null written by this route would
    blank a real value seeded from a grouped list page. Everything outside those
    columns must still match the ungrouped item exactly.
    """
    seed = await _seed(db_session)

    single = await _single(db_session, seed)
    ungrouped = await _list_item(db_session, seed, group_by_upholstery=False)

    assert {k: v for k, v in single.items() if k not in _GROUP_KEYS} == {
        k: v for k, v in ungrouped.items() if k not in _GROUP_KEYS
    }
    assert single["upholstery_group_key"] == seed.upholstery.name
    assert single["upholstery_group_image_url"] == seed.upholstery.image_url
    assert single["upholstery_group_upholstery_id"] == seed.upholstery.client_id
    assert ungrouped["upholstery_group_key"] is None


@pytest.mark.integration
async def test_step_whose_primary_item_has_no_upholstery_reports_null_group_columns(db_session):
    """The unconditional resolution above must not invent a group for an item
    that has no upholstery — the "no upholstery" bucket stays null."""
    seed = await _seed(db_session, with_upholstery=False)

    single = await _single(db_session, seed)

    assert single["upholstery_group_key"] is None
    assert single["upholstery_group_image_url"] is None
    assert single["upholstery_group_upholstery_id"] is None
    assert single["upholstery_group_inventory"] is None


@pytest.mark.integration
async def test_is_reassigned_is_true_for_the_worker_who_owes_the_acknowledgment(db_session):
    seed = await _seed(db_session)
    other_worker = User(
        client_id=f"usr_{uuid4().hex[:8]}",
        username=f"other_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password="secret",
    )
    db_session.add(other_worker)
    await db_session.flush()
    db_session.add(
        TaskStepAcknowledgment(
            client_id=f"tsa_{uuid4().hex[:8]}",
            workspace_id=seed.workspace.client_id,
            step_id=seed.step.client_id,
            task_id=seed.task.client_id,
            worker_id=seed.user.client_id,
            created_by_id=seed.user.client_id,
        )
    )
    await db_session.flush()

    assert (await _single(db_session, seed))["is_reassigned"] is True
    # Viewer-relative, exactly as in the list: the obligation belongs to one worker.
    assert (await _single(db_session, seed, user_id=other_worker.client_id))["is_reassigned"] is False


@pytest.mark.integration
async def test_acknowledgment_on_a_terminal_step_does_not_flag_it_reassigned(db_session):
    """`is_reassigned` is the section list's definition, which excludes terminal
    steps — an obligation row alone is not enough."""
    seed = await _seed(db_session)
    db_session.add(
        TaskStepAcknowledgment(
            client_id=f"tsa_{uuid4().hex[:8]}",
            workspace_id=seed.workspace.client_id,
            step_id=seed.step.client_id,
            task_id=seed.task.client_id,
            worker_id=seed.user.client_id,
            created_by_id=seed.user.client_id,
        )
    )
    seed.step.state = TaskStepStateEnum.COMPLETED
    await db_session.flush()

    assert (await _single(db_session, seed))["is_reassigned"] is False


@pytest.mark.integration
async def test_unknown_step_id_is_not_found(db_session):
    seed = await _seed(db_session)

    with pytest.raises(NotFound):
        await get_task_step(
            _ctx(
                db_session,
                workspace_id=seed.workspace.client_id,
                user_id=seed.user.client_id,
                incoming_data={"step_id": "tsp_does_not_exist"},
            )
        )


@pytest.mark.integration
async def test_deleted_step_is_not_found(db_session):
    seed = await _seed(db_session)
    seed.step.is_deleted = True
    await db_session.flush()

    with pytest.raises(NotFound):
        await _single(db_session, seed)


@pytest.mark.integration
async def test_step_on_a_deleted_task_is_not_found(db_session):
    seed = await _seed(db_session)
    seed.task.is_deleted = True
    await db_session.flush()

    with pytest.raises(NotFound):
        await _single(db_session, seed)


@pytest.mark.integration
async def test_step_in_another_workspace_is_not_found(db_session):
    """The workspace scope is the security boundary, and a 404 — not an empty
    payload — is what the caller gets."""
    seed = await _seed(db_session)
    intruder_workspace = Workspace(client_id=f"ws_{uuid4().hex[:8]}", name="Intruder")
    db_session.add(intruder_workspace)
    await db_session.flush()

    with pytest.raises(NotFound):
        await get_task_step(
            _ctx(
                db_session,
                workspace_id=intruder_workspace.client_id,
                user_id=seed.user.client_id,
                incoming_data={"step_id": seed.step.client_id},
            )
        )


@pytest.mark.integration
async def test_missing_step_id_is_not_found_not_a_crash(db_session):
    seed = await _seed(db_session)

    with pytest.raises(NotFound):
        await get_task_step(
            _ctx(
                db_session,
                workspace_id=seed.workspace.client_id,
                user_id=seed.user.client_id,
                incoming_data={},
            )
        )
