from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum
from beyo_manager.errors.stock_report import (
    StockAssignmentPropertyMismatch,
    StockAssignmentRefused,
)
from beyo_manager.models.database import get_db
from beyo_manager.routers.api_v1 import stock_report
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims

ROUTES = [
    ("GET", "/api/v1/stock-report/consistency"),
    ("POST", "/api/v1/stock-report/repair"),
]

_ASSIGNMENT_ENTRY = {
    "stock_report_item_id": "sri_1",
    "task_id": "tsk_1",
    "item_id": "itm_1",
}
ASSIGNMENT_ROUTES = [
    ("POST", "/api/v1/stock-report/assignments", {"entries": [_ASSIGNMENT_ENTRY]}),
    ("POST", "/api/v1/stock-report/assignments/delete", {"client_ids": ["sta_1"]}),
]
PREVIEW_BODY = {
    "task_id": "tsk_1",
    "article_number": "SR-1",
    "sku": None,
    "item_category_id": "itc_1",
    "properties": {"wood_type": "Teak"},
    "quantity": 4,
}


def client(monkeypatch, role, *, fake_outcome=None):
    app = FastAPI()
    app.include_router(stock_report.router, prefix="/api/v1/stock-report")
    calls = []

    async def fake_db():
        yield object()

    async def fake_run(service, context):
        calls.append((service, context))
        if fake_outcome is not None:
            return fake_outcome
        return SimpleNamespace(success=True, data={"ok": True}, error=None)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_jwt_claims] = lambda: {
        "role_name": role,
        "workspace_id": "ws_test",
        "user_id": "usr_test",
    }
    monkeypatch.setattr(stock_report, "run_service", fake_run)
    return TestClient(app), calls


@pytest.mark.parametrize("role", ["worker", "seller"])
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_stock_report_routes_reject_non_manager_roles(monkeypatch, role, method, path):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path).status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager"])
@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_stock_report_routes_reach_service_for_permitted_roles(
    monkeypatch, role, method, path
):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path).status_code == 200
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Plan 8 C8 — assignment role cells (ADMIN, MANAGER, WORKER reach; SELLER refused)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["seller"])
@pytest.mark.parametrize(("method", "path", "body"), ASSIGNMENT_ROUTES)
def test_assignment_routes_reject_seller(monkeypatch, role, method, path, body):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path, json=body).status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager", "worker"])
@pytest.mark.parametrize(("method", "path", "body"), ASSIGNMENT_ROUTES)
def test_assignment_routes_reach_service_for_permitted_roles(
    monkeypatch, role, method, path, body
):
    http, calls = client(monkeypatch, role)
    assert http.request(method, path, json=body).status_code == 200
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Plan 8 C8(i)/(j) — the two structured assignment errors render code + details
# ---------------------------------------------------------------------------


def test_stock_assignment_refused_renders_code_and_details(monkeypatch):
    error = StockAssignmentRefused([{"index": 0, "reason": "item_already_assigned"}])
    http, _ = client(
        monkeypatch,
        "manager",
        fake_outcome=SimpleNamespace(success=False, data=None, error=error),
    )
    response = http.post(
        "/api/v1/stock-report/assignments", json={"entries": [_ASSIGNMENT_ENTRY]}
    )
    assert response.status_code == 422
    body = response.json()
    assert body == {
        "error": "Stock assignment refused.",
        "ok": False,
        "code": "stock_assignment_refused",
        "details": [{"index": 0, "reason": "item_already_assigned"}],
    }


# ---------------------------------------------------------------------------
# S1 (batch C1 review 1, 2026-09-21) — unknown fields refused with 422 over HTTP.
# Intention §9C MC-13: "Unknown fields -> 422 (a local API, so strict)." Without
# `extra="forbid"` on the router's own body models, an unrecognized field was
# silently dropped by `body.model_dump()` before the command's own strict model
# ever saw it, so the request succeeded (200) instead of refusing (422).
# ---------------------------------------------------------------------------


