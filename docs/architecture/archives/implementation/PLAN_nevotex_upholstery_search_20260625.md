# PLAN_nevotex_upholstery_search_20260625

## Metadata

- Plan ID: `PLAN_nevotex_upholstery_search_20260625`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T09:38:21Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/upholstery_nevotex_fetch.txt`

---

## Goal and intent

- **Goal:** Add a new backend route `GET /api/v1/upholsteries/external/nevotex` that accepts a `q` search string, calls the Nevotex external search API server-side, normalizes the results into the existing upholstery card shape, and returns them as `origin: "nevotex"` candidates. Also add `origin: "database"` to all existing `serialize_upholstery` output.
- **Business/user intent:** Browser requests to Nevotex are blocked by CORS. The backend acts as a proxy, fetching Nevotex products and normalizing them into the same card shape already used by the upholstery selector. The user selects an external candidate in the same UI as internal ones. No database record is created during the search.
- **Non-goals:** Creating `Upholstery` records from Nevotex candidates, deduplication against DB upholsteries, frontend changes, product detail page scraping.

---

## Scope

- **In scope:**
  - New error class `ExternalServiceError` (`http_status = 502`)
  - New infra module `services/infra/nevotex/client.py` — async httpx Nevotex fetcher
  - New infra module `services/infra/nevotex/normalizer.py` — pure normalization + image URL absolutization
  - New query service `services/queries/upholstery/list_nevotex_upholsteries.py`
  - New router handler `route_list_nevotex_upholsteries` in `routers/api_v1/upholsteries.py` declared before all `/{client_id}` routes
  - `"origin": "database"` added to `serialize_upholstery` in `domain/upholstery/serializers.py`
  - Unit tests for the normalizer

- **Out of scope:**
  - Category derivation from shared name prefix (follow-up phase)
  - Upholstery creation from Nevotex candidates
  - Caching of Nevotex search results
  - Nevotex pagination beyond `pagesize` (no proven offset support)

- **Assumptions:**
  - `httpx==0.28.1` is already installed (confirmed in `requirements.txt`).
  - `aiohttp==3.13.5` is also available but `httpx` is preferred (async, matches FastAPI async model, already present).
  - Nevotex does not require cookies (confirmed by curl tests in the intention doc).
  - `inventory_condition` value `"out_of_stock"` is confirmed correct — it is the `.value` of `UpholsteryInventoryConditionEnum.OUT_OF_STOCK` (verified in `domain/upholstery/enums.py`).
  - Adding `"origin": "database"` to `serialize_upholstery` is a non-breaking extension for the frontend (new field, no removed fields).

---

## Clarifications required

- [x] **`inventory_condition` value for Nevotex candidates** — resolved: `"out_of_stock"` is the exact string value from `UpholsteryInventoryConditionEnum.OUT_OF_STOCK.value` (confirmed from `app/beyo_manager/domain/upholstery/enums.py`).
- [x] **`DoNotShowVariantsAsSingleProducts`** — value must stay `False` (returns all variant-level products, which is required so users can select specific upholstery variants). Using `True` would collapse variants to one product entry per product family, losing the per-variant code/image needed for creating an `Upholstery` instance.
- [x] **Nevotex offset/page pagination** — the tested endpoint exposes only `pagesize`, not a page or offset parameter. Pagination block is returned with `has_more: false` (honest — no real offset support).
- [x] **Route path** — `GET /api/v1/upholsteries/external/nevotex` is chosen (sub-path under the existing prefix, fits router domain ownership, avoids a new router file for a single read route).
- [x] **Session injection** — the Nevotex query function does not use `ctx.session`, but the router still injects `session: AsyncSession = Depends(get_db)` and passes it to `ServiceContext`. This avoids deviating from the standard handler skeleton. `ctx.session` is simply unused inside `list_nevotex_upholsteries`.
- [ ] **Category derivation** — deferred to follow-up. Phase 1 returns `"upholstery_category": None` for all Nevotex candidates.

---

## Acceptance criteria

1. `GET /api/v1/upholsteries/external/nevotex?q=Tyg+Afrodite` returns a JSON response with `{"data": {"upholsteries": [...], "upholsteries_pagination": {...}}, "ok": true}`.
2. Each item in `upholsteries` has `"origin": "nevotex"`, `"client_id": null`, `"code"` mapped from Nevotex `product.number`, `"image_url"` as an absolute decoded URL (`https://nevotex.se/...`), `"inventory_condition": "out_of_stock"`, `"favorite": null`, `"list_order": null`, `"current_stored_amount_meters": 0`, `"upholstery_category": null`.
3. `GET /api/v1/upholsteries?q=...` and `GET /api/v1/upholsteries/{id}` include `"origin": "database"` in every upholstery object.
4. Nevotex timeout (>10s) returns a controlled `502` error response, not an unhandled exception.
5. Nevotex non-200, invalid JSON, or missing `Product` array returns a controlled `502` error response.
6. A malformed individual product (missing `name`, `number`, or `image`) is skipped; remaining valid products are returned.
7. `q` is required (`min_length=1`, `max_length=200`) at the router layer; missing or empty `q` returns `422`.
8. The `/external/nevotex` route is declared before `/{client_id}` in `upholsteries.py` so FastAPI matches it correctly.
9. Unit tests pass for: successful normalization, image URL decode+absolutize, empty products list, malformed product skipped.

