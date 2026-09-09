from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.tasks import list_tasks


BASE = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


class _World:
    """A workspace with two working sections, plus builders that flush as they go."""

    def __init__(self, db_session, workspace, user, section_a, section_b, suffix):
        self.db_session = db_session
        self.workspace = workspace
        self.user = user
        self.section_a = section_a
        self.section_b = section_b
        self.suffix = suffix
        self._n = 0

    async def task(self, name, *, state=TaskStateEnum.WORKING, completed_at=None) -> Task:
        self._n += 1
        task = Task(
            client_id=f"tsk_{self.suffix}_{name}",
            workspace_id=self.workspace.client_id,
            task_scalar_id=self._n,
            task_type=TaskTypeEnum.INTERNAL,
            state=state,
            completed_at=completed_at,
            created_by_id=self.user.client_id,
            created_at=BASE,
        )
        self.db_session.add(task)
        await self.db_session.flush()
        return task

    async def step(self, task, name, section, *, is_deleted=False) -> TaskStep:
        step = TaskStep(
            client_id=f"tsp_{self.suffix}_{name}",
            workspace_id=self.workspace.client_id,
            task_id=task.client_id,
            working_section_id=section.client_id,
            working_section_name_snapshot=section.name,
            state=TaskStepStateEnum.PENDING,
            readiness_status=TaskStepReadinessStatusEnum.READY,
            total_dependencies=0,
            completed_dependencies=0,
            created_by_id=self.user.client_id,
            created_at=BASE,
            is_deleted=is_deleted,
        )
        self.db_session.add(step)
        await self.db_session.flush()
        return step

    async def record(self, step, name, *, state, entered_at, exited_at=None) -> StepStateRecord:
        # uix_step_state_records_active allows only one open record per step, so a step with a
        # history must close each record as the next opens — exactly what the production
        # close-then-open transition does.
        record = StepStateRecord(
            client_id=f"ssr_{self.suffix}_{name}",
            workspace_id=self.workspace.client_id,
            step_id=step.client_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            created_by_id=self.user.client_id,
        )
        self.db_session.add(record)
        await self.db_session.flush()
        return record


async def _world(db_session) -> _World:
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

    section_a = WorkingSection(
        client_id=f"wsec_a_{suffix}", workspace_id=workspace.client_id, name=f"Alpha {suffix}"
    )
    section_b = WorkingSection(
        client_id=f"wsec_b_{suffix}", workspace_id=workspace.client_id, name=f"Beta {suffix}"
    )
    db_session.add_all([section_a, section_b])
    await db_session.flush()
    return _World(db_session, workspace, user, section_a, section_b, suffix)


def _ctx(world, **query_params) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": world.workspace.client_id,
            "user_id": world.user.client_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={},
        query_params={"limit": 50, "offset": 0, **query_params},
        session=world.db_session,
    )


async def _ids(world, **query_params) -> list[str]:
    result = await list_tasks(_ctx(world, **query_params))
    return [item["task"]["client_id"] for item in result["tasks_pagination"]["items"]]


# --- recently_completed -------------------------------------------------------------------


@pytest.mark.integration
async def test_recently_completed_orders_newest_completion_first(db_session) -> None:
    world = await _world(db_session)
    await world.task("old", state=TaskStateEnum.READY, completed_at=_at(10))
    await world.task("newest", state=TaskStateEnum.RESOLVED, completed_at=_at(90))
    await world.task("middle", state=TaskStateEnum.READY, completed_at=_at(50))

    ids = await _ids(world, task_states="ready,resolved", order_by="recently_completed")

    assert ids == [
        f"tsk_{world.suffix}_newest",
        f"tsk_{world.suffix}_middle",
        f"tsk_{world.suffix}_old",
    ]


@pytest.mark.integration
async def test_recently_completed_ascending_reverses_the_order(db_session) -> None:
    world = await _world(db_session)
    await world.task("old", state=TaskStateEnum.READY, completed_at=_at(10))
    await world.task("newest", state=TaskStateEnum.READY, completed_at=_at(90))

    ids = await _ids(world, task_states="ready", order_by="recently_completed:asc")

    assert ids == [f"tsk_{world.suffix}_old", f"tsk_{world.suffix}_newest"]


@pytest.mark.integration
async def test_recently_completed_sorts_unstamped_tasks_last(db_session) -> None:
    """A READY task with no completed_at (a stepless force-ready the backfill could not
    reconstruct) must sink, not float to the top as Postgres' DESC default would do."""
    world = await _world(db_session)
    await world.task("unstamped", state=TaskStateEnum.READY, completed_at=None)
    await world.task("stamped", state=TaskStateEnum.READY, completed_at=_at(10))

    ids = await _ids(world, task_states="ready", order_by="recently_completed")

    assert ids == [f"tsk_{world.suffix}_stamped", f"tsk_{world.suffix}_unstamped"]


