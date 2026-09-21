# Plan 7 — Demand endpoint: key auth, body validation, duplicates, identity invariant over real bytes, envelope

```
state: NOT_STARTED
phase: 7 of 15
depends_on: 6 (APPROVED)
projection: mandatory, NOT waivable (rule 17: Starlette header/body shapes, JSON decoder behaviour)
complex: no
```

## 1. Goal

The inbound boundary for demand: the verifier (settings → key → workspace), the raw-bytes parser
with MC-8's entry-defect tables and the duplicate-identity rule, the command that wires deadline →
verify → parse → `apply_stock_demand` → response, the router, and the M4 identity invariant proven
through the endpoint with real JSON bytes. **Not in this phase:** the write path itself (phase 6),
the processed webhook (phase 9).

## 2. Read first

1. `master_plan.md` §6.3, §6.4, §6.5 (`stock_demand_request.py`, `receive_stock_demand_webhook.py`,
   verifier), §6.6 (webhook route shape), §9 rules 5–6.
2. Intention §2.5, §8 (auth paragraph), §8.1, §8A, §8B MC-8 in full (the 9-step table, the 401
   rule, bytes in `compare_digest`, the workspace guard, the 422 body, both defect tables, success
   bodies), §4A MC-3 (invariant (a)–(e) "proven through the webhook endpoint with real JSON bytes"),
   §14C C3, C12, C19, C24, C36, U7, U19, U21.
3. Scanner v2 handoff §2, §3.1, §3.3, §3.4 (what the sender expects back; read-only).
4. Repo: `bm/routers/api_v1/connecteam_webhooks.py` (route shape),
   `bm/services/infra/connecteam/webhook_verifier.py` (precedent incl. the `str` defect not copied),
   `bm/routers/http/response.py`, `bm/services/run_service.py`,
   `app/tests/unit/test_shopify_webhooks_router.py:13-60` (raw-body router test shape).

## 3. Dependencies

Phase 6 APPROVED.

## 4. Files expected to change

New: `bm/services/infra/location_tracker/__init__.py` (if absent), `webhook_verifier.py`;
`bm/services/commands/stock_report/stock_demand_request.py`, `receive_stock_demand_webhook.py`;
`bm/routers/api_v1/location_tracker_webhooks.py`;
`app/tests/unit/services/infra/test_location_tracker_webhook_verifier.py`,
`app/tests/unit/services/commands/stock_report/test_stock_demand_request.py`,
`app/tests/integration/services/commands/stock_report/test_receive_stock_demand_webhook.py`,
`app/tests/unit/routers/api_v1/test_location_tracker_webhooks_router.py`.
Edited: `bm/routers/api_v1/__init__.py` (mount).

## 5. Tasks

1. `verify_location_tracker_webhook(headers)`: read both settings; either `None` or blank after
   `strip()` → raise (logged cause `unconfigured`); header lookup case-insensitive (`headers` is
   `dict(request.headers)` — Starlette lower-cases keys; look up `"x-api-key"`); missing → raise
   (`missing_header`); compare `hmac.compare_digest(provided.encode("utf-8"), configured.encode("utf-8"))`;
   mismatch → raise (`mismatch`). Returns the configured workspace id. Every raise is
   `LocationTrackerWebhookAuthError("Unauthorized.")`.
2. `parse_stock_demand_body(raw: bytes) -> list[DemandEntry]`: UTF-8 decode → `json.loads` → top-level
   list with ≥ 1 entry → per-entry shape per the MC-8 demand defect table (`type(v) is int` for the
   quantity, `0 ≤ v ≤ 2147483647`; `properties` must be a `dict`; unknown keys ignored) → collect
   **every** defect as `entry <i>: <what>` → duplicates by `(item_category_key, properties_signature)`
   → `entries <i> and <j> resolve to the same identity` → if any defect, raise
   `ValidationError("Malformed request: " + "; ".join(defects) + ".")`. Builds `DemandEntry` with raw
   and normalized properties.
3. `receive_stock_demand_webhook(ctx)`: `deadline = time.monotonic() + timeout_ms / 1000` **first
   line**; `workspace_id = verify_location_tracker_webhook(ctx.incoming_data["headers"])`;
   `entries = parse_stock_demand_body(ctx.incoming_data["raw_body"])`; `result = await
   apply_stock_demand(ctx.session, workspace_id=…, entries=…, now=ctx.now, deadline=…, timeout_ms=…)`;
   `await event_bus.dispatch(result.events)`; return `{"results": [{"itemCategory": raw,
   "properties": raw, "outcome": ...}]}` in request order. Never reads `ctx.workspace_id`.
4. Router: `POST /webhooks/stock-demand` exactly in the connecteam shape; mount at
   `/api/v1/location-tracker`, tag `location-tracker-webhooks`.
5. Tests first from the table. Integration rows call the **command** with
   `ServiceContext(identity={}, incoming_data={"raw_body": b"...", "headers": {...}}, session=db_session)`
   and assert the raised error's class, `http_status` and `message` (that is what `build_err`
   renders); one unit router test proves the route forwards raw bytes and headers and renders
   `build_ok`/`build_err` (C5(c)).

