from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import commit_item_cost_evaluation
from beyo_manager.services.commands.item_economics.create_item_cost_projection import create_item_cost_projection
from beyo_manager.services.commands.item_economics.delete_item_valuation import delete_item_valuation
from beyo_manager.services.commands.item_economics.promote_item_cost_projection import promote_item_cost_projection
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.list_task_evaluations import list_task_evaluations


def _ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "phase7"},
        incoming_data=data,
        session=session,
    )


async def _fixture(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"phase7 {token}")
    user = User(client_id=f"usr_{token}", username=f"phase7_{token}", email=f"{token}@example.test", password="test")
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        article_number=f"ART-{token}",
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    group = ProductionCostGroup(
        workspace_id=workspace.client_id,
        name="Wood",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    task = Task(
        client_id=f"tsk_{token}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.RETURN,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([item, group, model, task])
    await db_session.flush()
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id,
        production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=100000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"),
        planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("99.9999"),
        created_by_id=user.client_id,
    )
    db_session.add(basis)
    await db_session.flush()
    term = CostModelTerm(
        workspace_id=workspace.client_id,
        cost_model_version_id=model.client_id,
        name="fixed",
        calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
        fixed_amount_minor=100,
        created_by_id=user.client_id,
    )
    valuation = ItemValuation(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        expected_sale_price_minor=1000,
        purchase_cost_minor=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    db_session.add_all([term, valuation, TaskItem(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        item_id=item.client_id,
        role=TaskItemRoleEnum.PRIMARY,
        created_by_id=user.client_id,
    )])
    await db_session.flush()
    return workspace, user, item, task, basis


@pytest.mark.integration
async def test_phase7_commit_projection_promotion_and_read(db_session, caplog):
    workspace, user, item, task, basis = await _fixture(db_session)
    committed = await commit_item_cost_evaluation(
        _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id, "label": "first"})
    )
    committed_row = await db_session.scalar(
        select(ItemCostEvaluation).where(ItemCostEvaluation.client_id == committed["evaluation"]["client_id"])
    )
    assert committed["evaluation"]["kind"] == "committed"
    assert committed["evaluation"]["cost_per_worker_minute_minor_snapshot"] == "13.0208"
    assert committed_row is not None

    projected = await create_item_cost_projection(
        _ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id,
            "source": "committed",
            "expected_sale_price_minor": 2000,
            "label": "what-if",
        })
    )
    projection_id = projected["evaluation"]["client_id"]
    assert projected["evaluation"]["kind"] == "projection"
    before = {
        column.name: getattr(await db_session.scalar(select(ItemCostEvaluation).where(ItemCostEvaluation.client_id == projection_id)), column.name)
        for column in ItemCostEvaluation.__table__.columns
    }
    promoted = await promote_item_cost_projection(
        _ctx(db_session, workspace.client_id, user.client_id, {"client_id": projection_id})
    )
    assert promoted["evaluation"]["promoted_from_id"] == projection_id
    after_row = await db_session.scalar(select(ItemCostEvaluation).where(ItemCostEvaluation.client_id == projection_id))
    assert {column.name: getattr(after_row, column.name) for column in ItemCostEvaluation.__table__.columns} == before

    read = await list_task_evaluations(_ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id}))
    assert set(read) == {"evaluations", "projections"}
    assert read["evaluations"][0]["client_id"] == promoted["evaluation"]["client_id"]
    assert read["evaluations"][0]["error"] is None
    assert read["evaluations"][0]["terms"][0]["amount_minor"] == 100

    promoted_row = await db_session.scalar(
        select(ItemCostEvaluation).where(
            ItemCostEvaluation.client_id == promoted["evaluation"]["client_id"]
        )
    )
    promoted_row.cost_per_worker_minute_minor_snapshot = Decimal("999.9999")
    await db_session.flush()
    with caplog.at_level("ERROR"):
        corrupted_read = await list_task_evaluations(
            _ctx(db_session, workspace.client_id, user.client_id, {"task_client_id": task.client_id})
        )
    corrupted = next(row for row in corrupted_read["evaluations"] if row["client_id"] == promoted_row.client_id)
    assert corrupted["error"] is not None
    assert "integrity check failed" in caplog.text
    assert "corruption" not in caplog.text.lower()


@pytest.mark.integration
async def test_phase7_create_task_auto_commits_and_dispatches_after_task_transaction(db_session, monkeypatch):
    workspace, user, item, _task, _basis = await _fixture(db_session)
    dispatched = []

    async def capture(events):
        dispatched.extend(events)

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", capture)
    result = await create_task(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "task_type": "return",
                "item": {"article_number": item.article_number},
            },
        )
    )

    task_id = result["client_id"]
    auto_row = await db_session.scalar(
        select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == task_id)
    )
    assert auto_row is not None
    assert any(event.event_name == "item_economics:evaluation-committed" for event in dispatched)


@pytest.mark.integration
async def test_phase7_auto_commit_overflow_rolls_back_savepoint_and_keeps_task(db_session, monkeypatch, caplog):
    workspace, user, item, _task, _basis = await _fixture(db_session)
    db_session.add_all(
        [
            *[
                CostModelTerm(
                    workspace_id=workspace.client_id,
                    cost_model_version_id=(await db_session.scalar(select(CostModelVersion).where(CostModelVersion.workspace_id == workspace.client_id))).client_id,
                    name=f"overflow-{index}",
                    calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
                    fixed_amount_minor=2147483647,
                    created_by_id=user.client_id,
                )
                for index in (1, 2)
            ],
        ]
    )
    await db_session.flush()

    async def noop(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", noop)
    with caplog.at_level("WARNING"):
        result = await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_type": "return",
                    "item": {"article_number": item.article_number},
                },
            )
        )

    assert await db_session.scalar(select(Task).where(Task.client_id == result["client_id"])) is not None
    assert await db_session.scalar(select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == result["client_id"])) is None
    assert "item_economics.auto_commit_failed | task_id=" in caplog.text


@pytest.mark.integration
async def test_phase7_extracted_valuation_chain_preserves_set_supersede_delete_invariants(db_session):
    workspace, user, item, _task, _basis = await _fixture(db_session)
    initial = await db_session.scalar(
        select(ItemValuation).where(
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
        )
    )
    await set_item_valuation(
        _ctx(db_session, workspace.client_id, user.client_id, {
            "item_client_id": item.client_id,
            "expected_sale_price_minor": 1100,
            "currency": "swedish_krona",
        })
    )
    second = await set_item_valuation(
        _ctx(db_session, workspace.client_id, user.client_id, {
            "item_client_id": item.client_id,
            "expected_sale_price_minor": 1200,
            "currency": "swedish_krona",
        })
    )
    assert second["item_valuation"]["expected_sale_price_minor"] == 1200
    current = await db_session.scalar(
        select(ItemValuation).where(
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )
    await delete_item_valuation(
        _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
    )
    assert initial.superseded_at is not None
    assert initial.superseded_by_id is not None
    assert current.is_deleted is True
