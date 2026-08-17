from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.item_economics.calculator import (
    calculate_cost_per_worker_minute,
)
from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import (
    CostModelVersion,
)
from beyo_manager.models.tables.item_economics.production_cost_basis_version import (
    ProductionCostBasisVersion,
)
from beyo_manager.models.tables.item_economics.production_cost_group import (
    ProductionCostGroup,
)
from beyo_manager.models.tables.item_economics.production_cost_group_section import (
    ProductionCostGroupSection,
)


@dataclass(frozen=True)
class BootstrapCostGroupSpec:
    group_client_id: str
    basis_client_id: str
    name: str
    major_category: ItemMajorCategoryEnum
    section_names: tuple[str, ...]
    fixed_monthly_cost_minor: int
    monthly_paid_hours: Decimal
    planning_utilization_percent: Decimal


@dataclass(frozen=True)
class BootstrapCostModelTermSpec:
    client_id: str
    name: str
    calculation_type: CostModelTermCalculationTypeEnum
    percent_value: Decimal | None


# These stable IDs are the ownership marker for bootstrap-managed configuration.
# A version is mutable only while it is the sole row in its version chain. The
# first additional version permanently closes the bootstrap write gate.
BOOTSTRAP_COST_GROUP_SPECS: tuple[BootstrapCostGroupSpec, ...] = (
    BootstrapCostGroupSpec(
        group_client_id="pcg_01M04J72NFMJJY2TQF6X0CZGJC",
        basis_client_id="pcbv_01M04J72NFSMZ6D9PD01GSB1R4",
        name="Seat",
        major_category=ItemMajorCategoryEnum.SEAT,
        section_names=(
            "disassembly",
            "cleaning seat",
            "structural repair",
            "upholstery removal",
            "padding",
            "upholstery installation",
            "assembly",
            "sewing",
            "weaving",
        ),
        fixed_monthly_cost_minor=40_000_000,
        monthly_paid_hours=Decimal("640.00"),
        planning_utilization_percent=Decimal("80.00"),
    ),
    BootstrapCostGroupSpec(
        group_client_id="pcg_01M04J72NFZCHNG3S9HAMX3FRT",
        basis_client_id="pcbv_01M04J72NFW3N57Y03KAHC2ZPN",
        name="Wood",
        major_category=ItemMajorCategoryEnum.WOOD,
        section_names=(
            "cleaning wood",
            "wood fix",
            "ground oil",
            "hardwax oil",
        ),
        fixed_monthly_cost_minor=20_000_000,
        monthly_paid_hours=Decimal("320.00"),
        planning_utilization_percent=Decimal("80.00"),
    ),
)

BOOTSTRAP_COST_MODEL_VERSION_ID = "cmv_01M04J72NFRZYE85W4RCKGJM6F"
BOOTSTRAP_COST_MODEL_TERM_SPECS: tuple[BootstrapCostModelTermSpec, ...] = (
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04J72NFQMES2WQTW39CQBZH",
        name="materials",
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent_value=Decimal("5.000"),
    ),
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04J72NFQFMWGPVYEQCZ251B",
        name="logistic_cost",
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent_value=Decimal("2.500"),
    ),
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04J72NFJJDZK8GKK5SZ9S8Q",
        name="packing",
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent_value=Decimal("2.500"),
    ),
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04J72NFTD9Q7QRWM0X83NSW",
        name="moms",
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent_value=Decimal("15.000"),
    ),
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04J72NF76WZR9853AY50YAF",
        name="profit_margin",
        calculation_type=CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE,
        percent_value=Decimal("25.000"),
    ),
    BootstrapCostModelTermSpec(
        client_id="cmvt_01M04JR9CK1M5QAA66WNM6AKRY",
        name="Purchase",
        calculation_type=CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST,
        percent_value=None,
    ),
)

_CURRENCY = ItemCurrencyEnum.SWEDISH_KRONA


def _assert_stable_row_scope(
    *,
    row_workspace_id: str,
    workspace_id: str,
    client_id: str,
) -> None:
    if row_workspace_id != workspace_id:
        raise ValidationError(
            f"Bootstrap item-economics ID '{client_id}' already belongs to another workspace."
        )


