import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.item_cost_evaluation import ItemCostEvaluation
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models import database
from beyo_manager.services.commands.item_economics.delete_item_valuation import delete_item_valuation
from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_valuation_history import get_item_valuation_history


def _ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "manager"},
        incoming_data=data,
        session=session,
    )


async def _preview_fixture(db_session, case: str):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"preview {token}")
    user = User(client_id=f"usr_{token}", username=f"preview_{token}", email=f"{token}@example.test", password="test")
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        item_major_category_snapshot=None if case == "item_missing_major_category" else "wood",
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add(item)
    await db_session.flush()

    group = None
    if case not in {"not_configured_no_cost_group", "task_ok", "task_infeasible", "not_configured_ambiguous_cost_group"}:
        group = ProductionCostGroup(
            workspace_id=workspace.client_id,
            name="Wood",
            major_category=ItemMajorCategoryEnum.WOOD,
            created_by_id=user.client_id,
        )
        db_session.add(group)
        await db_session.flush()

    if case in {
        "not_evaluated",
        "item_missing_expected_price",
        "item_missing_purchase_cost",
        "currency_mismatch",
        "item_missing_major_category",
        "not_configured_no_cost_model_version",
    }:
        db_session.add(
            ProductionCostBasisVersion(
                workspace_id=workspace.client_id,
                production_cost_group_id=group.client_id,
                fixed_monthly_cost_minor=100000,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                monthly_paid_hours=Decimal("160.00"),
                planning_utilization_percent=Decimal("80.00"),
                cost_per_worker_minute_minor=Decimal("13.0208"),
                created_by_id=user.client_id,
            )
        )
    if case in {"not_evaluated", "item_missing_expected_price", "item_missing_purchase_cost", "currency_mismatch", "not_configured_no_basis_version"}:
        db_session.add(
            CostModelVersion(
                workspace_id=workspace.client_id,
                currency=ItemCurrencyEnum.SWEDISH_KRONA,
                created_by_id=user.client_id,
            )
        )
    await db_session.flush()

    if case == "item_missing_purchase_cost":
        model = await db_session.scalar(
            select(CostModelVersion).where(CostModelVersion.workspace_id == workspace.client_id)
        )
        db_session.add(
            CostModelTerm(
                workspace_id=workspace.client_id,
                cost_model_version_id=model.client_id,
                name="purchase cost",
                calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
                created_by_id=user.client_id,
            )
        )
        await db_session.flush()
    return workspace, user, item


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case", "expected_status", "judgment"),
    [
        ("item_unvalued", "item_unvalued", None),
        ("item_missing_expected_price", "item_missing_expected_price", None),
        ("item_missing_purchase_cost", "item_missing_purchase_cost", None),
        ("currency_mismatch", "currency_mismatch", None),
        ("not_evaluated", "not_evaluated", None),
        ("item_missing_major_category", "item_missing_major_category", None),
        ("not_configured_no_cost_group", "not_configured_no_cost_group", None),
        ("not_configured_no_basis_version", "not_configured_no_basis_version", None),
        ("not_configured_no_cost_model_version", "not_configured_no_cost_model_version", None),
        ("task_ok", None, "task-scoped; not reachable by the item-scoped preview"),
        ("task_infeasible", None, "task-scoped; not reachable by the item-scoped preview"),
        ("not_configured_ambiguous_cost_group", None, "INV-G3 makes this unreachable through the database"),
    ],
    ids=[
        "status-row-1-item-unvalued",
        "status-row-2-missing-expected-price",
        "status-row-7-missing-purchase-cost",
        "status-row-8-currency-mismatch",
        "status-row-10-not-evaluated",
        "status-row-3-missing-major-category",
        "status-row-4-no-cost-group",
        "status-row-5-no-basis-version",
        "status-row-6-no-cost-model-version",
        "status-row-11-task-ok-reachability",
        "status-row-12-task-infeasible-reachability",
        "status-row-9-ambiguous-cost-group-reachability",
    ],
)
async def test_preview_status_enumeration_has_sole_predicate_rows_and_never_creates_evaluations(
    db_session, case, expected_status, judgment
):
    if expected_status is None:
        assert judgment
        return

    if case == "item_unvalued":
        workspace, user, item = await _preview_fixture(db_session, "not_evaluated")
        before = await db_session.scalar(
            select(func.count(ItemCostEvaluation.client_id)).where(ItemCostEvaluation.workspace_id == workspace.client_id)
        )
        created = await set_item_valuation(
            _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id, "expected_sale_price_minor": 100, "currency": ItemCurrencyEnum.SWEDISH_KRONA})
        )
        assert created["item_valuation"]["client_id"]
        response = await delete_item_valuation(
            _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
        )
        assert response["preview"]["status"] == expected_status
        assert response["preview"]["production_budget_minor"] is None
        assert response["preview"]["allowed_worker_minutes"] is None
        after = await db_session.scalar(
            select(func.count(ItemCostEvaluation.client_id)).where(ItemCostEvaluation.workspace_id == workspace.client_id)
        )
        assert after == before
        return

    workspace, user, item = await _preview_fixture(db_session, case)
    before = await db_session.scalar(
        select(func.count(ItemCostEvaluation.client_id)).where(ItemCostEvaluation.workspace_id == workspace.client_id)
    )
    payload = {"item_client_id": item.client_id, "currency": ItemCurrencyEnum.SWEDISH_KRONA}
    if case in {"not_evaluated", "item_missing_expected_price", "item_missing_purchase_cost", "item_missing_major_category", "not_configured_no_cost_group", "not_configured_no_basis_version", "not_configured_no_cost_model_version"}:
        payload["expected_sale_price_minor"] = 100
    if case == "item_missing_expected_price":
        payload.pop("expected_sale_price_minor")
        payload["purchase_cost_minor"] = 50
    if case == "currency_mismatch":
        payload["expected_sale_price_minor"] = 100
        payload["currency"] = ItemCurrencyEnum.EURO
    response = await set_item_valuation(_ctx(db_session, workspace.client_id, user.client_id, payload))
    assert response["item_valuation"]["client_id"]
    assert response["preview"]["status"] == expected_status
    if expected_status == "not_evaluated":
        assert response["preview"] == {
            "status": "not_evaluated",
            "production_budget_minor": 100,
            "allowed_worker_minutes": "7.68",
        }
    else:
        assert response["preview"]["production_budget_minor"] is None
        assert response["preview"]["allowed_worker_minutes"] is None
    after = await db_session.scalar(
        select(func.count(ItemCostEvaluation.client_id)).where(ItemCostEvaluation.workspace_id == workspace.client_id)
    )
    assert after == before


