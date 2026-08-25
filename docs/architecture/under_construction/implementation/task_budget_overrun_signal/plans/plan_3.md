# Plan 3 — The route, the four HC-2a artifacts, and the frontend handoff

```
plan: plan_3
project: task_budget_overrun_signal
projection_gate: WAIVABLE — coordinator's call (route wiring, hand-maintained docs, no derivation); recommended justification: "no rule-6 mechanism; every payload figure was proven in phases 1–2"
```

## 1. Goal

Mount `GET /api/v1/item-economics/tasks/budget-signals` (master plan §6.5) gated
`ADMIN, MANAGER`, declared immediately after `route_get_task_budget_allocations`; make the
**exactly four** HC-2a artifacts true again (mirror table +1 row and `26 → 27` including the
function name; router role test `_ROUTES` +1; `routers/README.md` row + detail section;
the router module); publish the dated `to_frontend` handoff answering the frontend's five
open questions and carrying the three inventory corrections; record the endpoint node in
the graph.

**Explicitly NOT in this phase:** no change to any service, serializer or domain module; no
worker/seller variant; no `docs/domains/item_economics/*` edit (master plan §5 exclusion);
no edit to either `from_frontend` file; no `_ALL_ROLE_ROUTES` change.

## 2. Read first

- Master plan §§5 (the excluded documentation rule and why), 6.1, 6.5, 6.6, 8 (phase-3 graph
  delta), 9 (rules 1, 6, 8, 10), 10 (docs guard).
- Intention header (confirm `RATIFIED`), §1 **HC-2a in full**, HC-3, HC-5, §1A (M4, M6),
  §2.4A, §4A.3, §5.1–5.3, §6 (D9, D10 in plain words), §7.1, §7.2, §7.4, **§7A.1, §7A.3,
  §7A.4, §7A.5, §7A.6 in full**, §8 (must-ship 5), §10 decision index, §11 S2/S9.
- `plans/plan_1.md` §6 C5–C6 and `plans/plan_2.md` §6 C4–C8 (the measured figures the
  handoff quotes) and both Review logs.
- The frontend's request `docs/handoff/from_frontend/HANDOFF_TO_BACKEND_task_budget_overrun_signal_20260823.md`
  — the five open questions and the nine acceptance criteria you are answering.
  `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md` (headings) and
  `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md` (register).
