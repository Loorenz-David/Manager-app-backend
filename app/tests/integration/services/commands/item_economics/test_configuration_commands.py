from uuid import uuid4

import pytest

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.services.commands.item_economics.create_cost_model_version import create_cost_model_version
from beyo_manager.services.commands.item_economics.create_production_cost_basis_version import create_production_cost_basis_version
from beyo_manager.services.commands.item_economics.create_production_cost_group import create_production_cost_group
from beyo_manager.services.commands.item_economics.update_production_cost_group import update_production_cost_group
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_economics_configuration_status import get_economics_configuration_status


def _ctx(session, workspace_id, user_id, data):
    return ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": user_id, "username": "manager"},
        incoming_data=data,
        session=session,
    )


@pytest.mark.integration
async def test_configuration_commands_canonicalize_chain_and_status(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"economics {token}")
    user = User(client_id=f"usr_{token}", username=f"economics_{token}", email=f"{token}@example.test", password="test")
    await db_session.begin()
    db_session.add_all([workspace, user])
    await db_session.flush()
    ctx = _ctx(db_session, workspace.client_id, user.client_id, {"name": "Main"})
    created = await create_production_cost_group(ctx)
    group_id = created["production_cost_group"]["client_id"]

    basis = await create_production_cost_basis_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "production_cost_group_id": group_id,
                "fixed_monthly_cost_minor": 100000,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "monthly_paid_hours": 173.456,
                "planning_utilization_percent": 80.00,
                "cost_per_worker_minute_minor": 0,
            },
        )
    )
    assert basis["production_cost_basis_version"]["monthly_paid_hours"] == "173.46"
    assert basis["production_cost_basis_version"]["cost_per_worker_minute_minor"] == "12.0105"

    model = await create_cost_model_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {"currency": ItemCurrencyEnum.SWEDISH_KRONA, "terms": []},
        )
    )
    assert model["cost_model_version"]["terms"] == []
    status = await get_economics_configuration_status(_ctx(db_session, workspace.client_id, user.client_id, {}))
    assert status == {
        "group_count": 1,
        "has_cost_group": True,
        "has_open_basis_version": True,
        "has_open_cost_model_version": True,
        "evaluable": True,
        "first_failure": None,
    }
    renamed = await update_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"client_id": group_id, "name": "Renamed"}))
    assert renamed["production_cost_group"]["name"] == "Renamed"


@pytest.mark.integration
async def test_basis_admission_ignores_a_soft_deleted_open_row(db_session):
    token = uuid4().hex
    workspace = Workspace(client_id=f"ws_{token}", name=f"economics {token}")
    user = User(client_id=f"usr_{token}", username=f"economics_{token}", email=f"{token}@example.test", password="test")
    await db_session.begin()
    db_session.add_all([workspace, user])
    await db_session.flush()
    group = await create_production_cost_group(_ctx(db_session, workspace.client_id, user.client_id, {"name": "Main"}))
    group_id = group["production_cost_group"]["client_id"]
    first = await create_production_cost_basis_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "production_cost_group_id": group_id,
                "fixed_monthly_cost_minor": 100000,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "monthly_paid_hours": 160,
                "planning_utilization_percent": 80,
            },
        )
    )
    row = await db_session.get(ProductionCostBasisVersion, first["production_cost_basis_version"]["client_id"])
    row.is_deleted = True
    await db_session.flush()
    second = await create_production_cost_basis_version(
        _ctx(
            db_session,
            workspace.client_id,
            user.client_id,
            {
                "production_cost_group_id": group_id,
                "fixed_monthly_cost_minor": 100000,
                "currency": ItemCurrencyEnum.SWEDISH_KRONA,
                "monthly_paid_hours": 160,
                "planning_utilization_percent": 80,
            },
        )
    )
    assert second["production_cost_basis_version"]["effective_from"] is None
