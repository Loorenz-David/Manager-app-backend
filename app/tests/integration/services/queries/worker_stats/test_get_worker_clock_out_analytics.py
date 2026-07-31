from datetime import datetime, timedelta, timezone
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import event as sa_event, select

from beyo_manager.domain.analytics.linear_timeline import UNSPECIFIED_REASON
from beyo_manager.domain.images.enums import (
    ImageLinkEntityTypeEnum,
    ImageSourceTypeEnum,
    ImageStorageProviderEnum,
)
from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.tasks.step_state_record import StepStateRecord
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.worker_stats.get_worker_clock_out_analytics import (
    get_worker_clock_out_analytics,
)
from beyo_manager.services.queries.worker_stats.list_workers_linear_timeline import (
    build_recorded_shift_timeline,
    load_recorded_shift_records,
)


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


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


def _ctx(db_session, workspace_id: str) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": "usr_manager",
            "role_name": "manager",
        },
        incoming_data={},
        session=db_session,
    )


async def _seed_completed_item(db_session, workspace_id: str, worker_id: str) -> tuple[Item, TaskStep]:
    suffix = uuid4().hex
    section = WorkingSection(workspace_id=workspace_id, name=f"Assembly-{suffix}")
    task = Task(
        workspace_id=workspace_id,
        task_scalar_id=int(suffix[:7], 16),
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        created_by_id=worker_id,
    )
    item = Item(
        workspace_id=workspace_id,
        article_number=f"ART-{suffix[:6]}",
        sku=f"SKU-{suffix[:6]}",
        quantity=4,
        state=ItemStateEnum.PENDING,
    )
    db_session.add_all([section, task, item])
    await db_session.flush()
    db_session.add(
        TaskItem(
            workspace_id=workspace_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
        )
    )
    step = TaskStep(
        workspace_id=workspace_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        working_section_name_snapshot=section.name,
        state=TaskStepStateEnum.COMPLETED,
        total_working_seconds=1200,
        total_pause_seconds=900,
        total_ended_shift_seconds=259200,
        created_by_id=worker_id,
    )
    db_session.add(step)
    await db_session.flush()
    return item, step


def _shift_record(
    db_session,
    workspace_id: str,
    worker_id: str,
    state: UserShiftStateEnum,
    entered_at: datetime,
    exited_at: datetime,
    reason: str | None = None,
) -> None:
    db_session.add(
        UserShiftStateRecord(
            workspace_id=workspace_id,
            user_id=worker_id,
            state=state,
            entered_at=entered_at,
            exited_at=exited_at,
            reason=reason,
        )
    )


async def _completed_record(
    db_session,
    workspace_id: str,
    worker_id: str,
    step_id: str,
    completed_at: datetime,
) -> None:
    db_session.add(
        StepStateRecord(
            workspace_id=workspace_id,
            step_id=step_id,
            state=TaskStepStateEnum.COMPLETED,
            entered_at=completed_at,
            exited_at=completed_at,
            created_by_id=worker_id,
            credited_user_id=worker_id,
        )
    )
    await db_session.flush()