async def _get_or_create_group(
    session: AsyncSession,
    *,
    workspace_id: str,
    creator_user_id: str,
    spec: BootstrapCostGroupSpec,
) -> tuple[ProductionCostGroup | None, str]:
    stable_group = await session.get(ProductionCostGroup, spec.group_client_id)
    if stable_group is not None:
        _assert_stable_row_scope(
            row_workspace_id=stable_group.workspace_id,
            workspace_id=workspace_id,
            client_id=stable_group.client_id,
        )
        if stable_group.major_category is not spec.major_category:
            raise ValidationError(
                f"Bootstrap cost group '{stable_group.client_id}' has an unexpected major category."
            )
        if stable_group.is_deleted:
            return None, "frozen"
        return stable_group, "reused"

    existing_category_group = await session.scalar(
        select(ProductionCostGroup).where(
            ProductionCostGroup.workspace_id == workspace_id,
            ProductionCostGroup.major_category == spec.major_category,
        )
    )
    if existing_category_group is not None:
        return None, "person_owned"

    stable_group = ProductionCostGroup(
        client_id=spec.group_client_id,
        workspace_id=workspace_id,
        name=spec.name,
        major_category=spec.major_category,
        created_by_id=creator_user_id,
    )
    session.add(stable_group)
    await session.flush()
    return stable_group, "created"


async def _seed_group_sections(
    session: AsyncSession,
    *,
    workspace_id: str,
    creator_user_id: str,
    group: ProductionCostGroup,
    section_ids: dict[str, str],
    section_names: tuple[str, ...],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"created": [], "reused": [], "conflicts": []}
    for section_name in section_names:
        section_id = section_ids.get(section_name)
        if section_id is None:
            continue
        active_membership = await session.scalar(
            select(ProductionCostGroupSection).where(
                ProductionCostGroupSection.workspace_id == workspace_id,
                ProductionCostGroupSection.working_section_id == section_id,
                ProductionCostGroupSection.removed_at.is_(None),
            )
        )
        if active_membership is not None:
            key = (
                "reused"
                if active_membership.production_cost_group_id == group.client_id
                else "conflicts"
            )
            result[key].append(section_name)
            continue

        session.add(
            ProductionCostGroupSection(
                workspace_id=workspace_id,
                production_cost_group_id=group.client_id,
                working_section_id=section_id,
                added_by_id=creator_user_id,
            )
        )
        result["created"].append(section_name)
    await session.flush()
    return result


async def _seed_basis_version(
    session: AsyncSession,
    *,
    workspace_id: str,
    creator_user_id: str,
    group: ProductionCostGroup,
    spec: BootstrapCostGroupSpec,
) -> str:
    stable_basis = await session.get(ProductionCostBasisVersion, spec.basis_client_id)
    all_group_versions = (
        (
            await session.execute(
                select(ProductionCostBasisVersion).where(
                    ProductionCostBasisVersion.workspace_id == workspace_id,
                    ProductionCostBasisVersion.production_cost_group_id
                    == group.client_id,
                )
            )
        )
        .scalars()
        .all()
    )

    if stable_basis is None:
        if all_group_versions:
            return "person_owned"
        stable_basis = ProductionCostBasisVersion(
            client_id=spec.basis_client_id,
            workspace_id=workspace_id,
            production_cost_group_id=group.client_id,
            effective_from=None,
            fixed_monthly_cost_minor=spec.fixed_monthly_cost_minor,
            currency=_CURRENCY,
            monthly_paid_hours=spec.monthly_paid_hours,
            planning_utilization_percent=spec.planning_utilization_percent,
            cost_per_worker_minute_minor=calculate_cost_per_worker_minute(
                spec.fixed_monthly_cost_minor,
                spec.monthly_paid_hours,
                spec.planning_utilization_percent,
            ),
            created_by_id=creator_user_id,
        )
        session.add(stable_basis)
        await session.flush()
        return "created"

    _assert_stable_row_scope(
        row_workspace_id=stable_basis.workspace_id,
        workspace_id=workspace_id,
        client_id=stable_basis.client_id,
    )
    if stable_basis.production_cost_group_id != group.client_id:
        raise ValidationError(
            f"Bootstrap basis version '{stable_basis.client_id}' belongs to an unexpected cost group."
        )

    has_another_version = any(
        version.client_id != stable_basis.client_id for version in all_group_versions
    )
    if (
        stable_basis.is_deleted
        or stable_basis.effective_to is not None
        or has_another_version
    ):
        return "frozen"

    # Deliberate bootstrap-only exception to the public append-only contract:
    # the stable row remains editable only until a person creates any successor.
    stable_basis.fixed_monthly_cost_minor = spec.fixed_monthly_cost_minor
    stable_basis.currency = _CURRENCY
    stable_basis.monthly_paid_hours = spec.monthly_paid_hours
    stable_basis.planning_utilization_percent = spec.planning_utilization_percent
    stable_basis.cost_per_worker_minute_minor = calculate_cost_per_worker_minute(
        spec.fixed_monthly_cost_minor,
        spec.monthly_paid_hours,
        spec.planning_utilization_percent,
    )
    stable_basis.updated_by_id = creator_user_id
    await session.flush()
    return "updated"


