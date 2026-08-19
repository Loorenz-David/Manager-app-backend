"""C4 — `routers/README.md` mirrors every item-economics route the registry shipped.

The expected set below is a **hand-written literal**. It is deliberately not derived
from ``router.routes`` or from the README: a table computed from the surface it audits
cannot disagree with that surface, which is the whole failure this criterion exists to
catch. Adding a route means editing three places — the router, the README, and this
list — and that friction is the point.

Two arbiters over the same 26 rows:

1. the README's Quick Index rows for `/api/v1/item-economics/` match (method, path);
2. the router source's ``@router.<verb>`` decorators and their ``require_roles([...])``
   dependencies match (method, path, role gate).
"""

import re
from pathlib import Path

import pytest


_APP_ROOT = Path(__file__).resolve().parents[3]
_README = _APP_ROOT / "beyo_manager" / "routers" / "README.md"
_ROUTER = _APP_ROOT / "beyo_manager" / "routers" / "api_v1" / "item_economics.py"
_ROUTER_REGISTRATION = _APP_ROOT / "beyo_manager" / "routers" / "api_v1" / "__init__.py"

_PREFIX = "/api/v1/item-economics"

_ADMIN_MANAGER = frozenset({"ADMIN", "MANAGER"})
_ALL_ROLES = frozenset({"ADMIN", "MANAGER", "WORKER", "SELLER"})

# (method, full path, role gate) — hand-written from master plan §6.5.
_EXPECTED_ROUTES = (
    ("POST", "/api/v1/item-economics/cost-groups", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/cost-groups", _ADMIN_MANAGER),
    ("PATCH", "/api/v1/item-economics/cost-groups/{client_id}", _ADMIN_MANAGER),
    ("DELETE", "/api/v1/item-economics/cost-groups/{client_id}", _ADMIN_MANAGER),
    ("POST", "/api/v1/item-economics/cost-groups/{client_id}/sections", _ADMIN_MANAGER),
    (
        "DELETE",
        "/api/v1/item-economics/cost-groups/{client_id}/sections/{working_section_client_id}",
        _ADMIN_MANAGER,
    ),
    ("POST", "/api/v1/item-economics/cost-groups/{client_id}/basis-versions", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/cost-groups/{client_id}/basis-versions", _ADMIN_MANAGER),
    ("DELETE", "/api/v1/item-economics/basis-versions/{client_id}", _ADMIN_MANAGER),
    ("POST", "/api/v1/item-economics/cost-model-versions", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/cost-model-versions", _ADMIN_MANAGER),
    ("DELETE", "/api/v1/item-economics/cost-model-versions/{client_id}", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/configuration-status", _ADMIN_MANAGER),
    ("PUT", "/api/v1/item-economics/items/{item_client_id}/valuation", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/items/{item_client_id}/valuations", _ADMIN_MANAGER),
    ("DELETE", "/api/v1/item-economics/items/{item_client_id}/valuation", _ADMIN_MANAGER),
    ("POST", "/api/v1/item-economics/tasks/{task_client_id}/evaluations/commit", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/tasks/{task_client_id}/evaluations", _ADMIN_MANAGER),
    ("POST", "/api/v1/item-economics/tasks/{task_client_id}/projections", _ADMIN_MANAGER),
    ("DELETE", "/api/v1/item-economics/projections/{client_id}", _ADMIN_MANAGER),
    ("POST", "/api/v1/item-economics/projections/{client_id}/promote", _ADMIN_MANAGER),
    # The all-role read-only route; its payload is time-only for every identity.
    ("GET", "/api/v1/item-economics/tasks/budget-allocations", _ALL_ROLES),
    # The budget-status handler picks the money-free worker service for WORKER and SELLER identities.
    ("GET", "/api/v1/item-economics/tasks/{task_client_id}/budget-status", _ALL_ROLES),
    ("GET", "/api/v1/item-economics/tasks/{task_client_id}/production-time", _ALL_ROLES),
    ("GET", "/api/v1/item-economics/tasks/{task_client_id}/price-scenario", _ADMIN_MANAGER),
    ("GET", "/api/v1/item-economics/items/{item_client_id}/economics", _ADMIN_MANAGER),
)

_README_ROW = re.compile(
    r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*(/api/v1/item-economics/[^|\s]*)\s*\|"
)
_DECORATOR = re.compile(r"^@router\.(get|post|put|patch|delete)\(\"([^\"]+)\"")
_REQUIRE_ROLES = re.compile(r"require_roles\(\[([^\]]*)\]\)")


def _readme_rows() -> set[tuple[str, str]]:
    rows = set()
    for line in _README.read_text().splitlines():
        match = _README_ROW.match(line)
        if match:
            rows.add((match.group(1), match.group(2)))
    return rows


def _router_routes() -> set[tuple[str, str, frozenset[str]]]:
    """Read decorator → role gate pairs out of the router source."""
    lines = _ROUTER.read_text().splitlines()
    routes = set()
    for index, line in enumerate(lines):
        match = _DECORATOR.match(line)
        if not match:
            continue
        method, suffix = match.group(1).upper(), match.group(2)
        # The gate sits in the signature that follows, before the next decorator.
        roles = None
        for following in lines[index + 1 : index + 20]:
            if following.startswith("@router."):
                break
            gate = _REQUIRE_ROLES.search(following)
            if gate:
                roles = frozenset(token.strip() for token in gate.group(1).split(",") if token.strip())
                break
        assert roles is not None, f"no require_roles found for {method} {suffix}"
        routes.add((method, f"{_PREFIX}{suffix}", roles))
    return routes


@pytest.mark.unit
def test_router_is_registered_under_the_expected_prefix() -> None:
    registration = _ROUTER_REGISTRATION.read_text()
    assert f'item_economics.router, prefix="{_PREFIX}"' in registration


@pytest.mark.unit
def test_readme_quick_index_mirrors_every_shipped_route() -> None:
    assert _readme_rows() == {(method, path) for method, path, _ in _EXPECTED_ROUTES}


@pytest.mark.unit
def test_router_source_matches_the_hand_written_route_and_role_set() -> None:
    assert _router_routes() == set(_EXPECTED_ROUTES)


@pytest.mark.unit
def test_the_registry_ships_twenty_six_routes() -> None:
    # Enumerated above, one row per route; the count is derived from that table,
    # never asserted independently of it.
    assert len(_EXPECTED_ROUTES) == 26
    assert len({(method, path) for method, path, _ in _EXPECTED_ROUTES}) == 26