async def test_clock_out_analytics_uses_recorded_timeline_and_batched_item_data(
    db_session,
    executed_statements,
) -> None:
    workspace = Workspace(name=f"clock-out-analytics-{uuid4().hex}")
    worker = User(
        username=f"analytics-worker-{uuid4().hex}",
        email=f"analytics-worker-{uuid4().hex}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    item, step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
    pause_reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Cleaning",
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=worker.client_id,
    )
    db_session.add(pause_reason)
    await db_session.flush()

    clock_out_at = datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc)
    today_start = clock_out_at.replace(hour=8, minute=0)
    pause_start = today_start + timedelta(hours=1)
    idle_start = pause_start + timedelta(minutes=15)
    _shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.WORKING,
        today_start,
        pause_start,
    )
    _shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IN_PAUSE,
        pause_start,
        idle_start,
        pause_reason.client_id,
    )
    _shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.IDLE,
        idle_start,
        clock_out_at,
    )
    previous_day_start = today_start - timedelta(days=1)
    _shift_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        UserShiftStateEnum.WORKING,
        previous_day_start,
        previous_day_start + timedelta(hours=1),
    )
    await _completed_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        today_start + timedelta(minutes=59),
    )
    await _completed_record(
        db_session,
        workspace.client_id,
        worker.client_id,
        step.client_id,
        previous_day_start + timedelta(minutes=59),
    )

    ctx = _ctx(db_session, workspace.client_id)
    del executed_statements[:]
    analytics = await get_worker_clock_out_analytics(ctx, worker.client_id, clock_out_at)
    one_item_query_count = len(executed_statements)

    # One range timeline read, completion/mapping reads, and four batched metadata
    # reads are the complete composite budget. This catches a fixed seven-day loop
    # that a one-item-versus-three-item comparison alone cannot detect.
    assert one_item_query_count <= 11

    assert set(analytics) == {
        "date",
        "timeline",
        "pause_reasons",
        "completed_items",
        "completed_items_truncated",
        "week",
        "rate",
    }
    records = (
        await load_recorded_shift_records(
            ctx,
            [worker.client_id],
            clock_out_at.replace(hour=0, minute=0, second=0, microsecond=0),
            clock_out_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
        )
    )[worker.client_id]
    expected_timeline = build_recorded_shift_timeline(
        records,
        clock_out_at.replace(hour=0, minute=0, second=0, microsecond=0),
        clock_out_at.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
        clock_out_at,
    )
    assert analytics["timeline"] == {
        "working_seconds": expected_timeline.working_seconds,
        "pause_seconds": expected_timeline.paused_seconds,
        "idle_seconds": expected_timeline.idle_seconds,
        "pause_by_reason": expected_timeline.pause_by_reason,
    }
    assert analytics["pause_reasons"] == {
        pause_reason.client_id: {
            "name": "Cleaning",
            "image_url": None,
            "pause_type": "personal",
        }
    }
    assert analytics["completed_items"] == [
        {
            "item_id": item.client_id,
            "reference": item.article_number,
            "image_url": None,
            "working_section": {
                "client_id": step.working_section_id,
                "name": step.working_section_name_snapshot,
            },
            "units": 4,
            "total_seconds": 1200,
            "issues_count": 0,
        }
    ]
    assert analytics["completed_items_truncated"] is False
    assert len(analytics["week"]["days"]) == 7
    assert analytics["week"]["days"][0]["date"] == "2026-07-27"
    assert analytics["week"]["totals"] == {
        "working_seconds": 7200,
        "pause_seconds": 900,
        "idle_seconds": 900,
    }
    assert analytics["rate"] == {
        "units_per_hour": 4.0,
        "baseline_units_per_hour": 4.0,
        "baseline_days": 1,
    }

    # This is a query-count mutation guard: changing any item metadata load to run
    # inside the item loop makes the three-item execution exceed this one-item count.
    for _ in range(2):
        extra_item, extra_step = await _seed_completed_item(
            db_session,
            workspace.client_id,
            worker.client_id,
        )
        assert extra_item.client_id
        await _completed_record(
            db_session,
            workspace.client_id,
            worker.client_id,
            extra_step.client_id,
            today_start + timedelta(minutes=58),
        )
    del executed_statements[:]
    await get_worker_clock_out_analytics(ctx, worker.client_id, clock_out_at)

    assert len(executed_statements) == one_item_query_count


