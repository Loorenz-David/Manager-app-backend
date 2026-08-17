from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from beyo_manager.domain.item_economics.calculator import (
    calculate_production_budget,
    calculate_term_amounts,
)
from beyo_manager.domain.item_economics.enums import CostModelTermCalculationTypeEnum
from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
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
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases import (
    seed_item_economics_configuration as seed_module,
)
from beyo_manager.services.commands.bootstrap.phases.seed_item_economics_configuration import (
    BOOTSTRAP_COST_MODEL_TERM_SPECS,
    BOOTSTRAP_COST_MODEL_VERSION_ID,
    BOOTSTRAP_COST_GROUP_SPECS,
    seed_item_economics_configuration,
)
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import (
    seed_working_sections,
)
from beyo_manager.services.commands.item_economics.create_cost_model_version import (
    create_cost_model_version,
)
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import (
    create_production_cost_basis_version,
)
from beyo_manager.services.context import ServiceContext


def _ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "username": "person",
        },
        incoming_data=data,
        session=session,
    )


async def _setup(db_session) -> tuple[Workspace, User, User, dict[str, str]]:
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"Bootstrap economics {token}")
    fayoz = User(
        client_id=f"usr_fayoz_{token}",
        username=f"Fayoz_{token}",
        email=f"fayoz_{token}@example.test",
        password="test",
    )
    person = User(
        client_id=f"usr_person_{token}",
        username=f"person_{token}",
        email=f"person_{token}@example.test",
        password="test",
    )
    db_session.add_all([workspace, fayoz, person])
    await db_session.flush()
    section_ids = await seed_working_sections(db_session, workspace.client_id)
    return workspace, fayoz, person, section_ids


