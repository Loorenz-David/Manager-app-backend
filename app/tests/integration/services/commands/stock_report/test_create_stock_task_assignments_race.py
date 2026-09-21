"""Plan 8 C5(a) — the Item lock serializes two concurrent `CR` calls naming the same
item on two different rows/tasks (MC-4 error contract). Precedent:
`test_apply_stock_demand.py`'s C5 tests (`asyncio.Barrier`, a second `get_db_session()`).

C5(b) (opposite-order two-item lock acquisition, owner card C / L-29) is not built
here — see the implementer handoff for why.
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.services.commands.stock_report.create_stock_task_assignments import (
    create_stock_task_assignments,
)
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    make_ctx,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


async def _make_row(session, seeded, suffix, *, criteria=None):
    criteria = criteria if criteria is not None else {"wood_group": ["teak"]}
    row = StockReportItem(
        workspace_id=seeded.workspace.client_id,
        item_category_id=seeded.categories[0].client_id,
        properties=criteria,
        properties_signature=compute_stock_criteria_signature(criteria),
        quantity_requested=1,
        client_id=f"sri_race_{suffix}_{seeded.workspace.client_id}",
    )
    session.add(row)
    await session.flush()
    return row


async def _second_task(session, seeded, suffix):
    from sqlalchemy import func

    from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
    from beyo_manager.models.tables.tasks.task import Task
    from beyo_manager.models.tables.tasks.task_item import TaskItem
    from beyo_manager.domain.tasks.enums import TaskItemRoleEnum

    next_scalar_id = (
        await session.scalar(
            select(func.max(Task.task_scalar_id)).where(
                Task.workspace_id == seeded.workspace.client_id
            )
        )
        or 0
    ) + 1
    task = Task(
        client_id=f"tsk_race_{suffix}_{seeded.workspace.client_id}",
        workspace_id=seeded.workspace.client_id,
        task_scalar_id=next_scalar_id,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=seeded.manager.client_id,
    )
    session.add(task)
    await session.flush()
    session.add(
        TaskItem(
            client_id=f"tim_race_{suffix}_{seeded.workspace.client_id}",
            workspace_id=seeded.workspace.client_id,
            task_id=task.client_id,
            item_id=seeded.item.client_id,
            role=TaskItemRoleEnum.PRIMARY,
            created_by_id=seeded.manager.client_id,
        )
    )
    await session.flush()
    return task


async def test_c5a_concurrent_create_on_the_same_item_leaves_exactly_one_active(db_session):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        row1 = await _make_row(db_session, seeded, "r1", criteria={"wood_group": ["teak"]})
        row2 = await _make_row(db_session, seeded, "r2", criteria={})
        task2 = await _second_task(db_session, seeded, "t2")
        item_client_id = seeded.item.client_id
        task1_client_id = seeded.task.client_id
        task2_client_id = task2.client_id
        row1_client_id = row1.client_id
        row2_client_id = row2.client_id
        await db_session.commit()

        barrier = asyncio.Barrier(2)

        entries_a = [
            {
                "stock_report_item_id": row1_client_id,
                "task_id": task1_client_id,
                "item_id": item_client_id,
                "override_property_mismatch": False,
            }
        ]
        entries_b = [
            {
                "stock_report_item_id": row2_client_id,
                "task_id": task2_client_id,
                "item_id": item_client_id,
                "override_property_mismatch": False,
            }
        ]

        async def _run_a():
            ctx = make_ctx(
                db_session, seeded, role_name="worker", incoming_data={"entries": entries_a}
            )
            await barrier.wait()
            try:
                return await create_stock_task_assignments(ctx), None
            except (StockAssignmentRefused, StockAssignmentPropertyMismatch) as exc:
                return None, exc

        async def _run_b():
            async for session2 in get_db_session():
                seeded_for_b = seeded
                ctx = make_ctx(
                    session2,
                    seeded_for_b,
                    role_name="worker",
                    incoming_data={"entries": entries_b},
                )
                await barrier.wait()
                try:
                    return await create_stock_task_assignments(ctx), None
                except (StockAssignmentRefused, StockAssignmentPropertyMismatch) as exc:
                    return None, exc
            raise AssertionError("Database session generator yielded no session")

        (result_a, error_a), (result_b, error_b) = await asyncio.wait_for(
            asyncio.gather(_run_a(), _run_b()), timeout=10
        )

        outcomes = [(result_a, error_a), (result_b, error_b)]
        winners = [r for r, e in outcomes if r is not None]
        losers = [e for r, e in outcomes if e is not None]
        assert len(winners) == 1
        assert len(losers) == 1
        assert losers[0].details == [{"index": 0, "reason": "item_already_assigned"}]

        active = (
            (
                await db_session.execute(
                    select(StockTaskAssignment).where(
                        StockTaskAssignment.workspace_id == workspace_id,
                        StockTaskAssignment.item_id == item_client_id,
                        StockTaskAssignment.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(active) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
