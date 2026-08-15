from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import (
    ProductionCostBasisVersion,
)
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.routers.api_v1 import tasks as tasks_router
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    commit_item_cost_evaluation,
)
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.commands.tasks.requests import parse_create_task_request
from beyo_manager.services.context import ServiceContext
from beyo_manager.models.database import get_db


def _ctx(session, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "username": "phase8b",
            "role_name": "manager",
        },
        incoming_data=incoming_data,
        session=session,
    )


async def _disable_event_dispatch(monkeypatch) -> None:
    async def noop(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", noop
    )


async def _seed_economic_workspace(
    db_session,
    *,
    purchase_term: bool = False,
    configured: bool = True,
    valuation: bool = False,
) -> tuple[Workspace, User, Item, ItemCategory]:
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"phase8b {token}")
    user = User(
        client_id=f"usr_{token}",
        username=f"phase8b_{token}",
        email=f"{token}@example.test",
        password="test",
    )
    category = ItemCategory(
        client_id=f"itc_{token}",
        workspace_id=workspace.client_id,
        name=f"Wood category {token}",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        item_category_id=category.client_id,
        article_number=f"ART-{token}",
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(category)
    await db_session.flush()
    db_session.add(item)
    await db_session.flush()

    if configured:
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
        db_session.add_all([group, model])
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
        terms = [
            CostModelTerm(
                workspace_id=workspace.client_id,
                cost_model_version_id=model.client_id,
                name="fixed",
                calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
                fixed_amount_minor=100,
                created_by_id=user.client_id,
            )
        ]
        if purchase_term:
            terms.append(
                CostModelTerm(
                    workspace_id=workspace.client_id,
                    cost_model_version_id=model.client_id,
                    name="purchase",
                    calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
                    created_by_id=user.client_id,
                )
            )
        db_session.add_all([basis, *terms])

    if valuation:
        db_session.add(
            ItemValuation(
                workspace_id=workspace.client_id,
                item_id=item.client_id,
                expected_sale_price_minor=1000,
                purchase_cost_minor=None,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=user.client_id,
            )
        )
    await db_session.flush()
    return workspace, user, item, category


async def _current_valuations(db_session, item_id: str) -> list[ItemValuation]:
    return list(
        (
            await db_session.scalars(
                select(ItemValuation)
                .where(ItemValuation.item_id == item_id)
                .order_by(ItemValuation.created_at.asc(), ItemValuation.client_id.asc())
            )
        ).all()
    )


async def _cleanup_committed_workspace(db_session, workspace_id: str, user_id: str) -> None:
    await db_session.rollback()
    for table in (
        ItemCostEvaluationTerm,
        ItemCostEvaluation,
        ItemValuation,
        CostModelTerm,
        ProductionCostBasisVersion,
        CostModelVersion,
        ProductionCostGroup,
        TaskItem,
        Task,
        Item,
        ItemCategory,
        AuditLog,
    ):
        await db_session.execute(delete(table).where(table.workspace_id == workspace_id))
    await db_session.execute(
        text(
            "DELETE FROM history_record_links WHERE history_record_id IN "
            "(SELECT client_id FROM history_records WHERE created_by_id = :user_id)"
        ),
        {"user_id": user_id},
    )
    await db_session.execute(
        text("DELETE FROM history_records WHERE created_by_id = :user_id"),
        {"user_id": user_id},
    )
    await db_session.execute(delete(User).where(User.client_id == user_id))
    await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case_id", "configured", "purchase_term", "item_values", "expected_status"),
    [
        (
            "C1-row-1-full-trio-purchase-term-commits",
            True,
            True,
            {"expected_sale_price_minor": 1000, "purchase_cost_minor": 200, "currency": "swedish_krona"},
            "committed",
        ),
        (
            "C1-row-2-expected-price-commits",
            True,
            False,
            {"expected_sale_price_minor": 1000, "currency": "swedish_krona"},
            "committed",
        ),
        (
            "C1-row-3-purchase-term-missing-purchase-cost",
            True,
            True,
            {"expected_sale_price_minor": 1000, "currency": "swedish_krona"},
            "item_missing_purchase_cost",
        ),
        (
            "C1-row-4-purchase-only-missing-expected-price",
            True,
            False,
            {"purchase_cost_minor": 200, "currency": "swedish_krona"},
            "item_missing_expected_price",
        ),
        (
            "C1-row-5-full-trio-currency-mismatch",
            True,
            True,
            {"expected_sale_price_minor": 1000, "purchase_cost_minor": 200, "currency": "danish_krona"},
            "currency_mismatch",
        ),
        (
            "C1-row-6-unconfigured-workspace",
            False,
            False,
            {"expected_sale_price_minor": 1000, "currency": "swedish_krona"},
            "not_configured_no_cost_group",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) and value.startswith("C1-") else None,
)
async def test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses(
    db_session,
    monkeypatch,
    caplog,
    case_id,
    configured,
    purchase_term,
    item_values,
    expected_status,
):
    del case_id
    await _disable_event_dispatch(monkeypatch)
    workspace, user, _item, category = await _seed_economic_workspace(
        db_session, configured=configured, purchase_term=purchase_term
    )
    item_payload = {
        "article_number": f"NEW-{uuid4().hex}",
        "item_category_id": category.client_id,
        **item_values,
    }
    with caplog.at_level("INFO"):
        result = await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"task_type": "return", "item": item_payload},
            )
        )

    valuations = await _current_valuations(db_session, result["item_id"])
    assert len(valuations) == 1
    valuation = valuations[0]
    assert valuation.expected_sale_price_minor == item_values.get("expected_sale_price_minor")
    assert valuation.purchase_cost_minor == item_values.get("purchase_cost_minor")
    assert valuation.currency.value == item_values["currency"]
    assert valuation.created_by_id == user.client_id
    assert valuation.superseded_at is None

    evaluations = list(
        (
            await db_session.scalars(
                select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == result["client_id"])
            )
        ).all()
    )
    if expected_status == "committed":
        assert len(evaluations) == 1
        assert evaluations[0].expected_sale_price_minor == valuation.expected_sale_price_minor
        assert evaluations[0].purchase_cost_minor == valuation.purchase_cost_minor
        assert len(valuations) == 1, "the auto path must not mirror its own inline valuation"
    else:
        assert evaluations == []
        assert (
            f"item_economics.auto_commit_skipped | task_id={result['client_id']} "
            f"item_id={result['item_id']} status={expected_status}"
        ) in caplog.text


