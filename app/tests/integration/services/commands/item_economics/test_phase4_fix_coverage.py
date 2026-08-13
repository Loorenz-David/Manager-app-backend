import asyncio
import importlib
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.calculator import (
    calculate_allowed_worker_minutes,
    rederive,
)
from beyo_manager.domain.item_economics.enums import ItemCostEvaluationKindEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models import database
from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.item_economics.add_section_to_cost_group import add_section_to_cost_group
from beyo_manager.services.commands.item_economics.create_cost_model_version import create_cost_model_version
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import create_production_cost_basis_version
from beyo_manager.services.commands.item_economics.create_production_cost_group import create_production_cost_group
from beyo_manager.services.commands.item_economics.delete_cost_model_version import delete_cost_model_version
from beyo_manager.services.commands.item_economics.delete_production_cost_basis_version import delete_production_cost_basis_version
from beyo_manager.services.commands.item_economics.delete_production_cost_group import delete_production_cost_group
from beyo_manager.services.commands.item_economics.remove_section_from_cost_group import remove_section_from_cost_group
from beyo_manager.services.commands.item_economics.update_production_cost_group import update_production_cost_group
from beyo_manager.services.commands.item_economics._common import today_utc
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_economics_configuration_status import get_economics_configuration_status
from beyo_manager.services.queries.item_economics.list_cost_model_versions import list_cost_model_versions
from beyo_manager.services.queries.item_economics.list_production_cost_basis_versions import list_production_cost_basis_versions
from beyo_manager.services.queries.item_economics.list_production_cost_groups import list_production_cost_groups


def _ctx(session, workspace_id: str, user_id: str, data: dict, query: dict | None = None) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "manager", "role_name": "manager"},
        incoming_data=data,
        query_params=query or {},
        session=session,
    )


async def _actor(db_session, label: str | None = None) -> tuple[Workspace, User]:
    token = label or uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"economics {token}")
    user = User(
        client_id=f"usr_{token}",
        username=f"economics_{token}",
        email=f"{token}@example.test",
        password="test",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _group(
    db_session,
    workspace: Workspace,
    user: User,
    name: str = "Main",
    major_category: ItemMajorCategoryEnum = ItemMajorCategoryEnum.WOOD,
) -> str:
    result = await create_production_cost_group(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"name": name, "major_category": major_category},
        )
    )
    return result["production_cost_group"]["client_id"]


def _basis_data(group_id: str, *, effective_from: date | None = None) -> dict:
    return {
        "production_cost_group_id": group_id,
        "effective_from": effective_from,
        "fixed_monthly_cost_minor": 100000,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA,
        "monthly_paid_hours": Decimal("160.00"),
        "planning_utilization_percent": Decimal("80.00"),
    }


async def _basis(db_session, workspace: Workspace, user: User, group_id: str, *, effective_from: date | None = None) -> str:
    result = await create_production_cost_basis_version(
        _ctx(db_session, workspace.client_id, user.client_id, _basis_data(group_id, effective_from=effective_from))
    )
    return result["production_cost_basis_version"]["client_id"]


async def _model(db_session, workspace: Workspace, user: User, *, effective_from: date | None = None, terms=None) -> str:
    result = await create_cost_model_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"effective_from": effective_from, "currency": ItemCurrencyEnum.SWEDISH_KRONA, "terms": terms or []},
        )
    )
    return result["cost_model_version"]["client_id"]


