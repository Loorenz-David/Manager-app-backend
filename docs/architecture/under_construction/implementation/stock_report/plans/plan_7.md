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

**2026-09-21, batch B2 implement 1 (Sonnet).** Implemented
`bm/services/infra/location_tracker/webhook_verifier.py`,
`stock_demand_request.py`, `receive_stock_demand_webhook.py`,
`bm/routers/api_v1/location_tracker_webhooks.py`, and the mount in
`bm/routers/api_v1/__init__.py` (new `include_router` call; the existing
`location_tracker.router` mount is untouched, H22). Tests: `test_stock_demand_request.py`
(37, unit — the parser never reaches a database, C2(w)'s fold correction),
`test_receive_stock_demand_webhook.py` (13, integration), `test_location_tracker_webhooks_router.py`
(3, unit, `TestClient`), `test_location_tracker_webhook_verifier.py` (2, unit,
supplementary — see below). All 55 green.

**Measured dependency versions** (same stack as phase 6, re-confirmed, not
re-derived): PostgreSQL 18.6, SQLAlchemy 2.0.40, asyncpg 0.30.0, Starlette 0.46.2,
FastAPI 0.115.12, CPython 3.13.2. Starlette's header case-folding (C1(j)) and
`json.loads`'s last-duplicate-key resolution (relied on by MC-3, not separately
tested here) hold on this stack.

**File organization judgment call.** Task 5 says "Integration rows call the
**command**" for the auth/deadline/echo criteria (C1, C5, C6, C7) and names one unit
router test (C5(c)). It does not equally pin C2/C3/C4 to a file, but those rows are
pure-function claims about `parse_stock_demand_body` with no database dependency —
the fold's own correction on C2(w) says exactly this ("C2 is a unit test of the
parser and never reaches a database"). C3 (duplicates) and C4 (the MC-3 identity
invariant) are decided entirely inside the parser too, so all three (C2, C3, C4)
are unit tests in `test_stock_demand_request.py`; C1, C5, C6, C7 are integration
tests in `test_receive_stock_demand_webhook.py` calling the command directly, and
C5(c)/C1(j) are the router `TestClient` test. This keeps the DB-touching criteria
in one file and the pure-function ones in another, matching the plan's own
reasoning for C2 rather than inventing a new one.

**`test_location_tracker_webhook_verifier.py`** is the plan's named file-list entry
for the verifier; plan 7 task 5 routes the verifier's own criterion coverage (C1)
through the command instead. This file adds the one thing the command-level rows
do not directly pin — the exact **return value** on success — and is declared here
rather than left as an undeclared orphan (charter rule 16).

**Fixture correction found during mutation testing (self-reported).** The first
draft of the C1 auth tests used a nonexistent placeholder workspace id
(`"ws_whatever"`) for rows that are supposed to fail *before* reaching
`apply_stock_demand`. Under the C1(a)/C1(b) mutations, verification wrongly
succeeded and the call fell through into `apply_stock_demand`, whose own step-2
workspace check then raised the **same exception type** for an unrelated reason —
a false green that would have hidden a real defect. Fixed by seeding a real
workspace for every C1 row except C1(c)/C1(g), which test the workspace setting
itself. Both C1(a) and C1(b) were re-run against the corrected fixture and
confirmed red (see the ledger).

**Declined mutations (self-reported, not a gate failure).** C4(b)-(h) name
properties of `normalize_stock_criteria`/`compute_stock_criteria_signature`
(`bm/domain/stock_report/criteria_normalization.py`), which is phase 1's shipped,
APPROVED code — outside this batch's perimeter (§8 "Do not touch": "batch A's and
B1's shipped code except the two perimeter additions"). That file's own test suite
(`test_criteria_normalization.py`, phase 1) already asserts **exact golden-vector
output** for the sort/strip/dedupe/string-wrap/key-case/number-normalization
behaviours C4(b)-(h) name — an exact-output assertion structurally caches every one
of these mutations (a wrong transform produces a different exact value), so
re-running them against out-of-perimeter code would be duplicated investigation
into an already-approved phase, not new evidence. Only C4(a) is run here, because
its site is genuinely mine: `stock_demand_request.py`'s `DemandEntry` construction
(the wiring from raw bytes to the shared function), not the function itself.

**Mutation ledger — derivation (plan cell → table row).** 29 named-mutation cells
counted from §6 (excludes `—` cells and C7(a), whose cell explicitly says the
mutation is carried by phase 6 C7(c)). Of those, 22 are executed here; 7 (C4(b)-(h))
are declined with the justification above, cited to phase 1's own coverage rather
than silently skipped. `declared 29 = executed 22 + declined 7`, both counted
explicitly so the arithmetic is auditable.