@pytest.mark.integration
async def test_c2_absent_inline_prices_preserves_item_unvalued_flow(db_session, monkeypatch, caplog):
    await _disable_event_dispatch(monkeypatch)
    workspace, user, _item, category = await _seed_economic_workspace(db_session)
    with caplog.at_level("INFO"):
        result = await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_type": "return",
                    "item": {
                        "article_number": f"NEW-{uuid4().hex}",
                        "item_category_id": category.client_id,
                    },
                },
            )
        )
    assert await _current_valuations(db_session, result["item_id"]) == []
    assert await db_session.scalar(
        select(ItemCostEvaluation).where(ItemCostEvaluation.task_id == result["client_id"])
    ) is None
    assert "status=item_unvalued" in caplog.text


@pytest.mark.integration
async def test_b8_inline_no_mirror_has_explicit_commit_mirror_companion(db_session, monkeypatch):
    await _disable_event_dispatch(monkeypatch)
    workspace, user, _item, category = await _seed_economic_workspace(db_session)
    result = await create_task(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "task_type": "return",
                "item": {
                    "article_number": f"NEW-{uuid4().hex}",
                    "item_category_id": category.client_id,
                    "expected_sale_price_minor": 1000,
                    "currency": "swedish_krona",
                },
            },
        )
    )
    assert len(await _current_valuations(db_session, result["item_id"])) == 1
    await commit_item_cost_evaluation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"task_client_id": result["client_id"], "expected_sale_price_minor": 1500},
        )
    )
    valuations = await _current_valuations(db_session, result["item_id"])
    assert len(valuations) == 2
    assert valuations[-1].expected_sale_price_minor == 1500
    assert valuations[-1].superseded_at is None


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case_id", "payload", "message_fragment"),
    [
        (
            "C3-row-1-legacy-plus-valid-trio",
            {
                "item_value_minor": 17,
                "expected_sale_price_minor": 1,
                "currency": "swedish_krona",
            },
            "ITEM_MONEY_MOVED",
        ),
        (
            "C3-row-2-legacy-plus-amount-without-currency",
            {"item_cost_minor": 17, "expected_sale_price_minor": 1},
            "ITEM_MONEY_MOVED",
        ),
        (
            "C3-row-3-legacy-plus-negative-amount",
            {
                "item_currency": "swedish_krona",
                "expected_sale_price_minor": -1,
                "currency": "swedish_krona",
            },
            "item.expected_sale_price_minor: Input should be greater than or equal to 0",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) and value.startswith("C3-") else None,
)
def test_c3_legacy_money_rejection_precedes_inline_currency_validation(
    case_id, payload, message_fragment
):
    del case_id
    with pytest.raises(ValidationError, match=message_fragment):
        parse_create_task_request(
            {"task_type": "return", "item": {"article_number": "A", **payload}}
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case_id", "payload", "message_fragment"),
    [
        ("C5-row-1-expected-without-currency", {"expected_sale_price_minor": 1}, "item.currency"),
        ("C5-row-2-purchase-without-currency", {"purchase_cost_minor": 1}, "item.currency"),
        ("C5-row-4-negative-expected", {"expected_sale_price_minor": -1, "currency": "euro"}, "item.expected_sale_price_minor"),
        ("C5-row-5-negative-purchase", {"purchase_cost_minor": -1, "currency": "euro"}, "item.purchase_cost_minor"),
    ],
    ids=lambda value: value if isinstance(value, str) and value.startswith("C5-") else None,
)
def test_c5_inline_validation_rows_are_exactly_rejected(case_id, payload, message_fragment):
    del case_id
    with pytest.raises(ValidationError, match=message_fragment):
        parse_create_task_request({"task_type": "return", "item": {"article_number": "A", **payload}})


