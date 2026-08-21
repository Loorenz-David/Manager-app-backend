from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event, select

from beyo_manager.domain.task_steps.constants import TERMINAL_STEP_STATES
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import WorkingSectionMembership
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.task_step_acknowledgments.count_reassigned_steps import count_reassigned_steps
from beyo_manager.services.queries.task_step_acknowledgments.list_reassigned_steps import list_reassigned_steps
from beyo_manager.services.queries.task_step_acknowledgments.list_pending_step_acknowledgments import (
    list_pending_step_acknowledgments,
)
from tests.integration.services.queries.working_sections.test_list_working_section_steps_payload_characterization import (
    _STEP_KEYS,
)


def _ctx(db_session, workspace_id, user_id, *, role_name="worker", **params):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "role_name": role_name},
        incoming_data={}, query_params=params, session=db_session,
    )


async def _seed(db_session, *, state=TaskStepStateEnum.PENDING, article="302.445", sku="SOFA-3S", item=True,
                membership=True, acknowledged=False, ack_deleted=False, step_deleted=False, task_deleted=False,
                section_deleted=False, worker_id=None, created_at=None, suffix=None, workspace=None, worker=None,
                other=None):
    suffix = suffix or uuid4().hex[:8]
    now = created_at or datetime.now(timezone.utc)
    if workspace is None:
        workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
        worker = User(client_id=f"usr_{suffix}", username=f"worker_{suffix}", email=f"{suffix}@example.com", password="secret")
        other = User(client_id=f"usr_other_{suffix}", username=f"other-{suffix}", email=f"other-{suffix}@example.com", password="secret")
        db_session.add_all([workspace, worker, other])
        await db_session.flush()
    section = WorkingSection(client_id=f"wsec_{suffix}", workspace_id=workspace.client_id, name=f"Section {suffix}", is_deleted=section_deleted)
    task = Task(client_id=f"tsk_{suffix}", workspace_id=workspace.client_id, task_scalar_id=int(suffix[:7], 16), task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=worker.client_id, is_deleted=task_deleted)
    step = TaskStep(client_id=f"tsp_{suffix}", workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id, working_section_name_snapshot=section.name, state=state, readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0, completed_dependencies=0, created_by_id=worker.client_id, total_cost_minor=4321, is_deleted=step_deleted)
    db_session.add_all([section, task, step])
    await db_session.flush()
    if item:
        primary_item = Item(client_id=f"itm_{suffix}", workspace_id=workspace.client_id, article_number=article, sku=sku, created_by_id=worker.client_id)
        db_session.add(primary_item)
        await db_session.flush()
        db_session.add(TaskItem(client_id=f"tim_{suffix}", workspace_id=workspace.client_id, task_id=task.client_id, item_id=primary_item.client_id, role=TaskItemRoleEnum.PRIMARY, created_by_id=worker.client_id))
    if membership:
        db_session.add(WorkingSectionMembership(client_id=f"wsme_{suffix}", workspace_id=workspace.client_id, working_section_id=section.client_id, user_id=worker.client_id, assigned_at=now, assigned_by_id=worker.client_id))
    db_session.add(TaskStepAcknowledgment(client_id=f"tsa_{suffix}", workspace_id=workspace.client_id, step_id=step.client_id, task_id=task.client_id, worker_id=worker_id or worker.client_id, created_by_id=worker.client_id, created_at=now, acknowledged_at=now if acknowledged else None, is_deleted=ack_deleted))
    db_session.add(StepStateRecord(workspace_id=workspace.client_id, step_id=step.client_id, state=state, entered_at=now, created_at=now, created_by_id=worker.client_id))
    await db_session.flush()
    return workspace, worker, other, section, task, step


def _list_ctx(db_session, workspace, worker, *, role_name="worker", **params):
    query_params = {
        "limit": 50,
        "offset": 0,
        "q": None,
        "string_filters": None,
        "unacknowledged_only": "false",
    }
    query_params.update(params)
    return _ctx(
        db_session,
        workspace.client_id,
        worker.client_id,
        role_name=role_name,
        **query_params,
    )


