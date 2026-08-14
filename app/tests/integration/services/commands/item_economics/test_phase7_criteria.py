"""REVIEWER PROBE — phase 7 review r1. Disposable; deleted at session close."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    ItemCostEvaluationKindEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum, TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    commit_item_cost_evaluation,
)
from beyo_manager.services.commands.item_economics.create_item_cost_projection import (
    create_item_cost_projection,
)
from beyo_manager.services.commands.item_economics.delete_item_cost_projection import (
    delete_item_cost_projection,
)
from beyo_manager.services.commands.item_economics.promote_item_cost_projection import (
    promote_item_cost_projection,
)
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


def _ctx(session, workspace_id, user_id, data):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "probe"},
        incoming_data=data,
        session=session,
    )


async def _fixture(db_session, *, purchase_cost=None, price=1000, purchase_term=False):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"probe {token}")
    user = User(client_id=f"usr_{token}", username=f"probe_{token}", email=f"{token}@example.test", password="t")
    item = Item(
        client_id=f"itm_{token}",
        workspace_id=workspace.client_id,
        article_number=f"ART-{token}",
        item_major_category_snapshot="wood",
        created_by_id=user.client_id,
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
        cost_per_worker_minute_minor=Decimal("99.9999"), created_by_id=user.client_id,
    )
    db_session.add(basis)
    await db_session.flush()
    terms = [CostModelTerm(
        workspace_id=workspace.client_id, cost_model_version_id=model.client_id, name="fixed",
        calculation_type=CostModelTermCalculationTypeEnum.FIXED_AMOUNT, fixed_amount_minor=100,
        created_by_id=user.client_id,
    )]
    if purchase_term:
        terms.append(CostModelTerm(
            workspace_id=workspace.client_id, cost_model_version_id=model.client_id, name="purchase",
            calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
            created_by_id=user.client_id,
        ))
    valuation = ItemValuation(
        workspace_id=workspace.client_id, item_id=item.client_id,
        expected_sale_price_minor=price, purchase_cost_minor=purchase_cost,
        currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
    )
    db_session.add_all([*terms, valuation, TaskItem(
        workspace_id=workspace.client_id, task_id=task.client_id, item_id=item.client_id,
        role=TaskItemRoleEnum.PRIMARY, created_by_id=user.client_id,
    )])
    await db_session.flush()
    return workspace, user, item, task, basis


async def _current_valuation(db_session, item_id):
    return await db_session.scalar(
        select(ItemValuation).where(
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )


# ---------------------------------------------------------------- PROBE 1
@pytest.mark.integration
async def test_probe_c5_row_7_projection_override_must_not_touch_the_valuation(db_session):
    """A speculative projection must never advance the item's valuation chain."""
    workspace, user, item, task, _ = await _fixture(db_session)
    before = await _current_valuation(db_session, item.client_id)
    assert before.expected_sale_price_minor == 1000

    await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id,
        "source": "scratch",
        "expected_sale_price_minor": 2000,
        "label": "what-if",
    }))

    after = await _current_valuation(db_session, item.client_id)
    rows = list((await db_session.scalars(
        select(ItemValuation).where(ItemValuation.item_id == item.client_id)
    )).all())
    assert after.client_id == before.client_id
    assert (after.expected_sale_price_minor, after.purchase_cost_minor) == (
        before.expected_sale_price_minor,
        before.purchase_cost_minor,
    )
    assert len(rows) == 1, (
        f"projection advanced the valuation chain: {len(rows)} valuation rows, "
        f"current price now {after.expected_sale_price_minor}"
    )