---

## Contracts and skills

### Read order

Applied per the document-only protocol from `task_system/backend_contract_goal_mapping_guide.md`:

| Contract (canonical) | Local extension | Applied rule |
|---|---|---|
| `architecture/05_errors.md` | — | Error hierarchy, `DomainError` base, `run_service` boundary |
| `architecture/07_queries.md` | `architecture/07_queries_local.md` | **Local overrides**: offset pagination, `_MAX_LIMIT`/`_DEFAULT_LIMIT`, response shape with `_pagination` key |
| `architecture/09_routers.md` | — | Handler skeleton, route declaration order (static before wildcard), `build_ok`/`build_err` |
| `architecture/19_integrations.md` | — | Adapter pattern, timeout rules, mapper pattern, graceful degradation |
| `architecture/21_naming_conventions.md` | — | File naming, function naming |
| `architecture/46_serialization.md` | `architecture/46_serialization_local.md` | Serializers are pure functions in `domain/<domain>/serializers.py` |
| `architecture/55_query_filters_local.md` | — | `q` param name, `max_length=200` validation at router |

### Applied contract deltas (local extensions over canonical)

- **07_queries_local.md overrides 07_queries.md**: Use offset pagination (`limit` + `offset`), NOT cursor pagination. Pagination response key is `upholsteries_pagination`, not a cursor object.
- **Response builder** (`routers/http/response.py`): Uses `build_ok(data, status_code, warnings)` and `build_err(error)` where `error.http_status` drives the HTTP status code. This is the app-local form — it differs from the contract example which uses a `_STATUS_MAP` dict.

### Contracts excluded

- `06_commands.md` — no database writes in this feature
- `11_infra_events.md`, `13_sockets.md`, `42_event.md` — no events or realtime
- `16_background_jobs.md` — the Nevotex call is inline (synchronous read required by the search UX); the integration contract permits inline external calls with timeout and graceful fallback when results must be returned to the client immediately

### File read intent

Permitted relational reads (what exists):
- `routers/api_v1/upholsteries.py` — to know existing routes and their declaration order
- `domain/upholstery/serializers.py` — to understand the current `serialize_upholstery` shape before adding `origin`
- `domain/upholstery/enums.py` — to verify exact `inventory_condition` string value
- `errors/base.py`, `errors/validation.py` — to understand the existing error subclass pattern
- `routers/http/response.py` — to verify exact `build_ok`/`build_err` signatures
- `routers/api_v1/__init__.py` — to know where to register the import

---

## Implementation plan

### Step 1 — Create `ExternalServiceError`

**File:** `app/beyo_manager/errors/external_service.py` *(new)*

```python
from beyo_manager.errors.base import DomainError


class ExternalServiceError(DomainError):
    http_status = 502

    def __init__(self, message: str = "External service request failed.") -> None:
        super().__init__(message)
```

**File:** `app/beyo_manager/errors/__init__.py` *(currently 0 bytes — add content)*

```python
from beyo_manager.errors.base import DomainError
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ValidationError, ConflictError
from beyo_manager.errors.external_service import ExternalServiceError
```

---

### Step 2 — Create Nevotex infra client

**File:** `app/beyo_manager/services/infra/nevotex/__init__.py` *(new, empty)*

**File:** `app/beyo_manager/services/infra/nevotex/client.py` *(new)*

