"""The accuracy arbiter for the two frontend handoffs and the living-docs folder.

Every route, error identity, status value and envelope key these documents publish must
grep to the shipped artifact. The expected sets here are **hand-written literals** — never
derived from the surface being audited — so the table and the code can actually disagree.

Anchored on ``parents[4]`` for the docs (``backend/docs/``) and ``parents[3]`` for the app
package, because commands run from ``backend/app/``.
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from beyo_manager.domain.item_economics.enums import EconomicsStatusEnum
from beyo_manager.domain.item_economics.serializers import serialize_task_budget_status


_APP_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[4]
_HANDOFFS = _BACKEND_ROOT / "docs" / "handoff"
_DOMAIN_DOCS = _BACKEND_ROOT / "docs" / "domains" / "item_economics"
_PACKAGE = _APP_ROOT / "beyo_manager"

_OPERATIONAL = _HANDOFFS / "to_frontend" / "HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md"
_CONFIGURATION = _HANDOFFS / "to_frontend" / "HANDOFF_TO_FRONTEND_item_economics_configuration_20260815.md"

_PREFIX = "/api/v1/item-economics"

# ── hand-written route sets (master plan §6.5) ──────────────────────────────────

_CONFIGURATION_ROUTES = frozenset({
    ("POST", "/cost-groups"),
    ("GET", "/cost-groups"),
    ("PATCH", "/cost-groups/{client_id}"),
    ("DELETE", "/cost-groups/{client_id}"),
    ("POST", "/cost-groups/{client_id}/sections"),
    ("DELETE", "/cost-groups/{client_id}/sections/{working_section_client_id}"),
    ("POST", "/cost-groups/{client_id}/basis-versions"),
    ("GET", "/cost-groups/{client_id}/basis-versions"),
    ("DELETE", "/basis-versions/{client_id}"),
    ("POST", "/cost-model-versions"),
    ("GET", "/cost-model-versions"),
    ("DELETE", "/cost-model-versions/{client_id}"),
    ("GET", "/configuration-status"),
})

_OPERATIONAL_ROUTES = frozenset({
    ("PUT", "/items/{item_client_id}/valuation"),
    ("GET", "/items/{item_client_id}/valuations"),
    ("DELETE", "/items/{item_client_id}/valuation"),
    ("POST", "/tasks/{task_client_id}/evaluations/commit"),
    ("GET", "/tasks/{task_client_id}/evaluations"),
    ("POST", "/tasks/{task_client_id}/projections"),
    ("DELETE", "/projections/{client_id}"),
    ("POST", "/projections/{client_id}/promote"),
    ("GET", "/tasks/{task_client_id}/budget-status"),
    ("GET", "/items/{item_client_id}/economics"),
})

_ALL_ROUTES = _CONFIGURATION_ROUTES | _OPERATIONAL_ROUTES

# ── hand-written identity registry (master plan §6.4) ───────────────────────────

# Raised as string literals somewhere under beyo_manager/.
_LITERAL_IDENTITIES = frozenset({
    "ITEM_COST_NO_COST_GROUP",
    "ITEM_COST_AMBIGUOUS_COST_GROUP",
    "ITEM_COST_NO_BASIS_VERSION",
    "ITEM_COST_NO_COST_MODEL_VERSION",
    "ITEM_COST_ITEM_UNVALUED",
    "ITEM_COST_EXPECTED_PRICE_REQUIRED",
    "ITEM_COST_PURCHASE_COST_REQUIRED",
    "ITEM_COST_CURRENCY_MISMATCH",
    "ITEM_COST_TASK_TERMINAL",
    "ITEM_COST_NO_PRIMARY_ITEM",
    "ITEM_COST_TERM_SHAPE_INVALID",
    "ITEM_COST_RATE_UNDERFLOW",
    "ITEM_COST_CONCURRENT_COMMIT",
    "ITEM_COST_CONCURRENT_VALUATION",
    "ITEM_COST_CONCURRENT_BASIS_VERSION",
    "ITEM_COST_CONCURRENT_MODEL_VERSION",
    "ITEM_COST_BASIS_VERSION_IN_USE",
    "ITEM_COST_MODEL_VERSION_IN_USE",
    "ITEM_COST_GROUP_IN_USE",
    "ITEM_COST_VALUATION_AMOUNT_REQUIRED",
    "ITEM_COST_VALUATION_SUPERSEDED_IMMUTABLE",
    "ITEM_COST_SECTION_ALREADY_GROUPED",
    "ITEM_COST_GROUP_NAME_TAKEN",
    "ITEM_COST_TERM_NAME_TAKEN",
    "ITEM_COST_PURCHASE_TERM_DUPLICATE",
    "ITEM_COST_GROUP_CATEGORY_TAKEN",
    "ITEM_COST_GROUP_CATEGORY_IMMUTABLE",
    "ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY",
    "ITEM_MONEY_MOVED",
})

# Composed at raise time by `admission_error(prefix, ...)`, so the full token is not
# greppable — the halves are, and both are asserted below.
_ADMISSION_PREFIXES = ("ITEM_COST_BASIS_VERSION", "ITEM_COST_MODEL_VERSION")
_ADMISSION_SUFFIXES = (
    "_EFFECTIVE_FROM_FUTURE",
    "_EFFECTIVE_FROM_REQUIRED",
    "_EFFECTIVE_FROM_NOT_AFTER_OPEN",
)
_COMPOSED_IDENTITIES = frozenset(
    prefix + suffix for prefix in _ADMISSION_PREFIXES for suffix in _ADMISSION_SUFFIXES
)

_REGISTRY = _LITERAL_IDENTITIES | _COMPOSED_IDENTITIES

_IDENTITY_TOKEN = re.compile(r"\b(ITEM_COST_[A-Z][A-Z_]*|ITEM_MONEY_MOVED)\b")
_HEADING_ROUTE = re.compile(r"`(GET|POST|PUT|PATCH|DELETE) (/[^`]+)`")
_FULL_PATH = re.compile(r"/api/v1/item-economics(/[A-Za-z0-9{}_\-/…]*)")
_BACKTICKED = re.compile(r"`([a-z][a-z_]*)`")


def _text(path: Path) -> str:
    return path.read_text()


def _heading_routes(text: str) -> set[tuple[str, str]]:
    routes = set()
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        for method, path in _HEADING_ROUTE.findall(line):
            routes.add((method, path))
    return routes


def _package_sources() -> str:
    return "\n".join(p.read_text() for p in _PACKAGE.rglob("*.py"))


_CONCRETE_ID = re.compile(r"^[a-z]+_[A-Za-z0-9…]+$")


def _normalize_path(path: str) -> str:
    """Collapse both `{param}` and a worked example's `itm_01H…` to one placeholder.

    Error messages quoted verbatim in the handoffs carry concrete client ids, so the
    check is on the route's SHAPE, not on the literal characters.
    """
    segments = []
    for segment in path.split("/"):
        if segment.startswith("{") or _CONCRETE_ID.match(segment):
            segments.append("{id}")
        else:
            segments.append(segment)
    return "/".join(segments)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("document", "expected"),
    [(_CONFIGURATION, _CONFIGURATION_ROUTES), (_OPERATIONAL, _OPERATIONAL_ROUTES)],
    ids=["configuration-13-routes", "operational-10-routes"],
)
def test_each_handoff_documents_exactly_its_half_of_the_surface(document, expected) -> None:
    assert _heading_routes(_text(document)) == set(expected)


@pytest.mark.unit
def test_the_two_handoffs_together_cover_all_twenty_three_routes() -> None:
    assert len(_ALL_ROUTES) == 23
    assert _heading_routes(_text(_CONFIGURATION)) | _heading_routes(_text(_OPERATIONAL)) == set(_ALL_ROUTES)


@pytest.mark.unit
@pytest.mark.parametrize(
    "document",
    [_CONFIGURATION, _OPERATIONAL, _DOMAIN_DOCS / "api.md", _DOMAIN_DOCS / "README.md"],
    ids=["configuration", "operational", "domain-api", "domain-readme"],
)
def test_no_document_invents_a_fully_qualified_item_economics_path(document) -> None:
    known = {_normalize_path(path) for _, path in _ALL_ROUTES} | {"", "/"}
    for suffix in _FULL_PATH.findall(_text(document)):
        assert _normalize_path(suffix.rstrip(".")) in known, suffix


@pytest.mark.unit
@pytest.mark.parametrize(
    "document",
    [_CONFIGURATION, _OPERATIONAL, _DOMAIN_DOCS / "api.md", _DOMAIN_DOCS / "README.md"],
    ids=["configuration", "operational", "domain-api", "domain-readme"],
)
def test_no_document_names_an_unregistered_error_identity(document) -> None:
    for token in _IDENTITY_TOKEN.findall(_text(document)):
        assert token in _REGISTRY, token


@pytest.mark.unit
def test_operational_handoff_documents_inline_repricing_contract() -> None:
    text = _text(_OPERATIONAL)
    assert "inline-pricing refusal" not in text
    section = " ".join(
        text.split("### 9.1 Inline re-pricing", 1)[1].split("### 9.2", 1)[0].split()
    )
    for required in (
        "a field omitted from the request keeps its current value",
        "writes a new valuation version credited to whoever created the task",
        "writes nothing at all",
        "still accepts the trio and starts a valuation chain",
        "continues to replace values wholesale",
    ):
        assert required in section

    validation = " ".join(
        text.split("## Validation notes", 1)[1].split("## Trace links", 1)[0].split()
    )
    assert "send a **different** price and confirm a new valuation version appears" in validation
    assert "repeat with the **identical** price and confirm no new version appears" in validation
    assert "inline-pricing versioning" in validation


@pytest.mark.unit
def test_retired_inline_refusal_identity_is_absent_from_live_sources() -> None:
    retired_identity = "ITEM_COST_INLINE_PRICE" + "_ON_PRICED_ITEM"
    for root in (_APP_ROOT, _HANDOFFS):
        for path in (*root.rglob("*.py"), *root.rglob("*.md")):
            if root == _APP_ROOT and ".venv" in path.relative_to(root).parts:
                continue
            assert retired_identity not in path.read_text(), path


@pytest.mark.unit
@pytest.mark.parametrize("identity", sorted(_LITERAL_IDENTITIES), ids=sorted(_LITERAL_IDENTITIES))
def test_every_literal_identity_is_greppable_in_the_package(identity: str) -> None:
    assert identity in _package_sources()


@pytest.mark.unit
@pytest.mark.parametrize(
    "fragment",
    [*_ADMISSION_PREFIXES, *_ADMISSION_SUFFIXES],
    ids=[*_ADMISSION_PREFIXES, *_ADMISSION_SUFFIXES],
)
def test_every_composed_identity_half_is_greppable_in_the_package(fragment: str) -> None:
    # The full token is built at raise time, so only the halves can be grepped.
    assert fragment in _package_sources()


@pytest.mark.unit
def test_the_published_status_vocabulary_is_exactly_the_enum() -> None:
    text = _text(_OPERATIONAL)
    section = text.split("## 6. The status vocabulary")[1].split("## 7.")[0]
    enum_values = {member.value for member in EconomicsStatusEnum}
    assert len(enum_values) == 12

    named = {token for token in _BACKTICKED.findall(section) if token in enum_values}
    assert named == enum_values

    # And nothing status-shaped in that section is outside the enum. The allow-list is
    # the non-status backticked prose the section legitimately contains.
    allowed_non_status = {"error", "preview", "null", "status", "percent_consumed"}
    for token in _BACKTICKED.findall(section):
        assert token in enum_values or token in allowed_non_status, token


def _status(*, with_result: bool) -> SimpleNamespace:
    result = SimpleNamespace(
        actual_worker_seconds=7200,
        actual_worker_minutes="120.00",
        consumed_cost_minor=150000,
        variance_worker_minutes="40.00",
        variance_cost_minor=50000,
        task_state_snapshot="ready",
        task_closed_at=None,
        calculation_version=1,
        computed_at=SimpleNamespace(isoformat=lambda: "2026-08-15T10:00:00+00:00"),
    )
    return SimpleNamespace(
        status=SimpleNamespace(value="ok"),
        item_binding="bound",
        actual_worker_seconds=7200,
        actual_worker_minutes="120.00",
        remaining_worker_minutes="40.00",
        percent_consumed="75.00",
        variance_worker_minutes="40.00",
        production_budget_minor=200000,
        allowed_worker_minutes="160.00",
        consumed_cost_minor=150000,
        variance_cost_minor=50000,
        evaluation_id="ice_1",
        item_id="itm_1",
        result=result if with_result else None,
    )


# Hand-written from the handoff's two JSON examples, NOT from the serializer.
_DOCUMENTED_MANAGER_KEYS = frozenset({
    "status", "item_binding", "actual_worker_seconds", "actual_worker_minutes",
    "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result",
    "production_budget_minor", "allowed_worker_minutes", "consumed_cost_minor",
    "variance_cost_minor", "evaluation_id", "item_id",
})
_DOCUMENTED_WORKER_KEYS = frozenset({
    "status", "item_binding", "actual_worker_seconds", "actual_worker_minutes",
    "remaining_worker_minutes", "percent_consumed", "variance_worker_minutes", "result",
    "allowed_worker_minutes",
})
_DOCUMENTED_MANAGER_RESULT_KEYS = frozenset({
    "actual_worker_seconds", "actual_worker_minutes", "consumed_cost_minor",
    "variance_worker_minutes", "variance_cost_minor", "task_state_snapshot",
    "task_closed_at", "calculation_version", "computed_at",
})
_DOCUMENTED_WORKER_RESULT_KEYS = frozenset({
    "actual_worker_minutes", "variance_worker_minutes", "percent_consumed",
    "task_state_snapshot", "computed_at",
})


@pytest.mark.unit
@pytest.mark.parametrize(
    ("include_monetary", "documented", "documented_result"),
    [
        (True, _DOCUMENTED_MANAGER_KEYS, _DOCUMENTED_MANAGER_RESULT_KEYS),
        (False, _DOCUMENTED_WORKER_KEYS, _DOCUMENTED_WORKER_RESULT_KEYS),
    ],
    ids=["budget-status-manager-shape", "budget-status-worker-shape"],
)
def test_the_documented_budget_status_keys_are_the_shipped_keys(
    include_monetary, documented, documented_result
) -> None:
    payload = serialize_task_budget_status(
        _status(with_result=True), include_monetary=include_monetary
    )
    assert set(payload) == set(documented)
    assert set(payload["result"]) == set(documented_result)


@pytest.mark.unit
def test_the_worker_budget_status_carries_no_monetary_key() -> None:
    payload = serialize_task_budget_status(_status(with_result=True), include_monetary=False)
    money = {
        "production_budget_minor", "consumed_cost_minor", "variance_cost_minor",
        "evaluation_id", "item_id",
    }
    assert money.isdisjoint(payload)
    assert {"consumed_cost_minor", "variance_cost_minor", "actual_worker_seconds"}.isdisjoint(
        payload["result"]
    )