# ---------------------------------------------------------------- PROBE 2
@pytest.mark.integration
async def test_probe_c2_second_commit_leaves_one_current_and_backlinks(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    first = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    second = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "expected_sale_price_minor": 1500}))

    current = list((await db_session.scalars(select(ItemCostEvaluation).where(
        ItemCostEvaluation.task_id == task.client_id,
        ItemCostEvaluation.kind == ItemCostEvaluationKindEnum.COMMITTED,
        ItemCostEvaluation.superseded_at.is_(None),
        ItemCostEvaluation.is_deleted.is_(False),
    ))).all())
    assert len(current) == 1
    assert current[0].client_id == second["evaluation"]["client_id"]
    old = await db_session.scalar(select(ItemCostEvaluation).where(
        ItemCostEvaluation.client_id == first["evaluation"]["client_id"]))
    assert old.superseded_at is not None
    assert old.superseded_by_id == second["evaluation"]["client_id"]


# ---------------------------------------------------------------- PROBE 3
@pytest.mark.integration
@pytest.mark.parametrize("state", [
    TaskStateEnum.PENDING, TaskStateEnum.ASSIGNED, TaskStateEnum.WORKING,
    TaskStateEnum.STALLED, TaskStateEnum.READY,
], ids=[
    "C3-row-1-PENDING", "C3-row-2-ASSIGNED", "C3-row-3-WORKING",
    "C3-row-4-STALLED", "C3-row-5-READY",
])
async def test_probe_c3_admitted_states(db_session, state):
    workspace, user, item, task, _ = await _fixture(db_session)
    task.state = state
    await db_session.flush()
    result = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    assert result["evaluation"]["kind"] == "committed"


@pytest.mark.integration
@pytest.mark.parametrize("state", [
    TaskStateEnum.RESOLVED, TaskStateEnum.FAILED, TaskStateEnum.CANCELLED,
], ids=["C3-row-6-RESOLVED", "C3-row-7-FAILED", "C3-row-8-CANCELLED"])
async def test_probe_c3_terminal_states(db_session, state):
    workspace, user, item, task, _ = await _fixture(db_session)
    task.state = state
    await db_session.flush()
    with pytest.raises(ValidationError, match=r"^ITEM_COST_TASK_TERMINAL:"):
        await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id}))


@pytest.mark.integration
async def test_probe_c3_deleted_task(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    task.is_deleted = True
    await db_session.flush()
    with pytest.raises(NotFound):
        await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id}))


# ---------------------------------------------------------------- PROBE 4
@pytest.mark.integration
async def test_probe_c4_no_primary_item(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    task_item = await db_session.scalar(select(TaskItem).where(TaskItem.task_id == task.client_id))
    from datetime import datetime, timezone
    task_item.removed_at = datetime.now(timezone.utc)
    await db_session.flush()
    with pytest.raises(ValidationError, match=r"^ITEM_COST_NO_PRIMARY_ITEM:"):
        await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id}))


# ---------------------------------------------------------------- PROBE 5
@pytest.mark.integration
async def test_probe_c5_none_equals_none_writes_no_mirror(db_session):
    """purchase cost NULL both sides + equal price => no mirror row."""
    workspace, user, item, task, _ = await _fixture(db_session)
    before = await _current_valuation(db_session, item.client_id)
    await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    rows = list((await db_session.scalars(
        select(ItemValuation).where(ItemValuation.item_id == item.client_id))).all())
    assert len(rows) == 1
    assert rows[0].client_id == before.client_id


@pytest.mark.integration
async def test_probe_c5_override_writes_mirror_on_explicit_commit(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "expected_sale_price_minor": 1500}))
    current = await _current_valuation(db_session, item.client_id)
    assert current.expected_sale_price_minor == 1500
    assert current.created_by_id == user.client_id
    assert current.currency == ItemCurrencyEnum.SWEDISH_KRONA


