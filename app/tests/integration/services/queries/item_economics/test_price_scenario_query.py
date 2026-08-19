from __future__ import annotations

import inspect
from datetime import datetime, timezone
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from beyo_manager.domain.item_economics.configuration import EconomicsSelection
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    EconomicsStatusEnum,
)
from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.domain.task_steps.enums import (
    TaskStepReadinessStatusEnum,
    TaskStepStateEnum,
)
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import (
    CostModelVersion,
)
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import (
    ProductionCostBasisVersion,
)
from beyo_manager.models.tables.item_economics.production_cost_group import (
    ProductionCostGroup,
)
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext


module = import_module(
    "beyo_manager.services.queries.item_economics.get_task_price_scenario"
)


class _ExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self.rows)

    def __iter__(self):
        return iter(self.rows)


class _TypicalSession:
    def __init__(self, steps, typical_rows):
        self.results = [_ExecuteResult(steps), _ExecuteResult(typical_rows)]

    async def execute(self, _statement):
        return self.results.pop(0)


class _UserSession:
    def __init__(self, user):
        self.user = user

    async def scalar(self, _statement):
        return self.user


def _ctx(session, task_id="tsk_scenario"):
    return ServiceContext(
        identity={
            "workspace_id": "ws_scenario",
            "user_id": "usr_scenario",
            "role_name": "manager",
        },
        incoming_data={"task_client_id": task_id},
        query_params={},
        session=session,
    )


def _step(section_id, *, state=TaskStepStateEnum.PENDING, deleted=False):
    return TaskStep(
        client_id=f"tsp_{section_id}_{state.value}",
        workspace_id="ws_scenario",
        task_id="tsk_scenario",
        working_section_id=section_id,
        state=state,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        total_dependencies=0,
        completed_dependencies=0,
        total_working_seconds=0,
        is_deleted=deleted,
    )


def _typical_row(section_id, value, *, sample_count=5):
    return SimpleNamespace(
        client_id=section_id,
        typical_worker_seconds=value,
        sample_count=sample_count,
    )


@pytest.mark.integration
async def test_c3_zero_typical_is_not_usable_and_uses_the_median() -> None:
    session = _TypicalSession(
        [_step("wsec_zero"), _step("wsec_measured")],
        [
            _typical_row("wsec_zero", 0, sample_count=5),
            _typical_row("wsec_measured", 100),
        ],
    )

    result = await module._typical_block(_ctx(session), "tsk_scenario")

    assert result["total_seconds"] == 200
    assert result["sections_without_sample"] == 1
    assert result["is_estimated"] is True


@pytest.mark.integration
async def test_c4_even_median_is_quantised_once_per_substituted_section() -> None:
    session = _TypicalSession(
        [_step(f"wsec_{index}") for index in range(4)],
        [
            _typical_row("wsec_0", 10),
            _typical_row("wsec_1", 11),
            _typical_row("wsec_2", None),
            _typical_row("wsec_3", None),
        ],
    )

    result = await module._typical_block(_ctx(session), "tsk_scenario")

    assert result["total_seconds"] == 41
    assert result["sections_without_sample"] == 2


@pytest.mark.integration
async def test_phase3_c3_half_even_median_differs_from_truncation() -> None:
    session = _TypicalSession(
        [_step(f"wsec_half_even_{index}") for index in range(3)],
        [
            _typical_row("wsec_half_even_0", 11),
            _typical_row("wsec_half_even_1", 12),
            _typical_row("wsec_half_even_2", None),
        ],
    )

    result = await module._typical_block(_ctx(session), "tsk_scenario")

    assert result["total_seconds"] == 35
    assert result["sections_without_sample"] == 1


@pytest.mark.parametrize(
    "state",
    [
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.CANCELLED,
        TaskStepStateEnum.FAILED,
    ],
)
@pytest.mark.integration
async def test_c5_each_excluded_state_removes_its_section(state) -> None:
    session = _TypicalSession(
        [_step("wsec_live"), _step("wsec_excluded", state=state)],
        [_typical_row("wsec_live", 100)],
    )

    result = await module._typical_block(_ctx(session), "tsk_scenario")

    assert result["sections_total"] == 1
    assert result["total_seconds"] == 100


