"""Plan 14 — the stock-report documentation guard (master plan §6.6, §6.7, §9 rules
11/15; intention §9B).

**The roots are stated here, not inferred** (verification-scope rule, L-38):

* routes — the app's own route table (`create_app()`), filtered to the two
  stock-report prefixes, plus the `require_roles([...])` lists read out of the two
  router modules' AST. The router declares roles as imported constants
  (`require_roles([ADMIN, MANAGER])`), never as string literals, so a guard that
  grepped for `"admin"` would find nothing and pass;
* event names — master plan **§6.7**'s list (transcribed below, verbatim) **plus**
  every `event_name=` site under `bm/services/commands/stock_report/`, the
  `stock_task_assignment:{kind}` template expanded over its three kinds. Rooting this
  in `_events.py` alone is the defect owner card 6 forbids: that module builds one
  literal name, `stock_report_item:created` is built at `apply_stock_demand.py` and
  `stock_report_item:deleted` at `_delete_stock_report_item_cascade.py`;
* errors — every class of `bm/errors/stock_report.py` and every
  `STOCK_REPORT_*` message identity raised under the stock-report services;
* states — `StockTaskAssignmentStateEnum`;
* nullability — the **shipped serializers** in
  `bm/domain/stock_report/serializers.py`, read as AST and resolved against the
  mapped columns' own `nullable`, compared field by field against the published
  handoff's tables (owner ruling 2026-09-22: C2(a) is a test, not a reviewer's eye).

The documents under test are the two domain documents and the **one current**
frontend handoff; `_CURRENT_HANDOFF` is the single place that name appears, so a
re-issue moves one line.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from beyo_manager.domain.stock_report.enums import StockTaskAssignmentStateEnum
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.stock_report.stock_task_assignment import (
    StockTaskAssignment,
)
from beyo_manager.models.tables.tasks.task import Task

pytestmark = pytest.mark.unit

_BACKEND = Path(__file__).resolve().parents[4]
_DOMAIN_DOCS = _BACKEND / "docs" / "domains" / "stock_report"
_PROJECT = (
    _BACKEND
    / "docs"
    / "architecture"
    / "under_construction"
    / "implementation"
    / "stock_report"
)
_CURRENT_HANDOFF = (
    _PROJECT
    / "handoffs"
    / "to_frontend"
    / "HANDOFF_TO_FRONTEND_stock_report_api_20260922.md"
)

_SOURCE = _BACKEND / "app" / "beyo_manager"
_ROUTER_MODULES = (
    _SOURCE / "routers" / "api_v1" / "stock_report.py",
    _SOURCE / "routers" / "api_v1" / "location_tracker_webhooks.py",
)
_STOCK_COMMANDS = _SOURCE / "services" / "commands" / "stock_report"
_SERIALIZERS = _SOURCE / "domain" / "stock_report" / "serializers.py"
_ERRORS = _SOURCE / "errors" / "stock_report.py"

_API_MD = _DOMAIN_DOCS / "api.md"
_STATES_MD = _DOMAIN_DOCS / "states.md"

_PREFIXES = ("/api/v1/stock-report", "/api/v1/location-tracker/webhooks")

# Verbatim from master plan §6.7 — the ratified event list (MC-19). This literal is
# one of the two roots; the other is the code scan below, and the guard fails in
# both directions.
_MASTER_PLAN_EVENT_NAMES = frozenset(
    {
        "stock_report_item:created",
        "stock_report_item:updated",
        "stock_report_item:deleted",
        "stock_task_assignment:created",
        "stock_task_assignment:state-changed",
        "stock_task_assignment:deleted",
    }
)
# The three kinds `build_stock_task_assignment_event` is called with (§6.5).
_ASSIGNMENT_EVENT_KINDS = ("created", "state-changed", "deleted")

_SERIALIZER_MODELS = {
    "row": StockReportItem,
    "category": ItemCategory,
    "assignment": StockTaskAssignment,
    "item": Item,
    "task": Task,
}


def _read(path: Path) -> str:
    return path.read_text()


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


# ---------------------------------------------------------------------------
# Roots: the code
# ---------------------------------------------------------------------------


def _role_lists_by_endpoint() -> dict[str, tuple[str, ...]]:
    """`require_roles([ADMIN, MANAGER])` → `("admin", "manager")`, keyed by the route
    function's name. The constants are resolved through the module that defines
    them, never guessed from a string literal (L-38)."""
    from beyo_manager.routers.utils import roles as roles_module

    found: dict[str, tuple[str, ...]] = {}
    for module_path in _ROUTER_MODULES:
        tree = ast.parse(_read(module_path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            names: list[str] = []
            for call in ast.walk(node.args):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "require_roles"
                    and call.args
                    and isinstance(call.args[0], ast.List)
                ):
                    for element in call.args[0].elts:
                        if isinstance(element, ast.Name):
                            names.append(getattr(roles_module, element.id))
                        elif isinstance(element, ast.Constant):
                            names.append(element.value)
            found[node.name] = tuple(names)
    return found


def _declared_routes() -> list[tuple[str, str, tuple[str, ...]]]:
    """(method, path, roles) for every stock-report route the app actually mounts.
    A webhook carries no role list and is reported as `("key",)`."""
    from beyo_manager import create_app

    app = create_app()
    roles_by_endpoint = _role_lists_by_endpoint()
    routes = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith(_PREFIXES):
            continue
        endpoint_name = getattr(getattr(route, "endpoint", None), "__name__", "")
        if endpoint_name not in roles_by_endpoint:
            continue
        roles = roles_by_endpoint[endpoint_name] or ("key",)
        for method in sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}):
            routes.append((method, path, roles))
    return sorted(set(routes))


def _event_names_in_code() -> set[str]:
    """Every name an `event_name=` site under `bm/services/commands/stock_report/`
    can build, the `stock_task_assignment:{kind}` template expanded."""
    names: set[str] = set()
    # `rglob`, not `glob`: the stated root is every `event_name=` site **under**
    # the package, and today's only subpackage (`requests/`) builds none — so the
    # scan matched its own description only by accident (review 1, N5).
    for module_path in sorted(_STOCK_COMMANDS.rglob("*.py")):
        tree = ast.parse(_read(module_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.keyword) or node.arg != "event_name":
                continue
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                names.add(value.value)
            elif isinstance(value, ast.JoinedStr):
                prefix = "".join(
                    part.value
                    for part in value.values
                    if isinstance(part, ast.Constant)
                )
                names.update(f"{prefix}{kind}" for kind in _ASSIGNMENT_EVENT_KINDS)
    return names


def _error_class_names() -> set[str]:
    tree = ast.parse(_read(_ERRORS))
    return {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }


def _message_identities() -> set[str]:
    """The `05_errors_local` leading-token identities this project registers
    (master plan §6.4), scanned out of the code that raises them."""
    identities: set[str] = set()
    for module_path in sorted(_SOURCE.rglob("*.py")):
        if "stock_report" not in str(module_path):
            continue
        identities.update(re.findall(r"\b(STOCK_REPORT_[A-Z_]+):", _read(module_path)))
    return identities


def _serializer_nullability() -> dict[str, dict[str, bool]]:
    """`{serializer name: {field path: nullable}}`, read out of the shipped
    serializers.

    Each returned key's value expression is resolved to the model attribute it
    reads, and the answer is that **column's** own `nullable`. A defensive
    `x.isoformat() if x else None` around a NOT NULL column is therefore not read as
    a nullable field — the column decides, not the guard style. A nested dict is
    flattened with a dotted prefix; a call or a comprehension (a sub-shape, an image
    list) is documented as its own shape and is skipped here.
    """
    tree = ast.parse(_read(_SERIALIZERS))
    result: dict[str, dict[str, bool]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        returns = [
            child for child in ast.walk(node) if isinstance(child, ast.Return)
        ]
        if not returns or not isinstance(returns[0].value, ast.Dict):
            continue
        result[node.name] = _flatten_dict(returns[0].value, prefix="")
    return result


def _flatten_dict(dict_node: ast.Dict, *, prefix: str) -> dict[str, bool]:
    fields: dict[str, bool] = {}
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if not isinstance(key_node, ast.Constant):
            continue
        key = f"{prefix}{key_node.value}"
        if isinstance(value_node, ast.Dict):
            fields.update(_flatten_dict(value_node, prefix=f"{key}."))
            continue
        nullable = _nullable_of(value_node)
        if nullable is not None:
            fields[key] = nullable
    return fields


def _nullable_of(node: ast.AST) -> bool | None:
    """The `nullable` of the first mapped column the expression reads, or `None`
    when the expression builds a sub-shape (a call, a comprehension)."""
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name)
            and child.value.id in _SERIALIZER_MODELS
        ):
            model = _SERIALIZER_MODELS[child.value.id]
            column = model.__table__.columns.get(child.attr)
            if column is not None:
                return bool(column.nullable)
    return None


# ---------------------------------------------------------------------------
# Roots: the documents
# ---------------------------------------------------------------------------


def _markdown_table_rows(text: str, *, after: str) -> list[list[str]]:
    """The rows of the first markdown table following the line containing
    `after`."""
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if after in line
    )
    rows: list[list[str]] = []
    seen_table = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("|"):
            seen_table = True
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif seen_table and stripped == "":
            break
    return rows


def _documented_fields(serializer_name: str) -> dict[str, tuple[bool, str]]:
    """`{field: (nullable, the condition that produces the null)}` from the current
    handoff's table for that serializer. Columns: Field | Type | Nullable | Null when."""
    rows = _markdown_table_rows(_read(_CURRENT_HANDOFF), after=f"`{serializer_name}`")
    documented: dict[str, tuple[bool, str]] = {}
    for cells in rows:
        field = cells[0].strip("` ")
        if field.lower() == "field":
            continue
        claim = cells[2].strip().lower()
        assert claim in {"yes", "no"}, f"{serializer_name}.{field}: {claim!r}"
        documented[field] = (claim == "yes", cells[3].strip())
    return documented