# ---------------------------------------------------------------- PROBE 6
@pytest.mark.integration
async def test_probe_c8_promotion_rows(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    projection = await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "source": "scratch"}))
    pid = projection["evaluation"]["client_id"]

    # soft-deleted projection -> NotFound
    other = await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "source": "scratch"}))
    await delete_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "client_id": other["evaluation"]["client_id"]}))
    with pytest.raises(NotFound):
        await promote_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
            "client_id": other["evaluation"]["client_id"]}))

    other_workspace = Workspace(client_id=f"ws_{uuid4().hex}", name="other workspace")
    other_user = User(
        client_id=f"usr_{uuid4().hex}",
        username=f"other_{uuid4().hex}",
        email=f"{uuid4().hex}@example.test",
        password="test",
    )
    db_session.add_all([other_workspace, other_user])
    await db_session.flush()
    with pytest.raises(NotFound):
        await promote_item_cost_projection(_ctx(
            db_session,
            other_workspace.client_id,
            other_user.client_id,
            {"client_id": pid},
        ))

    # terminal task + live projection -> ITEM_COST_TASK_TERMINAL
    task.state = TaskStateEnum.RESOLVED
    await db_session.flush()
    with pytest.raises(ValidationError, match=r"^ITEM_COST_TASK_TERMINAL:"):
        await promote_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
            "client_id": pid}))


@pytest.mark.integration
async def test_probe_c8_delete_projection_never_touches_committed(db_session):
    workspace, user, item, task, _ = await _fixture(db_session)
    committed = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    projection = await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "source": "committed"}))
    await delete_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "client_id": projection["evaluation"]["client_id"]}))
    row = await db_session.scalar(select(ItemCostEvaluation).where(
        ItemCostEvaluation.client_id == committed["evaluation"]["client_id"]))
    assert row.is_deleted is False
    assert row.superseded_at is None


# ---------------------------------------------------------------- PROBE 7
@pytest.mark.integration
async def test_probe_c9_auto_commit_skipped_line_for_unvalued_item(db_session, monkeypatch, caplog):
    workspace, user, item, task, _ = await _fixture(db_session)
    valuation = await _current_valuation(db_session, item.client_id)
    valuation.is_deleted = True
    await db_session.flush()

    async def noop(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", noop)
    with caplog.at_level("INFO"):
        result = await create_task(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_type": "return", "item": {"article_number": item.article_number}}))

    assert await db_session.scalar(select(ItemCostEvaluation).where(
        ItemCostEvaluation.task_id == result["client_id"])) is None
    assert "item_economics.auto_commit_skipped" in caplog.text
    assert "status=item_unvalued" in caplog.text


# ---------------------------------------------------------------- PROBE 8
@pytest.mark.integration
async def test_probe_c10_history_reaches_task_flow_and_audit_row_exists(db_session):
    from beyo_manager.models.tables.audit.audit_log import AuditLog
    from beyo_manager.services.queries.tasks.task_flow_records import get_task_flow_records

    workspace, user, item, task, _ = await _fixture(db_session)
    await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))

    ctx = _ctx(db_session, workspace.client_id, user.client_id, {"task_id": task.client_id})
    ctx.query_params = {}
    flow = await get_task_flow_records(ctx)
    records = flow["flow_records"]
    assert [r["entity_type"] for r in records] == ["task"]
    assert records[0]["entity_client_id"] == task.client_id
    assert records[0]["description"] == "Item cost evaluation committed"

    audits = list((await db_session.scalars(select(AuditLog).where(
        AuditLog.workspace_id == workspace.client_id))).all())
    assert [a.event for a in audits] == ["item_cost_evaluation.committed"]


@pytest.mark.integration
async def test_probe_c10_nothing_fires_on_a_failed_commit(db_session):
    from beyo_manager.models.tables.audit.audit_log import AuditLog
    workspace, user, item, task, _ = await _fixture(db_session)
    task.state = TaskStateEnum.RESOLVED
    await db_session.flush()
    with pytest.raises(ValidationError):
        await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id}))
    audits = list((await db_session.scalars(select(AuditLog).where(
        AuditLog.workspace_id == workspace.client_id))).all())
    assert audits == []