async def _seed_cost_model(
    session: AsyncSession,
    *,
    workspace_id: str,
    creator_user_id: str,
) -> str:
    stable_model = await session.get(CostModelVersion, BOOTSTRAP_COST_MODEL_VERSION_ID)
    all_workspace_models = (
        (
            await session.execute(
                select(CostModelVersion).where(
                    CostModelVersion.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )

    if stable_model is None:
        if all_workspace_models:
            return "person_owned"
        stable_model = CostModelVersion(
            client_id=BOOTSTRAP_COST_MODEL_VERSION_ID,
            workspace_id=workspace_id,
            effective_from=None,
            currency=_CURRENCY,
            created_by_id=creator_user_id,
        )
        session.add(stable_model)
        await session.flush()
        model_status = "created"
    else:
        _assert_stable_row_scope(
            row_workspace_id=stable_model.workspace_id,
            workspace_id=workspace_id,
            client_id=stable_model.client_id,
        )
        has_another_version = any(
            model.client_id != stable_model.client_id for model in all_workspace_models
        )
        if (
            stable_model.is_deleted
            or stable_model.effective_to is not None
            or has_another_version
        ):
            return "frozen"
        model_status = "updated"

    stable_term_ids = {spec.client_id for spec in BOOTSTRAP_COST_MODEL_TERM_SPECS}
    model_terms = (
        (
            await session.execute(
                select(CostModelTerm).where(
                    CostModelTerm.workspace_id == workspace_id,
                    CostModelTerm.cost_model_version_id == stable_model.client_id,
                )
            )
        )
        .scalars()
        .all()
    )
    if any(
        term.client_id not in stable_term_ids or term.is_deleted for term in model_terms
    ):
        return "frozen"

    terms_by_id = {term.client_id: term for term in model_terms}
    stable_model.currency = _CURRENCY
    if model_status == "updated":
        stable_model.updated_by_id = creator_user_id

    for spec in BOOTSTRAP_COST_MODEL_TERM_SPECS:
        term = terms_by_id.get(spec.client_id)
        if term is None:
            global_term = await session.get(CostModelTerm, spec.client_id)
            if global_term is not None:
                raise ValidationError(
                    f"Bootstrap cost-model term ID '{spec.client_id}' belongs to an unexpected model."
                )
            session.add(
                CostModelTerm(
                    client_id=spec.client_id,
                    workspace_id=workspace_id,
                    cost_model_version_id=stable_model.client_id,
                    name=spec.name,
                    calculation_type=spec.calculation_type,
                    percent_value=spec.percent_value,
                    fixed_amount_minor=None,
                    created_by_id=creator_user_id,
                )
            )
            continue
        term.name = spec.name
        term.calculation_type = spec.calculation_type
        term.percent_value = spec.percent_value
        term.fixed_amount_minor = None
        term.updated_by_id = creator_user_id

    await session.flush()
    return model_status


async def seed_item_economics_configuration(
    session: AsyncSession,
    *,
    workspace_id: str,
    creator_user_id: str,
    section_ids: dict[str, str],
) -> dict:
    """Seed bootstrap-owned economics values without crossing human version gates."""
    group_results: dict[str, dict] = {}
    for spec in BOOTSTRAP_COST_GROUP_SPECS:
        category = spec.major_category.value
        group, group_status = await _get_or_create_group(
            session,
            workspace_id=workspace_id,
            creator_user_id=creator_user_id,
            spec=spec,
        )
        if group is None:
            group_results[category] = {
                "group_status": group_status,
                "basis_status": "skipped",
                "section_memberships": {"created": [], "reused": [], "conflicts": []},
            }
            continue

        memberships = await _seed_group_sections(
            session,
            workspace_id=workspace_id,
            creator_user_id=creator_user_id,
            group=group,
            section_ids=section_ids,
            section_names=spec.section_names,
        )
        basis_status = await _seed_basis_version(
            session,
            workspace_id=workspace_id,
            creator_user_id=creator_user_id,
            group=group,
            spec=spec,
        )
        group_results[category] = {
            "group_id": group.client_id,
            "basis_id": spec.basis_client_id,
            "group_status": group_status,
            "basis_status": basis_status,
            "section_memberships": memberships,
        }

    model_status = await _seed_cost_model(
        session,
        workspace_id=workspace_id,
        creator_user_id=creator_user_id,
    )
    return {
        "groups": group_results,
        "cost_model": {
            "version_id": BOOTSTRAP_COST_MODEL_VERSION_ID,
            "status": model_status,
        },
    }