# ---------------------------------------------------------------------------
# C1(a) — every route of §6.6 is in api.md, with its roles
# ---------------------------------------------------------------------------


def test_c1a_api_md_carries_every_route_with_its_roles():
    api_md = _normalized(_API_MD)
    routes = _declared_routes()
    assert len(routes) == 13, routes
    for method, path, roles in routes:
        row = f"| `{method}` | `{path}` | " + ", ".join(f"`{role}`" for role in roles)
        assert row in api_md, f"missing from api.md: {row}"


def test_c1a_api_md_documents_no_route_the_app_does_not_serve():
    """The reverse direction: a path in the document that the app does not mount."""
    served = {path for _method, path, _roles in _declared_routes()}
    documented = set(re.findall(r"\| `(/api/v1/[^`]+)` \|", _read(_API_MD)))
    assert documented - served == set()


# ---------------------------------------------------------------------------
# C1(b) — event names, in both directions
# ---------------------------------------------------------------------------


def test_c1b_every_event_name_the_code_builds_is_in_the_handoff():
    handoff = _normalized(_CURRENT_HANDOFF)
    built = _event_names_in_code()
    # A scan that returned nothing would make this loop pass over nothing, which is
    # the vacuity C1(a)'s `len(routes) == 13` already forbids (review 1, N6). The
    # contract is "the scan finds event names", not a pinned count (charter r13).
    assert built, "the `event_name=` scan found nothing"
    for name in sorted(_MASTER_PLAN_EVENT_NAMES | built):
        assert f"`{name}`" in handoff, f"missing from the handoff: {name}"