## 6. Criteria

`REQ(body_bytes, headers)` = the command call above with the two settings configured for W unless
the row says otherwise. "401" = raises `LocationTrackerWebhookAuthError` with `http_status 401` and
`message == "Unauthorized."`; "422" = raises `ValidationError` (`http_status 422`) whose message starts
`Malformed request: `. "nothing written" = W's four tables have the same row counts and the same
`quantity_requested` values as before (workspace-scoped).

| Row | Fixture / input | Exact outcome | Named mutation (site) | Trace |
|---|---|---|---|---|
| C1(a) | key setting `None`, valid header and body | 401; nothing written | fall through to parse | MC-8 step 2, M7 |
| C1(b) | key setting `"   "` | 401 | skip `strip()` check | MC-8 step 2 |
| C1(c) | workspace setting `None` | 401 | — | MC-8 step 2 |
| C1(d) | no `x-api-key` header | 401 | — | MC-8 step 3 |
| C1(e) | header `wrong` | 401 | remove the comparison entirely from `verify_location_tracker_webhook` (`webhook_verifier.py`, definition site) — return the configured workspace id as soon as the header is present → this row's 401 assertion reddens. (Swapping `compare_digest` for `==` is **inert on this row** — a wrong value is unequal either way — and is carried by C1(f), where the non-ASCII input makes the two forms diverge.) | MC-8 step 3 |
| C1(f) | header `"clé-non-ascii"` against an ASCII key | 401 (**not** 500) | compare `str` objects (`compare_digest(str, str)` raises `TypeError` on non-ASCII) | MC-8 bytes rule (C24) |
| C1(g) | workspace setting names a non-existent workspace | 401 | — (phase 6 C1(f) covers the SELECT; this row proves the command maps it) | MC-8 step 4 |
| C1(h) | rows (a), (d), (g) | the three error messages are byte-identical (`"Unauthorized."`) | include the cause in the message | MC-8 (U19) |
| C1(i) | header wrong **and** body `b"not json"` | 401, not 422 | parse before verify | MC-8 order (C19) |
| C1(j) | header key sent as `X-API-KEY` (through the router test, C5(c)) | accepted (Starlette lower-cases) | — | MC-8 step 3 |
| C2(a) | body `b"\xff\xfe"` | 422; nothing written | — | MC-8 step 5 |
| C2(b) | `b"{not json"` | 422 | — | MC-8 step 5 |
| C2(c) | `b"{}"` (object, not array) | 422 | — | MC-8 step 6 |
| C2(d) | `b"[]"` | 422 | accept empty → 200 | MC-8 (U21) |
| C2(e) | `["x"]` | 422 (`entry 0: must be an object`) | — | MC-8 whole-entry |
| C2(f) | `[1]` | 422 | — | MC-8 |
| C2(g) | `[null]` | 422 | — | MC-8 |
| C2(h) | `[[]]` | 422 | — | MC-8 |
| C2(i) | entry without `itemCategory` | 422 | — | MC-8 |
| C2(j) | `itemCategory: 5` | 422 | — | MC-8 |
| C2(k) | `itemCategory: "  "` | 422 | — | MC-8 |
| C2(l) | entry without `properties` | 422 | default to `{}` | MC-8 |
| C2(m) | `properties: null` | 422 | treat as `{}` | MC-8 (C3) |
| C2(n) | `properties: []` | 422 | — | MC-8 |
| C2(o) | `properties: "x"` | 422 | — | MC-8 |
| C2(p) | `properties: 1` | 422 | — | MC-8 |
| C2(q) | `properties: true` | 422 | — | MC-8 |
| C2(r) | entry without `quantityRequested` | 422 | — | MC-8 |
| C2(s) | `quantityRequested: "5"` | 422 | `int(v)` coercion | MC-8 |
| C2(t) | `quantityRequested: 5.0` | 422 | accept integral floats | MC-8 |
| C2(u) | `quantityRequested: true` | 422 (`type(v) is int`) | `isinstance(v, int)` → accepts bool | MC-8 |
| C2(v) | `quantityRequested: -1` | 422 | — | MC-8 |
| C2(w) | `quantityRequested: 2147483648` | 422 | drop the `v <= 2147483647` bound from `parse_stock_demand_body` (`stock_demand_request.py`, definition site) → the parser returns an entry instead of raising → `pytest.raises(ValidationError)` reddens. *Corrected at the fold: C2 is a **unit** test of the parser and never reaches a database, so the previous cell's "DB error (500)" names a consequence this row cannot observe.* | MC-8 |
| C2(x) | entries 0 and 2 malformed, 1 valid | 422 whose message names `entry 0` **and** `entry 2`; nothing written (entry 1 not applied) | stop at the first defect | MC-8 "names every offending entry", §8 atomic |
| C2(y) | entry with an extra key `"location": "LC1"` | 200, `applied` | reject unknown keys | MC-8 (U7) |
| C3(a) | two entries same category, same properties | 422 naming `entries 0 and 1` | — | MC-8 step 7, §8.1 |
| C3(b) | two entries, properties `{"wood_group": ["Teak", "Dark"]}` and `{"wood_group": ["dark", "teak"]}` | 422 (same identity after normalization) | compare raw dicts → 200 | MC-8 step 7, MC-3 |
| C3(c) | same properties, categories K and K2 | 200, both applied | key the duplicate check on `properties_signature` alone (drop `item_category_key` from the tuple), `stock_demand_request.py` (definition site) → these two entries collide → 422 instead of 200 → red | MC-8 |
| C3(d) | categories `"Sofas"` and `"sofas"` with identical properties | 422 (key is `lower(strip(name))`) | compare raw names | MC-8 step 7 |
| C4(a) | two deliveries: `{"a": ["x"], "b": ["y"]}` then `{"b": ["y"], "a": ["x"]}` (bytes in that order) | one live row | compute the identity from the **raw** dict's `json.dumps` instead of `compute_stock_criteria_signature(normalize_stock_criteria(raw))`, `stock_demand_request.py` (`DemandEntry` construction, definition site) → the two key orders produce different signatures → two rows → red | MC-3 invariant (a), M4 |
| C4(b) | `["teak", "dark"]` then `["dark", "teak"]` | one row | drop `sorted()` | MC-3 (b) |
| C4(c) | `["Teak"]` then `[" teak "]` | one row | drop strip/lower | MC-3 (c) |
| C4(d) | `["teak", "teak"]` then `["teak"]` | one row | drop dedupe | MC-3 (d) |
| C4(e) | `"teak"` then `["teak"]` | one row | drop the string-wrap | MC-3 (e) |
| C4(f) | `{"Wood_Group": ["teak"]}` then `{"wood_group": ["teak"]}` | two rows | lower keys | MC-3 "two rows" |
| C4(g) | `{" wood_group": ["teak"]}` then `{"wood_group": ["teak"]}` | two rows | strip keys | MC-3 |
| C4(h) | `{"n": 1}` then `{"n": 1.0}` | two rows | normalise numbers | MC-3 (not-understood values) |
| C5(a) | entries `[K new with `["Teak","Dark"]`, unknown category]` | `results` in request order: `[{itemCategory: "Dining Chairs", properties: {"wood_group": ["Teak","Dark"]} (as received), outcome: applied}, {itemCategory: "Bar Stools", properties: {...}, outcome: category_not_found}]`; the stored row's `properties` is `{"wood_group": ["dark","teak"]}` | echo the normalized form | MC-3 "echo as received", v2 §3.4 |
| C5(b) | any accepted request | every result has exactly the keys `itemCategory`, `properties`, `outcome` | add a fourth key (e.g. `"index"`) to each result dict in `receive_stock_demand_webhook.py` (definition site) → the exact-key-set assertion reddens | §8A |
| C5(c) | unit router test: `TestClient` POST `/api/v1/location-tracker/webhooks/stock-demand` with `content=b'[...]'`, header `X-API-KEY: k`, `run_service` faked | the command receives `incoming_data == {"raw_body": b'[...]', "headers": {..."x-api-key": "k"...}}` and `identity == {}`; success renders `{"data": {"results": ...}, "ok": true, "warnings": []}`; a faked `LocationTrackerWebhookAuthError` renders status 401 body `{"error": "Unauthorized.", "ok": false}` | — (wiring; calibration) | §8A envelope |
| C6(a) | valid request | the created row's `workspace_id == W` (the setting), events carry `W` | pass `ctx.workspace_id` instead of the verifier's return value into `apply_stock_demand`, `receive_stock_demand_webhook.py` (call site) → `ctx.workspace_id` is `""` on a webhook path, so step 2's workspace `SELECT` finds nothing and a 401 is raised before any write → the "created row's `workspace_id == W`" assertion reddens. *Corrected at the fold: no FK is ever touched on this path.* | MC-8 guard, §2.5 |
| C7(a) | `receive_stock_demand_webhook` run through `run_service`, with **`monkeypatch.setattr(apply_stock_demand, "time", SimpleNamespace(monotonic=lambda: 10**9))`** — the module *reference inside `apply_stock_demand`* is replaced, not `time.monotonic` itself. Patching `apply_stock_demand.time.monotonic` mutates the shared `time` module, so the command's own first-line `deadline = time.monotonic() + timeout_ms/1000` moves with it and the deadline can **never** be exceeded (it would also freeze the asyncio event-loop clock) | `run_service` outcome `success False`, `error.http_status == 503`; nothing written; no dispatch | — (phase 6 C7(c) carries the mutation) | MC-9 part 1, §14D D5 |

## 7. Notes

- Sizing: 52 criterion rows in 7 criteria; `complex: no`.
- C2 rows are one parametrized test; each id names its row letter.
- Rule 17 cells: Starlette header case-folding (C1(j)) and `json.loads` last-duplicate-key
  behaviour (MC-3 says the decoder resolves repeated keys) are library facts; projection confirms
  them on the installed Starlette/CPython and records the versions in the Review log.
- The 422 message is display text for Scanner's logs; tests assert the leading `Malformed request: `
  and the presence of each offending index, not the full sentence.

## 8. Review log

(empty)