@pytest.mark.integration
async def test_c5_row_3_currency_alone_is_accepted_ignored_and_item_unvalued(
    db_session, monkeypatch, caplog
):
    await _disable_event_dispatch(monkeypatch)
    workspace, user, _item, category = await _seed_economic_workspace(db_session)
    with caplog.at_level("INFO"):
        result = await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_type": "return",
                        "item": {
                            "article_number": f"NEW-{uuid4().hex}",
                            "item_category_id": category.client_id,
                            "currency": "euro",
                        },
                },
            )
        )
    assert result["item_id"]
    assert await _current_valuations(db_session, result["item_id"]) == []
    assert "status=item_unvalued" in caplog.text


@pytest.mark.integration
async def test_c4_row_1_current_valuation_refusal_rolls_back_item_mutation_and_task(
    db_session,
):
    workspace, user, item, _category = await _seed_economic_workspace(db_session, valuation=True)
    workspace_id = workspace.client_id
    user_id = user.client_id
    item_id = item.client_id
    item_article_number = item.article_number
    original_designer = "original"
    item.designer = original_designer
    await db_session.flush()
    await db_session.commit()
    try:
        with pytest.raises(
            ValidationError,
            match=rf"^ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM: item {item_id}.*valuation",
        ):
            await create_task(
                _ctx(
                    db_session,
                    workspace_id,
                    user_id,
                    {
                        "task_type": "return",
                        "item": {
                            "article_number": item_article_number,
                            "designer": "changed-before-refusal",
                            "expected_sale_price_minor": 2000,
                            "currency": "swedish_krona",
                        },
                    },
                )
            )
        await db_session.rollback()
        stored_item = await db_session.scalar(select(Item).where(Item.client_id == item_id))
        assert stored_item.designer == original_designer
        assert await db_session.scalar(
            select(Task).where(Task.workspace_id == workspace_id)
        ) is None
        assert await db_session.scalar(
            select(TaskItem).where(TaskItem.workspace_id == workspace_id)
        ) is None
        assert len(await _current_valuations(db_session, item_id)) == 1
    finally:
        await _cleanup_committed_workspace(db_session, workspace_id, user_id)


