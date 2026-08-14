from datetime import date
from decimal import Decimal
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.item_economics.configuration import (
    ITEM_READINESS_PRECEDENCE,
    EconomicsSelection,
    is_applicable,
    resolve_major_category,
    resolve_economics_configuration,
    resolve_economics_selection,
    resolve_item_economics_status,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup


def _row(**values):
    return SimpleNamespace(is_deleted=values.pop("is_deleted", False), **values)


def test_configuration_classifier_uses_explicit_failure_order_and_same_basis_identity_for_gap():
    group = ProductionCostGroup(client_id="pcg_1", major_category=ItemMajorCategoryEnum.SEAT)
    second = ProductionCostGroup(client_id="pcg_2", major_category=ItemMajorCategoryEnum.SEAT)
    deleted = ProductionCostBasisVersion(
        client_id="pcbv_1",
        production_cost_group_id="pcg_1",
        effective_from=None,
        effective_to=None,
        is_deleted=True,
    )
    today = date(2026, 8, 12)
    assert resolve_economics_configuration(None, [], [], [], today) is EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY
    assert resolve_economics_configuration(ItemMajorCategoryEnum.SEAT, [], [], [], today) is EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP
    assert resolve_economics_configuration(ItemMajorCategoryEnum.SEAT, [group, second], [], [], today) is EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP
    assert resolve_economics_configuration(ItemMajorCategoryEnum.SEAT, [group], [], [], today) is EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION
    assert resolve_economics_configuration(ItemMajorCategoryEnum.SEAT, [group], [deleted], [], today) is EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION


def test_is_applicable_is_half_open_and_excludes_deleted_versions():
    version = _row(effective_from=date(2026, 8, 12), effective_to=date(2026, 8, 13))
    assert not is_applicable(version, date(2026, 8, 11))
    assert is_applicable(version, date(2026, 8, 12))
    assert not is_applicable(version, date(2026, 8, 13))
    version.is_deleted = True
    assert not is_applicable(version, date(2026, 8, 12))


def test_selection_and_configuration_status_share_one_resolution():
    group = _row(client_id="pcg_1", major_category=ItemMajorCategoryEnum.SEAT)
    basis = _row(
        client_id="pcbv_1", production_cost_group_id="pcg_1",
        effective_from=None, effective_to=None, currency=ItemCurrencyEnum.SWEDISH_KRONA,
        cost_per_worker_minute_minor=Decimal("13.0208"),
    )
    model = _row(
        client_id="cmv_1", effective_from=None, effective_to=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
    )
    selection = resolve_economics_selection(
        ItemMajorCategoryEnum.SEAT, [group], [basis], [model], date(2026, 8, 13)
    )
    assert isinstance(selection, EconomicsSelection)
    assert selection.status is EconomicsStatusEnum.OK
    assert resolve_economics_configuration(
        ItemMajorCategoryEnum.SEAT, [group], [basis], [model], date(2026, 8, 13)
    ) is selection.status


def test_item_readiness_uses_registered_order_and_requires_a_purchase_term():
    selection = EconomicsSelection(EconomicsStatusEnum.OK, _row(client_id="g"), _row(currency=ItemCurrencyEnum.SWEDISH_KRONA), _row(currency=ItemCurrencyEnum.SWEDISH_KRONA))
    valuation = _row(expected_sale_price_minor=None, purchase_cost_minor=None, currency=ItemCurrencyEnum.SWEDISH_KRONA)
    purchase_term = _row(calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST)
    assert ITEM_READINESS_PRECEDENCE[0] is EconomicsStatusEnum.ITEM_UNVALUED
    assert resolve_item_economics_status(None, selection, [purchase_term]) is EconomicsStatusEnum.ITEM_UNVALUED
    assert resolve_item_economics_status(valuation, selection, []) is EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE
    valuation.expected_sale_price_minor = 100
    assert resolve_item_economics_status(valuation, selection, [purchase_term]) is EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST
    valuation.expected_sale_price_minor = None
    assert resolve_item_economics_status(valuation, selection, [purchase_term]) is EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE


@pytest.mark.parametrize(
    ("valuation_currency", "basis_currency", "model_currency"),
    [
        (ItemCurrencyEnum.EURO, ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.SWEDISH_KRONA),
        (ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.EURO, ItemCurrencyEnum.SWEDISH_KRONA),
        (ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.SWEDISH_KRONA, ItemCurrencyEnum.EURO),
    ],
    ids=["basis-model", "valuation-model", "valuation-basis"],
)
def test_item_readiness_rejects_each_currency_mismatch_pair(
    valuation_currency, basis_currency, model_currency
):
    selection = EconomicsSelection(
        EconomicsStatusEnum.OK,
        _row(client_id="g"),
        _row(currency=basis_currency),
        _row(currency=model_currency),
    )
    valuation = _row(
        expected_sale_price_minor=100,
        purchase_cost_minor=50,
        currency=valuation_currency,
    )

    assert resolve_item_economics_status(valuation, selection, []) is EconomicsStatusEnum.CURRENCY_MISMATCH


def test_item_readiness_purchase_cost_precedes_currency_mismatch():
    selection = EconomicsSelection(
        EconomicsStatusEnum.OK,
        _row(client_id="g"),
        _row(currency=ItemCurrencyEnum.SWEDISH_KRONA),
        _row(currency=ItemCurrencyEnum.SWEDISH_KRONA),
    )
    valuation = _row(
        expected_sale_price_minor=100,
        purchase_cost_minor=None,
        currency=ItemCurrencyEnum.EURO,
    )
    purchase_term = _row(calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST)

    assert resolve_item_economics_status(valuation, selection, [purchase_term]) is EconomicsStatusEnum.ITEM_MISSING_PURCHASE_COST


def test_item_major_category_snapshot_is_read_only_by_the_registered_resolver():
    app_root = Path(__file__).resolve().parents[4]
    package_roots = (
        app_root / "beyo_manager" / "domain" / "item_economics",
        app_root / "beyo_manager" / "services",
    )
    module_sources = []
    for root in package_roots:
        paths = root.rglob("*.py") if root.name == "services" else root.glob("*.py")
        for path in paths:
            if root.name == "services" and path.parent.name != "item_economics":
                continue
            module_sources.append((path, path.read_text()))

    resolver_source = inspect.getsource(resolve_major_category)
    assert "snapshot" in resolver_source

    set_path = app_root / "beyo_manager" / "services" / "commands" / "item_economics" / "set_item_valuation.py"
    set_source = set_path.read_text()
    assert "resolve_major_category(" in set_source
    assert "resolve_major_category(item.item_major_category_snapshot)" in set_source
    assert "ItemMajorCategoryEnum(" not in set_source
    assert any(path == set_path and "item_major_category_snapshot" in source for path, source in module_sources)