async def test_completed_cards_are_deduplicated_and_use_primary_task_item(db_session) -> None:
    workspace = Workspace(name=f"clock-out-dedup-{uuid4().hex}")
    worker = User(username=f"dedup-{uuid4().hex}", email=f"dedup-{uuid4().hex}@example.com", password="hash")
    other_worker = User(username=f"dedup-other-{uuid4().hex}", email=f"dedup-other-{uuid4().hex}@example.com", password="hash")
    db_session.add_all([workspace, worker, other_worker])
    await db_session.flush()
    primary, step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
    secondary = Item(workspace_id=workspace.client_id, article_number=f"SECONDARY-{uuid4().hex}", quantity=99)
    db_session.add(secondary)
    await db_session.flush()
    db_session.add(TaskItem(workspace_id=workspace.client_id, task_id=step.task_id, item_id=secondary.client_id, role=TaskItemRoleEnum.RELATED))
    clock_out_at = datetime(2026, 8, 3, 0, 10, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id, UserShiftStateEnum.WORKING, clock_out_at - timedelta(minutes=10), clock_out_at)
    await _completed_record(db_session, workspace.client_id, worker.client_id, step.client_id, clock_out_at - timedelta(minutes=2))
    await _completed_record(db_session, workspace.client_id, worker.client_id, step.client_id, clock_out_at - timedelta(minutes=1))
    await _completed_record(db_session, workspace.client_id, other_worker.client_id, step.client_id, clock_out_at - timedelta(minutes=1))

    analytics = await get_worker_clock_out_analytics(_ctx(db_session, workspace.client_id), worker.client_id, clock_out_at)

    assert analytics["date"] == "2026-08-03"
    assert analytics["week"]["days"][0]["date"] == "2026-08-03"
    assert [card["item_id"] for card in analytics["completed_items"]] == [primary.client_id]
    assert analytics["completed_items"][0]["total_seconds"] == step.total_working_seconds
    assert analytics["rate"]["units_per_hour"] == 24.0


async def test_completed_cards_resolve_metadata_and_ignore_deleted_related_rows(db_session) -> None:
    workspace = Workspace(name=f"clock-out-metadata-{uuid4().hex}")
    worker = User(username=f"metadata-{uuid4().hex}", email=f"metadata-{uuid4().hex}@example.com", password="hash")
    db_session.add_all([workspace, worker])
    await db_session.flush()
    article_item, article_step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
    sku_item, sku_step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
    null_item, null_step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
    sku_item.article_number = None
    null_item.article_number = None
    null_item.sku = None
    article_step.working_section_name_snapshot = None
    section = await db_session.get(WorkingSection, article_step.working_section_id)
    assert section is not None
    section.is_deleted = True
    live_image = Image(image_url="https://images.example/first.jpg", storage_provider=ImageStorageProviderEnum.EXTERNAL, source_type=ImageSourceTypeEnum.EXTERNAL_URL, created_by_id=worker.client_id)
    later_image = Image(image_url="https://images.example/later.jpg", storage_provider=ImageStorageProviderEnum.EXTERNAL, source_type=ImageSourceTypeEnum.EXTERNAL_URL, created_by_id=worker.client_id)
    deleted_image = Image(image_url="https://images.example/deleted.jpg", storage_provider=ImageStorageProviderEnum.EXTERNAL, source_type=ImageSourceTypeEnum.EXTERNAL_URL, created_by_id=worker.client_id, deleted_at=datetime.now(timezone.utc))
    db_session.add_all([live_image, later_image, deleted_image])
    await db_session.flush()
    db_session.add_all([
        ImageLink(image_id=later_image.client_id, entity_type=ImageLinkEntityTypeEnum.ITEM, entity_client_id=article_item.client_id, display_order=2),
        ImageLink(image_id=live_image.client_id, entity_type=ImageLinkEntityTypeEnum.ITEM, entity_client_id=article_item.client_id, display_order=1),
        ImageLink(image_id=deleted_image.client_id, entity_type=ImageLinkEntityTypeEnum.ITEM, entity_client_id=sku_item.client_id, display_order=0),
    ])
    category = await db_session.scalar(select(ItemCategory).where(ItemCategory.workspace_id == workspace.client_id).limit(1))
    if category is None:
        from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
        category = ItemCategory(workspace_id=workspace.client_id, name=f"cat-{uuid4().hex}", major_category=ItemMajorCategoryEnum.WOOD)
        db_session.add(category)
        await db_session.flush()
    db_session.add_all([
        ItemIssue(workspace_id=workspace.client_id, item_id=article_item.client_id, step_id=article_step.client_id, worker_id=worker.client_id, working_section_id=article_step.working_section_id, item_category_id=category.client_id, issue_type_snapshot="Scratch", intensity=1),
        ItemIssue(workspace_id=workspace.client_id, item_id=article_item.client_id, step_id=article_step.client_id, worker_id=worker.client_id, working_section_id=article_step.working_section_id, item_category_id=category.client_id, issue_type_snapshot="Stain", intensity=2),
    ])
    clock_out_at = datetime(2026, 7, 31, 10, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id, UserShiftStateEnum.WORKING, clock_out_at - timedelta(hours=1), clock_out_at)
    for step in (article_step, sku_step, null_step):
        await _completed_record(db_session, workspace.client_id, worker.client_id, step.client_id, clock_out_at - timedelta(minutes=1))

    cards = {card["item_id"]: card for card in (await get_worker_clock_out_analytics(_ctx(db_session, workspace.client_id), worker.client_id, clock_out_at))["completed_items"]}

    assert cards[article_item.client_id]["reference"] == article_item.article_number
    assert cards[sku_item.client_id]["reference"] == sku_item.sku
    assert cards[null_item.client_id]["reference"] is None
    assert cards[article_item.client_id]["image_url"] == live_image.image_url
    assert cards[sku_item.client_id]["image_url"] is None
    assert cards[null_item.client_id]["image_url"] is None
    assert cards[article_item.client_id]["issues_count"] == 2
    assert cards[article_item.client_id]["working_section"] is None