@pytest.mark.integration
async def test_c4_row_2_never_valued_existing_item_accepts_inline_price(db_session, monkeypatch):
    await _disable_event_dispatch(monkeypatch)
    workspace, user, item, _category = await _seed_economic_workspace(db_session)
    await db_session.commit()
    try:
        result = await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_type": "return",
                    "item": {
                        "article_number": item.article_number,
                        "expected_sale_price_minor": 1200,
                        "currency": "swedish_krona",
                    },
                },
            )
        )
        assert result["item_id"] == item.client_id
        valuations = await _current_valuations(db_session, item.client_id)
        assert len(valuations) == 1
        assert valuations[0].expected_sale_price_minor == 1200
    finally:
        await _cleanup_committed_workspace(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
async def test_c4_row_3_deleted_only_existing_item_accepts_and_grows_chain(
    db_session, monkeypatch
):
    await _disable_event_dispatch(monkeypatch)
    workspace, user, item, _category = await _seed_economic_workspace(db_session, valuation=True)
    old = await db_session.scalar(select(ItemValuation).where(ItemValuation.item_id == item.client_id))
    old.is_deleted = True
    await db_session.flush()
    await db_session.commit()
    try:
        await create_task(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {
                    "task_type": "return",
                    "item": {
                        "article_number": item.article_number,
                        "purchase_cost_minor": 300,
                        "currency": "swedish_krona",
                    },
                },
            )
        )
        valuations = await _current_valuations(db_session, item.client_id)
        assert len(valuations) == 2
        assert valuations[0].is_deleted is True
        assert valuations[1].purchase_cost_minor == 300
        assert valuations[1].superseded_at is None
        assert valuations[1].is_deleted is False
    finally:
        await _cleanup_committed_workspace(db_session, workspace.client_id, user.client_id)


@pytest.mark.integration
def test_c6_router_body_declares_inline_trio_fields():
    assert {
        "expected_sale_price_minor",
        "purchase_cost_minor",
        "currency",
    }.issubset(tasks_router._TaskItemInputBody.model_fields)
    body = tasks_router._TaskItemInputBody.model_validate(
        {
            "expected_sale_price_minor": 10,
            "purchase_cost_minor": 5,
            "currency": "swedish_krona",
        }
    )
    assert body.model_dump() == {
        "client_id": None,
        "article_number": None,
        "sku": None,
        "item_category_id": None,
        "quantity": 1,
        "designer": None,
        "height_in_cm": None,
        "width_in_cm": None,
        "depth_in_cm": None,
        "item_value_minor": None,
        "item_cost_minor": None,
        "item_currency": None,
        "expected_sale_price_minor": 10,
        "purchase_cost_minor": 5,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA,
        "item_position": None,
        "item_zone": None,
        "external_id": None,
        "external_url": None,
        "external_source": None,
        "external_order_id": None,
        "can_have_upholstery": True,
    }


@pytest.mark.integration
def test_c6_create_task_endpoint_preserves_trio_into_domain_validator(monkeypatch):
    app = FastAPI()
    app.include_router(tasks_router.router, prefix="/tasks")
    captured = {}

    async def fake_get_db():
        yield object()

    async def fake_run_service(command, context):
        captured["incoming_data"] = context.incoming_data
        return SimpleNamespace(success=True, data={"client_id": "tsk_test"}, error=None)

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": "worker",
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(tasks_router, "run_service", fake_run_service)

    response = TestClient(app).put(
        "/tasks",
        json={
            "task_type": "return",
            "item": {
                "article_number": "A-1",
                "expected_sale_price_minor": 17,
                "purchase_cost_minor": 9,
                "currency": "swedish_krona",
            },
        },
    )

    assert response.status_code == 200
    assert captured["incoming_data"]["item"] == {
        "article_number": "A-1",
        "expected_sale_price_minor": 17,
        "purchase_cost_minor": 9,
        "currency": ItemCurrencyEnum.SWEDISH_KRONA,
    }
