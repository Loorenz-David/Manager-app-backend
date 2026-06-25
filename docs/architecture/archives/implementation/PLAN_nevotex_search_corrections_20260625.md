# PLAN_nevotex_search_corrections_20260625

## Metadata

- Plan ID: `PLAN_nevotex_search_corrections_20260625`
- Status: `archived`
- Owner agent: `claude-sonnet-4-6`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T10:01:54Z`
- Related issue/ticket: —
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_nevotex_upholstery_search_20260625.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_nevotex_upholstery_search_20260625.md`

---

## Goal and intent

- **Goal:** Fix four verified defects in the Nevotex upholstery search implementation: one critical runtime bug, one logging gap, one constant duplication, and one missing test file.
- **Business/user intent:** A valid empty Nevotex search result currently returns HTTP 502 instead of an empty list. This breaks the selector UX for any query that finds nothing on Nevotex.
- **Non-goals:** New feature work, category derivation, pagination changes, any change to the normalizer shape or router handler.

---

## Scope

- **In scope:**
  - Remove `found_product_array` tracking from `client.py` — fix the critical empty-result bug
  - Add `logger.warning` to the `TimeoutException` handler in `client.py`
  - Extract `_NEVOTEX_BASE_URL` and `_NEVOTEX_SEARCH_URL` into a new `constants.py` module and update both `client.py` and `normalizer.py` to import from it
  - Add `tests/unit/services/infra/nevotex/test_client.py` with three focused tests covering the previously untested client error paths
  - Add one missing normalizer test for non-string field values

- **Out of scope:**
  - Any change to `normalizer.py` logic (it is correct as-is)
  - Any change to the router, query service, or serializer
  - Any change to existing passing tests

---

## Clarifications required

None. All defects are unambiguous.

---

## Acceptance criteria

1. `GET /api/v1/upholsteries/external/nevotex?q=<query_with_no_results>` returns HTTP 200 with `{"data": {"upholsteries": [], "upholsteries_pagination": {"has_more": false, "limit": 7, "offset": 0}}, "ok": true}` — not HTTP 502.
2. When Nevotex returns an empty JSON array `[]`, `fetch_nevotex_raw_products` returns `[]` without raising.
3. When all containers in the Nevotex response lack a `Product` key, `fetch_nevotex_raw_products` returns `[]` without raising.
4. When a `TimeoutException` occurs, a `logger.warning` is emitted before the `ExternalServiceError` is raised.
5. `_NEVOTEX_BASE_URL` is defined in exactly one place (`constants.py`). Neither `client.py` nor `normalizer.py` define it.
6. All five new tests in `test_client.py` pass.
7. The one new test in `test_normalizer.py` passes.
8. All previously passing tests continue to pass.

---

## Contracts and skills

### Read order

| Contract | Applied rule |
|---|---|
| `architecture/05_errors.md` | `ExternalServiceError` propagation — no change needed |
| `architecture/19_integrations.md` | Graceful degradation: "Return empty result" for empty external response |
| `architecture/15_testing.md` | Unit test isolation via mocking — no real HTTP calls in tests |

### File read intent

Permitted relational reads (what exists):
- `services/infra/nevotex/client.py` — to understand the exact lines being replaced
- `services/infra/nevotex/normalizer.py` — to understand the import being updated
- `tests/unit/services/infra/nevotex/test_normalizer.py` — to understand test conventions before adding to it

---

## Implementation plan

### Step 1 — Create `services/infra/nevotex/constants.py`

**File:** `app/beyo_manager/services/infra/nevotex/constants.py` *(new)*

```python
NEVOTEX_BASE_URL = "https://nevotex.se"
NEVOTEX_SEARCH_URL = f"{NEVOTEX_BASE_URL}/Default.aspx"
```

No other logic. Two constants only.

---

### Step 2 — Fix `client.py`: remove `found_product_array`, add timeout log, update constant import

**File:** `app/beyo_manager/services/infra/nevotex/client.py`

Replace the entire file with the corrected version. The three changes are:

1. Import `NEVOTEX_BASE_URL` and `NEVOTEX_SEARCH_URL` from `constants.py` — remove the module-level constant definitions.
2. Add `logger.warning(...)` before the `ExternalServiceError` raise in the `TimeoutException` handler.
3. Replace the `found_product_array` loop with a simple loop that silently skips containers without a valid `Product` list.

Full corrected file:

```python
import logging
from typing import Any

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.constants import NEVOTEX_SEARCH_URL

logger = logging.getLogger(__name__)

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


async def fetch_nevotex_raw_products(q: str, limit: int) -> list[dict[str, Any]]:
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
            response = await client.get(NEVOTEX_SEARCH_URL, params=params)
    except httpx.TimeoutException as exc:
        logger.warning("Nevotex search timed out for q=%r", q)
        raise ExternalServiceError("Nevotex search timed out.") from exc
    except httpx.RequestError as exc:
        logger.warning("Nevotex request error for q=%r: %s", q, exc)
        raise ExternalServiceError("Nevotex search request failed.") from exc

    if response.status_code != 200:
        logger.warning("Nevotex returned HTTP %s for q=%r", response.status_code, q)
        raise ExternalServiceError(
            f"Nevotex search returned unexpected status {response.status_code}."
        )

    try:
        containers = response.json()
    except ValueError as exc:
        logger.warning("Nevotex returned invalid JSON for q=%r", q)
        raise ExternalServiceError("Nevotex search returned a non-JSON response.") from exc

    if not isinstance(containers, list):
        logger.warning("Nevotex response is not a list for q=%r", q)
        raise ExternalServiceError("Nevotex search returned an unexpected response shape.")

    raw_products: list[dict[str, Any]] = []
    for container in containers:
        if not isinstance(container, dict):
            continue
        products = container.get("Product")
        if not isinstance(products, list):
            continue
        raw_products.extend(product for product in products if isinstance(product, dict))

    return raw_products
```

**What changed vs. the current file:**

| Line(s) | Before | After |
|---|---|---|
| `_NEVOTEX_BASE_URL` constant | Defined inline | Removed — imported from `constants.py` |
| `_NEVOTEX_SEARCH_URL` constant | Defined inline | Removed — imported from `constants.py` |
| `TimeoutException` handler | No warning | `logger.warning("Nevotex search timed out for q=%r", q)` added |
| Loop body | Tracks `found_product_array` flag, raises if False | Removed flag entirely; `if not isinstance(products, list): continue` silently skips |
| Post-loop check | `if not found_product_array: raise ExternalServiceError(...)` | Removed entirely |

The critical fix: `if not isinstance(products, list): continue` covers `products is None` (key absent), `products` is a non-list scalar, and any other unexpected type — all silently skipped. An empty `containers` list returns `[]` naturally because the loop body never executes.

---

### Step 3 — Update `normalizer.py`: import base URL from `constants.py`

**File:** `app/beyo_manager/services/infra/nevotex/normalizer.py`

Replace the module-level constant with an import:

```python
# Remove this line:
_NEVOTEX_BASE_URL = "https://nevotex.se"

# Replace with:
from beyo_manager.services.infra.nevotex.constants import NEVOTEX_BASE_URL as _NEVOTEX_BASE_URL
```

No other change to `normalizer.py`. The aliased import `as _NEVOTEX_BASE_URL` keeps the rest of the file identical — zero diff to `_absolutize_image` or any other function.

---

### Step 4 — Add missing client tests

**File:** `app/tests/unit/services/infra/nevotex/test_client.py` *(new)*