@pytest.mark.integration
async def test_recently_completed_falls_back_without_a_completed_state_filter(db_session) -> None:
    world = await _world(db_session)
    # ready_by_at drives the default ordering and is deliberately the inverse of completed_at,
    # so the guarded and honored orders cannot coincide by accident.
    early = await world.task("a", state=TaskStateEnum.READY, completed_at=_at(10))
    early.ready_by_at = _at(0)
    late = await world.task("b", state=TaskStateEnum.READY, completed_at=_at(90))
    late.ready_by_at = _at(60)
    await db_session.flush()

    a, b = f"tsk_{world.suffix}_a", f"tsk_{world.suffix}_b"
    guarded = await _ids(world, order_by="recently_completed")
    default = await _ids(world)
    honored = await _ids(world, task_states="ready", order_by="recently_completed")

    assert guarded == default == [a, b]
    assert honored == [b, a]


@pytest.mark.integration
async def test_recently_completed_pagination_is_stable_across_ties(db_session) -> None:
    """Five tasks sharing one completed_at: without a deterministic tiebreaker the pages
    reshuffle between fetches, duplicating one task and dropping another."""
    world = await _world(db_session)
    shared = _at(30)
    for name in ("a", "b", "c", "d", "e"):
        await world.task(name, state=TaskStateEnum.READY, completed_at=shared)

    pages = []
    for offset in (0, 2, 4):
        pages.append(
            await _ids(
                world,
                task_states="ready",
                order_by="recently_completed",
                limit=2,
                offset=offset,
            )
        )

    collected = [task_id for page in pages for task_id in page]
    assert len(collected) == 5
    assert len(set(collected)) == 5


# --- last_interacted ----------------------------------------------------------------------


@pytest.mark.integration
async def test_last_interacted_orders_by_newest_step_state_record(db_session) -> None:
    world = await _world(db_session)
    for name, minutes in (("old", 10), ("newest", 90), ("middle", 50)):
        task = await world.task(name)
        step = await world.step(task, name, world.section_a)
        await world.record(step, name, state=TaskStepStateEnum.WORKING, entered_at=_at(minutes))

    ids = await _ids(world, order_by="last_interacted")

    assert ids == [
        f"tsk_{world.suffix}_newest",
        f"tsk_{world.suffix}_middle",
        f"tsk_{world.suffix}_old",
    ]


@pytest.mark.integration
async def test_last_interacted_ignores_the_pending_creation_record(db_session) -> None:
    """A step that was only ever created carries a PENDING record dated at creation. If it
    counted, an untouched task would outrank a task genuinely worked earlier."""
    world = await _world(db_session)
    untouched = await world.task("untouched")
    untouched_step = await world.step(untouched, "untouched", world.section_a)
    await world.record(
        untouched_step, "untouched", state=TaskStepStateEnum.PENDING, entered_at=_at(999)
    )

    worked = await world.task("worked")
    worked_step = await world.step(worked, "worked", world.section_a)
    await world.record(
        worked_step,
        "worked_p",
        state=TaskStepStateEnum.PENDING,
        entered_at=_at(0),
        exited_at=_at(10),
    )
    await world.record(
        worked_step, "worked_w", state=TaskStepStateEnum.WORKING, entered_at=_at(10)
    )

    ids = await _ids(world, order_by="last_interacted")

    assert ids == [f"tsk_{world.suffix}_worked", f"tsk_{world.suffix}_untouched"]


@pytest.mark.integration
async def test_last_interacted_is_scoped_to_the_requested_working_sections(db_session) -> None:
    """Each task is newest in one section and oldest in the other, so scoping to a section
    must invert the order relative to scoping to the other one."""
    world = await _world(db_session)
    task_one = await world.task("one")
    one_a = await world.step(task_one, "one_a", world.section_a)
    one_b = await world.step(task_one, "one_b", world.section_b)
    await world.record(one_a, "one_a", state=TaskStepStateEnum.WORKING, entered_at=_at(90))
    await world.record(one_b, "one_b", state=TaskStepStateEnum.WORKING, entered_at=_at(10))

    task_two = await world.task("two")
    two_a = await world.step(task_two, "two_a", world.section_a)
    two_b = await world.step(task_two, "two_b", world.section_b)
    await world.record(two_a, "two_a", state=TaskStepStateEnum.WORKING, entered_at=_at(20))
    await world.record(two_b, "two_b", state=TaskStepStateEnum.WORKING, entered_at=_at(80))

    scoped_a = await _ids(
        world, order_by="last_interacted", working_section_ids=world.section_a.client_id
    )
    scoped_b = await _ids(
        world, order_by="last_interacted", working_section_ids=world.section_b.client_id
    )

    assert scoped_a == [f"tsk_{world.suffix}_one", f"tsk_{world.suffix}_two"]
    assert scoped_b == [f"tsk_{world.suffix}_two", f"tsk_{world.suffix}_one"]