async def test_clock_out_analytics_limits_cards_and_keeps_actor_data_out(db_session) -> None:
    workspace = Workspace(name=f"clock-out-target-{uuid4().hex}")
    worker = User(username=f"target-{uuid4().hex}", email=f"target-{uuid4().hex}@example.com", password="hash")
    manager = User(username=f"actor-{uuid4().hex}", email=f"actor-{uuid4().hex}@example.com", password="hash")
    db_session.add_all([workspace, worker, manager])
    await db_session.flush()
    clock_out_at = datetime(2026, 7, 27, 0, 10, tzinfo=timezone.utc)
    _shift_record(db_session, workspace.client_id, worker.client_id, UserShiftStateEnum.WORKING, clock_out_at - timedelta(minutes=20), clock_out_at)
    _shift_record(db_session, workspace.client_id, manager.client_id, UserShiftStateEnum.WORKING, clock_out_at - timedelta(minutes=20), clock_out_at)
    manager_item, manager_step = await _seed_completed_item(db_session, workspace.client_id, manager.client_id)
    await _completed_record(db_session, workspace.client_id, manager.client_id, manager_step.client_id, clock_out_at - timedelta(minutes=1))
    worker_items: list[str] = []
    for _ in range(101):
        item, step = await _seed_completed_item(db_session, workspace.client_id, worker.client_id)
        worker_items.append(item.client_id)
        await _completed_record(db_session, workspace.client_id, worker.client_id, step.client_id, clock_out_at - timedelta(minutes=1))

    other_workspace = Workspace(name=f"clock-out-other-{uuid4().hex}")
    db_session.add(other_workspace)
    await db_session.flush()
    foreign_item, foreign_step = await _seed_completed_item(
        db_session,
        other_workspace.client_id,
        worker.client_id,
    )
    await _completed_record(
        db_session,
        other_workspace.client_id,
        worker.client_id,
        foreign_step.client_id,
        clock_out_at - timedelta(minutes=1),
    )

    started_at = perf_counter()
    analytics = await get_worker_clock_out_analytics(_ctx(db_session, workspace.client_id), worker.client_id, clock_out_at)
    elapsed_ms = (perf_counter() - started_at) * 1000

    returned_ids = {card["item_id"] for card in analytics["completed_items"]}
    assert analytics["date"] == "2026-07-27"
    assert analytics["week"]["days"][0]["date"] == "2026-07-27"
    assert analytics["completed_items_truncated"] is True
    assert len(returned_ids) == 100
    assert returned_ids <= set(worker_items)
    assert manager_item.client_id not in returned_ids
    assert foreign_item.client_id not in returned_ids
    assert elapsed_ms < 500
    print(f"clock-out analytics 101-item fixture: {elapsed_ms:.1f} ms")
    assert analytics["week"]["totals"] == {
        key: sum(day[key] for day in analytics["week"]["days"])
        for key in ("working_seconds", "pause_seconds", "idle_seconds")
    }