@pytest.mark.integration
async def test_c5_deleted_steps_do_not_create_a_participating_section() -> None:
    session = _TypicalSession(
        [_step("wsec_live"), _step("wsec_deleted", deleted=True)],
        [_typical_row("wsec_live", 100)],
    )

    result = await module._typical_block(_ctx(session), "tsk_scenario")

    assert result["sections_total"] == 1
    assert result["total_seconds"] == 100


@pytest.mark.integration
async def test_c6_nonempty_no_evidence_is_estimated_zero() -> None:
    result = await module._typical_block(
        _ctx(_TypicalSession([_step("wsec_missing")], [])),
        "tsk_scenario",
    )

    assert result["total_seconds"] == 0
    assert result["is_estimated"] is True
    assert result["sections_without_sample"] == result["sections_total"] == 1


@pytest.mark.integration
async def test_c6_empty_participating_set_is_estimated_zero() -> None:
    result = await module._typical_block(
        _ctx(_TypicalSession([], [])),
        "tsk_scenario",
    )

    assert result["total_seconds"] == 0
    assert result["is_estimated"] is True
    assert result["sections_without_sample"] == result["sections_total"] == 0


@pytest.mark.integration
async def test_c19_missing_typical_statement_row_uses_defensive_lookup() -> None:
    result = await module._typical_block(
        _ctx(_TypicalSession([_step("wsec_deleted_row")], [])),
        "tsk_scenario",
    )

    assert result["sections_total"] == 1
    assert result["sections_without_sample"] == 1
    assert result["total_seconds"] == 0


def _scenario_objects(
    *,
    expected_price=855_000,
    purchase_cost=None,
    task_state=TaskStateEnum.ASSIGNED,
    basis_currency=ItemCurrencyEnum.SWEDISH_KRONA,
    model_currency=ItemCurrencyEnum.SWEDISH_KRONA,
    valuation_currency=ItemCurrencyEnum.SWEDISH_KRONA,
    rate=Decimal("1300.0000"),
    with_valuation=True,
    with_purchase_term=False,
    with_deleted_purchase_term=False,
    with_percent_term=True,
    with_item=True,
    selection_status=EconomicsStatusEnum.OK,
    cost_model_id="cmv_full_identifier_01",
):
    user = User(
        client_id="usr_scenario",
        username="Marta Lind",
        email="marta@example.com",
        password="secret",
        profile_picture="https://example.com/marta.webp",
    )
    task = Task(
        client_id="tsk_scenario",
        workspace_id="ws_scenario",
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=task_state,
    )
    item = (
        Item(
            client_id="itm_scenario",
            workspace_id="ws_scenario",
            article_number="0000608",
            item_category_snapshot="Dining chairs",
            item_major_category_snapshot="wood",
            quantity=6,
        )
        if with_item
        else None
    )
    valuation = (
        ItemValuation(
            client_id="ival_scenario",
            workspace_id="ws_scenario",
            item_id="itm_scenario",
            expected_sale_price_minor=expected_price,
            purchase_cost_minor=purchase_cost,
            currency=valuation_currency,
            created_at=datetime(2026, 8, 14, 10, 24, tzinfo=timezone.utc),
            created_by_id=user.client_id,
        )
        if with_valuation
        else None
    )
    group = ProductionCostGroup(
        client_id="pcg_scenario",
        workspace_id="ws_scenario",
        name="Wood",
        major_category="wood",
        created_by_id=user.client_id,
    )
    basis = ProductionCostBasisVersion(
        client_id="pcbv_full_identifier_01",
        workspace_id="ws_scenario",
        production_cost_group_id=group.client_id,
        fixed_monthly_cost_minor=1,
        currency=basis_currency,
        monthly_paid_hours=Decimal("1.00"),
        planning_utilization_percent=Decimal("1.00"),
        cost_per_worker_minute_minor=rate,
        created_by_id=user.client_id,
    )
    model = CostModelVersion(
        client_id=cost_model_id,
        workspace_id="ws_scenario",
        currency=model_currency,
        created_by_id=user.client_id,
    )
    terms = []
    if with_percent_term:
        terms.append(
            CostModelTerm(
                client_id="cmvt_percent",
                workspace_id="ws_scenario",
                cost_model_version_id=model.client_id,
                name="Percentage",
                calculation_type=(
                    CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE
                ),
                percent_value=Decimal("78.000"),
                created_by_id=user.client_id,
            )
        )
    if with_purchase_term:
        terms.append(
            CostModelTerm(
                client_id="cmvt_purchase",
                workspace_id="ws_scenario",
                cost_model_version_id=model.client_id,
                name="Purchase",
                calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
                created_by_id=user.client_id,
            )
        )
    if with_deleted_purchase_term:
        terms.append(
            CostModelTerm(
                client_id="cmvt_deleted_purchase",
                workspace_id="ws_scenario",
                cost_model_version_id=model.client_id,
                name="Deleted purchase",
                calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
                is_deleted=True,
                created_by_id=user.client_id,
            )
        )
    selection = EconomicsSelection(
        selection_status,
        group if selection_status is EconomicsStatusEnum.OK else None,
        basis if selection_status is EconomicsStatusEnum.OK else None,
        model if selection_status is EconomicsStatusEnum.OK else None,
    )
    return SimpleNamespace(
        user=user,
        task=task,
        item=item,
        valuation=valuation,
        selection=selection,
        terms=terms,
    )


