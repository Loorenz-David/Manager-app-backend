from datetime import date
from decimal import Decimal

import pytest

from beyo_manager.domain.item_economics.configuration import (
    resolve_economics_configuration,
    resolve_major_category,
)
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup


TODAY = date(2026, 8, 13)


def _group(client_id: str, category: ItemMajorCategoryEnum, *, deleted: bool = False) -> ProductionCostGroup:
    return ProductionCostGroup(
        client_id=client_id,
        workspace_id="ws_1",
        name=client_id,
        major_category=category,
        created_by_id="usr_1",
        is_deleted=deleted,
    )


def _basis(client_id: str, group_id: str, *, deleted: bool = False) -> ProductionCostBasisVersion:
    return ProductionCostBasisVersion(
        client_id=client_id,
        workspace_id="ws_1",
        production_cost_group_id=group_id,
        effective_from=None,
        effective_to=None,
        fixed_monthly_cost_minor=100,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        monthly_paid_hours=Decimal("160.00"),
        planning_utilization_percent=Decimal("80.00"),
        cost_per_worker_minute_minor=Decimal("1.0000"),
        created_by_id="usr_1",
        is_deleted=deleted,
    )


def _model(client_id: str, *, deleted: bool = False) -> CostModelVersion:
    return CostModelVersion(
        client_id=client_id,
        workspace_id="ws_1",
        effective_from=None,
        effective_to=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id="usr_1",
        is_deleted=deleted,
    )


def _status(
    category: ItemMajorCategoryEnum | None,
    groups: list[ProductionCostGroup],
    basis: list[ProductionCostBasisVersion],
    models: list[CostModelVersion],
) -> EconomicsStatusEnum:
    return resolve_economics_configuration(category, groups, basis, models, TODAY)


def test_resolve_major_category_maps_only_known_snapshot_values():
    assert resolve_major_category(None) is None
    assert resolve_major_category("metal") is None
    assert resolve_major_category("wood") is ItemMajorCategoryEnum.WOOD
    assert resolve_major_category("seat") is ItemMajorCategoryEnum.SEAT


@pytest.mark.parametrize(
    ("case", "category", "groups", "basis", "models", "expected"),
    [
        (
            "V1-missing-category-with-everything-present",
            None,
            [_group("pcg_wood", ItemMajorCategoryEnum.WOOD)],
            [_basis("pcbv_wood", "pcg_wood")],
            [_model("cmv_1")],
            EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY,
        ),
        (
            "V2-wrong-category-group",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_wood", ItemMajorCategoryEnum.WOOD)],
            [],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP,
        ),
        (
            "V2b-only-matching-group-is-soft-deleted",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT, deleted=True)],
            [],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_GROUP,
        ),
        (
            "V3-two-active-matching-groups",
            ItemMajorCategoryEnum.SEAT,
            [
                _group("pcg_seat_a", ItemMajorCategoryEnum.SEAT),
                _group("pcg_seat_b", ItemMajorCategoryEnum.SEAT),
            ],
            [],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP,
        ),
        (
            "V4-basis-hangs-on-other-category-group",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT), _group("pcg_wood", ItemMajorCategoryEnum.WOOD)],
            [_basis("pcbv_wood", "pcg_wood")],
            [_model("cmv_1")],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION,
        ),
        (
            "V4b-only-basis-is-soft-deleted-open-row",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT)],
            [_basis("pcbv_seat", "pcg_seat", deleted=True)],
            [_model("cmv_1")],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION,
        ),
        (
            "V5-no-applicable-model",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT)],
            [_basis("pcbv_seat", "pcg_seat")],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION,
        ),
        (
            "V6-everything-present",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT)],
            [_basis("pcbv_seat", "pcg_seat")],
            [_model("cmv_1")],
            EconomicsStatusEnum.OK,
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_classifier_value_rows_have_one_first_failure(
    case, category, groups, basis, models, expected
):
    assert _status(category, groups, basis, models) is expected, case

@pytest.mark.parametrize(
    ("case", "category", "groups", "basis", "models", "expected"),
    [
        (
            "P1-missing-category-before-no-group",
            None,
            [],
            [],
            [],
            EconomicsStatusEnum.ITEM_MISSING_MAJOR_CATEGORY,
        ),
        (
            "P3-ambiguous-before-no-basis",
            ItemMajorCategoryEnum.SEAT,
            [
                _group("pcg_seat_a", ItemMajorCategoryEnum.SEAT),
                _group("pcg_seat_b", ItemMajorCategoryEnum.SEAT),
            ],
            [],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_AMBIGUOUS_COST_GROUP,
        ),
        (
            "P4-no-basis-before-no-model",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT)],
            [],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_BASIS_VERSION,
        ),
        (
            "P5-no-model-before-ok",
            ItemMajorCategoryEnum.SEAT,
            [_group("pcg_seat", ItemMajorCategoryEnum.SEAT)],
            [_basis("pcbv_seat", "pcg_seat")],
            [],
            EconomicsStatusEnum.NOT_CONFIGURED_NO_COST_MODEL_VERSION,
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_classifier_adjacent_pair_rows_choose_the_earlier_failure(
    case, category, groups, basis, models, expected
):
    assert _status(category, groups, basis, models) is expected, case
