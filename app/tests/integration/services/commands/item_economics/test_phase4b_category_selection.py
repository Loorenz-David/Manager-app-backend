from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemMajorCategoryEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.audit.audit_log import AuditLog
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.item_economics.create_cost_model_version import create_cost_model_version
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import (
    create_production_cost_basis_version,
)
from beyo_manager.services.commands.item_economics.create_production_cost_group import create_production_cost_group
from beyo_manager.services.commands.item_economics.update_production_cost_group import update_production_cost_group
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_economics_configuration_status import (
    get_economics_configuration_status,
)


def _ctx(session, workspace_id: str, user_id: str, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "username": "manager",
            "role_name": "manager",
        },
        incoming_data=data,
        session=session,
    )


async def _actor(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"workspace {token}")
    user = User(
        client_id=f"usr_{token}",
        username=f"user_{token}",
        email=f"{token}@example.test",
        password="test",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _group(db_session, workspace, user, name: str, category: ItemMajorCategoryEnum):
    result = await create_production_cost_group(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"name": name, "major_category": category},
        )
    )
    return result["production_cost_group"]["client_id"]


async def _basis(db_session, workspace, user, group_id: str):
    result = await create_production_cost_basis_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "production_cost_group_id": group_id,
                "fixed_monthly_cost_minor": 100000,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "monthly_paid_hours": Decimal("160.00"),
                "planning_utilization_percent": Decimal("80.00"),
            },
        )
    )
    return result["production_cost_basis_version"]["client_id"]


async def _model(db_session, workspace, user, *, future: bool = False):
    result = await create_cost_model_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "effective_from": date.today() + timedelta(days=2) if future else None,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "terms": [],
            },
        )
    )
    return result["cost_model_version"]["client_id"]


@pytest.mark.integration
async def test_category_create_precheck_reports_taken_identity_and_category(db_session):
    workspace, user = await _actor(db_session)
    await _group(db_session, workspace, user, "First", ItemMajorCategoryEnum.WOOD)

    with pytest.raises(ValidationError) as raised:
        await _group(db_session, workspace, user, "Second", ItemMajorCategoryEnum.WOOD)

    assert str(raised.value).startswith("ITEM_COST_GROUP_CATEGORY_TAKEN:")
    assert "wood" in str(raised.value)


@pytest.mark.integration
async def test_category_update_precheck_reports_taken_identity_when_target_is_free_of_basis(db_session):
    workspace, user = await _actor(db_session)
    first_id = await _group(db_session, workspace, user, "Wood", ItemMajorCategoryEnum.WOOD)
    second_id = await _group(db_session, workspace, user, "Seat", ItemMajorCategoryEnum.SEAT)

    with pytest.raises(ValidationError) as raised:
        await update_production_cost_group(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"client_id": second_id, "name": "Seat", "major_category": ItemMajorCategoryEnum.WOOD},
            )
        )

    assert str(raised.value).startswith("ITEM_COST_GROUP_CATEGORY_TAKEN:")
    assert first_id != second_id


@pytest.mark.integration
async def test_category_flip_with_live_basis_is_immutable_and_reports_both_values(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user, "Main", ItemMajorCategoryEnum.WOOD)
    await _basis(db_session, workspace, user, group_id)

    with pytest.raises(ValidationError) as raised:
        await update_production_cost_group(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"client_id": group_id, "name": "Main", "major_category": ItemMajorCategoryEnum.SEAT},
            )
        )

    message = str(raised.value)
    assert message.startswith("ITEM_COST_GROUP_CATEGORY_IMMUTABLE:")
    assert group_id in message
    assert "wood" in message


@pytest.mark.integration
async def test_category_flip_remains_immutable_when_the_only_basis_is_deleted(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user, "Main", ItemMajorCategoryEnum.WOOD)
    basis_id = await _basis(db_session, workspace, user, group_id)
    basis = await db_session.get(ProductionCostBasisVersion, basis_id)
    basis.is_deleted = True
    await db_session.flush()

    with pytest.raises(ValidationError, match=r"^ITEM_COST_GROUP_CATEGORY_IMMUTABLE:"):
        await update_production_cost_group(
            _ctx(
                db_session,
                workspace.client_id,
                user.client_id,
                {"client_id": group_id, "name": "Main", "major_category": ItemMajorCategoryEnum.SEAT},
            )
        )


@pytest.mark.integration
async def test_category_flip_without_basis_updates_row_and_audits_existing_event(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user, "Main", ItemMajorCategoryEnum.WOOD)

    response = await update_production_cost_group(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"client_id": group_id, "name": "Main", "major_category": ItemMajorCategoryEnum.SEAT},
        )
    )
    row = await db_session.get(ProductionCostGroup, group_id)
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace.client_id,
            AuditLog.resource_client_id == group_id,
            AuditLog.event == "production_cost_group.updated",
        )
    )

    assert response["production_cost_group"]["major_category"] == "seat"
    assert row.major_category is ItemMajorCategoryEnum.SEAT
    assert audit is not None


@pytest.mark.integration
async def test_equal_category_is_an_accepted_noop_for_a_versioned_group(db_session):
    workspace, user = await _actor(db_session)
    group_id = await _group(db_session, workspace, user, "Main", ItemMajorCategoryEnum.WOOD)
    await _basis(db_session, workspace, user, group_id)

    response = await update_production_cost_group(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"client_id": group_id, "name": "Main", "major_category": ItemMajorCategoryEnum.WOOD},
        )
    )

    assert response["production_cost_group"]["major_category"] == "wood"


@pytest.mark.integration
async def test_status_has_exact_per_category_shape_and_scopes_basis_to_each_group(db_session):
    workspace, user = await _actor(db_session)
    wood_id = await _group(db_session, workspace, user, "Wood", ItemMajorCategoryEnum.WOOD)
    await _basis(db_session, workspace, user, wood_id)
    await _group(db_session, workspace, user, "Seat", ItemMajorCategoryEnum.SEAT)
    await _model(db_session, workspace, user)

    status = await get_economics_configuration_status(_ctx(db_session, workspace.client_id, user.client_id, {}))

    assert status == {
        "categories": {
            "wood": {
                "group_count": 1,
                "has_cost_group": True,
                "has_open_basis_version": True,
                "evaluable": True,
                "first_failure": None,
            },
            "seat": {
                "group_count": 1,
                "has_cost_group": True,
                "has_open_basis_version": False,
                "evaluable": False,
                "first_failure": "not_configured_no_basis_version",
            },
        },
        "has_open_cost_model_version": True,
    }


@pytest.mark.integration
async def test_status_shared_model_failure_is_repeated_in_each_category_block(db_session):
    workspace, user = await _actor(db_session)
    wood_id = await _group(db_session, workspace, user, "Wood", ItemMajorCategoryEnum.WOOD)
    await _basis(db_session, workspace, user, wood_id)
    await _group(db_session, workspace, user, "Seat", ItemMajorCategoryEnum.SEAT)

    status = await get_economics_configuration_status(_ctx(db_session, workspace.client_id, user.client_id, {}))

    assert status["has_open_cost_model_version"] is False
    assert status["categories"]["wood"]["first_failure"] == "not_configured_no_cost_model_version"
    assert status["categories"]["seat"]["first_failure"] == "not_configured_no_basis_version"