def test_create_assignments_route_refuses_unknown_top_level_field(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    body = {"entries": [_ASSIGNMENT_ENTRY], "unexpected": True}
    response = http.post("/api/v1/stock-report/assignments", json=body)
    assert response.status_code == 422
    assert calls == []


def test_create_assignments_route_refuses_unknown_entry_field(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    body = {"entries": [{**_ASSIGNMENT_ENTRY, "unexpected": True}]}
    response = http.post("/api/v1/stock-report/assignments", json=body)
    assert response.status_code == 422
    assert calls == []


def test_delete_assignments_route_refuses_unknown_top_level_field(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    body = {"client_ids": ["sta_1"], "unexpected": True}
    response = http.post("/api/v1/stock-report/assignments/delete", json=body)
    assert response.status_code == 422
    assert calls == []


def test_stock_assignment_property_mismatch_renders_code_and_details(monkeypatch):
    details = [
        {
            "index": 0,
            "stock_report_item_id": "sri_1",
            "task_id": "tsk_1",
            "item_id": "itm_1",
            "failures": [
                {
                    "key": "wood_group",
                    "reason": "missing_on_item",
                    "accepted_values": ["teak"],
                    "item_values": [],
                }
            ],
        }
    ]
    error = StockAssignmentPropertyMismatch(details)
    http, _ = client(
        monkeypatch,
        "manager",
        fake_outcome=SimpleNamespace(success=False, data=None, error=error),
    )
    response = http.post(
        "/api/v1/stock-report/assignments", json={"entries": [_ASSIGNMENT_ENTRY]}
    )
    assert response.status_code == 409
    body = response.json()
    assert body == {
        "error": "Stock assignment property mismatch.",
        "ok": False,
        "code": "stock_assignment_property_mismatch",
        "details": details,
    }


@pytest.mark.parametrize("role", ["admin", "manager", "worker"])
def test_match_preview_route_reaches_service_for_allowed_roles(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    response = http.post(
        "/api/v1/stock-report/items/sri_1/match-preview", json=PREVIEW_BODY
    )
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][1].incoming_data["client_id"] == "sri_1"


def test_match_preview_route_rejects_seller(monkeypatch):
    http, calls = client(monkeypatch, "seller")
    response = http.post(
        "/api/v1/stock-report/items/sri_1/match-preview", json=PREVIEW_BODY
    )
    assert response.status_code == 403
    assert calls == []


def test_match_preview_route_rejects_unknown_field(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    response = http.post(
        "/api/v1/stock-report/items/sri_1/match-preview",
        json={**PREVIEW_BODY, "unexpected": True},
    )
    assert response.status_code == 422
    assert calls == []


# ---------------------------------------------------------------------------
# Plan 12 C7 — the three phase-12 routes: role cells, `client_id` in the path,
# and the two request-model contracts the endpoint's 422s rest on.
# ---------------------------------------------------------------------------

PRIORITY_ROUTES = [
    ("/api/v1/stock-report/items/sri_1/priority", {"priority": "high"}),
    ("/api/v1/stock-report/items/sri_1/priority-order", {"priority_order": 2}),
]


@pytest.mark.parametrize("role", ["admin", "manager", "seller"])
@pytest.mark.parametrize(("path", "body"), PRIORITY_ROUTES)
def test_ordering_routes_reach_service_for_permitted_roles(
    monkeypatch, role, path, body
):
    http, calls = client(monkeypatch, role)
    assert http.patch(path, json=body).status_code == 200
    assert len(calls) == 1
    assert calls[0][1].incoming_data["client_id"] == "sri_1"


@pytest.mark.parametrize(("path", "body"), PRIORITY_ROUTES)
def test_ordering_routes_reject_worker(monkeypatch, path, body):
    http, calls = client(monkeypatch, "worker")
    assert http.patch(path, json=body).status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager", "worker", "seller"])
def test_list_items_route_reaches_service_for_every_role(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    response = http.get(
        "/api/v1/stock-report/items?priority=high,low&include_zero_requested=true"
        "&item_major_categories=seat&item_major_categories=wood"
        "&item_category_ids=itc_1&item_category_ids=itc_2"
    )
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][1].query_params == {
        "priority": "high,low",
        "include_zero_requested": True,
        "item_major_categories": [
            ItemMajorCategoryEnum.SEAT,
            ItemMajorCategoryEnum.WOOD,
        ],
        "item_category_ids": ["itc_1", "itc_2"],
        "live_stock": False,
        "missing_only": False,
    }


def test_list_items_route_passes_priority_all_through_verbatim(monkeypatch):
    """`all` is interpreted by the query, not the router: it arrives as the raw
    string, exactly like a priority list."""
    http, calls = client(monkeypatch, "worker")
    assert http.get("/api/v1/stock-report/items?priority=all").status_code == 200
    assert calls[0][1].query_params["priority"] == "all"


def test_list_items_route_passes_no_priority_when_the_param_is_absent(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    assert http.get("/api/v1/stock-report/items").status_code == 200
    assert calls[0][1].query_params == {
        "priority": None,
        "include_zero_requested": False,
        "item_major_categories": None,
        "item_category_ids": None,
        "live_stock": False,
        "missing_only": False,
    }


def test_list_items_route_passes_the_two_snapshot_flags(monkeypatch):
    http, calls = client(monkeypatch, "worker")
    response = http.get(
        "/api/v1/stock-report/items?live_stock=true&missing_only=true"
    )
    assert response.status_code == 200
    assert calls[0][1].query_params["live_stock"] is True
    assert calls[0][1].query_params["missing_only"] is True


def test_list_items_route_refuses_an_unknown_major_category(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    response = http.get("/api/v1/stock-report/items?item_major_categories=unknown")
    assert response.status_code == 422
    assert calls == []


@pytest.mark.parametrize(("path", "body"), PRIORITY_ROUTES)
def test_ordering_routes_refuse_unknown_fields(monkeypatch, path, body):
    http, calls = client(monkeypatch, "manager")
    assert http.patch(path, json={**body, "unexpected": True}).status_code == 422
    assert calls == []


@pytest.mark.parametrize(
    ("path", "body"),
    [
        # The key is required and has no default (plan 12 C1(m)).
        ("/api/v1/stock-report/items/sri_1/priority", {}),
        # Rejected by value, not silently passed through.
        ("/api/v1/stock-report/items/sri_1/priority", {"priority": "urgent"}),
        # `StrictInt`: pydantic's lax mode would coerce "2" to 2 (plan 12 C1(n)).
        ("/api/v1/stock-report/items/sri_1/priority-order", {"priority_order": "2"}),
    ],
)
def test_ordering_routes_refuse_malformed_bodies(monkeypatch, path, body):
    http, calls = client(monkeypatch, "manager")
    assert http.patch(path, json=body).status_code == 422
    assert calls == []


def test_priority_route_accepts_an_explicit_null(monkeypatch):
    """`null` is a legal value and means "clear the priority"."""
    http, calls = client(monkeypatch, "manager")
    response = http.patch(
        "/api/v1/stock-report/items/sri_1/priority", json={"priority": None}
    )
    assert response.status_code == 200
    assert calls[0][1].incoming_data == {"priority": None, "client_id": "sri_1"}


# ---------------------------------------------------------------------------
# Plan 13 C5 — the two phase-13 routes. `DELETE` is narrower than every other
# route (admin and manager only); `GET …/assignments` is open to all four roles.
# Both take `client_id` from the path, and `DELETE` takes no body at all.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_delete_item_route_reaches_service_for_admin_and_manager(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    assert http.delete("/api/v1/stock-report/items/sri_1").status_code == 200
    assert len(calls) == 1
    assert calls[0][1].incoming_data == {"client_id": "sri_1"}


@pytest.mark.parametrize("role", ["worker", "seller"])
def test_delete_item_route_rejects_worker_and_seller(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    assert http.delete("/api/v1/stock-report/items/sri_1").status_code == 403
    assert calls == []


@pytest.mark.parametrize("role", ["admin", "manager", "worker", "seller"])
def test_list_assignments_route_reaches_service_for_every_role(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    response = http.get(
        "/api/v1/stock-report/items/sri_1/assignments?include_resolved=true"
    )
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][1].incoming_data == {"client_id": "sri_1"}
    assert calls[0][1].query_params == {"include_resolved": True}


def test_list_assignments_route_hides_resolved_by_default(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    assert http.get("/api/v1/stock-report/items/sri_1/assignments").status_code == 200
    assert calls[0][1].query_params == {"include_resolved": False}


# ---------------------------------------------------------------------------
# The snapshot routes (2026-09-26): role cells, path ids, body contracts.
# ---------------------------------------------------------------------------

SNAPSHOT_READ_ROUTES = [
    "/api/v1/stock-report/snapshots/versions",
    "/api/v1/stock-report/snapshots/versions/active",
    "/api/v1/stock-report/snapshots/missing-summary",
]
SNAPSHOT_MANAGER_ROUTES = [
    ("/api/v1/stock-report/snapshots/versions", None),
    ("/api/v1/stock-report/snapshots/versions/srv_1/apply-priorities", "srv_1"),
]


@pytest.mark.parametrize("role", ["admin", "manager", "worker", "seller"])
@pytest.mark.parametrize("path", SNAPSHOT_READ_ROUTES)
def test_snapshot_read_routes_reach_service_for_every_role(monkeypatch, role, path):
    http, calls = client(monkeypatch, role)
    assert http.get(path).status_code == 200
    assert len(calls) == 1


def test_versions_list_route_passes_limit_and_offset(monkeypatch):
    http, calls = client(monkeypatch, "manager")
    assert (
        http.get("/api/v1/stock-report/snapshots/versions?limit=5&offset=10").status_code
        == 200
    )
    assert calls[0][1].query_params == {"limit": 5, "offset": 10}
    assert http.get("/api/v1/stock-report/snapshots/versions?limit=201").status_code == 422
    # Default page size 20 (owner ruling 2026-09-26), not the contract's 50.
    assert http.get("/api/v1/stock-report/snapshots/versions").status_code == 200
    assert calls[-1][1].query_params == {"limit": 20, "offset": 0}


@pytest.mark.parametrize("role", ["admin", "manager"])
@pytest.mark.parametrize(("path", "client_id"), SNAPSHOT_MANAGER_ROUTES)
def test_snapshot_write_routes_reach_service_for_admin_and_manager(
    monkeypatch, role, path, client_id
):
    http, calls = client(monkeypatch, role)
    assert http.post(path).status_code == 200
    assert len(calls) == 1
    if client_id is not None:
        assert calls[0][1].incoming_data == {"client_id": client_id}


@pytest.mark.parametrize("role", ["worker", "seller"])
@pytest.mark.parametrize(("path", "_client_id"), SNAPSHOT_MANAGER_ROUTES)
def test_snapshot_write_routes_reject_worker_and_seller(monkeypatch, role, path, _client_id):
    http, calls = client(monkeypatch, role)
    assert http.post(path).status_code == 403
    assert calls == []


MISSING_ROUTE = "/api/v1/stock-report/items/sri_1/missing-quantity"


@pytest.mark.parametrize("role", ["admin", "manager", "worker"])
def test_missing_quantity_route_reaches_service_for_permitted_roles(monkeypatch, role):
    http, calls = client(monkeypatch, role)
    assert http.patch(MISSING_ROUTE, json={"quantity_missing": 2}).status_code == 200
    assert calls[0][1].incoming_data == {"quantity_missing": 2, "client_id": "sri_1"}


def test_missing_quantity_route_rejects_seller(monkeypatch):
    http, calls = client(monkeypatch, "seller")
    assert http.patch(MISSING_ROUTE, json={"quantity_missing": 2}).status_code == 403
    assert calls == []


@pytest.mark.parametrize(
    "body",
    [{}, {"quantity_missing": "2"}, {"quantity_missing": 2, "unexpected": True}],
)
def test_missing_quantity_route_refuses_malformed_bodies(monkeypatch, body):
    """Strict integer, required key, no unknown keys — the `priority_order` contract."""
    http, calls = client(monkeypatch, "manager")
    assert http.patch(MISSING_ROUTE, json=body).status_code == 422
    assert calls == []