- Code, at source: `routers/api_v1/item_economics.py:1-40` (imports), `:123-134` (`_ctx`,
  `_run`), `:346-360` (the sibling route; declare yours directly after `:360`);
  `tests/unit/routers/test_phase9_item_economics_route_mirror.py` whole file (`:33`, `:60`,
  `:115-128`); `tests/unit/routers/api_v1/test_item_economics_router.py:14-56, :101-150, :186`;
  `tests/unit/routers/api_v1/test_budget_division_routes.py:54-115` (the over-cap and
  at-cap shapes to mirror); `routers/README.md:1-8` (header), `:79` (the sibling's Quick
  Index row), `:1648-1700` (the sibling's detail section — mirror its table format);
  `tests/unit/docs/test_item_economics_handoff_accuracy.py:24-35, :226-233` (the rglob sweep
  your handoff is subject to); `routers/http/response.py`.

## 3. Dependencies

Phase 2 **APPROVED**. Gate: intention header `RATIFIED`; projection routed or the waiver recorded.

## 4. Files expected to change (derived: 4 MOD + 3 NEW = 7)

| File | Kind |
|---|---|
| `app/beyo_manager/routers/api_v1/item_economics.py` | MOD — HC-2a artifact 4: one import (`get_task_budget_signals`), one route |
| `app/beyo_manager/routers/README.md` | MOD — HC-2a artifact 2: Quick Index row after `:79`; detail section after `:1700` |
| `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` | MOD — HC-2a artifact 1: `_EXPECTED_ROUTES` row, `26 → 27` twice, function renamed |
| `app/tests/unit/routers/api_v1/test_item_economics_router.py` | MOD — HC-2a artifact 3: `_ROUTES` row only |
| `app/tests/unit/routers/api_v1/test_budget_signals_route.py` | NEW |
| `app/tests/unit/docs/test_budget_signals_handoff.py` | NEW |
| `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_<YYYYMMDD>.md` | NEW |

## 5. Ordered tasks

0. **Task 0.** Derive the mirror count from the table (`len(_EXPECTED_ROUTES)` before = 26,
   verified at `:127`), the README row count for the prefix (`grep -c "| /api/v1/item-economics/" README.md`
   before = 26), and the `_ROUTES` length before (23). Write the trace map. Confirm
   `git diff --name-only <phase-2 gate SHA>..HEAD -- app/` is empty on entry.
1. Write `test_budget_signals_route.py` from §6 C1, C3, C4(d); add the `_ROUTES` row (C2);
   add the mirror row, counts and rename (C4).
2. Add the import and the route (§6.5). Add the README row and the detail section (ten
   `data.budget_signals[].<field>` rows, all `Required: Yes`, types `string`/`integer`, the
   two enums in the Enum column; `422` with the `detail[]` shape as the sibling documents).
3. L1 green on the four test files; every §6.1 mutation run and reverted.
4. Write the handoff (§7) **after** step 3, quoting only measured figures; then
   `test_budget_signals_handoff.py` from §6 C6; run the docs guard (`tests/unit/docs/`,
   67 → 67 + your new tests).
5. L2, then one L4 stamp, ID-diffed. Handoff + graph delta (one `endpoint` node,
   `accepts` → the projection) + owner layer.

## 6. Tests / acceptance criteria

### C1 — mounting and precedence · trace **§7A.4, §7.1 → M6**

Home: `test_budget_signals_route.py`, using `test_item_economics_router.py`'s `_client`
pattern (a `FastAPI()` with the router, `get_db`/`get_jwt_claims` overridden, `run_service`
monkeypatched to a fake that records `(function, context)` and returns success).

| Row | Assertion | Expected |
|---|---|---|
| C1(a) | `GET /api/v1/item-economics/tasks/budget-signals?task_ids=tsk_1&task_ids=tsk_2` as `manager` | `200`; `calls[0][0] is item_economics.get_task_budget_signals`; the recorded context's `query_params == {"task_ids": ["tsk_1", "tsk_2"]}` |
| C1(b) | over `item_economics.router.routes` paths in declaration order | `index("/tasks/budget-signals") == index("/tasks/budget-allocations") + 1`, and both indices are smaller than the index of **every** route whose path starts with `/tasks/{` |

### C2 — the authorization boundary · trace **§7A.5, HC-3 → M6**

Home: `test_item_economics_router.py` via the `_ROUTES` row (HC-2a artifact 3) — the two
parametrized tests at `:101` and `:112` then generate four ids for the new route.

| Row | Assertion | Expected |
|---|---|---|
| C2(a) | `admin`, `manager` | `200`, `len(calls) == 1` |
| C2(b) | `worker`, `seller` | `403`, `calls == []` — the service is never entered |
| C2(c) | `test_router_route_pairs_match_the_authoritative_route_table` | green with the row in `_ROUTES` and **absent** from `_ALL_ROLE_ROUTES` |

### C3 — the over-cap identity and the two 422 envelopes · trace **§7A.3, §7A.1 → M4**

Home: `test_budget_signals_route.py`, with a fake `run_service` that **invokes** the service
(as `test_budget_division_routes.py:54-76` does — the cap raises before any query, so a stub
session suffices).

| Row | Assertion | Expected |
|---|---|---|
| C3(a) | 51 `task_ids` as `manager` | `422`; body `{"error": <str>, "ok": False}` with `error.startswith("BUDGET_SIGNALS_TOO_MANY_TASK_IDS:")`; no `detail` key |
| C3(b) | 50 `task_ids` | `200`; the service was entered exactly once |
| C3(c) | no `task_ids` parameter at all | `422`; body has `detail` (a list) and **no** `error` key; the service was never entered |

### C4 — the four HC-2a artifacts, and no fifth · trace **§7A.6, HC-2a → M6**

| Row | Home | Assertion | Expected |
|---|---|---|---|
| C4(a) | mirror test `test_readme_quick_index_mirrors_every_shipped_route` | green | the README row `\| GET \| /api/v1/item-economics/tasks/budget-signals \| item-economics \| route_get_task_budget_signals_api_v1_item_economics_tasks_budget_signals_get \|` present |
| C4(b) | `test_router_source_matches_the_hand_written_route_and_role_set` | green | the table row carries `_ADMIN_MANAGER` |
| C4(c) | `test_the_registry_ships_twenty_seven_routes` (renamed) | both assertions `== 27` | True (derived: 26 + 1) |
| C4(d) | `test_budget_signals_route.py` reads `routers/README.md` | the heading `### GET /api/v1/item-economics/tasks/budget-signals` exists once and is followed (before the next `### `) by the ten `data.budget_signals[].<field>` rows, each `Required: Yes`, with `budget_state` and `currency` typed `string` and the seven numerics `integer` | True |

### C5 — collateral: nothing else moved · trace **HC-2, HC-2a → M6** (gate evidence, not a test)

| Row | Evidence | Expected |
|---|---|---|
| C5(a) | the closing L4 stamp | failing-ID set **∅/∅** against the 21-ID baseline; the sibling files `test_budget_allocations_query.py`, `test_production_time_query.py`, `test_price_scenario_query.py`, `test_budget_status_filter_spec.py`, `test_live_clock_goldens.py`, `test_budget_division_routes.py` all green — these are M6's automated proxy (charter rule 1 exemption: a gate check) |
| C5(b) | reviewer's perimeter check `git diff --name-only <phase-2 gate>..<phase-3 checkpoint>` | exactly the seven paths of §4, and `docs/architecture/.../task_budget_overrun_signal/**` |

### C6 — the `to_frontend` handoff · trace **§8 must-ship 5; §4A.3, §7A.1, §7A.3 (the three corrections); §5.3, §6 (D9, D10), §2.4A, §7.4, §4.1 → M4 (documentation of the served contract)**

Home: `tests/unit/docs/test_budget_signals_handoff.py`. The file is located by
`glob("docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_*.md")`.

| Row | Assertion | Expected |
|---|---|---|
| C6(a) | the glob | **exactly one** match; its `## Metadata` names the intention path and this plan |
| C6(b) | the three corrections, each a pinned sentence under a heading `## Corrections to the request` | present verbatim: (1) *"`over_cost_minor` may be `0` while `over_seconds > 0` — acceptance criterion 2 is not satisfiable as written"*; (2) *"N rows means one row per **distinct** visible requested id"*; (3) *"the route has two different 422 envelopes"* |
| C6(c) | five headings `### Open question 1` … `### Open question 5` | each present, each followed by a non-empty answer paragraph |
| C6(d) | the D9/D10 paragraph under `## What changed since your request` | contains *"a negative budget before any work is a forecast"* and *"no work left to come means no forecast"* and *"production-time shows no amber on an infeasible task"* |
| C6(e) | the contract section | contains the literal ten-field table header row, the four `budget_state` members and the four `currency` members exactly as master plan §6.6, the sentence *"ADMIN and MANAGER only; WORKER and SELLER receive 403"*, *"rows are ordered by `task_id` ascending"*, and *"no server timestamp is served"* |
| C6(f) | `test_retired_inline_refusal_identity_is_absent_from_live_sources` (pre-existing rglob) | still green |

### 6.1 Named mutations — the closed set (9)

| # | Mutation (site) | Must redden |
|---|---|---|
| MUT-01 | move the new decorator below `route_get_task_price_scenario` | C1(b) — **C1(a) stays green today** (no bare `/tasks/{param}` route exists); record that it does |
| MUT-02 | `require_roles([ADMIN, MANAGER, WORKER, SELLER])` | C2(b) |
| MUT-03 | add the route to `_ALL_ROLE_ROUTES` as well | C2(b) via the all-roles test's `200` expectation for `worker` (and C2(c) if the union no longer matches) |
| MUT-04 | in the service (temporarily, for this probe only): `_MAX_TASK_IDS = 51` | C3(a) |
| MUT-05 | `task_ids: list[str] \| None = Query(None)` | C3(c) |
| MUT-06 | delete the README Quick Index row | C4(a) |
| MUT-07 | table row role `_ALL_ROLES` | C4(b) |
| MUT-08 | delete one field row from the README detail section | C4(d) |
| MUT-09 | delete correction (2) from the handoff | C6(b) |

## 7. The handoff — content the coordinator's prompt will require (refine at prompt time)

Path and headings per the template. Sections and what each must say, with the figures to
quote from the phase-1/2 ledgers:

1. **Metadata** — related documents: the 2026-08-23 request; `HANDOFF_TO_FRONTEND_worker_step_card_budget_allocations_20260822.md` (unchanged); the intention path.
2. **Backend delivery context** — one endpoint, additive; `budget-allocations` unchanged; roles.
3. **What changed since your request** — S2 (both pairs populated; `budget_state` names the headline, `over` wins; on every `over` row `projected_over_seconds ≥ over_seconds`), D3 (`no_currency`), HC-3 (no worker/seller variant; 403), D9 and D10 in plain words, §2.4A (production-time shows no amber on an infeasible task until it converges).
4. **Corrections to the request** — the three pinned sentences of C6(b), each with its reason (§4A.3's table: at `3.7500` the first eight seconds cost `0`; duplicates collapse in the `IN` clause; FastAPI's own `{"detail": [...]}` when `task_ids` is absent vs `{"error": "...", "ok": false}` over the cap).
5. **Open questions answered** — five headings: Q1 both populated (§5.3); Q2 hysteresis belongs to the future event, not this read (§7.4); Q3 the 60-second floor gates the state only, raw seconds always served (§3.3); Q4 convergence is possible but not scheduled, and is no longer a zero-behaviour-change swap for infeasible tasks (§2.4A); Q5 the rate is per task, resolved at commit from the evaluation snapshot (§4.1).
6. **Interface details** — the ten-field table (master plan §6.6 types), the enums, request shape (`task_ids` repeatable, cap 50, over-cap identity prefix), silent omission, ordering, no server "now", polling unchanged, the between-poll extrapolation rule (HC-5) and what `cost_per_worker_minute_ten_thousandths` is for.
7. **Validation notes** — the measured rows: `136 s → 9`, `8 s → 0` at `3.7500`; the `59/60` boundary; the untouched infeasible task (`-12.50` → `projected_over 750`, `over` after one worked second).
8. **Trace links** — the intention, this plan, the sibling handoffs.

Never edit the 2026-08-23 request or the 2026-08-24 worker-time-pressure file. Do not name
the retired inline-price identity. Do not add the path to `docs/domains/item_economics/*`.

## 8. Notes

- The mirror test's **function name** is part of artifact 1 (§7A.6); leaving
  `twenty_six` with a `27` assertion ships a lie in an identifier.
- `_ALL_ROLE_ROUTES` must **not** gain the row; the all-roles test at `:125` would then expect
  a `200` for `worker` and fail — which is the fixture that proves the gate (MUT-03).
- MUT-04 edits a phase-2 file for the duration of one probe only; revert and md5-verify.
- Graph delta: `endpoint-item-economics-task-budget-signals`, `accepts` → the phase-2
  projection; evidence span on `route_get_task_budget_signals` in the closing tree.

## 9. Review log

*(append-only)*

- **Projection waiver recorded (2026-08-25).** The coordinator waived this plan's waivable
  projection gate: it wires the approved Phase-2 service into one route and its four HC-2a
  artifacts, plus the required frontend handoff; it introduces no new derivation or rule-6
  mechanism. The owner also directed that no further projection sessions be run. Proceed to
  implementation under the full criteria and review gates.

- **Implementation closeout (2026-08-25, Codex).** Implemented the manager-only route directly
  after the all-role budget-allocation route, moved the fixed batch pair ahead of every
  parameterized task route to satisfy C1(b), updated the four HC-2a artifacts, and published
  `HANDOFF_TO_FRONTEND_task_budget_overrun_signal_20260825.md`. The nine declared mutations
  all reddened their named assertions and were reverted. L1 targeted evidence is 128 passed;
  L2 radius is 653 passed; docs guard is 70 passed; the one final L4 stamp and its 21-ID delta
  are recorded in the implementer handoff. Graph closeout added one endpoint and two links in
  one batch; no existing graph item was promoted, rejected, edited, or removed.

- **First review dispatched (2026-08-25, coordinator).** Review the full Phase 3 criteria and
  semantic authorities. Reconcile the implementation evidence against checkpoint `c83c815` and
  evidence-record commit `032b0d3`; specifically determine whether the endpoint graph delta,
  currently mixed with unrelated unstaged `.archgraph/architecture.yml` work, has acceptable
  phase provenance and is ready for an approval-gate commit.

- **Review round 1 (2026-08-25, Claude Opus 5 — CHANGES_REQUESTED).** Tree `032b0d3`, `app/` clean
  and byte-identical to checkpoint `c83c815`; dirty-tree digest `974275ab…`. Perimeter
  `18f774f..c83c815` is exactly the seven §4 paths plus tracker, this Review log and the implementer
  handoff — C5(b) holds. One closing L4 (`-m 'not e2e'`) → **21 failed / 2800 passed / 1 skipped**,
  IDs compared member-by-member against the published durable set: **∅/∅**; all six C5(a) sibling
  files green.
  **SF1 (should-fix, the only fix required).** C4(d) requires each of the ten
  `data.budget_signals[].<field>` README rows to be `Required: Yes` with the seven numerics typed
  `integer`; `test_budget_signals_readme_detail_documents_the_ten_field_contract` asserts neither —
  it pins only the two string rows as literals and uses `count("| Yes |") >= 10`, which the section
  satisfies 17 times. Mutation `over_seconds: integer|Yes → string|No` in `routers/README.md` left
  **5 passed**. Correction: assert the exact cell trio per field; fix round runs two mutations (one
  type, one `Required`, on different rows — rule 12).
  **N1.** The pre-existing `budget-allocations` decorator was relocated above the parameterized
  evaluation routes to satisfy C1(b). Required by the plan, declared by the implementer,
  behaviourally inert (no `/tasks/{…}` route can match a two-segment fixed path). Not a finding —
  but intention HC-2a ("by addition only, each reverted by one edit") and §7A.4 ("ahead of every
  parameterized `/tasks/...` **GET**") no longer describe the tree. **Owner card 1.**
  **N2.** C4(a) names the operation-id column; its home test matches method and path only. Verified
  correct independently: 27/27 README operation ids match the generated OpenAPI.
  **N3.** C2(c) compares the *union* of `_ROUTES` and `_ALL_ROLE_ROUTES`, so it cannot see a
  double-listed row; the exclusion is enforced by the all-roles test (MUT-03's four reds).
  **N4.** MUT-01 tripped C1(b)'s first assertion, so its precedence sub-check was unmutated. Closed
  here by variation — fixed pair moved back below the evaluation routes with adjacency preserved:
  red at `assert 19 < 16`.
  **N5.** C6(e) guards the frontend handoff's ten-field table by its header row only; deleting three
  of the ten rows left **3 passed**. Plan defect, not an implementation one — routed as a candidate
  criterion, with C6(a)/C6(b) heading-locality as the same shape.
  **N6.** The implementer handoff's prose names 22 IDs for the 21-ID baseline (one test counted
  twice); the measured set is correct.
  All four probes reverted and checksum-verified; no graph tool called and no graph state touched.
  Full detail: `handoffs/reviewer/20260825_plan_3_review_round_1.md`.

- **Coordinator disposition after review r1 (2026-08-25).** The owner approved card 1's
  recommendation: keep the fixed `budget-allocations` relocation and record the stronger route
  ordering. Intention round 13 amends HC-2a and §7A.4 as a RATIFIED record-precision correction;
  it changes neither payload nor current dispatch. **SF1 proceeds to a one-file fix round:**
  C4(d)'s test must assert every README field's exact type and `Required: Yes` cell, with the
  reviewer's two distinct mutations. N2 (operation-id guard), N3 (union observation), N4
  (sequential-assertion mutation coverage), N5 (handoff-table candidate criterion), and N6
  (historical handoff prose count) are recorded lessons only. They do not expand this closing
  fix or authorize alteration of the published handoff.

- **Fix round 1 closeout (2026-08-25, Codex).** SF1 is closed in the sole allowed implementation
  file, `app/tests/unit/routers/api_v1/test_budget_signals_route.py`: C4(d) now asserts the exact
  `string|Yes` cell for `task_id`, `budget_state`, and `currency`, and the exact `integer|Yes`
  cell for each of the seven numeric fields. The two required README mutations (numeric type and
  a different numeric Required marker) both reddened this test and were reverted to checksum
  `e23b93f8b17cb1d9034383a255254e81ec00f1f48b53a7cec6a1697e90db6620`. L1 is 13 passed; the
  single closing L4 and its durable 21-ID delta are recorded in the fix handoff. No production,
  README, frontend handoff, or graph state changed; N2–N6 remain non-blocking lessons.

- **Re-review dispatched (2026-08-25, coordinator).** Delta scope is SF1 and the sole committed
  test-file change in checkpoint `709fe7c`; review round 1's route, handoff, graph-provenance,
  and non-blocking-note dispositions are settled. The fix handoff's L4 digest intentionally
  excludes dirty paths, so it is not a complete charter tree identity; the re-review takes the
  one authoritative closing L4 stamp on its actual handover tree.

- **Re-review round 1 (2026-08-25, Claude Opus 5 — APPROVED).** Perimeter `032b0d3..709fe7c` is
  exactly two paths — the sole allowed test file and the fix handoff; no production, README,
  frontend-handoff or `.archgraph/` path. Tree `709fe7c` with `git diff -- app/` **empty**
  (`e3b0c442…b855`, the empty-string digest), so the tested source is byte-identical to the
  checkpoint; full tracked-diff digest `51d65ecf…`; dirt confined to project docs plus pre-existing
  `.archgraph`/anchor-observation work. README sha256 `e23b93f8…6620` at entry and exit.
  **SF1 CLOSED.** C4(d) now asserts one exact cell per field. Derived, not transcribed: the test's
  AST gives 3 string + 7 numeric = 10 distinct fields, overlap ∅; the README section gives 10
  `data.budget_signals[].<field>` rows; set difference both ways **∅/∅**; and those ten names are
  exactly the keys `serialize_budget_signal` emits (`division_serializers.py:74-88`), so the
  documented contract is the served contract. The section split is heading-local and `#### `
  sub-headings do not terminate it. Both declared fix mutations are credible from the assertion
  structure; their L1 evidence was consumed by citation, not re-run.
  **Probe by variation (the sub-check the ledger missed):** `currency` `| string | Yes |` →
  `| string | No |` — a **string** row — reddened the string-loop exact-cell assertion,
  **1 failed / 5 passed**. Reverted, checksum verified.
  One closing L4 (`-m 'not e2e'`, budget 1, spent 1, authorization recorded pre-run) →
  **21 failed / 2800 passed / 1 skipped**; failing-ID set differenced member-by-member against the
  durable 21-ID baseline: **∅/∅**. The six C5(a) siblings plus this phase's test file collect 97
  tests, none in the failing set.
  **N7 (note).** The repair dropped the pre-fix per-field occurrence guard; a contradictory
  duplicate `currency` row (`integer | No`) leaves **6 passed**. Not chargeable to C4(d), which
  does not forbid an eleventh row — plan lesson, folded with N5.
  **N8 (note).** Rule 12: both declared mutations landed on the numeric loop, so the three
  string-field assertions had no ledger mutation. The r1 correction said "different rows"; rule 12
  wants one per sub-check. Closed empirically by this review's probe. Prompt-authorship lesson.
  Zero blocking, zero should-fix, zero owner cards. Both probes reverted and checksum-verified; no
  graph tool called and no graph state touched; the mixed `.archgraph/architecture.yml` hunks are
  preserved for the approval closeout.
  Full detail: `handoffs/reviewer/20260825_plan_3_re_review_round_1.md`.