@pytest.fixture
def executed_statements():
    from beyo_manager.models import database

    engine = database._engine
    assert engine is not None, "init_db() must have run before this fixture"
    statements: list[str] = []

    @sa_event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    yield statements

    sa_event.remove(engine.sync_engine, "before_cursor_execute", _record)


@pytest.mark.integration
async def test_reassigned_list_and_count_agree_and_include_acknowledged_rows(db_session):
    workspace, worker, _, _, _, first = await _seed(db_session, suffix=uuid4().hex[:8])
    for index in range(2):
        suffix = uuid4().hex[:8]
        section = WorkingSection(client_id=f"wsec_{suffix}", workspace_id=workspace.client_id, name=f"Section {suffix}")
        task = Task(client_id=f"tsk_{suffix}", workspace_id=workspace.client_id, task_scalar_id=index + 2, task_type=TaskTypeEnum.INTERNAL, state=TaskStateEnum.ASSIGNED, created_by_id=worker.client_id)
        step = TaskStep(client_id=f"tsp_{suffix}", workspace_id=workspace.client_id, task_id=task.client_id, working_section_id=section.client_id, state=TaskStepStateEnum.PENDING, readiness_status=TaskStepReadinessStatusEnum.READY, total_dependencies=0, completed_dependencies=0, created_by_id=worker.client_id)
        now = datetime.now(timezone.utc) + timedelta(seconds=index)
        db_session.add_all([section, task, step])
        await db_session.flush()
        db_session.add_all([WorkingSectionMembership(client_id=f"wsme_{suffix}", workspace_id=workspace.client_id, working_section_id=section.client_id, user_id=worker.client_id, assigned_at=now, assigned_by_id=worker.client_id), TaskStepAcknowledgment(client_id=f"tsa_{suffix}", workspace_id=workspace.client_id, step_id=step.client_id, task_id=task.client_id, worker_id=worker.client_id, created_by_id=worker.client_id, created_at=now, acknowledged_at=now if index else None), StepStateRecord(workspace_id=workspace.client_id, step_id=step.client_id, state=TaskStepStateEnum.PENDING, entered_at=now, created_at=now, created_by_id=worker.client_id)])
    await db_session.flush()
    seen = set()
    offset = 0
    while True:
        page = await list_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id, limit=1, offset=offset, q=None, string_filters=None, unacknowledged_only="false"))
        ids = {item["client_id"] for item in page["steps_pagination"]["items"]}
        assert not seen.intersection(ids)
        seen.update(ids)
        if not page["steps_pagination"]["has_more"]:
            break
        offset += 1
    count = await count_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id))
    assert count["reassigned_steps_count"] == {"total": len(seen), "unacknowledged": 2}
    assert first.client_id in seen


@pytest.mark.integration
@pytest.mark.parametrize("state", sorted(TERMINAL_STEP_STATES, key=lambda state: state.value))
async def test_reassigned_list_excludes_terminal_steps(db_session, state):
    workspace, worker, _, _, _, _ = await _seed(db_session, state=state)
    result = await list_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id, limit=50, offset=0, q=None, string_filters=None, unacknowledged_only="false"))
    assert result["steps_pagination"]["items"] == []


@pytest.mark.integration
async def test_reassigned_list_excludes_deleted_and_membership_and_supports_q(db_session):
    workspace, worker, other, section, task, step = await _seed(db_session, article="302.445", sku="SOFA-3S")
    visible = await list_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id, limit=50, offset=0, q="sOfA", string_filters=None, unacknowledged_only="false"))
    assert [item["client_id"] for item in visible["steps_pagination"]["items"]] == [step.client_id]
    no_item_workspace, no_item_worker, _, _, _, no_item_step = await _seed(db_session, item=False)
    no_item = await list_reassigned_steps(_ctx(db_session, no_item_workspace.client_id, no_item_worker.client_id, limit=50, offset=0, q=None, string_filters=None, unacknowledged_only="false"))
    assert [item["client_id"] for item in no_item["steps_pagination"]["items"]] == [no_item_step.client_id]
    filtered = await list_reassigned_steps(_ctx(db_session, no_item_workspace.client_id, no_item_worker.client_id, limit=50, offset=0, q="anything", string_filters=None, unacknowledged_only="false"))
    assert filtered["steps_pagination"]["items"] == []
    membership = (await db_session.execute(__import__("sqlalchemy").select(WorkingSectionMembership).where(WorkingSectionMembership.working_section_id == section.client_id))).scalar_one()
    membership.removed_at = datetime.now(timezone.utc)
    await db_session.flush()
    removed = await list_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id, limit=50, offset=0, q=None, string_filters=None, unacknowledged_only="false"))
    assert removed["steps_pagination"]["items"] == []


