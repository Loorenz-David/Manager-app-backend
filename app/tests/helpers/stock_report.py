from dataclasses import dataclass
from uuid import uuid4
from sqlalchemy import delete, select
from beyo_manager.domain.items.enums import ItemStateEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import (
    TaskStateEnum,
    TaskTypeEnum,
    TaskItemRoleEnum,
)
from beyo_manager.models.tables.execution.execution_payload import ExecutionPayload
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.stock_report.stock_report_history_record import (
    StockReportHistoryRecord,
)
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_report_item_snapshot import (
    StockReportItemSnapshot,
)
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext


@dataclass(frozen=True)
class SeededWorkspace:
    workspace: Workspace
    manager: User
    worker: User
    categories: tuple[ItemCategory, ItemCategory]
    item: Item
    task: Task


async def seed_stock_report_workspace(session, *, suffix=None):
    suffix = suffix or uuid4().hex[:10]
    manager = User(
        client_id=f"usr_sm_{suffix}",
        username=f"sr-manager-{suffix}",
        email=f"sr-manager-{suffix}@example.com",
        password="test",
    )
    worker = User(
        client_id=f"usr_sw_{suffix}",
        username=f"sr-worker-{suffix}",
        email=f"sr-worker-{suffix}@example.com",
        password="test",
    )
    workspace = Workspace(client_id=f"ws_sr_{suffix}", name=f"Stock report {suffix}")
    session.add_all([manager, worker, workspace])
    await session.flush()
    categories = (
        ItemCategory(
            client_id=f"itc_sr_a_{suffix}",
            workspace_id=workspace.client_id,
            name="Dining Chairs",
            major_category=ItemMajorCategoryEnum.SEAT,
        ),
        ItemCategory(
            client_id=f"itc_sr_b_{suffix}",
            workspace_id=workspace.client_id,
            name="Coffee Tables",
            major_category=ItemMajorCategoryEnum.WOOD,
        ),
    )
    session.add_all(categories)
    await session.flush()
    item = Item(
        client_id=f"itm_sr_{suffix}",
        workspace_id=workspace.client_id,
        article_number=f"SR-{suffix}",
        state=ItemStateEnum.PENDING,
        quantity=4,
        item_category_id=categories[0].client_id,
        properties={"wood_type": "Teak", "upholstery": "Down"},
    )
    task = Task(
        client_id=f"tsk_sr_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=manager.client_id,
    )
    session.add_all([item, task])
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_sr_{suffix}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=manager.client_id,
        )
    )
    await session.flush()
    return SeededWorkspace(workspace, manager, worker, categories, item, task)


def make_ctx(
    session,
    seeded,
    *,
    role_name="manager",
    user=None,
    incoming_data=None,
    query_params=None,
):
    user = user or seeded.manager
    return ServiceContext(
        identity={
            "workspace_id": seeded.workspace.client_id,
            "user_id": user.client_id,
            "role_name": role_name,
        },
        incoming_data=incoming_data or {},
        query_params=query_params or {},
        session=session,
    )


def capture_dispatch(monkeypatch, import_site: str) -> list:
    """Capture events dispatched by a command module that imported ``dispatch``."""
    captured = []

    async def _capture(events):
        captured.extend(events)

    monkeypatch.setattr(import_site, _capture)
    return captured


async def create_snapshot_version(session, workspace_id, *, now, user_id=None):
    """Open a board version through the shipped command (closes the previous one)."""
    from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
        create_stock_report_snapshot_version,
    )

    return await create_stock_report_snapshot_version(
        ServiceContext(
            identity={
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role_name": "manager",
            },
            incoming_data={},
            session=session,
            now=now,
        )
    )


async def ensure_active_snapshots(session, workspace_id, *, now, user_id=None):
    """Every live row of the workspace has an active snapshot afterwards.

    Creates a version through the shipped command when the workspace has none; a
    row minted **after** that version (a fixture seeding in two steps) gets its
    snapshot inserted directly into the active version — a test-only seam, the
    production path being "the next version picks it up".
    """
    version_id = await session.scalar(
        select(StockReportSnapshotVersion.client_id).where(
            StockReportSnapshotVersion.workspace_id == workspace_id,
            StockReportSnapshotVersion.active_at.is_not(None),
            StockReportSnapshotVersion.closed_at.is_(None),
        )
    )
    if version_id is None:
        result = await create_snapshot_version(
            session, workspace_id, now=now, user_id=user_id
        )
        return result["stock_report_snapshot_version"]["client_id"]
    covered = select(StockReportItemSnapshot.stock_report_item_id).where(
        StockReportItemSnapshot.workspace_id == workspace_id,
        StockReportItemSnapshot.active_at.is_not(None),
        StockReportItemSnapshot.closed_at.is_(None),
    )
    orphans = (
        await session.execute(
            select(StockReportItem).where(
                StockReportItem.workspace_id == workspace_id,
                StockReportItem.is_deleted.is_(False),
                StockReportItem.client_id.not_in(covered),
            )
        )
    ).scalars().all()
    for row in orphans:
        session.add(
            StockReportItemSnapshot(
                workspace_id=workspace_id,
                version_id=version_id,
                stock_report_item_id=row.client_id,
                quantity_requested_scanner=row.quantity_requested,
                quantity_requested_manual=None,
                quantity_in_queue=row.quantity_in_queue,
                quantity_in_progress=row.quantity_in_progress,
                quantity_awaiting=row.quantity_awaiting,
                quantity_missing=0,
                active_at=now,
                created_at=now,
            )
        )
    await session.flush()
    return version_id


