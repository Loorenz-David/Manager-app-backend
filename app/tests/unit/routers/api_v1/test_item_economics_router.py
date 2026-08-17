from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import item_economics
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.queries.item_economics.get_task_budget_status import TaskBudgetStatus
from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum


_ROUTES = [
    ("POST", "/api/v1/item-economics/cost-groups", {"name": "Main", "major_category": "wood"}),
    ("GET", "/api/v1/item-economics/cost-groups", None),
    ("PATCH", "/api/v1/item-economics/cost-groups/pcg_1", {"name": "Renamed"}),
    ("DELETE", "/api/v1/item-economics/cost-groups/pcg_1", None),
    ("POST", "/api/v1/item-economics/cost-groups/pcg_1/sections", {"working_section_id": "wsec_1"}),
    ("DELETE", "/api/v1/item-economics/cost-groups/pcg_1/sections/wsec_1", None),
    (
        "POST",
        "/api/v1/item-economics/cost-groups/pcg_1/basis-versions",
        {
            "fixed_monthly_cost_minor": 100000,
            "currency": "swedish_krona",
            "monthly_paid_hours": "160.00",
            "planning_utilization_percent": "80.00",
        },
    ),
    ("GET", "/api/v1/item-economics/cost-groups/pcg_1/basis-versions", None),
    ("DELETE", "/api/v1/item-economics/basis-versions/pcbv_1", None),
    ("POST", "/api/v1/item-economics/cost-model-versions", {"currency": "swedish_krona", "terms": []}),
    ("GET", "/api/v1/item-economics/cost-model-versions", None),
    ("DELETE", "/api/v1/item-economics/cost-model-versions/cmv_1", None),
    ("GET", "/api/v1/item-economics/configuration-status", None),
    ("PUT", "/api/v1/item-economics/items/itm_1/valuation", {"expected_sale_price_minor": 100, "currency": "swedish_krona"}),
    ("GET", "/api/v1/item-economics/items/itm_1/valuations", None),
    ("DELETE", "/api/v1/item-economics/items/itm_1/valuation", None),
    ("POST", "/api/v1/item-economics/tasks/tsk_1/evaluations/commit", {}),
    ("GET", "/api/v1/item-economics/tasks/tsk_1/evaluations", None),
    ("POST", "/api/v1/item-economics/tasks/tsk_1/projections", {}),
    ("DELETE", "/api/v1/item-economics/projections/ice_1", None),
    ("POST", "/api/v1/item-economics/projections/ice_1/promote", None),
    ("GET", "/api/v1/item-economics/items/itm_1/economics", None),
]

_ALL_ROLE_ROUTES = [
    ("GET", "/api/v1/item-economics/tasks/tsk_1/budget-status", None),
    ("GET", "/api/v1/item-economics/tasks/tsk_1/production-time", None),
    ("GET", "/api/v1/item-economics/tasks/budget-allocations?task_ids=tsk_1", None),
]


def _client(monkeypatch, role_name: str):
    app = FastAPI()
    app.include_router(item_economics.router, prefix="/api/v1/item-economics")
    calls = []

    async def fake_get_db():
        yield object()

    async def fake_run_service(command, context):
        calls.append((command, context))
        if command in {
            item_economics.get_task_budget_status,
            item_economics.get_task_budget_status_worker,
        }:
            data = TaskBudgetStatus(
                status=EconomicsStatusEnum.NOT_EVALUATED,
                item_binding="detached",
                actual_worker_seconds=None,
                actual_worker_minutes=None,
                remaining_worker_minutes=None,
                percent_consumed=None,
                variance_worker_minutes=None,
                production_budget_minor=None,
                allowed_worker_minutes=None,
                consumed_cost_minor=None,
                variance_cost_minor=None,
                evaluation_id=None,
                item_id=None,
                result=None,
            )
        else:
            data = {"ok": "test"}
        return SimpleNamespace(success=True, data=data, error=None)

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role_name,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    return TestClient(app), calls


@pytest.mark.parametrize("role_name", ["worker", "seller"])
@pytest.mark.parametrize(("method", "path", "body"), _ROUTES, ids=[f"{method.lower()}-{path.split('/')[-1]}" for method, path, _ in _ROUTES])
def test_every_item_economics_route_rejects_worker_and_seller(method, path, body, role_name, monkeypatch):
    client, calls = _client(monkeypatch, role_name)

    response = client.request(method, path, json=body)

    assert response.status_code == 403
    assert calls == []


@pytest.mark.parametrize("role_name", ["admin", "manager"])
@pytest.mark.parametrize(("method", "path", "body"), _ROUTES, ids=[f"{method.lower()}-{path.split('/')[-1]}" for method, path, _ in _ROUTES])
def test_every_item_economics_route_retains_admin_and_manager_access(method, path, body, role_name, monkeypatch):
    client, calls = _client(monkeypatch, role_name)

    response = client.request(method, path, json=body)

    assert response.status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize("role_name", ["admin", "manager", "worker", "seller"])