```python
import logging

import httpx

from beyo_manager.errors.external_service import ExternalServiceError

logger = logging.getLogger(__name__)

_NEVOTEX_BASE_URL = "https://nevotex.se"
_NEVOTEX_SEARCH_URL = f"{_NEVOTEX_BASE_URL}/Default.aspx"
_TIMEOUT_SECONDS = 10.0

_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
    "Referer": "https://nevotex.se/produkter/bekladnadsmaterial/mobeltyger/alla-mobeltyger",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
}


async def fetch_nevotex_raw_products(q: str, limit: int) -> list[dict]:
    """Call Nevotex search and return the flat list of raw product dicts.

    Raises ExternalServiceError on timeout, non-200, invalid JSON, or unexpected shape.
    Skips containers without a Product array — they are silently ignored.
    """
    params = {
        "ID": "9403",
        "instasearch": "1",
        "feed": "true",
        "pagesize": str(limit),
        "Search": q,
        "feedType": "productsOnly",
        "redirect": "false",
        "DoNotShowVariantsAsSingleProducts": "False",
        "Template": "SearchProductsTemplate",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=_HEADERS) as client:
            response = await client.get(_NEVOTEX_SEARCH_URL, params=params)
    except httpx.TimeoutException:
        raise ExternalServiceError("Nevotex search timed out.")
    except httpx.RequestError as exc:
        logger.warning("Nevotex request error: %s", exc)
        raise ExternalServiceError("Nevotex search request failed.")

    if response.status_code != 200:
        logger.warning("Nevotex returned HTTP %s for q=%r", response.status_code, q)
        raise ExternalServiceError(
            f"Nevotex search returned unexpected status {response.status_code}."
        )

    try:
        containers = response.json()
    except Exception:
        logger.warning("Nevotex returned non-JSON body for q=%r", q)
        raise ExternalServiceError("Nevotex search returned a non-JSON response.")

    if not isinstance(containers, list):
        logger.warning("Nevotex response is not a list for q=%r", q)
        raise ExternalServiceError("Nevotex search returned an unexpected response shape.")

    raw_products: list[dict] = []
    for container in containers:
        products = container.get("Product")
        if not isinstance(products, list):
            continue
        raw_products.extend(products)

    return raw_products
```

---

### Step 3 — Create Nevotex normalizer

**File:** `app/beyo_manager/services/infra/nevotex/normalizer.py` *(new)*

```python
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)

_NEVOTEX_BASE_URL = "https://nevotex.se"


def _absolutize_image(raw_image: str) -> str:
    """URL-decode a relative Nevotex image path and prepend the base URL."""
    decoded = unquote(raw_image)
    if decoded.startswith("/"):
        return f"{_NEVOTEX_BASE_URL}{decoded}"
    return f"{_NEVOTEX_BASE_URL}/{decoded}"


def normalize_nevotex_candidate(raw: dict) -> dict | None:
    """Convert one raw Nevotex product dict to an upholstery-card-compatible dict.

    Returns None when required fields (name, number, image) are absent or empty.
    The caller must skip None returns.
    """
    name = raw.get("name", "").strip()
    code = raw.get("number", "").strip()
    image_raw = raw.get("image", "").strip()

    if not name or not code or not image_raw:
        logger.debug(
            "Skipping malformed Nevotex product (missing name/number/image): %r",
            {k: raw.get(k) for k in ("name", "number", "image", "productId")},
        )
        return None

    return {
        "client_id": None,
        "name": name,
        "code": code,
        "image_url": _absolutize_image(image_raw),
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": "out_of_stock",
        "upholstery_category": None,
        "origin": "nevotex",
    }


def normalize_nevotex_candidates(raw_products: list[dict]) -> list[dict]:
    """Normalize a list of raw Nevotex product dicts, skipping malformed entries."""
    result = []
    for raw in raw_products:
        candidate = normalize_nevotex_candidate(raw)
        if candidate is not None:
            result.append(candidate)
    return result
```

---

### Step 4 — Create the Nevotex query service

**File:** `app/beyo_manager/services/queries/upholstery/list_nevotex_upholsteries.py` *(new)*

```python
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products
from beyo_manager.services.infra.nevotex.normalizer import normalize_nevotex_candidates

_MAX_LIMIT = 20
_DEFAULT_LIMIT = 7


async def list_nevotex_upholsteries(ctx: ServiceContext) -> dict:
    q = ctx.query_params.get("q", "").strip()
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)

    raw_products = await fetch_nevotex_raw_products(q=q, limit=limit)
    candidates = normalize_nevotex_candidates(raw_products)

    return {
        "upholsteries": candidates,
        "upholsteries_pagination": {
            "has_more": False,
            "limit": limit,
            "offset": 0,
        },
    }
```