def test_c1b_the_handoff_names_no_event_no_site_builds():
    """The reverse direction (projection r0 F-13): a name in the document that no
    `event_name=` site and no §6.7 entry produces."""
    buildable = _MASTER_PLAN_EVENT_NAMES | _event_names_in_code()
    documented = set(
        re.findall(
            r"`(stock_report_item:[a-z-]+|stock_task_assignment:[a-z-]+)`",
            _read(_CURRENT_HANDOFF),
        )
    )
    assert documented - buildable == set()


# ---------------------------------------------------------------------------
# C1(c) — errors and message identities, in both documents
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("document", ["api.md", "handoff"])
def test_c1c_every_error_class_and_identity_appears(document):
    text = _normalized(_API_MD if document == "api.md" else _CURRENT_HANDOFF)
    classes = _error_class_names()
    identities = _message_identities()
    # Both scans observed non-empty, so neither loop can pass over nothing
    # (review 1, N6). Non-emptiness is the contract; the counts are not pinned.
    assert classes, "the error-class scan found nothing"
    assert identities, "the message-identity scan found nothing"
    for name in sorted(classes | identities):
        assert name in text, f"missing from {document}: {name}"


# ---------------------------------------------------------------------------
# C1(d) — the six assignment states, in states.md and in the handoff
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("document", ["states.md", "handoff"])
def test_c1d_every_assignment_state_appears(document):
    text = _normalized(_STATES_MD if document == "states.md" else _CURRENT_HANDOFF)
    states = [member.value for member in StockTaskAssignmentStateEnum]
    assert len(states) == 6
    for state in states:
        assert f"`{state}`" in text, f"missing from {document}: {state}"


# ---------------------------------------------------------------------------
# C2(a) — the handoff's nullability tables against the shipped serializers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "serializer_name",
    [
        "serialize_stock_report_item",
        "serialize_stock_task_assignment",
        "serialize_item_compact",
        "serialize_task_compact",
    ],
)
def test_c2a_the_handoff_nullability_matches_the_shipped_serializer(serializer_name):
    shipped = _serializer_nullability()[serializer_name]
    documented = _documented_fields(serializer_name)
    assert {
        field: nullable for field, (nullable, _when) in documented.items()
    } == shipped
    # "…and names the condition that produces the null" — a nullable field with an
    # empty condition cell is not documented, it is merely listed.
    for field, (nullable, when) in documented.items():
        if nullable:
            assert when and when != "—", f"{serializer_name}.{field} names no condition"


def test_c2a_at_least_one_field_of_each_kind_exists_to_discriminate():
    """L-26: an agreement check proves nothing if one side is empty or uniform. Every
    table must carry at least one nullable **and** one non-nullable field, or the
    comparison above could pass by having nothing to disagree about."""
    for serializer_name, shipped in _serializer_nullability().items():
        assert any(shipped.values()), serializer_name
        assert not all(shipped.values()), serializer_name