async def test_pause_reasons_resolves_every_timeline_key_including_unspecified(db_session) -> None:
    # A pause recorded without a reason buckets under UNSPECIFIED_REASON, which is not a
    # PauseReason client_id and so cannot be looked up in the table. Every key present in
    # timeline.pause_by_reason must still have an entry in the pause_reasons map.
    workspace = Workspace(name=f"clock-out-unspecified-{uuid4().hex}")
    worker = User(
        username=f"unspecified-{uuid4().hex}",
        email=f"unspecified-{uuid4().hex}@example.com",
        password="hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()
    named_reason = PauseReason(
        workspace_id=workspace.client_id,
        name="Cleaning",
        pause_type=PauseTypeEnum.PERSONAL,
        created_by_id=worker.client_id,
    )
    db_session.add(named_reason)
    await db_session.flush()

    clock_out_at = datetime(2026, 7, 31, 10, tzinfo=timezone.utc)
    shift_start = clock_out_at - timedelta(hours=1)
    named_pause_start = shift_start + timedelta(minutes=10)
    null_pause_start = named_pause_start + timedelta(minutes=10)
    working_again = null_pause_start + timedelta(minutes=10)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.WORKING, shift_start, named_pause_start)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, named_pause_start, null_pause_start,
                  named_reason.client_id)
    # No reason recorded — this is the bucket that has no row to resolve against.
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.IN_PAUSE, null_pause_start, working_again, None)
    _shift_record(db_session, workspace.client_id, worker.client_id,
                  UserShiftStateEnum.WORKING, working_again, clock_out_at)
    await db_session.flush()

    analytics = await get_worker_clock_out_analytics(
        _ctx(db_session, workspace.client_id), worker.client_id, clock_out_at
    )

    assert UNSPECIFIED_REASON in analytics["timeline"]["pause_by_reason"]
    assert named_reason.client_id in analytics["timeline"]["pause_by_reason"]
    missing = set(analytics["timeline"]["pause_by_reason"]) - set(analytics["pause_reasons"])
    assert missing == set(), f"pause_by_reason keys without a pause_reasons entry: {missing}"
    assert analytics["pause_reasons"][UNSPECIFIED_REASON] == {
        "name": "Reason unavailable",
        "image_url": None,
        "pause_type": None,
    }
    assert analytics["pause_reasons"][named_reason.client_id]["name"] == "Cleaning"


async def test_clock_out_analytics_returns_no_completed_items_for_an_empty_day(db_session) -> None:
    workspace = Workspace(name=f"clock-out-analytics-empty-{uuid4().hex}")
    worker = User(
        username=f"analytics-empty-{uuid4().hex}",
        email=f"analytics-empty-{uuid4().hex}@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, worker])
    await db_session.flush()

    analytics = await get_worker_clock_out_analytics(
        _ctx(db_session, workspace.client_id),
        worker.client_id,
        datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc),
    )

    assert analytics["completed_items"] == []
    assert analytics["completed_items_truncated"] is False
    assert analytics["rate"] == {
        "units_per_hour": 0.0,
        "baseline_units_per_hour": None,
        "baseline_days": 0,
    }