@pytest.mark.integration
async def test_seed_item_economics_creates_requested_configuration_and_updates_owned_values(
    db_session,
    monkeypatch,
):
    workspace, fayoz, _, section_ids = await _setup(db_session)

    first = await seed_item_economics_configuration(
        db_session,
        workspace_id=workspace.client_id,
        creator_user_id=fayoz.client_id,
        section_ids=section_ids,
    )

    assert first["groups"]["seat"]["basis_status"] == "created"
    assert first["groups"]["wood"]["basis_status"] == "created"
    assert first["cost_model"]["status"] == "created"

    groups = (
        (
            await db_session.execute(
                select(ProductionCostGroup).where(
                    ProductionCostGroup.workspace_id == workspace.client_id,
                    ProductionCostGroup.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    groups_by_category = {group.major_category: group for group in groups}
    assert set(groups_by_category) == {
        ItemMajorCategoryEnum.SEAT,
        ItemMajorCategoryEnum.WOOD,
    }
    assert all(group.created_by_id == fayoz.client_id for group in groups)

    basis_rows = (
        (
            await db_session.execute(
                select(ProductionCostBasisVersion).where(
                    ProductionCostBasisVersion.workspace_id == workspace.client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert {row.client_id for row in basis_rows} == {
        spec.basis_client_id for spec in BOOTSTRAP_COST_GROUP_SPECS
    }
    basis_by_group = {row.production_cost_group_id: row for row in basis_rows}
    seat_basis = basis_by_group[
        groups_by_category[ItemMajorCategoryEnum.SEAT].client_id
    ]
    wood_basis = basis_by_group[
        groups_by_category[ItemMajorCategoryEnum.WOOD].client_id
    ]
    assert seat_basis.fixed_monthly_cost_minor == 40_000_000
    assert seat_basis.monthly_paid_hours == Decimal("640.00")
    assert wood_basis.fixed_monthly_cost_minor == 20_000_000
    assert wood_basis.monthly_paid_hours == Decimal("320.00")
    assert seat_basis.planning_utilization_percent == Decimal("80.00")
    assert wood_basis.planning_utilization_percent == Decimal("80.00")
    assert seat_basis.cost_per_worker_minute_minor == Decimal("1302.0833")
    assert wood_basis.cost_per_worker_minute_minor == Decimal("1302.0833")
    assert all(row.currency is ItemCurrencyEnum.SWEDISH_KRONA for row in basis_rows)
    assert all(row.created_by_id == fayoz.client_id for row in basis_rows)

    memberships = (
        (
            await db_session.execute(
                select(ProductionCostGroupSection).where(
                    ProductionCostGroupSection.workspace_id == workspace.client_id,
                    ProductionCostGroupSection.removed_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    membership_group_by_section = {
        membership.working_section_id: membership.production_cost_group_id
        for membership in memberships
    }
    for spec in BOOTSTRAP_COST_GROUP_SPECS:
        for section_name in spec.section_names:
            assert (
                membership_group_by_section[section_ids[section_name]]
                == spec.group_client_id
            )
    assert section_ids["photography"] not in membership_group_by_section

    model = await db_session.get(CostModelVersion, BOOTSTRAP_COST_MODEL_VERSION_ID)
    assert model is not None
    assert model.currency is ItemCurrencyEnum.SWEDISH_KRONA
    assert model.created_by_id == fayoz.client_id
    terms = (
        (
            await db_session.execute(
                select(CostModelTerm).where(
                    CostModelTerm.cost_model_version_id
                    == BOOTSTRAP_COST_MODEL_VERSION_ID
                )
            )
        )
        .scalars()
        .all()
    )
    assert {term.name: term.percent_value for term in terms} == {
        "materials": Decimal("5.000"),
        "logistic_cost": Decimal("2.500"),
        "packing": Decimal("2.500"),
        "moms": Decimal("15.000"),
        "profit_margin": Decimal("25.000"),
        "Purchase": None,
    }
    assert sum(
        term.percent_value for term in terms if term.percent_value is not None
    ) == Decimal("50.000")
    percentage_terms = [term for term in terms if term.name != "Purchase"]
    assert all(
        term.calculation_type
        is CostModelTermCalculationTypeEnum.PERCENTAGE_OF_EXPECTED_SALE_PRICE
        for term in percentage_terms
    )
    purchase_term = next(term for term in terms if term.name == "Purchase")
    assert (
        purchase_term.calculation_type
        is CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST
    )
    assert purchase_term.percent_value is None
    assert purchase_term.fixed_amount_minor is None
    term_amounts = calculate_term_amounts(
        terms,
        expected_sale_price_minor=100_000,
        purchase_cost_minor=20_000,
    )
    assert calculate_production_budget(100_000, term_amounts) == 30_000

    changed_group_specs = (
        replace(
            BOOTSTRAP_COST_GROUP_SPECS[0],
            fixed_monthly_cost_minor=41_000_000,
            monthly_paid_hours=Decimal("650.00"),
        ),
        BOOTSTRAP_COST_GROUP_SPECS[1],
    )
    changed_term_specs = (
        replace(BOOTSTRAP_COST_MODEL_TERM_SPECS[0], percent_value=Decimal("6.000")),
        *BOOTSTRAP_COST_MODEL_TERM_SPECS[1:],
    )
    monkeypatch.setattr(seed_module, "BOOTSTRAP_COST_GROUP_SPECS", changed_group_specs)
    monkeypatch.setattr(
        seed_module, "BOOTSTRAP_COST_MODEL_TERM_SPECS", changed_term_specs
    )

    second = await seed_item_economics_configuration(
        db_session,
        workspace_id=workspace.client_id,
        creator_user_id=fayoz.client_id,
        section_ids=section_ids,
    )

    assert second["groups"]["seat"]["basis_status"] == "updated"
    assert second["cost_model"]["status"] == "updated"
    await db_session.refresh(seat_basis)
    assert seat_basis.fixed_monthly_cost_minor == 41_000_000
    assert seat_basis.monthly_paid_hours == Decimal("650.00")
    assert seat_basis.cost_per_worker_minute_minor == Decimal("1314.1026")
    materials = await db_session.get(
        CostModelTerm, BOOTSTRAP_COST_MODEL_TERM_SPECS[0].client_id
    )
    assert materials.percent_value == Decimal("6.000")
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(ProductionCostBasisVersion)
            .where(ProductionCostBasisVersion.workspace_id == workspace.client_id)
        )
        == 2
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(CostModelVersion)
            .where(CostModelVersion.workspace_id == workspace.client_id)
        )
        == 1
    )


@pytest.mark.integration
async def test_human_successors_permanently_freeze_bootstrap_basis_and_model(
    db_session,
    monkeypatch,
):
    workspace, fayoz, person, section_ids = await _setup(db_session)
    await seed_item_economics_configuration(
        db_session,
        workspace_id=workspace.client_id,
        creator_user_id=fayoz.client_id,
        section_ids=section_ids,
    )
    seat_spec = BOOTSTRAP_COST_GROUP_SPECS[0]

    human_basis_result = await create_production_cost_basis_version(
        _ctx(
            db_session,
            workspace.client_id,
            person.client_id,
            {
                "production_cost_group_id": seat_spec.group_client_id,
                "effective_from": datetime.now(timezone.utc).date(),
                "fixed_monthly_cost_minor": 99_000_000,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "monthly_paid_hours": Decimal("700.00"),
                "planning_utilization_percent": Decimal("75.00"),
            },
        )
    )
    human_model_result = await create_cost_model_version(
        _ctx(
            db_session,
            workspace.client_id,
            person.client_id,
            {
                "effective_from": datetime.now(timezone.utc).date(),
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "terms": [
                    {
                        "name": "human_term",
                        "calculation_type": CostModelTermCalculationTypeEnum.FIXED_AMOUNT,
                        "fixed_amount_minor": 123,
                    }
                ],
            },
        )
    )
    human_basis = await db_session.get(
        ProductionCostBasisVersion,
        human_basis_result["production_cost_basis_version"]["client_id"],
    )
    human_model = await db_session.get(
        CostModelVersion,
        human_model_result["cost_model_version"]["client_id"],
    )
    human_basis.is_deleted = True
    human_model.is_deleted = True
    await db_session.flush()

    monkeypatch.setattr(
        seed_module,
        "BOOTSTRAP_COST_GROUP_SPECS",
        (
            replace(seat_spec, fixed_monthly_cost_minor=1_000_000),
            BOOTSTRAP_COST_GROUP_SPECS[1],
        ),
    )
    monkeypatch.setattr(
        seed_module,
        "BOOTSTRAP_COST_MODEL_TERM_SPECS",
        (
            replace(
                BOOTSTRAP_COST_MODEL_TERM_SPECS[0], percent_value=Decimal("99.000")
            ),
            *BOOTSTRAP_COST_MODEL_TERM_SPECS[1:],
        ),
    )

    result = await seed_item_economics_configuration(
        db_session,
        workspace_id=workspace.client_id,
        creator_user_id=fayoz.client_id,
        section_ids=section_ids,
    )

    assert result["groups"]["seat"]["basis_status"] == "frozen"
    assert result["cost_model"]["status"] == "frozen"
    stable_basis = await db_session.get(
        ProductionCostBasisVersion, seat_spec.basis_client_id
    )
    stable_materials = await db_session.get(
        CostModelTerm,
        BOOTSTRAP_COST_MODEL_TERM_SPECS[0].client_id,
    )
    assert stable_basis.fixed_monthly_cost_minor == 40_000_000
    assert stable_basis.effective_to == datetime.now(timezone.utc).date()
    assert stable_materials.percent_value == Decimal("5.000")
    assert human_basis.fixed_monthly_cost_minor == 99_000_000


@pytest.mark.integration
async def test_person_owned_configuration_and_section_membership_are_not_overridden(
    db_session,
):
    workspace, fayoz, person, section_ids = await _setup(db_session)
    person_group = ProductionCostGroup(
        workspace_id=workspace.client_id,
        name="Person wood",
        major_category=ItemMajorCategoryEnum.WOOD,
        created_by_id=person.client_id,
    )
    person_model = CostModelVersion(
        workspace_id=workspace.client_id,
        effective_from=None,
        currency=ItemCurrencyEnum.SWEDISH_KRONA,
        created_by_id=person.client_id,
    )
    db_session.add_all([person_group, person_model])
    await db_session.flush()
    existing_membership = ProductionCostGroupSection(
        workspace_id=workspace.client_id,
        production_cost_group_id=person_group.client_id,
        working_section_id=section_ids["disassembly"],
        added_by_id=person.client_id,
    )
    db_session.add(existing_membership)
    await db_session.flush()

    result = await seed_item_economics_configuration(
        db_session,
        workspace_id=workspace.client_id,
        creator_user_id=fayoz.client_id,
        section_ids=section_ids,
    )

    assert result["groups"]["wood"]["group_status"] == "person_owned"
    assert result["groups"]["seat"]["section_memberships"]["conflicts"] == [
        "disassembly"
    ]
    assert result["cost_model"]["status"] == "person_owned"
    await db_session.refresh(existing_membership)
    assert existing_membership.production_cost_group_id == person_group.client_id
    assert existing_membership.removed_at is None
    assert (
        await db_session.get(
            ProductionCostGroup,
            BOOTSTRAP_COST_GROUP_SPECS[1].group_client_id,
        )
        is None
    )
    assert (
        await db_session.get(CostModelVersion, BOOTSTRAP_COST_MODEL_VERSION_ID) is None
    )