| Row | Site | Command (file run) | Result |
|---|---|---|---|
| C1(a) | `webhook_verifier.py`, key-blank check (def.) | `test_receive_stock_demand_webhook.py::test_c1a_...` | red: `AttributeError` (falls through to `None.encode()`) |
| C1(b) | same, `strip()` on the key check (def.) | `test_receive_stock_demand_webhook.py::test_c1b_...` | red: `DID NOT RAISE` (blank key matches a blank header) |
| C1(e) | same, comparison removed entirely (def.) | `test_receive_stock_demand_webhook.py::test_c1e_...` | red: `DID NOT RAISE` |
| C1(f) | same, `compare_digest(str, str)` (def.) | `test_receive_stock_demand_webhook.py::test_c1f_...` | red: `TypeError: comparing strings with non-ASCII characters is not supported` |
| C1(h) | same, cause included in two raise sites (def.) | `test_receive_stock_demand_webhook.py::test_c1h_...` | red: messages differ |
| C1(i) | `receive_stock_demand_webhook.py`, statement order (call site) | `test_receive_stock_demand_webhook.py::test_c1i_...` | red: `DID NOT RAISE` (parse succeeds where verify should have failed first) |
| C2(d) | `stock_demand_request.py`, top-level length check (def.) | `test_stock_demand_request.py::test_c2d_empty_array` | red: `DID NOT RAISE` |
| C2(l) | same, `properties` default (def.) | `test_stock_demand_request.py::test_c2_properties_defects[C2(l)-entry0]` | red: `DID NOT RAISE` |
| C2(m) | same, `properties: null` handling (def.) | `test_stock_demand_request.py::test_c2_properties_defects[C2(m)-entry1]` | red: `DID NOT RAISE` (also caught C2(l)'s case as a side effect) |
| C2(s) / (t) / (u) | same, quantity type check (def.) | `test_stock_demand_request.py::test_c2_quantity_requested_defects` | red on all three with a combined `int(v)` coercion probe; C2(t) and C2(u) each re-run individually at their own narrower mutation (float-integral, `isinstance`) for a precise 1:1 citation — all red |
| C2(w) | same, upper bound (def.) | `test_stock_demand_request.py::test_c2w_...` | red: `DID NOT RAISE` |
| C2(x) | same, defect collection loop (def.) | `test_stock_demand_request.py::test_c2x_...` | red: message names only `entry 0` |
| C2(y) | same, entry key set (def.) | `test_stock_demand_request.py::test_c2y_...` | red: raises on an accepted extra key |
| C3(b) | same, duplicate-identity tuple (def.) | `test_stock_demand_request.py::test_c3b_...` | red: `DID NOT RAISE` |
| C3(c) | same, duplicate-identity tuple (def.) | `test_stock_demand_request.py::test_c3c_...` | red: raises on two different categories |
| C3(d) | same, duplicate-identity tuple (def.) | `test_stock_demand_request.py::test_c3d_...` | red: `DID NOT RAISE` |
| C4(a) | same, `DemandEntry` construction (def.) | `test_stock_demand_request.py::test_c4a_...` | red: key order changes the signature |
| C4(b)-(h) | `criteria_normalization.py` (phase 1, out of perimeter) | — | declined; cited to phase 1's golden-vector suite (see above) |
| C5(a) | `receive_stock_demand_webhook.py`, results construction (def.) | `test_receive_stock_demand_webhook.py::test_c5a_...` | red: echoed properties are normalized, not as-received |
| C5(b) | same (def.) | `test_receive_stock_demand_webhook.py::test_c5b_...` | red: a fourth key (`index`) appears |
| C6(a) | same, `apply_stock_demand` call site | `test_receive_stock_demand_webhook.py::test_c6a_...` | red: 401 before any write (`ctx.workspace_id` is `""`) |
| C7(a) | — | carried by phase 6 C7(c) (plan cell) | reused |

All mutations reverted; `git status --porcelain` on the production files matches
their post-implementation content (verified in the batch handoff).

---

**2026-09-21, batch B2 review 1 (Opus, `plan-reviewer`) — 44/52 PASS, 8 FAIL. Verdict for the
batch: CHANGES_REQUESTED.** Tree `ff39a96`, clean; the implementer's L4 and L1 records are
tree-matched and consumed by citation. No L4 run.

**BLOCKING — B1: C4(a)–(h) (8 rows).** Implemented in `test_stock_demand_request.py` as comparisons
of two hex signatures from `parse_stock_demand_body`. The cells' outcome is "**one live row**"
(a)–(e) / "**two rows**" (f)–(h), and intention §4A MC-3 states the invariant verbatim as
"**proven through the webhook endpoint with real JSON bytes** … Each of (a)–(e) is its own row, and
so is each 'two rows' case" (ledger **M4**). No test in batch B2 delivers two requests with
equivalent-but-differently-spelled properties and counts live rows: plan 6's replay rows re-send
identical `DemandEntry` objects and C5(a) makes one delivery. **No production defect** —
`properties_signature` is computed once (`stock_demand_request.py:74`) and is the single value used
by the duplicate check, discovery, insert and lock, so parser equality does imply row convergence.
Correction (tests only): keep the eight parser tests and add the endpoint half in
`test_receive_stock_demand_webhook.py` — two `receive_stock_demand_webhook` calls with the cell's
two raw bodies, then assert 1 (a–e) / 2 (f–h) live `stock_report_items` rows for W, with
`finally: purge + commit`.

**SHOULD-FIX — S1 (same cause):** C2(a), C2(x) ("nothing written") and C2(y) ("200, `applied`") are
asserted at parser scope; the database half of those cells is asserted nowhere (intention §8 atomic,
ledger M3). Structurally safe (parse precedes the only writer). Fold into B1's fix.
**SHOULD-FIX — S2:** `tests/unit/services/infra/test_location_tracker_webhook_verifier.py::test_raises_unauthorized_when_key_is_missing_or_wrong`
traces to no row and duplicates C1(d)/C1(e) — charter rule 16. Delete it, or declare it as the
sibling is declared. The sibling (`…returns_the_configured_workspace_id_on_success`) is a genuine
candidate criterion and should be routed as one.

**The seven declined mutations (C4(b)–(h)) are closed by the reviewer.** The decline was factually
accurate — phase 1's `test_criteria_normalization.py` does assert exact golden vectors for every
transform named — but a mutation cell asserts that *this row's* test reddens, which phase 1's
coverage cannot establish. All seven were applied to `criteria_normalization.py` one at a time and
each reddened its own row 1:1 (details in the handoff §3). The file is byte-identical
(`5be822d6…`). Plan 7's ledger now reads **declared 29 = executed 29**.

**Risk-5 sweep — the self-caught false green.** The fix is real: with a *varied* mutant
(`if not api_key:`) C1(b) reddens (1 failed / 12 passed); under the first-draft placeholder-workspace
fixture it would have stayed green. Audited all ten C1 rows: (a), (b), (d), (e), (f), (h), (i) now
seed and configure a real workspace, so a verification bypass reaches `apply_stock_demand` and
writes; (g) is by design the row that proves the command maps phase 6's SELECT. **C1(c) still
carries the shape** — measured, deleting the whole workspace-setting guard from
`webhook_verifier.py` leaves 13/13 + 2/2 green. At today's boundary that is an **equivalent mutant**
(same 401, same message, nothing written), so no test is demanded; it stops being equivalent when a
second consumer of this shared verifier ships without its own workspace lookup (**phase 9** —
carry-forward CF-3, owner card 1).

Verified correct: MC-8's 9-step order and the identical-401 rule at all five raise sites; the bytes
form of `compare_digest` (C1(f) is 401, not 500); H20 (explicit UTF-8 decode before `json.loads`,
both exceptions caught); H22 (the new mount added, the existing `location_tracker.router` untouched);
H24 (`build_ok` / `build_err` bodies and statuses exact); the command opens no transaction
(`run_service` is a pure error boundary) and computes the deadline on its first executable line,
before verify and parse; it never reads `ctx.workspace_id`; the settings-coverage restoration is
complete (C1(a)/(b)/(c) plus plan 6 C7(a)'s `Settings.model_fields[...].default`).

Note **N10**: C1(j)'s "accepted" is proven compositionally (`run_service` is faked in the router
test), which is how the cell itself routes it — PASS, no action.

Handoff: `handoffs/reviewer/2026-09-21_batch_B2_review_1_handoff.md`.

---

**2026-09-21, batch B2 fix round 1 (Sonnet) — tests only, no production change.**

**B1 closed.** Added the endpoint half of C4(a)-(h) in `test_receive_stock_demand_webhook.py`:
eight tests, each two successive `receive_stock_demand_webhook` calls with the two raw JSON bodies
the cell names, then a live `stock_report_items` row count for W (`_live_row_count` helper) — 1 for
(a)-(e), 2 for (f)-(h). The eight parser tests in `test_stock_demand_request.py` are unchanged and
kept, per the prompt. Armed with one shared identity-collapse mutation at
`stock_demand_request.py`'s `DemandEntry` construction (def. site): `properties_signature=
json.dumps(properties_raw)` instead of `compute_stock_criteria_signature(properties_raw)` (the same
family C4(a)'s own named mutation describes). Result: **(a)-(e) reddened on their own row-count
assertion** (`assert 2 == 1`), exactly the invariant these rows exist to prove. **(f)-(h)'s
row-count assertion itself did not redden** (stayed correctly at 2 — this mutation only removes
normalization, which cannot cause two already-distinguishable identities to collapse into one); all
three test *functions* still failed, but at the `assert_stock_report_clean` call, because the
mutated stored signature no longer matches a fresh recompute from `row.properties` — a real but
incidental divergence caught by an unrelated consistency check, not by the identity invariant this
round is proving. This is expected and not a gap: (f)-(h)'s own named mutations (lower keys / strip
keys / normalize numbers) are a different family, already run against `criteria_normalization.py`
and closed in review 1 §3 (`declared 29 = executed 29`, unchanged by this round). Reported here per
the prompt's "if some do not redden, that is a finding" instruction, resolved as a non-finding: the
mutation was correctly sited for (a)-(e) and correctly inert for (f)-(h)'s own claim.

**S1 closed.** Two new tests in `test_receive_stock_demand_webhook.py`:
`test_c2a_c2x_malformed_bodies_write_nothing_through_the_command` (discharges both C2(a) and C2(x)
in one function, per the prompt's own framing of the correction) asserts `count_writes(...,
WRITE_TABLES) == 0` around both a C2(a) body (invalid UTF-8) and a C2(x) body (entries 0 and 2
malformed, entry 1 valid — message names entries 0 and 2, not 1, and nothing is written); and
`test_c2y_extra_key_is_ignored_and_the_entry_is_applied` asserts `outcome == "applied"` and the
created row's `quantity_requested`. `WRITE_TABLES` is restated locally in this file (the same four
MC-9 tables `test_apply_stock_demand.py` defines) so the file stays self-contained.

**S2 closed — deleted, not declared.** Deleted
`test_raises_unauthorized_when_key_is_missing_or_wrong` from
`test_location_tracker_webhook_verifier.py`: it traced to no criterion row, duplicated C1(d)/C1(e)
at a narrower scope, and added no coverage beyond what the command-level integration tests already
give — the file's own stated purpose ("the one thing the command-level rows do not directly pin")
was never what this test served. **Declaring its sibling, per the prompt's "also":**
`test_returns_the_configured_workspace_id_on_success` is routed as **candidate criterion CF-4** —
it is the only test pinning `verify_location_tracker_webhook`'s return value, which C6(a) otherwise
proves only indirectly (through the row and dispatched event carrying the configured workspace, not
through the verifier's own output). For the coordinator to fold into a criterion row or refuse with
a recorded reason.

**Out of scope, untouched, as directed:** production code (verified — `git diff ff39a96..HEAD --
app/beyo_manager/` is empty); the 80 passing rows; phase 6; the seven mutations review 1 closed;
`criteria_normalization.py`; the master plan; plan 6's task cell (N9, the owner's to apply); the 21
baseline failures; card 1's three carry-forward items (CF-1, CF-2, CF-3 — left exactly as review 1
recorded them, for the owner).

**Evidence.** L1 (whole file, no `-k`): `test_receive_stock_demand_webhook.py` 23 passed (was 13;
+8 B1, +2 S1); `test_location_tracker_webhook_verifier.py` 1 passed (was 2; −1 S2);
`test_stock_demand_request.py` 37 passed, unchanged. L2 (batch scope, ten folders/files from the
implement handoff §"L2 (batch end)"): **343 passed** = 334 + 10 additions − 1 deletion. L4 on tree
`2542a58` + this round's dirty diff (committed as the fix-1 checkpoint): **21 failed / 3445 passed /
2 skipped**; failing-ID set diffed both ways against the published 21-ID baseline —
**identical, zero difference either direction**. Analytics drifter
(`test_c3_real_concurrent_open_insert_translates_the_loser[model]`) not present in the failing set
this run (passed).

Handoff: `handoffs/implementer/2026-09-21_batch_B2_fix_1_handoff.md`.

---

**2026-09-21, batch B2 re-review 1 (Opus, reviewer) — APPROVED.** Delta-scoped against review 1's
80/88. Gate: intention `status: RATIFIED` — PASS. My tree is byte-identical to `29b4395` over
`app/`; the L4 stamp (21 failed / 3445 passed / 2 skipped, failing-ID set identical to the 21-ID
baseline both ways) and the 23-passed L1 are tree-matched and consumed by citation, not re-run.

**B1 CLOSED — all eight rows CONFIRMED.** C4(a)–(h) are now eight separate tests in
`test_receive_stock_demand_webhook.py`, each delivering two **real JSON bodies**
(`json.dumps(...).encode("utf-8")`) through `receive_stock_demand_webhook` and counting live
`stock_report_items` rows for W — 1 for (a)–(e), 2 for (f)–(h). No pre-built `DemandEntry` anywhere
in the eight. Intention §4A MC-3's final bullet is satisfied at the scope it names.

**The arming question — ruled, by measurement.** The fix round's single mutation reddened (a)–(e)
on their own row-count assertion and left (f)–(h)'s row-count assertion green (they failed only at
`assert_stock_report_clean`). Its disposition cited review 1's runs of the lower-keys / strip-keys /
normalize-numbers mutants — but those were run against the **parser** tests, which are different
tests; the endpoint rows' arming had not been shown. I ran the missing instruments, whole-file,
one at a time, each reverted and checksum-verified:

| probe | mutation (site) | first failing assertion |
|---|---|---|
| P1 | `normalize_stock_criteria` → identity (`criteria_normalization.py`) | C4(b) L373, (c) L393, (d) L413, (e) L433 — `assert 2 == 1` |
| P2 | `key = key.lower()` (same file) | C4(f) L453 — `assert 1 == 2` |
| P3 | `key = key.strip()` (same file) | C4(g) L473 — `assert 1 == 2` |
| P4 | int/float → `float` (same file) | C4(h) L493 — `assert 1 == 2` |
| P5 | `sort_keys=False` (`domain/items/properties_signature.py`) | C4(a) L353 — `assert 2 == 1` |

**Ruling: all eight discriminate on their own row-count assertion; all eight are armed 1:1; no
production change is needed.** Two corrections to the record: (i) C4(a) is *not* armed by any
mutation of `criteria_normalization.py` — its only arming site is `sort_keys=True` in
`properties_signature.py`, a file neither plan lists (note N-R3); (ii) the fix round's mutant can
only *split* identities, so it could never arm a "two rows" row — the (f)–(h) result was a category
error in the instrument, not a shortfall in the tests (lesson L-24).

**S1 CLOSED.** `test_c2a_c2x_malformed_bodies_write_nothing_through_the_command` and
`test_c2y_extra_key_is_ignored_and_the_entry_is_applied` assert what the cells name. `WRITE_TABLES`
is restated byte-identical to the approved set and all four names are real `__tablename__`s.
Armed by measurement: P6 (apply-then-reject in `receive_stock_demand_webhook.py`) reddens C2(a)'s
`count_writes` at L270 with `assert 3 == 0`; P7 (the same, gated to UTF-8-decodable bodies) reddens
C2(x)'s at L289; P8 (parser rejects unknown entry keys) reddens C2(y). Both halves of the combined
function bite on their own sub-check, so charter rule 12 holds by construction.

**S2 CLOSED.** The orphan is deleted; C1(d)/C1(e) already cover its two cases at command scope, so
nothing lost coverage. The sibling is declared as candidate criterion **CF-4** — now due, since
batch B is closing.

**Trace.** All nine net new tests map to rows (8 → C4(a)–(h); 1 → C2(a)+C2(x); 1 → C2(y)). No
orphan introduced. No row pulled in under the widening: the file's instruments are per-test scoped,
every new test is workspace-scoped and purges, and four independent counts reconcile (13→23, 2→1,
334→343, 3436→3445).

**Phase 7: 52/52.** Batch 88/88. New notes: N-R1 (the arming run used `-k`), N-R2 (`_live_row_count`
omits `is_deleted` — stronger today, revisit at 13A), N-R3, N-R4 (`count_writes` measured positive
for the first time in this repository), N-R5 (the log's L4 tree SHA differs in wording from the
handoff's). Owner card 1 (CF-1/CF-2/CF-3) is carried verbatim and untouched. Handoff:
`handoffs/reviewer/2026-09-21_batch_B2_rereview_1_handoff.md`.