async def _run_scenario(
    monkeypatch,
    *,
    status=EconomicsStatusEnum.NOT_EVALUATED,
    binding="bound",
    typical=None,
    created_by_present=True,
    **object_options,
):
    objects = _scenario_objects(**object_options)
    typical = typical or {
        "total_seconds": 12_300,
        "is_estimated": False,
        "sections_without_sample": 0,
        "sections_total": 4,
        "method": "median_completed_section_totals",
        "window_days": 90,
        "min_sample_size": 5,
    }

    async def fake_status(_ctx):
        return SimpleNamespace(status=status, item_binding=binding)

    async def fake_task_and_item(_ctx):
        return objects.task, objects.item

    async def fake_valuation(_ctx, _item_id):
        return objects.valuation

    async def fake_preview(_ctx, _item):
        return objects.selection, objects.terms

    async def fake_typical(_ctx, _task_id):
        return typical

    monkeypatch.setattr(module, "get_task_budget_status", fake_status)
    monkeypatch.setattr(module, "_load_task_and_item", fake_task_and_item)
    monkeypatch.setattr(module, "_current_valuation", fake_valuation)
    monkeypatch.setattr(module, "_load_preview_inputs", fake_preview)
    monkeypatch.setattr(module, "_typical_block", fake_typical)
    session = _UserSession(objects.user if created_by_present else None)
    return await module.get_task_price_scenario(_ctx(session)), objects


@pytest.mark.parametrize(
    ("status", "expected_present"),
    [
        (EconomicsStatusEnum.OK, True),
        (EconomicsStatusEnum.INFEASIBLE, True),
        (EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY, False),
        (EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP, False),
        (EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP, False),
        (EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION, False),
        (EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION, False),
        (EconomicsStatusEnum.ITEM_UNVALUED, True),
        (EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE, True),
        (EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST, False),
        (EconomicsStatusEnum.CURRENCY_MISMATCH, False),
        (EconomicsStatusEnum.NOT_EVALUATED, True),
    ],
)
@pytest.mark.integration
async def test_c1_status_matrix_has_twelve_exact_rows(
    monkeypatch,
    status,
    expected_present,
) -> None:
    options = {}
    if status is EconomicsStatusEnum.ITEM_UNVALUED:
        options["with_valuation"] = False
    if status is EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE:
        options["expected_price"] = None
    result, _ = await _run_scenario(monkeypatch, status=status, **options)

    assert (result["model"] is not None) is expected_present
    assert (result["anchors"] is not None) is expected_present
    assert (result["domain"] is not None) is expected_present


