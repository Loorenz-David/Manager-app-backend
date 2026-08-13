from datetime import date
from types import SimpleNamespace

from beyo_manager.domain.item_economics.configuration import is_applicable, resolve_economics_configuration
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
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