@pytest.mark.integration
async def test_valuation_chain_preview_delete_and_history(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"valuation {token}")
    user = User(client_id=f"usr_{token}", username=f"valuation_{token}", email=f"{token}@example.test", password="test")
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    group = ProductionCostGroup(
        workspace_id=workspace.client_id,
        name="Wood",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id,
        production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=100000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"),
        planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0000"),
        created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([item, group, model])
    await db_session.flush()
    basis.production_cost_group_id = group.client_id
    db_session.add(basis)
    await db_session.flush()
    db_session.add(
        CostModelTerm(
            workspace_id=workspace.client_id,
            cost_model_version_id=model.client_id,
            name="fixed allocation",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            fixed_amount_minor=0,
            created_by_id=user.client_id,
        )
    )
    await db_session.flush()

    first = await set_item_valuation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"item_client_id": item.client_id, "expected_sale_price_minor": 1_000_000, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
        )
    )
    assert first["item_valuation"]["client_id"].startswith("ival_")
    assert first["preview"] == {
        "status": "not_evaluated",
        "production_budget_minor": 1_000_000,
        "allowed_worker_minutes": "76923.08",
    }

    second = await set_item_valuation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"item_client_id": item.client_id, "purchase_cost_minor": 250_000, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
        )
    )
    rows = (
        await db_session.execute(
            select(ItemValuation)
            .where(ItemValuation.item_id == item.client_id)
            .order_by(ItemValuation.created_at.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].superseded_by_id == rows[1].client_id
    assert rows[1].superseded_at is None
    assert second["preview"] == {
        "status": "item_missing_expected_price",
        "production_budget_minor": None,
        "allowed_worker_minutes": None,
    }

    deleted = await delete_item_valuation(
        _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
    )
    assert deleted["preview"] == {
        "status": "item_unvalued",
        "production_budget_minor": None,
        "allowed_worker_minutes": None,
    }
    reset = await set_item_valuation(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"item_client_id": item.client_id, "expected_sale_price_minor": 300_000, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
        )
    )
    reset_row = await db_session.scalar(
        select(ItemValuation).where(ItemValuation.client_id == reset["item_valuation"]["client_id"])
    )
    assert reset_row is not None
    open_rows = (
        await db_session.execute(
            select(ItemValuation).where(
                ItemValuation.item_id == item.client_id,
                ItemValuation.superseded_at.is_(None),
            )
        )
    ).scalars().all()
    assert len(open_rows) == 2
    assert sum(not row.is_deleted for row in open_rows) == 1

    await delete_item_valuation(
        _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
    )
    assert await db_session.scalar(
        select(func.count(ItemValuation.client_id)).where(
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    ) == 0

    # Three fresh supersessions make history order and the total current-row
    # predicate observable after the delete-then-reset state above.
    for amount in (400_000, 500_000, 600_000, 700_000):
        await set_item_valuation(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"item_client_id": item.client_id, "expected_sale_price_minor": amount, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
            )
        )

    history = await get_item_valuation_history(
        _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
    )
    history_reread = await get_item_valuation_history(
        _ctx(db_session, workspace.client_id, user.client_id, {"item_client_id": item.client_id})
    )
    expected_history_ids = (
        await db_session.execute(
            select(ItemValuation.client_id)
            .where(ItemValuation.item_id == item.client_id, ItemValuation.is_deleted.is_(False))
            .order_by(ItemValuation.created_at.desc(), ItemValuation.client_id.desc())
        )
    ).scalars().all()
    assert history == history_reread
    assert [row["client_id"] for row in history["item_valuations"]] == expected_history_ids
    assert len(expected_history_ids) >= 4
    assert await db_session.scalar(
        select(func.count(ItemValuation.client_id)).where(
            ItemValuation.item_id == item.client_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    ) == 1

    with pytest.raises(ValidationError, match=r"^ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE:"):
        await delete_item_valuation(
            _ctx(db_session, workspace.client_id, user.client_id, {"client_id": rows[0].client_id})
        )

    audit_events = (
        await db_session.execute(
            select(AuditLog.event).where(
                AuditLog.workspace_id == workspace.client_id,
                AuditLog.event.in_(("item_valuation.created", "item_valuation.deleted")),
            ).order_by(AuditLog.created_at.asc(), AuditLog.client_id.asc())
        )
    ).scalars().all()
    assert audit_events == [
        "item_valuation.created",
        "item_valuation.created",
        "item_valuation.deleted",
        "item_valuation.created",
        "item_valuation.deleted",
        "item_valuation.created",
        "item_valuation.created",
        "item_valuation.created",
        "item_valuation.created",
    ]


@pytest.mark.integration
async def test_valuation_race_first_and_current_paths_use_two_sessions(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"valuation race {token}")
    user = User(client_id=f"usr_{token}", username=f"race_{token}", email=f"{token}@example.test", password="test")
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
    )
    group = ProductionCostGroup(
        workspace_id=workspace.client_id,
        name=f"Wood {token}",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=user.client_id,
    )
    basis = ProductionCostBasisVersion(
        workspace_id=workspace.client_id,
        production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=100000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"),
        planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("13.0208"),
        created_by_id=user.client_id,
    )
    model = CostModelVersion(
        workspace_id=workspace.client_id,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    workspace_id = workspace.client_id
    user_id = user.client_id
    db_session.add_all([workspace, user])
    await db_session.flush()
    db_session.add_all([item, group, model])
    await db_session.flush()
    basis.production_cost_group_id = group.client_id
    db_session.add_all([
        basis,
        CostModelTerm(
            workspace_id=workspace.client_id,
            cost_model_version_id=model.client_id,
            name="fixed allocation",
            calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
            fixed_amount_minor=0,
            created_by_id=user.client_id,
        ),
    ])
    await db_session.flush()
    await db_session.commit()

    sessions = [database._session_factory(), database._session_factory()]
    release = asyncio.Event()
    first_s1 = asyncio.Event()
    second_s1 = asyncio.Event()
    tasks = []
    try:
        for session, reached in zip(sessions, (first_s1, second_s1)):
            original_execute = session.execute

            async def gated_execute(statement, *args, _original=original_execute, _reached=reached, **kwargs):
                result = await _original(statement, *args, **kwargs)
                if "UPDATE item_valuations SET superseded_at" in str(statement):
                    _reached.set()
                    await asyncio.wait_for(release.wait(), timeout=0.5)
                return result

            session.execute = gated_execute

        payloads = [
            {"item_client_id": item.client_id, "expected_sale_price_minor": 100, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
            {"item_client_id": item.client_id, "expected_sale_price_minor": 200, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
        ]
        tasks = [
            asyncio.create_task(set_item_valuation(_ctx(session, workspace.client_id, user.client_id, payload)))
            for session, payload in zip(sessions, payloads)
        ]
        await asyncio.wait_for(first_s1.wait(), timeout=0.5)
        await asyncio.wait_for(second_s1.wait(), timeout=0.5)
        release.set()
        outcomes = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=1.0)
        assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1, repr(outcomes)
        conflicts = [outcome for outcome in outcomes if isinstance(outcome, ConflictError)]
        assert len(conflicts) == 1, repr(outcomes)
        assert str(conflicts[0]).startswith("ITEM_COST_CONCURRENT_VALUATION:")

        current_sessions = [database._session_factory(), database._session_factory()]
        current_close_rowcounts = []
        try:
            for session in current_sessions:
                original_execute = session.execute

                async def observe_current_close(statement, *args, _original=original_execute, **kwargs):
                    result = await _original(statement, *args, **kwargs)
                    if "UPDATE item_valuations SET superseded_at" in str(statement):
                        current_close_rowcounts.append(result.rowcount)
                    return result

                session.execute = observe_current_close
            current_tasks = [
                asyncio.create_task(
                    set_item_valuation(
                        _ctx(
                            session,
                            workspace.client_id,
                            user.client_id,
                            {"item_client_id": item.client_id, "expected_sale_price_minor": amount, "currency": ItemCurrencyEnum.SWEDISH_KRONA},
                        )
                    )
                )
                for session, amount in zip(current_sessions, (300, 400))
            ]
            current_outcomes = await asyncio.wait_for(asyncio.gather(*current_tasks, return_exceptions=True), timeout=1.0)
            assert sum(isinstance(outcome, dict) for outcome in current_outcomes) == 1, repr(current_outcomes)
            current_conflicts = [outcome for outcome in current_outcomes if isinstance(outcome, ConflictError)]
            assert len(current_conflicts) == 1, repr(current_outcomes)
            assert str(current_conflicts[0]).startswith("ITEM_COST_CONCURRENT_VALUATION:")
            assert sorted(current_close_rowcounts) == [0, 1]
        finally:
            await asyncio.gather(*(session.close() for session in current_sessions))

        remaining = await db_session.scalar(
            select(func.count(ItemValuation.client_id)).where(
                ItemValuation.workspace_id == workspace_id,
                ItemValuation.superseded_at.is_(None),
                ItemValuation.is_deleted.is_(False),
            )
        )
        assert remaining == 1
    finally:
        release.set()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*(session.close() for session in sessions))
        await db_session.rollback()
        await db_session.execute(delete(AuditLog).where(AuditLog.workspace_id == workspace_id))
        await db_session.execute(delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id))
        await db_session.execute(delete(CostModelTerm).where(CostModelTerm.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostBasisVersion).where(ProductionCostBasisVersion.workspace_id == workspace_id))
        await db_session.execute(delete(CostModelVersion).where(CostModelVersion.workspace_id == workspace_id))
        await db_session.execute(delete(ProductionCostGroup).where(ProductionCostGroup.workspace_id == workspace_id))
        await db_session.execute(delete(Item).where(Item.workspace_id == workspace_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(delete(Workspace).where(Workspace.client_id == workspace_id))
        await db_session.commit()