@pytest.mark.parametrize(
    "status",
    [
        EconomicsStatusEnum.ITEM_UNVALUED,
        EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE,
    ],
)
@pytest.mark.integration
async def test_c1_b6_b7_purchase_term_without_cost_collapses_all_blocks(
    monkeypatch,
    status,
) -> None:
    result, _ = await _run_scenario(
        monkeypatch,
        status=status,
        with_valuation=status is not EconomicsStatusEnum.ITEM_UNVALUED,
        expected_price=None,
        with_purchase_term=True,
    )

    assert result["model"] is None
    assert result["anchors"] is None
    assert result["domain"] is None


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("healthy", True),
        ("terminal", False),
        ("no_primary", False),
        ("deleted_item", False),
        ("no_valuation", False),
        ("no_group", False),
        ("currency_mismatch", False),
        ("purchase_missing", False),
        ("null_expected_price", True),
        ("committed_live_model_expired", False),
    ],
)
@pytest.mark.integration
async def test_c2_can_commit_uses_each_live_admission_condition(
    monkeypatch,
    case,
    expected,
) -> None:
    options = {}
    status = EconomicsStatusEnum.NOT_EVALUATED
    if case == "terminal":
        options["task_state"] = TaskStateEnum.RESOLVED
    elif case in {"no_primary", "deleted_item"}:
        options["with_item"] = False
    elif case == "no_valuation":
        options["with_valuation"] = False
    elif case == "no_group":
        options["selection_status"] = EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP
    elif case == "currency_mismatch":
        options["valuation_currency"] = ItemCurrencyEnum.EURO
    elif case == "purchase_missing":
        options["with_purchase_term"] = True
    elif case == "null_expected_price":
        options["expected_price"] = None
        status = EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE
    elif case == "committed_live_model_expired":
        options["selection_status"] = (
            EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION
        )
        status = EconomicsStatusEnum.OK
    result, _ = await _run_scenario(monkeypatch, status=status, **options)

    assert result["can_commit"] is expected


@pytest.mark.integration
async def test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model(
    monkeypatch,
) -> None:
    result, _ = await _run_scenario(
        monkeypatch,
        with_deleted_purchase_term=True,
    )

    assert result["can_commit"] is True
    assert result["model"]["constant_deduction_minor"] == 0


@pytest.mark.parametrize("sections_total", [1, 0])
@pytest.mark.integration
async def test_c6_no_evidence_keeps_null_anchor_members_and_no_domain(
    monkeypatch,
    sections_total,
) -> None:
    result, _ = await _run_scenario(
        monkeypatch,
        typical={
            "total_seconds": 0,
            "is_estimated": True,
            "sections_without_sample": sections_total,
            "sections_total": sections_total,
            "method": "median_completed_section_totals",
            "window_days": 90,
            "min_sample_size": 5,
        },
    )

    assert result["anchors"] == {
        "is_fundable": False,
        "break_even_price_minor": None,
        "suggested_price_minor": None,
        "infeasible_at_or_below_minor": 29,
    }
    assert result["domain"] is None
    assert result["typical"]["sections_without_sample"] == sections_total
    assert result["typical"]["sections_total"] == sections_total


@pytest.mark.integration
async def test_c7_saved_absence_null_price_and_missing_author(monkeypatch) -> None:
    absent, _ = await _run_scenario(monkeypatch, with_valuation=False)
    null_price, _ = await _run_scenario(
        monkeypatch,
        status=EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE,
        expected_price=None,
    )
    missing_author, _ = await _run_scenario(
        monkeypatch,
        created_by_present=False,
    )

    assert absent["saved"] is None and absent["currency"] is None
    assert null_price["saved"]["expected_sale_price_minor"] is None
    assert null_price["saved"]["created_by"]["username"] == "Marta Lind"
    assert missing_author["saved"]["created_by"] is None


@pytest.mark.integration
async def test_c8_fingerprint_uses_full_ids_fixed_order_and_changes_by_model(
    monkeypatch,
) -> None:
    first, _ = await _run_scenario(monkeypatch)
    reread, _ = await _run_scenario(monkeypatch)
    changed, _ = await _run_scenario(
        monkeypatch,
        cost_model_id="cmv_full_identifier_02",
    )
    null_model, _ = await _run_scenario(
        monkeypatch,
        status=EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP,
    )

    assert first["config_fingerprint"] == (
        "cmv_full_identifier_01:pcbv_full_identifier_01:v1"
    )
    assert reread["config_fingerprint"] == first["config_fingerprint"]
    assert changed["config_fingerprint"] != first["config_fingerprint"]
    assert null_model["config_fingerprint"] is None


@pytest.mark.parametrize("binding", ["detached", "mismatched"])
@pytest.mark.integration
async def test_c9_non_bound_binding_governs_the_full_payload(
    monkeypatch, binding
) -> None:
    result, _ = await _run_scenario(
        monkeypatch,
        binding=binding,
        with_item=binding == "mismatched",
    )

    assert result["item_binding"] == binding
    assert (result["item"] is None) is (binding == "detached")
    assert result["saved"] is None
    assert result["currency"] is None
    assert result["model"] is None
    assert result["anchors"] is None
    assert result["domain"] is None
    assert result["config_fingerprint"] is None
    assert result["typical"]["sections_total"] == 4
    if binding == "detached":
        assert result["can_commit"] is False
    else:
        assert result["can_commit"] is True