@pytest.mark.parametrize(
    ("method", "path", "body"),
    _ALL_ROLE_ROUTES,
    ids=[f"{method.lower()}-{path.split('/')[-1]}" for method, path, _ in _ALL_ROLE_ROUTES],
)
def test_budget_status_route_is_available_to_all_roles(method, path, body, role_name, monkeypatch):
    client, calls = _client(monkeypatch, role_name)

    response = client.request(method, path, json=body)

    assert response.status_code == 200
    assert len(calls) == 1
    if "budget-allocations" in path:
        assert calls[0][0] is item_economics.get_task_budget_allocations
        return
    if "production-time" in path:
        assert calls[0][0] is item_economics.get_task_production_time
        return
    if role_name in {"worker", "seller"}:
        assert calls[0][0] is item_economics.get_task_budget_status_worker
    else:
        assert calls[0][0] is item_economics.get_task_budget_status


def test_router_surface_has_no_term_mutation_and_no_derived_rate_input():
    route_pairs = {(route.path, tuple(sorted(route.methods or ()))) for route in item_economics.router.routes}

    assert "/cost-model-versions/{client_id}" in {
        path for path, _ in route_pairs
    }
    assert not any(
        path.endswith("/terms") and any(method in methods for method in ("PUT", "PATCH", "DELETE"))
        for path, methods in route_pairs
    )
    assert "cost_per_worker_minute_minor" not in item_economics._BasisVersionBody.model_fields


def test_router_route_pairs_match_the_authoritative_route_table():
    def template(path):
        path = path.split("?", 1)[0]
        for value, placeholder in (
            ("pcg_1", "{client_id}"),
            ("wsec_1", "{working_section_client_id}"),
            ("pcbv_1", "{client_id}"),
            ("cmv_1", "{client_id}"),
            ("itm_1", "{item_client_id}"),
            ("tsk_1", "{task_client_id}"),
            ("ice_1", "{client_id}"),
        ):
            path = path.replace(value, placeholder)
        return path.removeprefix("/api/v1/item-economics")

    expected = {
        (method, template(path))
        for method, path, _ in [*_ROUTES, *_ALL_ROLE_ROUTES]
    }
    actual = {
        (method, route.path)
        for route in item_economics.router.routes
        for method in (route.methods or ())
    }
    assert actual == expected


def test_item_economics_routes_declare_no_response_model():
    assert all(route.response_model is None for route in item_economics.router.routes)


async def test_budget_status_audience_predicate_fails_closed_for_unknown_role(monkeypatch):
    calls = []

    async def fake_run_service(command, _context):
        calls.append(command)
        return SimpleNamespace(
            success=True,
            error=None,
            data=TaskBudgetStatus(
                status=EconomicsStatusEnum.NOT_EVALUATED,
                item_binding="detached",
                actual_worker_seconds=None,
                actual_worker_minutes=None,
                remaining_worker_minutes=None,
                percent_consumed=None,
                variance_worker_minutes=None,
                production_budget_minor=None,
                allowed_worker_minutes=None,
                consumed_cost_minor=None,
                variance_cost_minor=None,
                evaluation_id=None,
                item_id=None,
                result=None,
            ),
        )

    monkeypatch.setattr(item_economics, "run_service", fake_run_service)
    await item_economics._run_budget_status(
        {"role_name": "future_role", "workspace_id": "ws", "user_id": "usr"},
        object(),
        "tsk",
    )

    assert calls == [item_economics.get_task_budget_status_worker]


def test_router_body_percent_field_carries_planning_allocation_documentation():
    description = item_economics._CostModelTermBody.model_fields["percent_value"].description

    assert description is not None
    assert "planning allocation" in description.lower()
    assert "never legally payable tax" in description.lower()


def test_group_router_body_models_keep_category_fields_at_the_http_boundary(monkeypatch):
    assert "major_category" in item_economics._CreateGroupBody.model_fields
    assert item_economics._CreateGroupBody.model_fields["major_category"].is_required()
    assert "major_category" in item_economics._UpdateGroupBody.model_fields
    assert item_economics._UpdateGroupBody.model_fields["major_category"].is_required() is False

    client, calls = _client(monkeypatch, "manager")
    response = client.patch("/api/v1/item-economics/cost-groups/pcg_1", json={"name": "Renamed"})

    assert response.status_code == 200
    assert calls[0][1].incoming_data == {
        "client_id": "pcg_1",
        "name": "Renamed",
        "major_category": None,
    }