async def set_snapshot_position(session, row_id, priority, order):
    """Raw-SQL seed of a row's **active** snapshot position (the fixture shape the
    ordering tests used on the row before 2026-09-26)."""
    from sqlalchemy import text

    await session.execute(
        text(
            "UPDATE stock_report_item_snapshots SET priority = :priority, "
            "priority_order = :order WHERE stock_report_item_id = :row_id "
            "AND active_at IS NOT NULL AND closed_at IS NULL"
        ),
        {"priority": priority, "order": order, "row_id": row_id},
    )


async def active_snapshot(session, row_id):
    """The row's snapshot in the **active** version (the pair, never a draft's)."""
    return await session.scalar(
        select(StockReportItemSnapshot)
        .where(
            StockReportItemSnapshot.stock_report_item_id == row_id,
            StockReportItemSnapshot.active_at.is_not(None),
            StockReportItemSnapshot.closed_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )


async def latest_snapshot(session, row_id):
    """The row's newest snapshot, active or closed (a deleted row's closed one)."""
    return await session.scalar(
        select(StockReportItemSnapshot)
        .where(StockReportItemSnapshot.stock_report_item_id == row_id)
        .order_by(
            StockReportItemSnapshot.created_at.desc(),
            StockReportItemSnapshot.client_id.desc(),
        )
        .limit(1)
        .execution_options(populate_existing=True)
    )


async def snapshot_positions(session, workspace_id, *, include_closed=False):
    """`row_id -> (priority value | None, priority_order)` over the workspace's
    active snapshots (or every snapshot when `include_closed`)."""
    statement = select(
        StockReportItemSnapshot.stock_report_item_id,
        StockReportItemSnapshot.priority,
        StockReportItemSnapshot.priority_order,
    ).where(StockReportItemSnapshot.workspace_id == workspace_id)
    if not include_closed:
        statement = statement.where(StockReportItemSnapshot.closed_at.is_(None))
    return {
        row_id: (priority.value if priority is not None else None, order)
        for row_id, priority, order in (await session.execute(statement)).all()
    }


async def snapshot_id_of(session, row_id):
    snapshot = await latest_snapshot(session, row_id)
    return snapshot.client_id if snapshot is not None else None


async def assert_stock_report_clean(session, workspace_id):
    from beyo_manager.services.queries.stock_report.consistency import (
        compute_stock_report_divergences,
    )

    assert await compute_stock_report_divergences(session, workspace_id) == []
    assert (
        await session.execute(
            select(StockReportRepairRecord).where(
                StockReportRepairRecord.workspace_id == workspace_id
            )
        )
    ).scalars().all() == []


async def purge_stock_report_workspace(session, workspace_id):
    """Remove the stock-report seed graph in FK-safe order for committing tests.

    Guarantee (plan §9, Q-11a): the workspace's version rows and everything hanging
    off them go, **including** the `delayed_schedulers` rows whose
    `event_client_id` is one of its versions and the execution tasks and payloads
    those schedulers produced — neither table has a workspace column, so this is
    the only place they are cleaned. Every test that creates a scheduler row
    purges in `finally`.
    """
    version_ids = (
        await session.scalars(
            select(StockReportSnapshotVersion.client_id).where(
                StockReportSnapshotVersion.workspace_id == workspace_id
            )
        )
    ).all()
    if version_ids:
        scheduler_ids = (
            await session.scalars(
                select(DelayedScheduler.client_id).where(
                    DelayedScheduler.event_client_id.in_(version_ids)
                )
            )
        ).all()
        if scheduler_ids:
            task_ids = (
                await session.scalars(
                    select(ExecutionPayload.execution_task_id).where(
                        ExecutionPayload.origin_id.in_(scheduler_ids)
                    )
                )
            ).all()
            await session.execute(
                delete(ExecutionPayload).where(
                    ExecutionPayload.origin_id.in_(scheduler_ids)
                )
            )
            if task_ids:
                await session.execute(
                    delete(ExecutionTask).where(ExecutionTask.client_id.in_(task_ids))
                )
            await session.execute(
                delete(DelayedScheduler).where(
                    DelayedScheduler.client_id.in_(scheduler_ids)
                )
            )
    for model in (
        StockReportRepairRecord,
        StockTaskAssignment,
        StockReportHistoryRecord,
        StockReportItemSnapshot,
        StockReportSnapshotVersion,
        StockReportItem,
        TaskItem,
        Task,
        Item,
        ItemCategory,
    ):
        await session.execute(delete(model).where(model.workspace_id == workspace_id))
    await session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
    if workspace_id.startswith("ws_sr_"):
        suffix = workspace_id.removeprefix("ws_sr_")
        await session.execute(
            delete(User).where(
                User.client_id.in_((f"usr_sm_{suffix}", f"usr_sw_{suffix}"))
            )
        )