# ---------------------------------------------------------------- PROBE 9 (C1)
@pytest.mark.integration
async def test_probe_c1_snapshot_immutability_after_superseding_everything(db_session):
    """Supersede valuation + both config chains; the committed rows must not move."""
    from beyo_manager.domain.item_economics.calculator import rederive
    from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm

    workspace, user, item, task, basis = await _fixture(db_session)
    committed = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    eid = committed["evaluation"]["client_id"]
    row = await db_session.scalar(select(ItemCostEvaluation).where(ItemCostEvaluation.client_id == eid))
    before = {c.name: getattr(row, c.name) for c in ItemCostEvaluation.__table__.columns}
    terms = list((await db_session.scalars(select(ItemCostEvaluationTerm).where(
        ItemCostEvaluationTerm.evaluation_id == eid))).all())
    terms_before = [{c.name: getattr(t, c.name) for c in ItemCostEvaluationTerm.__table__.columns} for t in terms]

    # supersede the valuation
    from beyo_manager.services.commands.item_economics.set_item_valuation import set_item_valuation
    await set_item_valuation(_ctx(db_session, workspace.client_id, user.client_id, {
        "item_client_id": item.client_id, "expected_sale_price_minor": 9999,
        "currency": "swedish_krona"}))
    # supersede both config chains
    basis.fixed_monthly_cost_minor = 555555
    model = await db_session.scalar(select(CostModelVersion).where(
        CostModelVersion.workspace_id == workspace.client_id))
    term_row = await db_session.scalar(select(CostModelTerm).where(
        CostModelTerm.cost_model_version_id == model.client_id))
    term_row.fixed_amount_minor = 77777
    await db_session.flush()
    db_session.expire_all()

    row = await db_session.scalar(select(ItemCostEvaluation).where(ItemCostEvaluation.client_id == eid))
    after = {c.name: getattr(row, c.name) for c in ItemCostEvaluation.__table__.columns}
    assert after == before
    terms_after = [{c.name: getattr(t, c.name) for c in ItemCostEvaluationTerm.__table__.columns}
                   for t in (await db_session.scalars(select(ItemCostEvaluationTerm).where(
                       ItemCostEvaluationTerm.evaluation_id == eid))).all()]
    assert terms_after == terms_before
    result = rederive(row, list((await db_session.scalars(select(ItemCostEvaluationTerm).where(
        ItemCostEvaluationTerm.evaluation_id == eid))).all()))
    assert isinstance(result, tuple), result
    rate, budget, allowed = result
    assert rate == row.cost_per_worker_minute_minor_snapshot
    assert budget == row.production_budget_minor
    assert allowed == row.allowed_worker_minutes