**Notes:**
- `_MAX_LIMIT = 20` (not 200 as for DB queries) because each call proxies to an external service.
- `_DEFAULT_LIMIT = 7` matches the tested curl example.
- `q` validation (required, non-empty) is enforced at the router layer. If `q` reaches the service empty, `fetch_nevotex_raw_products` will still run (Nevotex will return an empty or full catalog). The router must guard against this.
- `ctx.session` is not used. This is intentional — this query calls an external service, not the database.
- `ExternalServiceError` raised inside `fetch_nevotex_raw_products` propagates through `run_service` as a `DomainError` and is returned as a `502` via `build_err`.

---

### Step 5 — Add `origin: "database"` to `serialize_upholstery`

**File:** `app/beyo_manager/domain/upholstery/serializers.py` — modify `serialize_upholstery` only.

Change the return dict in `serialize_upholstery` to include `"origin": "database"` as the last key:

```python
return {
    "client_id": row.client_id,
    "name": row.name,
    "code": row.code,
    "image_url": row.image_url,
    "favorite": row.favorite,
    "list_order": row.list_order,
    "current_stored_amount_meters": available_stored_amount,
    "inventory_condition": inventory.inventory_condition.value if inventory is not None else None,
    "upholstery_category": {
        "id": category.client_id,
        "name": category.name,
        "image_url": category.image_url,
    } if category is not None else None,
    "origin": "database",
}
```

This affects both `list_upholsteries` and `get_upholstery` — all database-sourced upholstery responses gain the `origin` field. This is a non-breaking additive change.

---

### Step 6 — Add the router handler

**File:** `app/beyo_manager/routers/api_v1/upholsteries.py` — add one import and one route handler.

**Import to add** (top of file):

```python
from beyo_manager.services.queries.upholstery.list_nevotex_upholsteries import (
    list_nevotex_upholsteries,
)
```

**Route handler to add** — must be declared BEFORE the existing `@router.get("/{client_id}")` handler. Place it immediately after `route_list_upholsteries` and before `route_mark_upholsteries_favorite`, because `/external/nevotex` is a static path that would be captured by `/{client_id}` if declared later.

Per `09_routers.md`: _"Static paths and collection-level routes must always be declared before wildcard path-parameter routes."_

```python
@router.get("/external/nevotex")
async def route_list_nevotex_upholsteries(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(7, ge=1, le=20),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"q": q, "limit": limit},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_nevotex_upholsteries, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Route declaration order check** — the final order in `upholsteries.py` must be:

```
PUT    ""                          → route_create_upholstery
GET    ""                          → route_list_upholsteries
GET    "/external/nevotex"         → route_list_nevotex_upholsteries  ← NEW (static, before wildcard)
PATCH  "/favorite"                 → route_mark_upholsteries_favorite
GET    "/{client_id}"              → route_get_upholstery
PATCH  "/{client_id}"              → route_update_upholstery
DELETE "/{client_id}"              → route_delete_upholstery
PATCH  "/{client_id}/favorite"     → route_mark_upholstery_favorite
PATCH  "/{client_id}/list-order"   → route_update_upholstery_list_order
```

`/external/nevotex` and `/favorite` are both static sub-paths that must precede `/{client_id}`.

---

### Step 7 — Unit tests for the normalizer

**File:** `app/tests/unit/test_nevotex_normalizer.py` *(new)*

```python
from beyo_manager.services.infra.nevotex.normalizer import (
    normalize_nevotex_candidate,
    normalize_nevotex_candidates,
)


def test_normalize_nevotex_candidate_full():
    raw = {
        "productId": "1000401",
        "name": "Tyg Afrodite 2 Midnight ",
        "number": "1000402",
        "link": "/Default.aspx?ID=6301",
        "variantid": "VARGRP208_1000402",
        "image": "%2fFiles%2fImages%2fproduktbilder%2f1000402.jpg",
        "currency": "SEK",
        "stockState": "stock-icon--in",
    }
    result = normalize_nevotex_candidate(raw)
    assert result is not None
    assert result["client_id"] is None
    assert result["name"] == "Tyg Afrodite 2 Midnight"
    assert result["code"] == "1000402"
    assert result["image_url"] == "https://nevotex.se/Files/Images/produktbilder/1000402.jpg"
    assert result["favorite"] is None
    assert result["list_order"] is None
    assert result["current_stored_amount_meters"] == 0
    assert result["inventory_condition"] == "out_of_stock"
    assert result["upholstery_category"] is None
    assert result["origin"] == "nevotex"


def test_normalize_image_url_decode_and_absolutize():
    raw = {
        "name": "Tyg X",
        "number": "12345",
        "image": "%2fFiles%2fImages%2fproduktbilder%2f12345.jpg",
    }
    result = normalize_nevotex_candidate(raw)
    assert result["image_url"] == "https://nevotex.se/Files/Images/produktbilder/12345.jpg"