@pytest.mark.integration
async def test_c18_suggested_price_rounds_to_the_domain_step(monkeypatch) -> None:
    result, _ = await _run_scenario(monkeypatch)

    assert result["anchors"]["break_even_price_minor"] == 1_211_335
    assert result["anchors"]["suggested_price_minor"] == 1_215_000


@pytest.mark.integration
async def test_c18_null_domain_forces_null_suggestion_with_break_even(
    monkeypatch,
) -> None:
    result, _ = await _run_scenario(
        monkeypatch,
        rate=Decimal("1.0000"),
        with_percent_term=False,
        typical={
            "total_seconds": 60,
            "is_estimated": False,
            "sections_without_sample": 0,
            "sections_total": 1,
            "method": "median_completed_section_totals",
            "window_days": 90,
            "min_sample_size": 5,
        },
    )

    assert result["anchors"]["break_even_price_minor"] == 1
    assert result["anchors"]["suggested_price_minor"] is None
    assert result["domain"] is None


@pytest.mark.parametrize("case", ["unknown", "deleted", "cross_workspace"])
@pytest.mark.integration
async def test_c10_task_resolution_is_workspace_scoped_and_hides_deleted(
    db_session,
    case,
) -> None:
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_price_{token}", name=f"Price {token}")
    foreign = Workspace(client_id=f"ws_price_foreign_{token}", name=f"Foreign {token}")
    deleted_task = Task(
        client_id=f"tsk_price_deleted_{token}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
        is_deleted=True,
    )
    foreign_task = Task(
        client_id=f"tsk_price_foreign_{token}",
        workspace_id=foreign.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.ASSIGNED,
    )
    db_session.add_all([workspace, foreign])
    await db_session.flush()
    db_session.add_all([deleted_task, foreign_task])
    await db_session.flush()
    task_id = {
        "unknown": f"tsk_price_unknown_{token}",
        "deleted": deleted_task.client_id,
        "cross_workspace": foreign_task.client_id,
    }[case]
    try:
        with pytest.raises(NotFound, match="Task not found"):
            await module.get_task_price_scenario(
                ServiceContext(
                    identity={
                        "workspace_id": workspace.client_id,
                        "user_id": "usr",
                        "role_name": "manager",
                    },
                    incoming_data={"task_client_id": task_id},
                    query_params={},
                    session=db_session,
                )
            )
    finally:
        await db_session.execute(
            delete(Task).where(
                Task.workspace_id.in_([workspace.client_id, foreign.client_id])
            )
        )
        await db_session.execute(
            delete(Workspace).where(
                Workspace.client_id.in_([workspace.client_id, foreign.client_id])
            )
        )
        await db_session.flush()

    task_residue = await db_session.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.workspace_id.in_([workspace.client_id, foreign.client_id]))
    )
    workspace_residue = await db_session.scalar(
        select(func.count())
        .select_from(Workspace)
        .where(Workspace.client_id.in_([workspace.client_id, foreign.client_id]))
    )
    assert task_residue == 0
    assert workspace_residue == 0