@pytest.mark.integration
async def test_last_interacted_ignores_records_of_removed_steps(db_session) -> None:
    """Step state records are not soft-deleted with their step, so a removed step's activity
    must not keep resurfacing its task."""
    world = await _world(db_session)
    live = await world.task("live")
    live_step = await world.step(live, "live", world.section_a)
    await world.record(live_step, "live", state=TaskStepStateEnum.WORKING, entered_at=_at(10))

    removed = await world.task("removed")
    removed_step = await world.step(removed, "removed", world.section_a, is_deleted=True)
    await world.record(
        removed_step, "removed", state=TaskStepStateEnum.WORKING, entered_at=_at(999)
    )

    ids = await _ids(world, order_by="last_interacted")

    assert ids == [f"tsk_{world.suffix}_live", f"tsk_{world.suffix}_removed"]


@pytest.mark.integration
async def test_last_interacted_survives_group_by_upholstery(db_session) -> None:
    """Grouping prepends its own key. With no upholstery every group key is NULL, so the
    requested sort still decides the order rather than being dropped."""
    world = await _world(db_session)
    for name, minutes in (("old", 10), ("newest", 90)):
        task = await world.task(name)
        step = await world.step(task, name, world.section_a)
        await world.record(step, name, state=TaskStepStateEnum.WORKING, entered_at=_at(minutes))

    ids = await _ids(world, order_by="last_interacted", group_by_upholstery=True)

    assert ids == [f"tsk_{world.suffix}_newest", f"tsk_{world.suffix}_old"]


# --- payload ------------------------------------------------------------------------------


@pytest.mark.integration
async def test_payload_carries_completed_at_and_last_interacted_at(db_session) -> None:
    world = await _world(db_session)
    task = await world.task("stamped", state=TaskStateEnum.READY, completed_at=_at(30))
    step = await world.step(task, "stamped", world.section_a)
    await world.record(step, "stamped", state=TaskStepStateEnum.WORKING, entered_at=_at(45))
    await world.task("bare")

    result = await list_tasks(_ctx(world, order_by="last_interacted"))
    by_id = {item["task"]["client_id"]: item for item in result["tasks_pagination"]["items"]}

    stamped = by_id[f"tsk_{world.suffix}_stamped"]
    assert stamped["task"]["completed_at"] == _at(30).isoformat()
    assert stamped["last_interacted_at"] == _at(45).isoformat()

    bare = by_id[f"tsk_{world.suffix}_bare"]
    assert bare["task"]["completed_at"] is None
    assert bare["last_interacted_at"] is None


@pytest.mark.integration
async def test_payload_last_interacted_at_respects_the_section_scope(db_session) -> None:
    """The payload value must be computed under the same rules as the ORDER BY, or the
    number shown will contradict the order it is shown in."""
    world = await _world(db_session)
    task = await world.task("one")
    step_a = await world.step(task, "one_a", world.section_a)
    step_b = await world.step(task, "one_b", world.section_b)
    await world.record(step_a, "one_a", state=TaskStepStateEnum.WORKING, entered_at=_at(10))
    await world.record(step_b, "one_b", state=TaskStepStateEnum.WORKING, entered_at=_at(90))

    unscoped = await list_tasks(_ctx(world))
    scoped = await list_tasks(_ctx(world, working_section_ids=world.section_a.client_id))

    assert unscoped["tasks_pagination"]["items"][0]["last_interacted_at"] == _at(90).isoformat()
    assert scoped["tasks_pagination"]["items"][0]["last_interacted_at"] == _at(10).isoformat()


@pytest.mark.integration
async def test_payload_keys_are_present_under_the_default_ordering(db_session) -> None:
    """Both keys are computed unconditionally: a key that appears only under a particular
    order_by is the kind of thing a client caches wrong."""
    world = await _world(db_session)
    await world.task("only")

    result = await list_tasks(_ctx(world))
    item = result["tasks_pagination"]["items"][0]

    assert "last_interacted_at" in item
    assert "completed_at" in item["task"]