@pytest.mark.integration
@pytest.mark.parametrize(
    "excluded",
    ["ack", "step", "task", "section", "no_membership", "wrong_worker"],
)
async def test_reassigned_list_and_count_exclude_ineligible_rows(db_session, excluded):
    workspace, worker, other, section, task, step = await _seed(db_session, membership=excluded != "no_membership")
    acknowledgment = (
        await db_session.execute(
            select(TaskStepAcknowledgment).where(TaskStepAcknowledgment.step_id == step.client_id)
        )
    ).scalar_one()
    if excluded == "ack":
        acknowledgment.is_deleted = True
    elif excluded == "step":
        step.is_deleted = True
    elif excluded == "task":
        task.is_deleted = True
    elif excluded == "section":
        section.is_deleted = True
    elif excluded == "wrong_worker":
        acknowledgment.worker_id = other.client_id
    await db_session.flush()

    listed = await list_reassigned_steps(_list_ctx(db_session, workspace, worker))
    counted = await count_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id))
    assert listed["steps_pagination"]["items"] == []
    assert listed["working_sections"] == {}
    assert counted["reassigned_steps_count"] == {"total": 0, "unacknowledged": 0}


@pytest.mark.integration
async def test_reassigned_list_enforces_workspace_and_unacknowledged_filter(db_session):
    workspace, worker, _, _, _, step = await _seed(db_session, acknowledged=True)
    other_workspace, _, _, _, _, _ = await _seed(db_session)
    acknowledgment = (
        await db_session.execute(
            select(TaskStepAcknowledgment).where(TaskStepAcknowledgment.step_id == step.client_id)
        )
    ).scalar_one()

    assert [item["client_id"] for item in (await list_reassigned_steps(_list_ctx(db_session, workspace, worker)))["steps_pagination"]["items"]] == [step.client_id]
    unacknowledged = await list_reassigned_steps(
        _list_ctx(db_session, workspace, worker, unacknowledged_only="true")
    )
    assert unacknowledged["steps_pagination"]["items"] == []

    acknowledgment.workspace_id = other_workspace.client_id
    await db_session.flush()
    assert (await list_reassigned_steps(_list_ctx(db_session, workspace, worker)))["steps_pagination"]["items"] == []
    assert (await list_reassigned_steps(_list_ctx(db_session, other_workspace, worker)))["steps_pagination"]["items"] == []