@pytest.mark.integration
async def test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain(
    db_session,
    monkeypatch,
) -> None:
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_price_chain_{token}", name=f"Chain {token}")
    user = User(
        client_id=f"usr_price_chain_{token}",
        username=f"price_chain_{token}",
        email=f"price_chain_{token}@example.test",
        password="test",
    )
    item = Item(
        client_id=f"itm_price_chain_{token}",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        quantity=6,
        created_by_id=user.client_id,
    )
    older = ItemValuation(
        client_id=f"ival_price_chain_old_{token}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        expected_sale_price_minor=700_000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        superseded_at=datetime(2026, 8, 18, 9, 0, tzinfo=timezone.utc),
        created_by_id=user.client_id,
    )
    current = ItemValuation(
        client_id=f"ival_price_chain_current_{token}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        expected_sale_price_minor=854_999,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
    )
    objects = _scenario_objects()
    objects.task.client_id = f"tsk_price_chain_{token}"
    objects.task.workspace_id = workspace.client_id
    workspace_id = workspace.client_id
    user_id = user.client_id
    item_id = item.client_id
    current_valuation_id = current.client_id
    current_price = 855_000

    async def fake_status(_ctx):
        return SimpleNamespace(
            status=EconomicsStatusEnum.NOT_EVALUATED,
            item_binding="bound",
        )

    async def fake_task_and_item(_ctx):
        return objects.task, item

    async def fake_preview(_ctx, _item):
        return objects.selection, objects.terms

    async def fake_typical(_ctx, _task_id):
        return {
            "total_seconds": 12_300,
            "is_estimated": False,
            "sections_without_sample": 0,
            "sections_total": 4,
            "method": "median_completed_section_totals",
            "window_days": 90,
            "min_sample_size": 5,
        }

    monkeypatch.setattr(module, "get_task_budget_status", fake_status)
    monkeypatch.setattr(module, "_load_task_and_item", fake_task_and_item)
    monkeypatch.setattr(module, "_load_preview_inputs", fake_preview)
    monkeypatch.setattr(module, "_typical_block", fake_typical)

    try:
        db_session.add_all([workspace, user])
        await db_session.flush()
        db_session.add(item)
        await db_session.flush()
        db_session.add(older)
        await db_session.flush()
        db_session.add(current)
        await db_session.flush()
        # The mutant this row exists to catch (dropping superseded_at IS NULL) returns
        # whichever live row the scan reaches first. Updating `older` BEFORE `current`
        # puts the older row's newer tuple earlier in the heap, so the mutant returns
        # the older row and this test goes red. Measured at review r1: swap these two
        # updates and the mutant passes 3/3. Heap order is not a guarantee — if this
        # ever stops discriminating, that is what changed.
        # The assertions below do not depend on any of it: the unmutated query is
        # deterministic by uix_item_valuations_current, a partial unique index on
        # item_id in models/tables/item_economics/item_valuation.py.
        older.superseded_by_id = current.client_id
        await db_session.flush()
        current.expected_sale_price_minor = current_price
        await db_session.commit()

        result = await module.get_task_price_scenario(
            ServiceContext(
                identity={
                    "workspace_id": workspace.client_id,
                    "user_id": user.client_id,
                    "role_name": "manager",
                },
                incoming_data={"task_client_id": objects.task.client_id},
                query_params={},
                session=db_session,
            )
        )

        assert result["saved"]["valuation_id"] == current_valuation_id
        assert result["saved"]["expected_sale_price_minor"] == current_price
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id)
        )
        await db_session.execute(delete(Item).where(Item.client_id == item_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(
            delete(Workspace).where(Workspace.client_id == workspace_id)
        )
        await db_session.commit()

    valuation_residue = await db_session.scalar(
        select(func.count())
        .select_from(ItemValuation)
        .where(ItemValuation.workspace_id == workspace_id)
    )
    item_residue = await db_session.scalar(
        select(func.count()).select_from(Item).where(Item.client_id == item_id)
    )
    user_residue = await db_session.scalar(
        select(func.count()).select_from(User).where(User.client_id == user_id)
    )
    workspace_residue = await db_session.scalar(
        select(func.count())
        .select_from(Workspace)
        .where(Workspace.client_id == workspace_id)
    )
    assert valuation_residue == 0
    assert item_residue == 0
    assert user_residue == 0
    assert workspace_residue == 0


@pytest.mark.integration
async def test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen(
    db_session,
    monkeypatch,
) -> None:
    token = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_price_del_{token}", name=f"Deleted {token}")
    user = User(
        client_id=f"usr_price_del_{token}",
        username=f"price_del_{token}",
        email=f"price_del_{token}@example.test",
        password="test",
    )
    item = Item(
        client_id=f"itm_price_del_{token}",
        workspace_id=workspace.client_id,
        item_major_category_snapshot="wood",
        quantity=6,
        created_by_id=user.client_id,
    )
    # The realistic post-delete state: delete_item_valuation.py:delete_item_valuation sets
    # is_deleted with superseded_at still null, and it is reachable from the live route
    # routers/api_v1/item_economics.py:route_delete_item_valuation. The partial index
    # uix_item_valuations_current covers live rows only, so this row is legal.
    deleted = ItemValuation(
        client_id=f"ival_price_del_{token}",
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        expected_sale_price_minor=910_000,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=user.client_id,
        is_deleted=True,
        deleted_at=datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc),
        deleted_by_id=user.client_id,
    )
    objects = _scenario_objects()
    objects.task.client_id = f"tsk_price_del_{token}"
    objects.task.workspace_id = workspace.client_id
    workspace_id = workspace.client_id
    user_id = user.client_id
    item_id = item.client_id

    async def fake_status(_ctx):
        return SimpleNamespace(
            status=EconomicsStatusEnum.NOT_EVALUATED,
            item_binding="bound",
        )

    async def fake_task_and_item(_ctx):
        return objects.task, item

    async def fake_preview(_ctx, _item):
        return objects.selection, objects.terms

    async def fake_typical(_ctx, _task_id):
        return {
            "total_seconds": 12_300,
            "is_estimated": False,
            "sections_without_sample": 0,
            "sections_total": 4,
            "method": "median_completed_section_totals",
            "window_days": 90,
            "min_sample_size": 5,
        }

    monkeypatch.setattr(module, "get_task_budget_status", fake_status)
    monkeypatch.setattr(module, "_load_task_and_item", fake_task_and_item)
    monkeypatch.setattr(module, "_load_preview_inputs", fake_preview)
    monkeypatch.setattr(module, "_typical_block", fake_typical)

    try:
        db_session.add_all([workspace, user])
        await db_session.flush()
        db_session.add(item)
        await db_session.flush()
        db_session.add(deleted)
        await db_session.commit()

        result = await module.get_task_price_scenario(
            ServiceContext(
                identity={
                    "workspace_id": workspace.client_id,
                    "user_id": user.client_id,
                    "role_name": "manager",
                },
                incoming_data={"task_client_id": objects.task.client_id},
                query_params={},
                session=db_session,
            )
        )

        # serialize_task_price_scenario emits `saved` wholesale: with the row hidden there is
        # no dict to hold valuation_id, expected_sale_price_minor or created_by, so this one
        # assertion is the strictest available form of all three. Drop
        # is_deleted.is_(False) from _current_valuation and `saved` becomes a dict carrying
        # the deleted row's ID, 910000, and this user's byline.
        assert result["saved"] is None
        assert result["currency"] is None
        # The deleted row would also readmit commit: task ASSIGNED, selection OK, currencies
        # agreeing and no purchase term leave valuation-presence as the only false conjunct.
        assert result["can_commit"] is False
    finally:
        await db_session.rollback()
        await db_session.execute(
            delete(ItemValuation).where(ItemValuation.workspace_id == workspace_id)
        )
        await db_session.execute(delete(Item).where(Item.client_id == item_id))
        await db_session.execute(delete(User).where(User.client_id == user_id))
        await db_session.execute(
            delete(Workspace).where(Workspace.client_id == workspace_id)
        )
        await db_session.commit()

    valuation_residue = await db_session.scalar(
        select(func.count())
        .select_from(ItemValuation)
        .where(ItemValuation.workspace_id == workspace_id)
    )
    item_residue = await db_session.scalar(
        select(func.count()).select_from(Item).where(Item.client_id == item_id)
    )
    user_residue = await db_session.scalar(
        select(func.count()).select_from(User).where(User.client_id == user_id)
    )
    workspace_residue = await db_session.scalar(
        select(func.count())
        .select_from(Workspace)
        .where(Workspace.client_id == workspace_id)
    )
    assert valuation_residue == 0
    assert item_residue == 0
    assert user_residue == 0
    assert workspace_residue == 0


@pytest.mark.integration
def test_c14_query_service_does_not_call_the_budget_divider() -> None:
    source = inspect.getsource(module)

    assert "divide_production_budget" not in source


@pytest.mark.integration
def test_c16_reciprocal_comment_pairs_are_present() -> None:
    price_source = inspect.getsource(
        import_module("beyo_manager.domain.item_economics.price_scenario")
    )
    calculator_source = inspect.getsource(
        import_module("beyo_manager.domain.item_economics.calculator")
    )
    item_serializer_source = inspect.getsource(
        import_module("beyo_manager.domain.item_economics.serializers")
    )
    case_serializer_source = inspect.getsource(
        import_module("beyo_manager.domain.cases.serializers")
    )

    assert "domain/item_economics/calculator.py:_shape_error" in price_source
    assert "domain/item_economics/price_scenario.py:_shape_error" in calculator_source
    assert "domain/cases/serializers.py:serialize_user_light" in item_serializer_source
    assert (
        "domain/item_economics/serializers.py:serialize_task_price_scenario"
        in case_serializer_source
    )