def test_normalize_skips_missing_name():
    raw = {"name": "", "number": "1000402", "image": "%2fFiles%2f1.jpg"}
    assert normalize_nevotex_candidate(raw) is None


def test_normalize_skips_missing_number():
    raw = {"name": "Tyg X", "number": "", "image": "%2fFiles%2f1.jpg"}
    assert normalize_nevotex_candidate(raw) is None


def test_normalize_skips_missing_image():
    raw = {"name": "Tyg X", "number": "1000402", "image": ""}
    assert normalize_nevotex_candidate(raw) is None


def test_normalize_nevotex_candidates_filters_malformed():
    products = [
        {"name": "Good", "number": "111", "image": "%2fa.jpg"},
        {"name": "", "number": "222", "image": "%2fb.jpg"},  # missing name
        {"name": "Also Good", "number": "333", "image": "%2fc.jpg"},
    ]
    results = normalize_nevotex_candidates(products)
    assert len(results) == 2
    assert results[0]["code"] == "111"
    assert results[1]["code"] == "333"


def test_normalize_nevotex_candidates_empty():
    assert normalize_nevotex_candidates([]) == []
```

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `/external/nevotex` captured by `/{client_id}` wildcard | Route must be declared before `/{client_id}` — enforced by Step 6 route order. Codex must verify the final order in the file. |
| Nevotex response shape changes | `fetch_nevotex_raw_products` validates that the top-level response is a list, and `normalize_nevotex_candidate` skips items missing required fields. Partial degradation instead of crash. |
| Nevotex URL or params change | Constants are centralized in `client.py` (`_NEVOTEX_SEARCH_URL`, `_HEADERS`, `params` dict). Single edit point. |
| `httpx.AsyncClient` not available in async context | `httpx` supports `AsyncClient` natively for async/await. FastAPI is async. No issue. |
| `origin` field breaks existing frontend | `origin` is an additive new key. No existing field is removed or renamed. Frontend must be updated to read `origin` when rendering card source badges, but no existing rendering should break. |
| Empty `q` reaching Nevotex API | `Query(..., min_length=1)` at the router layer raises `422` before the service is called. |
| Very large `limit` hammering Nevotex | `Query(7, ge=1, le=20)` at the router and `_MAX_LIMIT = 20` in the service cap all requests. |

---

## Validation plan

After implementation:

```bash
# 1. Smoke test the Nevotex route
curl -X GET 'http://localhost:8000/api/v1/upholsteries/external/nevotex?q=Tyg+Afrodite' \
  -H 'Authorization: Bearer <token>' | jq

# Expected: {"data": {"upholsteries": [...], "upholsteries_pagination": {"has_more": false, ...}}, "ok": true}
# Each upholstery item must have origin="nevotex", client_id=null, code=<number>, image_url="https://nevotex.se/..."

# 2. Verify existing database route still works with origin field
curl -X GET 'http://localhost:8000/api/v1/upholsteries' \
  -H 'Authorization: Bearer <token>' | jq '.data.upholsteries[0].origin'
# Expected: "database"

# 3. Verify missing q returns 422
curl -X GET 'http://localhost:8000/api/v1/upholsteries/external/nevotex' \
  -H 'Authorization: Bearer <token>'
# Expected: HTTP 422

# 4. Verify empty q returns 422
curl -X GET 'http://localhost:8000/api/v1/upholsteries/external/nevotex?q=' \
  -H 'Authorization: Bearer <token>'
# Expected: HTTP 422

# 5. Run unit tests
cd app && python -m pytest tests/unit/test_nevotex_normalizer.py -v
```

---

## Review log

- `2026-06-25`: Implemented the Nevotex adapter/query/route flow, added `origin` to database upholstery serialization, and validated with targeted unit tests plus `py_compile`.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Added `ExternalServiceError`, a Nevotex HTTP client, and a pure normalizer so the backend can proxy Nevotex search results and return them in the existing upholstery card shape as `origin: "nevotex"` candidates.
- Added `GET /api/v1/upholsteries/external/nevotex` with `q` validation and static-path placement before `/{client_id}` so FastAPI resolves the route correctly.
- Extended `serialize_upholstery` to include `origin: "database"` for existing internal upholstery responses.
- Validation completed with targeted `pytest` coverage for the normalizer and serializer plus `py_compile` on the touched modules; no live Nevotex HTTP smoke call was run in this task.