@pytest.mark.integration
@pytest.mark.parametrize("chain", ["basis", "model"], ids=["basis", "model"])
@pytest.mark.parametrize(
    ("case", "open_from", "requested_from", "expected"),
    [
        ("row-1-none-null-soft-deleted-open", "soft-deleted", "none", None),
        ("row-2-none-at-or-before-today", "none", "today", None),
        ("row-3-none-future", "none", "future", "_EFFECTIVE_FROM_FUTURE"),
        ("row-4-null-open-null", "null", "none", "_EFFECTIVE_FROM_REQUIRED"),
        ("row-5-null-open-at-or-before-today", "null", "past", None),
        ("row-6-null-open-future", "null", "future", "_EFFECTIVE_FROM_FUTURE"),
        ("row-7-dated-open-null", "dated", "none", "_EFFECTIVE_FROM_REQUIRED"),
        ("row-8-dated-open-at-or-before-open", "dated", "open", "_EFFECTIVE_FROM_NOT_AFTER_OPEN"),
        ("row-9-dated-open-after-open", "dated", "after", None),
        ("row-10-dated-open-future", "dated", "future", "_EFFECTIVE_FROM_FUTURE"),
    ],
    ids=[
        "table-row-1-none-null",
        "table-row-2-none-at-or-before-today",
        "table-row-3-none-future",
        "table-row-4-null-open-null",
        "table-row-5-null-open-at-or-before-today",
        "table-row-6-null-open-future",
        "table-row-7-dated-open-null",
        "table-row-8-dated-open-at-or-before-open",
        "table-row-9-dated-open-after-open",
        "table-row-10-dated-open-future",
    ],
)
async def test_c1_admission_matrix_has_one_exact_outcome_per_chain(
    db_session, chain, case, open_from, requested_from, expected
):
    workspace, user = await _actor(db_session)
    today = today_utc()
    requested_from = {
        "none": None,
        "today": today,
        "past": today - timedelta(days=1),
        "future": today + timedelta(days=1),
        "open": today - timedelta(days=5),
        "after": today - timedelta(days=4),
    }[requested_from]
    group_id = await _group(db_session, workspace, user) if chain == "basis" else None
    predecessor_id = None
    if open_from == "soft-deleted":
        if chain == "basis":
            predecessor_id = await _basis(db_session, workspace, user, group_id)
            row = await db_session.get(ProductionCostBasisVersion, predecessor_id)
        else:
            predecessor_id = await _model(db_session, workspace, user)
            row = await db_session.get(CostModelVersion, predecessor_id)
        row.is_deleted = True
        await db_session.flush()
    elif open_from == "null":
        if chain == "basis":
            predecessor_id = await _basis(db_session, workspace, user, group_id)
        else:
            predecessor_id = await _model(db_session, workspace, user)
    elif open_from == "dated":
        dated_open = today - timedelta(days=5)
        if chain == "basis":
            predecessor_id = await _basis(db_session, workspace, user, group_id, effective_from=dated_open)
        else:
            predecessor_id = await _model(db_session, workspace, user, effective_from=dated_open)

    if chain == "basis":
        payload = _basis_data(group_id, effective_from=requested_from)
        command = create_production_cost_basis_version
    else:
        payload = {"effective_from": requested_from, "currency": ItemCurrencyEnum.SWEDISH_KRONA, "terms": []}
        command = create_cost_model_version

    if expected is None:
        result = await command(_ctx(db_session, workspace.client_id, user.client_id, payload))
        assert result
        if case == "row-5-null-open-at-or-before-today":
            predecessor = await db_session.get(
                ProductionCostBasisVersion if chain == "basis" else CostModelVersion,
                predecessor_id,
            )
            assert predecessor.effective_to == requested_from
    else:
        with pytest.raises(ValidationError) as raised:
            await command(_ctx(db_session, workspace.client_id, user.client_id, payload))
        assert str(raised.value).startswith(f"ITEM_COST_{'BASIS' if chain == 'basis' else 'MODEL'}_VERSION{expected}")


@pytest.mark.integration
@pytest.mark.parametrize("chain", ["basis", "model"])
@pytest.mark.parametrize("boundary", ["v1-before", "v1-at", "v2-at"])
async def test_c2_adjacency_uses_command_built_orm_versions_and_is_applicable(db_session, chain, boundary):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user) if chain == "basis" else None
    first_day = date(2026, 8, 10)
    second_day = date(2026, 8, 12)
    if chain == "basis":
        first_id = await _basis(db_session, workspace, user, group_id, effective_from=first_day)
        second_id = await _basis(db_session, workspace, user, group_id, effective_from=second_day)
        first = await db_session.get(ProductionCostBasisVersion, first_id)
        second = await db_session.get(ProductionCostBasisVersion, second_id)
    else:
        first_id = await _model(db_session, workspace, user, effective_from=first_day)
        second_id = await _model(db_session, workspace, user, effective_from=second_day)
        first = await db_session.get(CostModelVersion, first_id)
        second = await db_session.get(CostModelVersion, second_id)

    from beyo_manager.domain.item_economics.configuration import is_applicable

    assert first.effective_to == second_day
    if boundary == "v1-before":
        assert is_applicable(first, second_day - timedelta(days=1)) is True
    elif boundary == "v1-at":
        assert is_applicable(first, second_day) is False
    else:
        assert is_applicable(second, second_day) is True


