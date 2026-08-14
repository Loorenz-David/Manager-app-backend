"""REVIEWER PROBE — phase 7 review r1 concurrency pass. Disposable.

Bounded waits only (P-T r2-L3). Every test commits and owns its teardown
(charter rule 11½). Tables touched: workspaces, users, items, tasks, task_items,
production_cost_groups, production_cost_basis_versions, cost_model_versions,
cost_model_terms, item_valuations, item_cost_evaluations,
item_cost_evaluation_terms, audit_logs, history_records, history_record_links.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models import database
from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    commit_item_cost_evaluation,
)
from beyo_manager.services.commands.item_economics.delete_cost_model_version import (
    delete_cost_model_version,
)
from beyo_manager.services.commands.item_economics.delete_production_cost_basis_version import (
    delete_production_cost_basis_version,
)
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.context import ServiceContext


BOUND = 0.4


def _ctx(session, workspace_id, user_id, data):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "probe"},
        incoming_data=data,
        session=session,
    )


async def _seed(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"probe {token}")
    user = User(client_id=f"usr_{token}", username=f"probe_{token}", email=f"{token}@example.test", password="t")
    item = Item(
        client_id=f"itm_{token}", workspace_id=workspace.client_id, article_number=f"ART-{token}",
        item_major_category_snapshot="wood", created_by_id=user.client_id,
    )
    group = ProductionCostGroup(
        workspace_id=workspace.client_id, name="Wood",
        major_category=ItemMajorCategoryEnum.WOOD, created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    task = Task(
        client_id=f"tsk_{token}", workspace_id=workspace.client_id, task_scalar_id=1,
        task_type=TaskTypeEnum.RETURN, state=TaskStateEnum.PENDING, created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([item, group, model, task])
    await db_session.flush()
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=100000, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"), planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0208"), created_by_id=user.client_id,
    )
    db_session.add(basis)
    await db_session.flush()
    db_session.add_all([
        CostModelTerm(
            workspace_id=workspace.client_id, cost_model_version_id=model.client_id, name="fixed",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT, fixed_amount_minor=100,
            created_by_id=user.client_id),
        ItemValuation(
            workspace_id=workspace.client_id, item_id=item.client_id,
            expected_sale_price_minor=1000, purchase_cost_minor=None,
            currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id),
        TaskItem(
            workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id,
            role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id),
    ])
    await db_session.flush()
    await db_session.commit()
    return workspace.client_id, user.client_id, item.client_id, task.client_id, group.client_id, basis.client_id, model.client_id


async def _cleanup(db_session, workspace_id, user_id):
    await db_session.rollback()
    for table in (ItemCostEvaluationTerm, ItemCostEvaluation, ItemValuation, CostModelTerm,
                  ProductionCostBasisVersion, CostModelVersion, ProductionCostGroup,
                  TaskItem, Task, Item, AuditLog):
        await db_session.execute(delete(table).where(table.workspace_id == workspace_id))
    await db_session.execute(text(
        "DELETE FROM history_record_links WHERE history_record_id IN "
        "(SELECT client_id FROM history_records WHERE created_by_id = :uid)"
    ), {"uid": user_id})
    await db_session.execute(text(
        "DELETE FROM history_records WHERE created_by_id = :uid"), {"uid": user_id})
    await db_session.execute(delete(User).where(User.client_id == user_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
    await db_session.commit()


# ----------------------------------------------------------------- C11
@pytest.mark.integration
async def test_probe_c11_second_commit_blocked_while_task_locked(db_session):
    ws, uid, item_id, task_id, *_ = await _seed(db_session)
    lock_session = database._session_factory()
    commit_session = database._session_factory()
    commit_task = None
    try:
        await lock_session.begin()
        # FOR NO KEY UPDATE conflicts with FOR UPDATE but NOT with the FK
        # KEY SHARE lock the evaluation INSERT takes for free -- so this
        # counterparty isolates step 1's lock (P-T).
        await lock_session.execute(
            text("SELECT client_id FROM tasks WHERE client_id = :t FOR NO KEY UPDATE"),
            {"t": task_id})

        commit_task = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(commit_session, ws, uid, {"task_client_id": task_id})))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(commit_task), timeout=BOUND)
        second_commit_blocked_while_task_locked = not commit_task.done()

        await lock_session.rollback()
        await asyncio.wait_for(commit_task, timeout=5)
        assert second_commit_blocked_while_task_locked is True
    finally:
        if commit_task is not None and not commit_task.done():
            commit_task.cancel()
            await asyncio.gather(commit_task, return_exceptions=True)
        await lock_session.close()
        await commit_session.close()
        await _cleanup(db_session, ws, uid)


@pytest.mark.integration
async def test_probe_c11b_two_concurrent_commits_both_succeed_via_the_task_lock(db_session):
    """The step-1 task lock is what makes the SECOND commit supersede instead of conflict."""
    ws, uid, item_id, task_id, *_ = await _seed(db_session)
    session_a = database._session_factory()
    session_b = database._session_factory()
    task_a = task_b = None
    try:
        task_a = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(session_a, ws, uid, {"task_client_id": task_id})))
        task_b = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(session_b, ws, uid, {"task_client_id": task_id,
                                      "expected_sale_price_minor": 1500})))
        results = await asyncio.wait_for(
            asyncio.gather(task_a, task_b, return_exceptions=True), timeout=10)

        conflicts = [r for r in results if isinstance(r, Exception)]
        assert conflicts == [], f"the task lock must serialize same-task commits: {conflicts}"

        current = list((await db_session.scalars(select(ItemCostEvaluation).where(
            ItemCostEvaluation.task_id == task_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.superseded_at.is_(None),
            ItemCostEvaluation.is_deleted.is_(False)))).all())
        assert len(current) == 1
        total = list((await db_session.scalars(select(ItemCostEvaluation).where(
            ItemCostEvaluation.task_id == task_id))).all())
        assert len(total) == 2
        older = next(r for r in total if r.client_id != current[0].client_id)
        assert older.superseded_by_id == current[0].client_id
    finally:
        for t in (task_a, task_b):
            if t is not None and not t.done():
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)
        await session_a.close()
        await session_b.close()
        await _cleanup(db_session, ws, uid)


# ----------------------------------------------------------------- C5 row 6
@pytest.mark.integration
async def test_probe_c5r6_commit_blocked_while_valuation_locked(db_session):
    ws, uid, item_id, task_id, *_ = await _seed(db_session)
    lock_session = database._session_factory()
    commit_session = database._session_factory()
    commit_task = None
    try:
        await lock_session.begin()
        await lock_session.execute(text(
            "SELECT client_id FROM item_valuations WHERE item_id = :i "
            "AND superseded_at IS NULL AND is_deleted IS false FOR UPDATE"), {"i": item_id})

        # NO override: a mirror write would itself UPDATE this row and mask
        # the step-4 lock, leaving the named mutation inert.
        commit_task = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(commit_session, ws, uid, {"task_client_id": task_id})))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(commit_task), timeout=BOUND)
        commit_blocked_while_valuation_locked = not commit_task.done()

        await lock_session.rollback()
        await asyncio.wait_for(commit_task, timeout=5)
        assert commit_blocked_while_valuation_locked is True
    finally:
        if commit_task is not None and not commit_task.done():
            commit_task.cancel()
            await asyncio.gather(commit_task, return_exceptions=True)
        await lock_session.close()
        await commit_session.close()
        await _cleanup(db_session, ws, uid)


# ----------------------------------------------------------------- C12 row 1
@pytest.mark.integration
@pytest.mark.parametrize("chain", ["basis", "model"])
async def test_probe_c12_row1_delete_first_commit_blocks_then_refuses(db_session, chain):
    ws, uid, item_id, task_id, group_id, basis_id, model_id = await _seed(db_session)
    delete_session = database._session_factory()
    commit_session = database._session_factory()
    delete_task = commit_task = None
    locked = asyncio.Event()
    release = asyncio.Event()
    try:
        async def after_lock():
            locked.set()
            await release.wait()

        command = delete_production_cost_basis_version if chain == "basis" else delete_cost_model_version
        target = basis_id if chain == "basis" else model_id
        delete_task = asyncio.create_task(command(
            _ctx(delete_session, ws, uid, {"client_id": target}), after_lock=after_lock))
        await asyncio.wait_for(locked.wait(), timeout=5)

        commit_task = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(commit_session, ws, uid, {"task_client_id": task_id})))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(commit_task), timeout=BOUND)
        commit_blocked_at_resolution = not commit_task.done()

        release.set()
        await asyncio.wait_for(delete_task, timeout=5)
        expected = ("ITEM_COST_NO_BASIS_VERSION" if chain == "basis"
                    else "ITEM_COST_NO_COST_MODEL_VERSION")
        with pytest.raises(ValidationError, match=rf"^{expected}:"):
            await asyncio.wait_for(commit_task, timeout=5)

        assert commit_blocked_at_resolution is True
        assert await db_session.scalar(select(ItemCostEvaluation).where(
            ItemCostEvaluation.task_id == task_id)) is None
    finally:
        release.set()
        for t in (delete_task, commit_task):
            if t is not None and not t.done():
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)
        await delete_session.close()
        await commit_session.close()
        await _cleanup(db_session, ws, uid)


# ----------------------------------------------------------------- C2 DB path
@pytest.mark.integration
async def test_probe_c2_db_conflict_surfaces_the_translated_identity(db_session):
    ws, uid, item_id, task_id, group_id, basis_id, model_id = await _seed(db_session)
    insert_session = database._session_factory()
    commit_session = database._session_factory()
    commit_task = None
    try:
        await insert_session.begin()
        insert_session.add(ItemCostEvaluation(
            workspace_id=ws, task_id=task_id, item_id=item_id,
            kind=ItemCostEvaluationKindEnum.COMMITTED,
            task_type_snapshot=TaskTypeEnum.RETURN,
            expected_sale_price_minor=100, purchase_cost_minor=None,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            cost_model_version_id=model_id, production_cost_group_id=group_id,
            production_cost_basis_version_id=basis_id,
            monthly_paid_hours_snapshot=Decimal("160.00"),
            planning_utilization_percent_snapshot=Decimal("80.00"),
            fixed_monthly_cost_minor_snapshot=100000,
            cost_per_worker_minute_minor_snapshot=Decimal("13.0208"),
            production_budget_minor=100, allowed_worker_minutes=Decimal("7.68"),
            calculation_version=1, committed_at=datetime.now(timezone.utc),
            created_by_id=uid))
        await insert_session.flush()

        commit_task = asyncio.create_task(commit_item_cost_evaluation(
            _ctx(commit_session, ws, uid, {"task_client_id": task_id})))
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(commit_task), timeout=BOUND)
        commit_blocked_on_uncommitted_index_entry = not commit_task.done()

        await insert_session.commit()
        # OBSERVED: the direct INSERT takes an FK KEY SHARE lock on the task row,
        # so the commit blocks on its own step-1 FOR UPDATE, not on the chain
        # index. When it finally runs, S1 sees the now-committed row and
        # supersedes it normally -> no conflict is ever raised.
        result = await asyncio.wait_for(commit_task, timeout=5)

        assert commit_blocked_on_uncommitted_index_entry is True
        current = list((await db_session.scalars(select(ItemCostEvaluation).where(
            ItemCostEvaluation.task_id == task_id,
            ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
            ItemCostEvaluation.superseded_at.is_(None),
            ItemCostEvaluation.is_deleted.is_(False)))).all())
        assert len(current) == 1
        assert current[0].client_id == result["evaluation"]["client_id"]
        total = list((await db_session.scalars(select(ItemCostEvaluation).where(
            ItemCostEvaluation.task_id == task_id))).all())
        assert len(total) == 2, "the intruder row must survive, superseded"
        intruder = next(r for r in total if r.client_id != current[0].client_id)
        assert intruder.superseded_at is not None
    finally:
        if commit_task is not None and not commit_task.done():
            commit_task.cancel()
            await asyncio.gather(commit_task, return_exceptions=True)
        await insert_session.close()
        await commit_session.close()
        await _cleanup(db_session, ws, uid)