@pytest.mark.integration
async def test_reassigned_list_payload_sections_order_and_filtered_pagination(db_session):
    now = datetime.now(timezone.utc)
    workspace, worker, _, first_section, _, first_step = await _seed(
        db_session,
        article="302.445",
        sku="SOFA-3S",
        created_at=now,
    )
    _, _, _, second_section, _, second_step = await _seed(
        db_session,
        workspace=workspace,
        worker=worker,
        article="other",
        sku="CHAIR-1S",
        created_at=now + timedelta(seconds=1),
    )
    _, _, _, third_section, _, third_step = await _seed(
        db_session,
        workspace=workspace,
        worker=worker,
        article="302.499",
        sku="SOFA-2S",
        created_at=now + timedelta(seconds=2),
    )

    first_page = await list_reassigned_steps(_list_ctx(db_session, workspace, worker, limit=2))
    second_page = await list_reassigned_steps(_list_ctx(db_session, workspace, worker, limit=2, offset=2))
    assert first_page["steps_pagination"]["has_more"] is True
    assert second_page["steps_pagination"]["has_more"] is False
    assert {item["client_id"] for item in first_page["steps_pagination"]["items"]}.isdisjoint(
        {item["client_id"] for item in second_page["steps_pagination"]["items"]}
    )
    assert [item["client_id"] for item in first_page["steps_pagination"]["items"]] == [third_step.client_id, second_step.client_id]

    item = first_page["steps_pagination"]["items"][0]
    assert set(item) == (_STEP_KEYS - {"total_cost_minor"}) | {"acknowledgment"}
    assert "total_cost_minor" not in item
    assert item["is_reassigned"] is True
    assert item["acknowledgment"]["acknowledged_at"] is None
    assert set(first_page["working_sections"]) == {third_section.client_id, second_section.client_id}
    assert set(first_page["working_sections"][third_section.client_id]) == {
        "client_id", "name", "image", "order_list", "allows_batch_working", "allows_shopify_product_modifications"
    }
    filtered = await list_reassigned_steps(_list_ctx(db_session, workspace, worker, q="SoFa", limit=1))
    filtered_next = await list_reassigned_steps(_list_ctx(db_session, workspace, worker, q="302.4", limit=1, offset=1))
    assert filtered["steps_pagination"]["has_more"] is True
    assert [item["client_id"] for item in filtered["steps_pagination"]["items"]] == [third_step.client_id]
    assert [item["client_id"] for item in filtered_next["steps_pagination"]["items"]] == [first_step.client_id]
    assert filtered_next["steps_pagination"]["has_more"] is False


@pytest.mark.integration
@pytest.mark.parametrize("role_name", ["manager", "admin"])
async def test_reassigned_and_pending_step_payloads_keep_money_for_manager_and_redact_worker(
    db_session, role_name
):
    workspace, worker, _, _, _, step = await _seed(db_session, suffix=uuid4().hex[:8])

    worker_reassigned = await list_reassigned_steps(_list_ctx(db_session, workspace, worker))
    manager_reassigned = await list_reassigned_steps(
        _list_ctx(db_session, workspace, worker, role_name=role_name)
    )
    assert "total_cost_minor" not in worker_reassigned["steps_pagination"]["items"][0]
    assert manager_reassigned["steps_pagination"]["items"][0]["total_cost_minor"] == 4321

    worker_pending = await list_pending_step_acknowledgments(
        _ctx(db_session, workspace.client_id, worker.client_id, limit=50, offset=0)
    )
    manager_pending = await list_pending_step_acknowledgments(
        _ctx(db_session, workspace.client_id, worker.client_id, role_name=role_name, limit=50, offset=0)
    )
    assert worker_pending["acknowledgments"][0]["client_id"] == step.client_id
    assert "total_cost_minor" not in worker_pending["acknowledgments"][0]
    assert manager_pending["acknowledgments"][0]["total_cost_minor"] == 4321

@pytest.mark.integration
async def test_reassigned_count_is_q_independent_and_list_statement_count_is_bounded(db_session, executed_statements):
    workspace, worker, _, _, _, _ = await _seed(db_session)
    await list_reassigned_steps(_list_ctx(db_session, workspace, worker))
    del executed_statements[:]
    await list_reassigned_steps(_list_ctx(db_session, workspace, worker))
    one_item_statement_count = len(executed_statements)

    for index in range(9):
        await _seed(
            db_session,
            workspace=workspace,
            worker=worker,
            article=f"302.4{index}",
            sku=f"SOFA-{index}",
        )
    del executed_statements[:]
    await list_reassigned_steps(_list_ctx(db_session, workspace, worker))
    assert len(executed_statements) == one_item_statement_count

    del executed_statements[:]
    count_without_q = await count_reassigned_steps(_ctx(db_session, workspace.client_id, worker.client_id))
    assert len(executed_statements) == 1
    count_with_q = await count_reassigned_steps(
        _ctx(db_session, workspace.client_id, worker.client_id, q="no-match")
    )
    assert count_without_q == count_with_q == {"reassigned_steps_count": {"total": 10, "unacknowledged": 10}}