@pytest.mark.integration
@pytest.mark.parametrize("chain", ["basis", "model"])
async def test_c3_real_concurrent_open_insert_translates_the_loser(chain, db_session, monkeypatch):
    workspace, user = await _actor(db_session)
    workspace_id, user_id = workspace.client_id, user.client_id
    group_id = await _group(db_session, workspace, user) if chain == "basis" else None
    if chain == "basis":
        await _basis(db_session, workspace, user, group_id)
    else:
        await _model(db_session, workspace, user)
    await db_session.commit()
    session_one = database._session_factory()
    session_two = database._session_factory()
    try:
        module = importlib.import_module(
            "beyo_manager.services.commands.item_economics.create_production_cost_basis_version"
            if chain == "basis"
            else "beyo_manager.services.commands.item_economics.create_cost_model_version"
        )
        flush_complete = asyncio.Event()
        release = asyncio.Event()

        async def gated_audit(*args, **kwargs):
            flush_complete.set()
            await asyncio.wait_for(release.wait(), timeout=0.3)

        monkeypatch.setattr(module, "audit", gated_audit)
        if chain == "basis":
            payload = _basis_data(group_id, effective_from=date(2026, 8, 11))
            command = create_production_cost_basis_version
        else:
            payload = {"effective_from": date(2026, 8, 11), "currency": ItemCurrencyEnum.SWEDISH_KRONA, "terms": []}
            command = create_cost_model_version
        winner = asyncio.create_task(command(_ctx(session_one, workspace.client_id, user.client_id, payload)))
        await asyncio.wait_for(flush_complete.wait(), timeout=0.3)
        loser = asyncio.create_task(command(_ctx(session_two, workspace.client_id, user.client_id, payload)))
        await asyncio.sleep(0.05)
        release.set()
        outcomes = await asyncio.gather(winner, loser, return_exceptions=True)
        assert sum(isinstance(outcome, ConflictError) for outcome in outcomes) == 1, repr(outcomes)
        assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1, repr(outcomes)
        loser_outcome = next(outcome for outcome in outcomes if isinstance(outcome, ConflictError))
        expected_identity = (
            "ITEM_COST_CONCURRENT_BASIS_VERSION"
            if chain == "basis"
            else "ITEM_COST_CONCURRENT_MODEL_VERSION"
        )
        assert str(loser_outcome).startswith(f"{expected_identity}:"), repr(outcomes)
        if chain == "basis":
            open_count = await db_session.scalar(
                select(func.count()).select_from(ProductionCostBasisVersion).where(
                    ProductionCostBasisVersion.production_cost_group_id == group_id,
                    ProductionCostBasisVersion.effective_to.is_(None),
                    ProductionCostBasisVersion.is_deleted.is_(False),
                )
            )
        else:
            open_count = await db_session.scalar(
                select(func.count()).select_from(CostModelVersion).where(
                    CostModelVersion.workspace_id == workspace.client_id,
                    CostModelVersion.effective_to.is_(None),
                    CostModelVersion.is_deleted.is_(False),
                )
            )
        assert open_count == 1
    finally:
        await session_one.close()
        await session_two.close()
        await db_session.rollback()
        await db_session.execute(delete(CostModelTerm).where(CostModelTerm.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostBasisVersion).where(ProductionCostBasisVersion.workspace_id == workspace_id))
        await db_session.execute(delete(CostModelVersion).where(CostModelVersion.workspace_id == workspace_id))
        await db_session.execute(delete(AuditLog).where(AuditLog.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.workspace_id == workspace_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
        await db_session.commit()


@pytest.mark.integration
async def test_c4_underflow_is_named_and_the_direct_insert_hits_the_database_check(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user)
    with pytest.raises(ValidationError, match=r"^ITEM_COST_RATE_UNDERFLOW:"):
        await create_production_cost_basis_version(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "production_cost_group_id": group_id,
                    "fixed_monthly_cost_minor": 1,
                    "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                    "monthly_paid_hours": Decimal("100000.00"),
                    "planning_utilization_percent": Decimal("1.00"),
                },
            )
        )

    db_session.add(
        ProductionCostBasisVersion(
            workspace_id=workspace.client_id,
            production_cost_group_id=group_id,
            fixed_monthly_cost_minor=1,
            currency=ItemCurrencyEnum.SWEDISH_KRONA,
            monthly_paid_hours=Decimal("100000.00"),
            planning_utilization_percent=Decimal("1.00"),
            cost_per_worker_minute_minor=Decimal("0.0000"),
            created_by_id=user.client_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.integration
async def test_c4_persisted_rate_is_the_calculator_output_and_rederives_exactly(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user)
    basis_id = await _basis(db_session, workspace, user, group_id)
    basis = await db_session.get(ProductionCostBasisVersion, basis_id)
    evaluation = ItemCostEvaluation(
        workspace_id=workspace.client_id,
        task_id="tsk_rate_test",
        item_id="itm_rate_test",
        kind=ItemCostEvaluationKindEnum.PROJECTION,
        task_type_snapshot=TaskTypeEnum.INTERNAL,
        expected_sale_price_minor=100000,
        purchase_cost_minor=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        cost_model_version_id="cmv_rate_test",
        production_cost_group_id=group_id,
        production_cost_basis_version_id=basis.client_id,
        monthly_paid_hours_snapshot=basis.monthly_paid_hours,
        planning_utilization_percent_snapshot=basis.planning_utilization_percent,
        fixed_monthly_cost_minor_snapshot=basis.fixed_monthly_cost_minor,
        cost_per_worker_minute_minor_snapshot=basis.cost_per_worker_minute_minor,
        production_budget_minor=100000,
        allowed_worker_minutes=calculate_allowed_worker_minutes(100000, basis.cost_per_worker_minute_minor),
        calculation_version=1,
        created_by_id=user.client_id,
    )
    result = rederive(evaluation, [])

    assert result == (
        Decimal(str(basis.cost_per_worker_minute_minor)),
        100000,
        Decimal(str(evaluation.allowed_worker_minutes)),
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("calculation_type", "values", "valid"),
    [
        ("percentage_of_expected_sale_price", {"percent_value": 10}, True),
        ("percentage_of_expected_sale_price", {}, False),
        ("percentage_of_expected_sale_price", {"percent_value": 10, "fixed_amount_minor": 1}, False),
        ("percentage_of_expected_sale_price", {"fixed_amount_minor": 1}, False),
        ("fixed_amount", {"fixed_amount_minor": 1}, True),
        ("fixed_amount", {}, False),
        ("fixed_amount", {"percent_value": 10}, False),
        ("fixed_amount", {"percent_value": 10, "fixed_amount_minor": 1}, False),
        ("item_purchase_cost", {}, True),
        ("item_purchase_cost", {"percent_value": 10}, False),
        ("item_purchase_cost", {"fixed_amount_minor": 1}, False),
        ("item_purchase_cost", {"percent_value": 10, "fixed_amount_minor": 1}, False),
    ],
    ids=["percent-valid", "percent-none", "percent-both", "percent-fixed-only", "fixed-valid", "fixed-none", "fixed-percent-only", "fixed-both", "purchase-valid", "purchase-percent-only", "purchase-fixed-only", "purchase-both"],
)
async def test_c5_command_term_matrix_has_one_exact_shape_outcome(db_session, calculation_type, values, valid):
    workspace, user = await _actor(db_session)
    term = {"name": "term", "calculation_type": calculation_type, **values}
    if valid:
        result = await _model(db_session, workspace, user, terms=[term])
        assert result.startswith("cmv")
    else:
        with pytest.raises(ValidationError, match=r"^ITEM_COST_TERM_SHAPE_INVALID:"):
            await _model(db_session, workspace, user, terms=[term])


@pytest.mark.integration
async def test_c5_duplicate_term_prechecks_have_their_registered_identities(db_session):
    workspace, user = await _actor(db_session)
    with pytest.raises(ValidationError, match=r"^ITEM_COST_PURCHASE_TERM_DUPLICATE:"):
        await _model(
            db_session,
            workspace,
            user,
            terms=[
                {"name": "purchase-a", "calculation_type": "item_purchase_cost"},
                {"name": "purchase-b", "calculation_type": "item_purchase_cost"},
            ],
        )
    with pytest.raises(ValidationError, match=r"^ITEM_COST_TERM_NAME_TAKEN:"):
        await _model(
            db_session,
            workspace,
            user,
            terms=[
                {"name": "same", "calculation_type": "item_purchase_cost"},
                {"name": "same", "calculation_type": "fixed_amount", "fixed_amount_minor": 1},
            ],
        )


async def _seed_evaluation(db_session, workspace: Workspace, user: User, group_id: str, basis_id: str, model_id: str):
    token = uuid4().hex
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, created_by_id=user.client_id)
    task = Task(
        client_id=f"tsk_{token}",
        workspace_id=workspace.client_id,
        task_scalar_id=int(token[:8], 16) % 2_000_000_000,
        task_type=TaskTypeEnum.INTERNAL,
        created_by_id=user.client_id,
    )
    db_session.add_all([item, task])
    await db_session.flush()
    evaluation = ItemCostEvaluation(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        kind=ItemCostEvaluationKindEnum.PROJECTION,
        task_type_snapshot=TaskTypeEnum.INTERNAL,
        expected_sale_price_minor=100,
        purchase_cost_minor=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        cost_model_version_id=model_id,
        production_cost_group_id=group_id,
        production_cost_basis_version_id=basis_id,
        monthly_paid_hours_snapshot=Decimal("160.00"),
        planning_utilization_percent_snapshot=Decimal("80.00"),
        fixed_monthly_cost_minor_snapshot=100000,
        cost_per_worker_minute_minor_snapshot=Decimal("13.0208"),
        production_budget_minor=100,
        allowed_worker_minutes=Decimal("7.68"),
        calculation_version=1,
        created_by_id=user.client_id,
    )
    db_session.add(evaluation)
    await db_session.flush()
    return item, task, evaluation


@pytest.mark.integration
@pytest.mark.parametrize("chain", ["basis", "model"])
async def test_c6_serial_delete_guard_rechecks_all_evaluation_references(db_session, chain):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user)
    basis_id = await _basis(db_session, workspace, user, group_id)
    model_id = await _model(db_session, workspace, user)
    await _seed_evaluation(db_session, workspace, user, group_id, basis_id, model_id)

    command = delete_production_cost_basis_version if chain == "basis" else delete_cost_model_version
    with pytest.raises(ValidationError) as raised:
        await command(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": basis_id if chain == "basis" else model_id}))
    assert str(raised.value).startswith(
        "ITEM_COST_BASIS_VERSION_IN_USE:" if chain == "basis" else "ITEM_COST_MODEL_VERSION_IN_USE:"
    )


@pytest.mark.integration
async def test_c6_interleaved_fk_insert_is_blocked_by_the_delete_row_lock_then_proceeds(db_session):
    workspace, user = await _actor(db_session)
    workspace_id, user_id = workspace.client_id, user.client_id
    group_id = await _group(db_session, workspace, user)
    basis_id = await _basis(db_session, workspace, user, group_id)
    model_id = await _model(db_session, workspace, user)
    item, task, evaluation = await _seed_evaluation(db_session, workspace, user, group_id, basis_id, model_id)
    await db_session.delete(await db_session.get(ItemCostEvaluation, evaluation.client_id))
    await db_session.flush()
    await db_session.commit()

    locked = asyncio.Event()
    release = asyncio.Event()
    started = asyncio.Event()
    delete_session = database._session_factory()
    insert_session = database._session_factory()

    async def after_lock():
        locked.set()
        await release.wait()

    async def insert_reference():
        async with insert_session.begin():
            insert_reference_row = ItemCostEvaluation(
                workspace_id=workspace.client_id,
                task_id=task.client_id,
                item_id=item.client_id,
                kind=ItemCostEvaluationKindEnum.PROJECTION,
                task_type_snapshot=TaskTypeEnum.INTERNAL,
                expected_sale_price_minor=100,
                purchase_cost_minor=None,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                cost_model_version_id=model_id,
                production_cost_group_id=group_id,
                production_cost_basis_version_id=basis_id,
                monthly_paid_hours_snapshot=Decimal("160.00"),
                planning_utilization_percent_snapshot=Decimal("80.00"),
                fixed_monthly_cost_minor_snapshot=100000,
                cost_per_worker_minute_minor_snapshot=Decimal("13.0208"),
                production_budget_minor=100,
                allowed_worker_minutes=Decimal("7.68"),
                calculation_version=1,
                created_by_id=user.client_id,
            )
            insert_session.add(insert_reference_row)
            started.set()
            await insert_session.flush()

    try:
        delete_task = asyncio.create_task(
            delete_production_cost_basis_version(
                _ctx(delete_session, workspace.client_id, user.client_id, {"client_id": basis_id}),
                after_lock=after_lock,
            )
        )
        await locked.wait()
        insert_task = asyncio.create_task(insert_reference())
        await started.wait()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(insert_task), timeout=0.3)
        reference_blocked_while_locked = not insert_task.done()
        release.set()
        await delete_task
        await insert_task
        assert reference_blocked_while_locked is True
    finally:
        release.set()
        if not delete_task.done():
            await delete_task
        if "insert_task" in locals() and not insert_task.done():
            await insert_task
        await delete_session.close()
        await insert_session.close()
        await db_session.rollback()
        await db_session.execute(delete(ItemCostEvaluation).where(ItemCostEvaluation.workspace_id == workspace_id))
        await db_session.execute(delete(Task).where(Task.workspace_id == workspace_id))
        await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
        await db_session.execute(delete(CostModelTerm).where(CostModelTerm.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostBasisVersion).where(ProductionCostBasisVersion.workspace_id == workspace_id))
        await db_session.execute(delete(CostModelVersion).where(CostModelVersion.workspace_id == workspace_id))
        await db_session.execute(delete(AuditLog).where(AuditLog.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.workspace_id == workspace_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
        await db_session.commit()


@pytest.mark.integration
async def test_c7_section_membership_identity_and_group_delete_guards(db_session):
    workspace, user = await _actor(db_session)
    first_group = await _group(db_session, workspace, user, "First")
    second_group = await _group(db_session, workspace, user, "Second", ItemMajorCategoryEnum.SEAT)
    section = WorkingSection(workspace_id=workspace.client_id, name="Assembly", created_by_id=user.client_id)
    db_session.add(section)
    await db_session.flush()
    await add_section_to_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": first_group, "working_section_id": section.client_id}))
    with pytest.raises(ValidationError, match=r"^ITEM_COST_SECTION_ALREADY_GROUPED:"):
        await add_section_to_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": second_group, "working_section_id": section.client_id}))
    with pytest.raises(ValidationError, match=r"^ITEM_COST_GROUP_IN_USE:"):
        await delete_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": first_group}))
    await remove_section_from_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": first_group, "working_section_id": section.client_id}))
    deleted = await delete_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": first_group}))
    assert deleted["production_cost_group"]["client_id"] == first_group


@pytest.mark.integration
async def test_c7_group_delete_rejects_a_non_deleted_basis_version(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user)
    await _basis(db_session, workspace, user, group_id)

    with pytest.raises(ValidationError, match=r"^ITEM_COST_GROUP_IN_USE:"):
        await delete_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": group_id}))


@pytest.mark.integration
async def test_c8_status_query_enumerates_each_first_failure_and_success(db_session):
    today = today_utc()
    cases = [
        "no-cost-group",
        "no-basis",
        "basis-not-applicable",
        "no-model",
        "all-present",
    ]
    expected = [
        "not_configured_no_cost_group",
        "not_configured_no_basis_version",
        "not_configured_no_basis_version",
        "not_configured_no_cost_model_version",
        None,
    ]
    for case, expected_failure in zip(cases, expected):
        workspace, user = await _actor(db_session)
        group = None
        if case != "no-cost-group":
            group = ProductionCostGroup(
                workspace_id=workspace.client_id,
                name="Main",
                major_category=ItemMajorCategoryEnum.WOOD,
                created_by_id=user.client_id,
            )
            db_session.add(group)
            await db_session.flush()
        if case in {"basis-not-applicable", "no-model", "all-present"}:
            db_session.add(
                ProductionCostBasisVersion(
                    workspace_id=workspace.client_id,
                    production_cost_group_id=group.client_id,
                    effective_from=today + timedelta(days=1) if case == "basis-not-applicable" else today - timedelta(days=1),
                    fixed_monthly_cost_minor=100000,
                    currency=ItemCurrencyEnum.SWEDISH_KRONA,
                    monthly_paid_hours=Decimal("160.00"),
                    planning_utilization_percent=Decimal("80.00"),
                    cost_per_worker_minute_minor=Decimal("13.0208"),
                    created_by_id=user.client_id,
                )
            )
        if case == "all-present":
            db_session.add(
                CostModelVersion(
                    workspace_id=workspace.client_id,
                    effective_from=today - timedelta(days=1),
                    currency=ItemCurrencyEnum.SWEDISH_KRONA,
                    created_by_id=user.client_id,
                )
            )
        await db_session.flush()
        status = await get_economics_configuration_status(_ctx(db_session, workspace.client_id, user.client_id, {}))
        assert set(status) == {"categories", "has_open_cost_model_version"}, case
        assert status["categories"]["wood"]["first_failure"] == expected_failure, case
        assert status["categories"]["wood"]["evaluable"] is (expected_failure is None)
        assert status["categories"]["seat"]["first_failure"] == "not_configured_no_cost_group", case
        await db_session.rollback()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("query_name", "filter_name"),
    [
        ("groups", "workspace"),
        ("groups", "is_deleted"),
        ("basis", "workspace"),
        ("basis", "is_deleted"),
        ("models", "workspace"),
        ("models", "is_deleted"),
    ],
    ids=[
        "groups-workspace",
        "groups-is-deleted",
        "basis-workspace",
        "basis-is-deleted",
        "models-workspace",
        "models-is-deleted",
    ],
)
async def test_c10_each_list_filter_has_a_sole_cause_fixture(db_session, query_name, filter_name):
    workspace, user = await _actor(db_session, f"filter_{query_name}_{filter_name}")
    expected_id = None

    if query_name == "groups":
        if filter_name == "workspace":
            other_workspace, other_user = await _actor(db_session, "filter_other_group")
            filtered_out = ProductionCostGroup(
                workspace_id=other_workspace.client_id,
                name="A",
                major_category=ItemMajorCategoryEnum.WOOD,
                created_by_id=other_user.client_id,
            )
            visible = ProductionCostGroup(
                workspace_id=workspace.client_id,
                name="Z",
                major_category=ItemMajorCategoryEnum.SEAT,
                created_by_id=user.client_id,
            )
        else:
            filtered_out = ProductionCostGroup(
                workspace_id=workspace.client_id,
                name="A",
                major_category=ItemMajorCategoryEnum.SEAT,
                created_by_id=user.client_id,
                is_deleted=True,
            )
            visible = ProductionCostGroup(
                workspace_id=workspace.client_id,
                name="Z",
                major_category=ItemMajorCategoryEnum.WOOD,
                created_by_id=user.client_id,
            )
        db_session.add_all([filtered_out, visible])
        await db_session.flush()
        expected_id = visible.client_id
        result = await list_production_cost_groups(
            _ctx(db_session, workspace.client_id, user.client_id, {}, {"limit": 1, "offset": 0})
        )
        rows = result["production_cost_groups"]
        pagination = result["production_cost_groups_pagination"]
    elif query_name == "basis":
        if filter_name == "workspace":
            other_workspace, other_user = await _actor(db_session, "filter_other_basis")
            other_group_id = await _group(db_session, other_workspace, other_user, "A")
            filtered_out = ProductionCostBasisVersion(
                workspace_id=other_workspace.client_id,
                production_cost_group_id=other_group_id,
                effective_from=None,
                fixed_monthly_cost_minor=100000,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                monthly_paid_hours=Decimal("160.00"),
                planning_utilization_percent=Decimal("80.00"),
                cost_per_worker_minute_minor=Decimal("13.0208"),
                created_by_id=other_user.client_id,
            )
            own_group_id = await _group(db_session, workspace, user, "Z")
            visible = ProductionCostBasisVersion(
                workspace_id=workspace.client_id,
                production_cost_group_id=own_group_id,
                effective_from=today_utc(),
                fixed_monthly_cost_minor=100000,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                monthly_paid_hours=Decimal("160.00"),
                planning_utilization_percent=Decimal("80.00"),
                cost_per_worker_minute_minor=Decimal("13.0208"),
                created_by_id=user.client_id,
            )
        else:
            own_group_id = await _group(db_session, workspace, user, "Main")
            filtered_out = ProductionCostBasisVersion(
                workspace_id=workspace.client_id,
                production_cost_group_id=own_group_id,
                effective_from=None,
                fixed_monthly_cost_minor=100000,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                monthly_paid_hours=Decimal("160.00"),
                planning_utilization_percent=Decimal("80.00"),
                cost_per_worker_minute_minor=Decimal("13.0208"),
                created_by_id=user.client_id,
                is_deleted=True,
            )
            visible = ProductionCostBasisVersion(
                workspace_id=workspace.client_id,
                production_cost_group_id=own_group_id,
                effective_from=today_utc(),
                fixed_monthly_cost_minor=100000,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                monthly_paid_hours=Decimal("160.00"),
                planning_utilization_percent=Decimal("80.00"),
                cost_per_worker_minute_minor=Decimal("13.0208"),
                created_by_id=user.client_id,
            )
        db_session.add_all([filtered_out, visible])
        await db_session.flush()
        expected_id = visible.client_id
        result = await list_production_cost_basis_versions(
            _ctx(db_session, workspace.client_id, user.client_id, {}, {"limit": 1, "offset": 0})
        )
        rows = result["production_cost_basis_versions"]
        pagination = result["production_cost_basis_versions_pagination"]
    else:
        if filter_name == "workspace":
            other_workspace, other_user = await _actor(db_session, "filter_other_model")
            filtered_out = CostModelVersion(
                workspace_id=other_workspace.client_id,
                effective_from=None,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=other_user.client_id,
            )
            visible = CostModelVersion(
                workspace_id=workspace.client_id,
                effective_from=today_utc(),
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=user.client_id,
            )
        else:
            filtered_out = CostModelVersion(
                workspace_id=workspace.client_id,
                effective_from=None,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=user.client_id,
                is_deleted=True,
            )
            visible = CostModelVersion(
                workspace_id=workspace.client_id,
                effective_from=today_utc(),
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=user.client_id,
            )
        db_session.add_all([filtered_out, visible])
        await db_session.flush()
        expected_id = visible.client_id
        result = await list_cost_model_versions(
            _ctx(db_session, workspace.client_id, user.client_id, {}, {"limit": 1, "offset": 0})
        )
        rows = result["cost_model_versions"]
        pagination = result["cost_model_versions_pagination"]

    assert [row["client_id"] for row in rows] == [expected_id]
    assert pagination["has_more"] is False


@pytest.mark.integration
async def test_c10_group_rename_collision_precheck_is_a_validation_error(db_session):
    workspace, user = await _actor(db_session, "rename_precheck")
    first_group = await _group(db_session, workspace, user, "First")
    await _group(db_session, workspace, user, "Taken", ItemMajorCategoryEnum.SEAT)

    with pytest.raises(ValidationError) as raised:
        await update_production_cost_group(
            _ctx(db_session, workspace.client_id, user.client_id, {"client_id": first_group, "name": "Taken"})
        )

    assert raised.value.http_status == 422
    assert str(raised.value).startswith("ITEM_COST_GROUP_NAME_TAKEN:")


@pytest.mark.integration
async def test_c10_group_rename_db_conflict_translates_the_registered_identity(db_session, monkeypatch):
    workspace, user = await _actor(db_session, "rename_db_path")
    workspace_id, user_id = workspace.client_id, user.client_id
    first_group = await _group(db_session, workspace, user, "First")
    second_group = await _group(db_session, workspace, user, "Second", ItemMajorCategoryEnum.SEAT)
    await db_session.commit()

    session_one = database._session_factory()
    session_two = database._session_factory()
    winner = loser = None
    release = asyncio.Event()
    flush_complete = asyncio.Event()
    try:
        module = importlib.import_module(
            "beyo_manager.services.commands.item_economics.update_production_cost_group"
        )

        async def gated_audit(*args, **kwargs):
            flush_complete.set()
            await asyncio.wait_for(release.wait(), timeout=0.3)

        monkeypatch.setattr(module, "audit", gated_audit)
        winner = asyncio.create_task(
            update_production_cost_group(
                _ctx(session_one, workspace_id, user_id, {"client_id": first_group, "name": "Merged"})
            )
        )
        await asyncio.wait_for(flush_complete.wait(), timeout=0.3)
        loser = asyncio.create_task(
            update_production_cost_group(
                _ctx(session_two, workspace_id, user_id, {"client_id": second_group, "name": "Merged"})
            )
        )
        await asyncio.sleep(0.05)
        assert not loser.done()
        release.set()
        outcomes = await asyncio.wait_for(
            asyncio.gather(winner, loser, return_exceptions=True),
            timeout=0.5,
        )
        assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1, repr(outcomes)
        conflicts = [outcome for outcome in outcomes if isinstance(outcome, ConflictError)]
        assert len(conflicts) == 1, repr(outcomes)
        assert str(conflicts[0]).startswith("ITEM_COST_GROUP_NAME_TAKEN:")
        assert conflicts[0].http_status == 409
    finally:
        release.set()
        tasks = [task for task in (winner, loser) if task is not None and not task.done()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await session_one.close()
        await session_two.close()
        await db_session.rollback()
        await db_session.execute(delete(AuditLog).where(AuditLog.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.workspace_id == workspace_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
        await db_session.commit()


@pytest.mark.integration
async def test_c10_queries_scope_filter_order_and_limit_plus_one_for_all_three_lists(db_session):
    workspace, user = await _actor(db_session, "query_a")
    other_workspace, other_user = await _actor(db_session, "query_b")
    group_b = ProductionCostGroup(workspace_id=workspace.client_id, name="B", major_category=ItemMajorCategoryEnum.SEAT, created_by_id=user.client_id)
    group_a = ProductionCostGroup(workspace_id=workspace.client_id, name="A", major_category=ItemMajorCategoryEnum.WOOD, created_by_id=user.client_id)
    deleted_group = ProductionCostGroup(workspace_id=workspace.client_id, name="Deleted", major_category=ItemMajorCategoryEnum.SEAT, created_by_id=user.client_id, is_deleted=True)
    other_group = ProductionCostGroup(workspace_id=other_workspace.client_id, name="Other", major_category=ItemMajorCategoryEnum.WOOD, created_by_id=other_user.client_id)
    db_session.add_all([group_b, group_a, deleted_group, other_group])
    await db_session.flush()
    basis_a = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group_a.client_id,
        effective_from=None, fixed_monthly_cost_minor=100000, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"), planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0208"), created_by_id=user.client_id,
    )
    basis_b = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group_b.client_id,
        effective_from=date(2026, 8, 11), fixed_monthly_cost_minor=100000, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"), planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0208"), created_by_id=user.client_id,
    )
    deleted_basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id, production_cost_group_id=group_a.client_id,
        effective_from=date(2026, 8, 10), fixed_monthly_cost_minor=100000, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"), planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0208"), created_by_id=user.client_id, is_deleted=True,
    )
    model_a = CostModelVersion(workspace_id=workspace.client_id, effective_from=None, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id)
    model_b = CostModelVersion(workspace_id=workspace.client_id, effective_from=date(2026, 8, 11), effective_to=date(2026, 8, 12), currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id)
    deleted_model = CostModelVersion(workspace_id=workspace.client_id, effective_from=date(2026, 8, 10), currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id, is_deleted=True)
    other_model = CostModelVersion(workspace_id=other_workspace.client_id, effective_from=None, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=other_user.client_id)
    db_session.add_all([basis_a, basis_b, deleted_basis, model_a, model_b, deleted_model, other_model])
    await db_session.flush()

    groups = await list_production_cost_groups(_ctx(db_session, workspace.client_id, user.client_id, {}, {"limit": 1, "offset": 0}))
    bases = await list_production_cost_basis_versions(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": group_a.client_id}, {"limit": 1, "offset": 0}))
    models = await list_cost_model_versions(_ctx(db_session, workspace.client_id, user.client_id, {}, {"limit": 1, "offset": 0}))

    assert [row["name"] for row in groups["production_cost_groups"]] == ["A"]
    assert groups["production_cost_groups_pagination"] == {"has_more": True, "limit": 1, "offset": 0}
    assert len(bases["production_cost_basis_versions"]) == 1
    assert bases["production_cost_basis_versions"][0]["client_id"] == basis_a.client_id
    assert bases["production_cost_basis_versions_pagination"] == {"has_more": False, "limit": 1, "offset": 0}
    assert len(models["cost_model_versions"]) == 1
    assert models["cost_model_versions"][0]["client_id"] == model_a.client_id
    assert models["cost_model_versions_pagination"]["has_more"] is True


@pytest.mark.integration
async def test_c11_every_configuration_command_writes_one_registered_audit_event(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user)
    await update_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": group_id, "name": "Renamed"}))
    section = WorkingSection(workspace_id=workspace.client_id, name="Assembly", created_by_id=user.client_id)
    db_session.add(section)
    await db_session.flush()
    await add_section_to_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": group_id, "working_section_id": section.client_id}))
    await remove_section_from_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"production_cost_group_id": group_id, "working_section_id": section.client_id}))
    basis_id = await _basis(db_session, workspace, user, group_id)
    model_id = await _model(db_session, workspace, user)
    await delete_production_cost_basis_version(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": basis_id}))
    await delete_cost_model_version(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": model_id}))
    await delete_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": group_id}))

    events = (await db_session.execute(select(AuditLog.event).where(AuditLog.workspace_id == workspace.client_id).order_by(AuditLog.created_at.asc(), AuditLog.client_id.asc()))).scalars().all()
    assert events == [
        "production_cost_group.created",
        "production_cost_group.updated",
        "production_cost_group_section.added",
        "production_cost_group_section.removed",
        "production_cost_basis_version.created",
        "cost_model_version.created",
        "production_cost_basis_version.deleted",
        "cost_model_version.deleted",
        "production_cost_group.deleted",
    ]