```python
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products


def _mock_response(status_code: int, json_body) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_body
    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_nevotex_response_returns_empty_list():
    """Nevotex returning [] (no results) must produce an empty list, not a 502."""
    with patch(
        "beyo_manager.services.infra.nevotex.client.httpx.AsyncClient",
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, []))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("query with no results", limit=7)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_containers_without_product_key_returns_empty_list():
    """Containers missing the Product key must be silently skipped, not raise."""
    containers = [
        {"template": "SomethingElse", "id": "abc"},
        {"template": "AnotherThing", "id": "def"},
    ]
    with patch(
        "beyo_manager.services.infra.nevotex.client.httpx.AsyncClient",
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, containers))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("q", limit=7)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_raises_external_service_error():
    with patch(
        "beyo_manager.services.infra.nevotex.client.httpx.AsyncClient",
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_class.return_value = mock_client

        with pytest.raises(ExternalServiceError, match="timed out"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_200_response_raises_external_service_error():
    with patch(
        "beyo_manager.services.infra.nevotex.client.httpx.AsyncClient",
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(503, None))
        mock_client_class.return_value = mock_client

        with pytest.raises(ExternalServiceError, match="503"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_products_are_flattened_across_containers():
    """Products from multiple containers are combined into one flat list."""
    containers = [
        {"Product": [{"name": "A", "number": "1", "image": "%2fa.jpg"}]},
        {"Product": [{"name": "B", "number": "2", "image": "%2fb.jpg"}]},
    ]
    with patch(
        "beyo_manager.services.infra.nevotex.client.httpx.AsyncClient",
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, containers))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("q", limit=7)

    assert len(result) == 2
    assert result[0]["name"] == "A"
    assert result[1]["name"] == "B"
```

---

### Step 5 — Add missing normalizer test for non-string field values

**File:** `app/tests/unit/services/infra/nevotex/test_normalizer.py` *(append one test)*

Add this test at the end of the existing file:

```python
@pytest.mark.unit
def test_normalize_nevotex_candidate_handles_non_string_field_values() -> None:
    """Non-string values in name/number/image must not crash — product is skipped."""
    assert normalize_nevotex_candidate({"name": 123, "number": "1000402", "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": None, "image": "%2f1.jpg"}) is None
    assert normalize_nevotex_candidate({"name": "Tyg X", "number": "1000402", "image": []}) is None
```

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `as _NEVOTEX_BASE_URL` aliased import looks unusual | The alias keeps all downstream code in `normalizer.py` unchanged. It is cleaner than a find-replace on `_NEVOTEX_BASE_URL` vs. `NEVOTEX_BASE_URL` across the file. |
| `httpx.AsyncClient` async context manager mocking is verbose | The mock pattern in Step 4 is explicit about `__aenter__`/`__aexit__` to match the `async with httpx.AsyncClient(...) as client:` usage in the production code. An alternative is `respx` or `pytest-httpx` if already available; use those if present in `requirements-dev.txt`. |
| Removing `found_product_array` raises concern that a fully malformed response goes undetected | The `not isinstance(containers, list)` check on the top-level response (line unchanged) still catches a non-list Nevotex response. The `not isinstance(products, list)` guard on the per-container level catches a malformed `Product` field. Only the "no containers have a Product key at all" case changes — and that is now correctly treated as empty, not as an error. |

---

## Validation plan

```bash
# Run the new client tests
cd app && ./.venv/bin/python -m pytest tests/unit/services/infra/nevotex/ -v

# Run the full unit suite to confirm no regressions
cd app && ./.venv/bin/python -m pytest tests/unit/ -v

# Compile-check all touched files
cd app && ./.venv/bin/python -m py_compile \
  beyo_manager/services/infra/nevotex/constants.py \
  beyo_manager/services/infra/nevotex/client.py \
  beyo_manager/services/infra/nevotex/normalizer.py

# Verify base URL is no longer duplicated
grep -rn "_NEVOTEX_BASE_URL\s*=" app/beyo_manager/services/infra/nevotex/
# Expected: zero matches (the constant is now only in constants.py as NEVOTEX_BASE_URL)
```

---

## Review log

- `2026-06-25`: Fixed the empty-result Nevotex client bug, centralized constants, added timeout logging, and validated with focused unit tests plus `py_compile`.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation summary

- Removed the `found_product_array` requirement from the Nevotex client so valid empty results now return `[]` instead of raising `ExternalServiceError`.
- Added timeout warning logging and extracted the shared Nevotex URL constants into `services/infra/nevotex/constants.py`.
- Added the missing client test file and one additional normalizer guard test for non-string required-field values.
- Validation completed with focused Nevotex unit tests and `py_compile`; no live HTTP smoke call was run in this task.