# --------------------------------------------------------------- PROBE 10 (C6/C7)
@pytest.mark.integration
@pytest.mark.parametrize(("case", "identity"), [
    ("item_missing_major_category", "ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY"),
    ("no_cost_group", "ITEM_COST_NO_COST_GROUP"),
    ("no_basis_version", "ITEM_COST_NO_BASIS_VERSION"),
    ("basis_not_applicable", "ITEM_COST_NO_BASIS_VERSION"),
    ("no_cost_model_version", "ITEM_COST_NO_COST_MODEL_VERSION"),
    ("item_unvalued", "ITEM_COST_ITEM_UNVALUED"),
    ("missing_expected_price", "ITEM_COST_EXPECTED_PRICE_REQUIRED"),
    ("missing_purchase_cost", "ITEM_COST_PURCHASE_COST_REQUIRED"),
    ("currency_mismatch_valuation_vs_basis", "ITEM_COST_CURRENCY_MISMATCH"),
    ("currency_mismatch_basis_vs_model", "ITEM_COST_CURRENCY_MISMATCH"),
], ids=[
    "C6-C7-row-1-item_missing_major_category",
    "C6-C7-row-2-no_cost_group",
    "C6-C7-row-3-no_basis_version",
    "C6-C7-row-4-basis_not_applicable",
    "C6-C7-row-5-no_cost_model_version",
    "C6-C7-row-6-item_unvalued",
    "C6-C7-row-7-missing_expected_price",
    "C6-C7-row-8-missing_purchase_cost",
    "C6-C7-row-9-currency_mismatch_valuation_vs_basis",
    "C6-C7-row-10-currency_mismatch_basis_vs_model",
])
async def test_probe_c6_c7_refusal_rows(db_session, case, identity):
    from datetime import timedelta
    workspace, user, item, task, basis = await _fixture(
        db_session, purchase_term=(case == "missing_purchase_cost"))
    group = await db_session.scalar(select(ProductionCostGroup).where(
        ProductionCostGroup.workspace_id == workspace.client_id))
    model = await db_session.scalar(select(CostModelVersion).where(
        CostModelVersion.workspace_id == workspace.client_id))
    valuation = await _current_valuation(db_session, item.client_id)

    if case == "item_missing_major_category":
        item.item_major_category_snapshot = None
    elif case == "no_cost_group":
        group.is_deleted = True
    elif case == "no_basis_version":
        basis.is_deleted = True
    elif case == "basis_not_applicable":
        basis.effective_from = (basis.created_at.date() + timedelta(days=5))
    elif case == "no_cost_model_version":
        model.is_deleted = True
    elif case == "item_unvalued":
        valuation.is_deleted = True
    elif case == "missing_expected_price":
        valuation.expected_sale_price_minor = None
        valuation.purchase_cost_minor = 10
    elif case == "missing_purchase_cost":
        valuation.purchase_cost_minor = None
    elif case == "currency_mismatch_valuation_vs_basis":
        valuation.currency = ItemCurrencyEnum.EURO
    elif case == "currency_mismatch_basis_vs_model":
        model.currency = ItemCurrencyEnum.EURO
    await db_session.flush()

    with pytest.raises(ValidationError, match=rf"^{identity}:"):
        await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
            "task_client_id": task.client_id}))
    assert await db_session.scalar(select(ItemCostEvaluation).where(
        ItemCostEvaluation.task_id == task.client_id)) is None


# --------------------------------------------------------------- PROBE 11 (C14)
@pytest.mark.integration
async def test_probe_c14_ordering_pins(db_session):
    from datetime import datetime, timezone
    from beyo_manager.models.tables.item_economics.item_cost_evaluation_term import ItemCostEvaluationTerm
    from beyo_manager.services.queries.item_economics.list_task_evaluations import list_task_evaluations

    workspace, user, item, task, _ = await _fixture(db_session)
    first = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    second = await commit_item_cost_evaluation(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "expected_sale_price_minor": 1200}))
    p1 = await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "source": "scratch"}))
    p2 = await create_item_cost_projection(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id, "source": "scratch"}))

    # equal created_at on two terms of the current row -> client_id ASC is the arbiter
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = list((await db_session.scalars(select(ItemCostEvaluationTerm).where(
        ItemCostEvaluationTerm.evaluation_id == second["evaluation"]["client_id"]))).all())
    extra = ItemCostEvaluationTerm(
        workspace_id=workspace.client_id, evaluation_id=second["evaluation"]["client_id"],
        name="tie", calculation_type=rows[0].calculation_type,
        percent_value=rows[0].percent_value, fixed_amount_minor=rows[0].fixed_amount_minor,
        amount_minor=rows[0].amount_minor, created_at=stamp)
    db_session.add(extra)
    rows[0].created_at = stamp
    await db_session.flush()

    read = await list_task_evaluations(_ctx(db_session, workspace.client_id, user.client_id, {
        "task_client_id": task.client_id}))
    assert [r["client_id"] for r in read["evaluations"]] == [
        second["evaluation"]["client_id"], first["evaluation"]["client_id"]]
    assert [r["client_id"] for r in read["projections"]] == [
        p2["evaluation"]["client_id"], p1["evaluation"]["client_id"]]
    current = read["evaluations"][0]
    tie_ids = [t["client_id"] for t in current["terms"] if t["created_at"].startswith("2026-01-01")]
    assert tie_ids == sorted(tie_ids)
