# Plan 2 — task-scoped section-keyed production-time view (E3, M3)

```
plan: 2
state: **APPROVED** (re-review r3, 2026-08-17, Opus 5 — 0 blocking, 0 should-fix,
       9 carried-forward notes)
date: 2026-08-17 (rev 2, post-projection)
```

## Goal

Implement intention §12 completely in one phase: the M3 grouping/ordering rules and the
allocation-unit change inside the **existing** `budget_division` module (D11), the
per-step split that keeps E2 working (D11a as rewritten in round 10), the new E3 query
service and serializers, the route mount with its HC-1a additions, and the full test set.

Read-only. Zero migrations. `CALCULATION_VERSION` not bumped.

**Read intention §12 at round 10.** Round 9's M3.5b and its "exclusion is decided at the
allocated unit" clause are **superseded**; building either would reverse D8 and rewrite
five phase-1 assertions for no benefit.

## Read first (self-contained session list)

1. `../planning/intention.md` — **§12 in full at round 10**. §12.4 (all 14 counts),
   §12.5 (M3.1 outer join, M3.5 charging-vs-weighting, M3.5b the split, M3.5c the label,
   M3.8a `percent_consumed`), §12.6 (properties incl. P1's scoping), §12.7 (E3 shape).
   §3–§6 remain in force for M1/M2 semantics phase 2 does not change.
2. `../planning/owner_decisions.md` — D9, D11, D11a, D12, **D13/D14/D15**.
3. `../master_plan.md` — §4 naming registry (phase-2 block), §6 standing rules + nine
   earned rules + MVP calibration rule, §7 environment, §9 gates.
4. `../handoffs/reviewer/2026-08-17_phase2_projection_r0_handoff.md` — §1 (the measured
   table), §3 (the per-test impact table; **column (ii) is your work list**), and the
   named-mutation wording in P8/P9. Do **not** read its appendix.
5. Code, read and verified independently:
   - `domain/item_economics/budget_division.py` — whole file; `:17` the label, `:72`
     `_sort_key`, `:136-141` the fallback median, `:142-147` the double-weighting D11 ends
   - `services/queries/item_economics/get_task_budget_allocations.py` — E2
   - `services/queries/item_economics/get_task_budget_status.py` — **E3 calls this
     directly** (P4); `:59-60` the 404, `:138-147` the SQL step sum
   - `domain/task_steps/constants.py:4-9` — `TERMINAL_STEP_STATES`, imported not re-listed
   - `domain/item_economics/serializers.py:193,243-249` — the `percent_consumed`
     injection precedent; `:207-217` `_serialize_result`, the money-at-depth-2 hazard
   - `models/tables/tasks/task_step.py:117-121` — `latest_state_record`, lazy
   - `routers/api_v1/item_economics.py:330-370`
   - `tests/unit/routers/api_v1/test_item_economics_router.py:126-139` — the test B10
     turns red

## Out of scope

The frontend handoff (coordinator closeout; **rewritten from scratch**, not edited).
Migrations, including any `order_list` uniqueness or backfill. `serialize_step` and the
step-listing endpoint (HC-1). Deprecating E1/E2 (HC-9). Dynamic reallocation (D6),
configured or per-category typicals (D2). **Extracting `status`/`item_binding` into a
shared home** — real improvement, blast radius crosses HC-1's v1 perimeter, recorded as a
follow-up (P4).

## Tasks

- **T1 — M3 grouping + ordering in `domain/item_economics/budget_division.py`.**
  `group_steps_by_section(...)` (M3.1) and `_section_sort_key(...)` (M3.2, key
  `(order_list IS NULL, order_list, name, working_section_id)`). The governing-step rule
  (M3.4/D12) and the `worked_seconds` sum (M3.3) live here too — mechanism, not glue.
  **Liveness is `state NOT IN TERMINAL_STEP_STATES`, imported from
  `domain/task_steps/constants.py`, never re-listed** (B7, one-copy rule).

- **T2 — allocation unit becomes the section (D11), inside the existing function.**
  `divide_production_budget` **returns BOTH keys** (B1):
  - `sections` — one row per allocated/excluded group: `working_section_id`,
    `allowance_seconds`, `worked_seconds`, `share_state`, `step_ids`, `step_count`;
  - `steps` — one row per non-deleted step, **keys byte-identical to today**, values per
    M3.5b.

  `steps` remains the key E2 reads. Both are produced inside `budget_division.py`;
  neither service computes an allowance (HC-6). This settles master plan §4's "E2 becomes
  a consumer that splits its section share" against C19 — **the split lives in the domain
  module, not in E2.** Grouped-unit remainder tie key is **`working_section_id` ASC** for
  both callers (B6), deliberately not M3.2's render order.

  **`C` does not move to the group unit** (B4/D15): it stays Σ worked over non-deleted
  excluded *steps*. A group is weightless only when all its steps are excluded.

- **T3 — the per-step split (M3.5b as rewritten).** Closed step → allowed its own worked
  seconds. Open steps → share `slice − Σ closed worked seconds`, **equal weights** (B5),
  largest-remainder, tie key `(sequence_order ASC NULLS LAST, client_id ASC)`. **No open
  step → the remainder goes to the governing step** (B2 — this branch governs 45 of the 50
  multi-step groups plus every closed single-step section, i.e. most rows in the
  database). The residual subtracts only **completed** steps' seconds, never an excluded
  step's — those are already charged against `B` (B4). Allowances may go **negative**; no
  clamping (B3/D14). A step row's `share_state` is **derived from its section's** total
  worked vs slice (D13). E2's payload shape unchanged; values move.

- **T4 — `services/queries/item_economics/get_task_production_time.py` (E3).**
  - **Calls `get_task_budget_status(ctx)` directly** (P4). It already returns `status`,
    `item_binding`, `actual_worker_seconds`, `actual_worker_minutes`,
    `remaining_worker_minutes`, `percent_consumed`, `allowed_worker_minutes` and
    `result` — every field M3.7/M3.8 need — plus the 404 tenant boundary. E3 therefore
    computes **no arithmetic** and adds **no third copy** of `status`/`item_binding`.
    Call the **manager** variant for all four roles, never the worker variant: one code
    path is what makes P-FLAT structural rather than merely tested. It carries monetary
    fields in-process; the serializer never emits them and C14 is the guard.
  - **`order_list` comes from a separate `WorkingSection` select** over the task's section
    ids (B9) — *not* by widening `typical_times_statement`, which would edit a phase-1
    file, change E1's grouping, and risk E2's pinned query count. This select must
    tolerate the outer-join case of M3.1/B8.
  - **`selectinload(TaskStep.latest_state_record)`** (B11) — the relationship is lazy and
    a bare access raises `MissingGreenlet`, a 500 on the happy path. `pause_reason` is
    not needed.
  - Filter typicals to the task's sections (P10) — SQL `WHERE … IN` or a Python dict
    lookup keyed by the task's section set; **either is correct, the choice is granted.**

- **T5 — serializers, extending `domain/item_economics/division_serializers.py`.**
  `serialize_task_production_time(...)`, `serialize_production_time_section(...)`.
  `final` per M3.8/M3.8a: every field from the frozen row **except**
  `percent_consumed`, which is the live figure and equals `budget.percent_consumed`
  (B12). **Write a time-only builder — do NOT reuse `serialize_item_cost_result`**, which
  emits `consumed_cost_minor`/`variance_cost_minor` and would put money at depth 2 with
  one import (P9's highest-risk object). Both names per M3.9. No `step_ids` on the wire.

- **T6 — route + HC-1a additions.**
  `GET /tasks/{task_client_id}/production-time`, declared beside `budget-status`
  (`:360`). **No return-type annotation, and set `response_model=None` explicitly** to
  match the neighbours (N4) — `test_item_economics_routes_declare_no_response_model`
  asserts it. Declaration order is **not** load-bearing here: proven that all probe paths
  resolve identically in both orders because the two paths differ in segment count (N1) —
  do not repeat the "therefore below the fixed path" rationale as a necessity.
  - `test_phase9_item_economics_route_mirror.py` — one `_EXPECTED_ROUTES` row; counts
    **24 → 25** (`:125-126`).
  - `tests/unit/routers/api_v1/test_item_economics_router.py` — one row in `_ROUTES` /
    `_ALL_ROLE_ROUTES` **plus a body change** (B10):
    `test_budget_status_route_is_available_to_all_roles` (`:126-139`) returns early for
    `budget-allocations` and otherwise asserts the budget-status service for
    worker/seller. A bare row sends `production-time` down that branch and the assertion
    **fails for worker and seller**. Add a third branch asserting
    `calls[0][0] is item_economics.get_task_production_time` (service-identity rule).
    **Do not loosen the dispatch** — that is a no-weaker-assertions violation in an
    HC-1a-protected file. This file has no count assertions.
  - `routers/README.md` — Quick Index row (24 → 25) + detail section.

- **T7 — tests, the criteria below**, each a distinct fixture, not a parametrization.

- **T7b — phase-1 test updates: exactly the two `live_partition` rows.** Per the
  projection's enumerated table, column (ii) — the adopted semantics — changes **only**
  `test_live_partition_includes_working_paused_and_completed_steps` (`:105` base and
  `:120` with_new). Every other phase-1 assertion stays **byte-identical**, and a change
  anywhere else is a signal you built something other than this contract. Two causes to
  name in the handoff: the removed double-weighting **and** the fallback-median multiset
  change (N8 — a two-step section contributed its typical twice, now once; `weaving` has
  `sample_count = 0` so this path is live in production).
  `test_uses_shared_typicals_for_two_section_proportional_split` (`:160`) stays
  **unchanged in value** under (ii) but its invariant is now section-level (P1) — restate
  it, do not loosen it. Baseline before you start: the six phase-1 files run **140
  passed**; verify that yourself before touching anything.

## Acceptance criteria

**Every criterion is an automated test that owns its teardown (rule 11½), DB-backed
unless it is a property of the pure allocator — those are proven by unit tests on the
function** (P6). Exact literals, never a range or an inequality a wrong value could pass.

| # | Criterion | Kind |
|---|---|---|
| C1a | `order_list` tie, insertion order Alpha→Beta: exact order asserted. | DB |
| C1b | **The same two sections seeded in the REVERSED insertion order** (sections *and* their steps), asserting the identical expected order. Idempotence (calling twice) is NOT reversal — r1 built the former. **Named mutation: delete the `name` component of `_section_sort_key` at its definition (`budget_division.py:90`) → C1b must go red.** It currently leaves 47 phase-2 tests green. | DB |
| C2 | `order_list` NULL sorts last with populated siblings present. | DB |
| C3 | `working_section_id` backstop: identical `order_list` **and** identical `name`. **Pure-function test on `_section_sort_key` with hand-built inputs** — `uix_working_sections_name_active` is a partial UNIQUE on `(workspace_id, name) WHERE is_deleted=false`, so two live same-named sections cannot exist in one workspace and the backstop is unreachable through the DB (P5). Keep it as defence in depth. | unit |
| C4 | Multi-step section → **one** row, `step_count == 2`, `worked_seconds` == the sum, `allowance_seconds` the pinned literal. | DB |
| C5 | **D11 numerically**: 180-min budget, typicals 60/30/60, two Upholstery steps → 4320/2160/4320 s, and assert it is **not** 3086/1543/6171. The regression guard for the whole decision. | unit |
| C6a | Governing step (D12), **DB row**, on a fixture whose `completed` step is created **LAST** — so that "live" and "newest-created" disagree (precedence-disagreement rule). Row reads `pending`. **Named mutation: delete the liveness partition in `_governing_step` at its definition → C6a must go red.** r1's DB row survived this mutation entirely. | DB |
| C6b | `state_entered_at` **exact value** on that row — the field has zero coverage anywhere today and §6.5's client-side live tick is built on it. | DB |
| C6c | Multi-open tie-break with a **non-vacuous** expected state (r1's fixture had both steps pending, so it held under any rule): assert M3.4's stated precedence `entered_at` DESC → `created_at` DESC → `client_id` ASC, on a fixture where those three disagree. | unit |
| C7 | Multi-open tie-break (0 rows in the DB) → deterministic winner, equal weights (B5). | unit |
| C8 | Excluded section: all steps `skipped` → `share_state: "excluded"`, no allowance, seconds charged. | DB |
| C9 | Mixed section, on a fixture whose **excluded seconds alone cross the slice** (r1's fixture had both readings return `on_track`, so it could not fail under either contract): section stays **weighted**; assert `worked_seconds` **exactly**; assert `share_state == "over_share"` per D16; assert `C` still charges the excluded seconds at task level (B4/D15). **Named mutation: compare only non-excluded worked seconds → C9 must go red.** | DB |
| C10 | P-SUM3: Σ allowances == `distributable_seconds` on typicals that do not divide evenly. `distributable_seconds` is on no payload, so this is necessarily a unit row (P6). | unit |
| C11 | P-COVER: Σ section `worked_seconds` == `budget.actual_worker_seconds`. Note this compares the SQL `SUM` from budget-status against E3's Python sum — **two independently computed numbers. Keep it that way** (P4). | DB |
| C12 | P-AGREE: same task through E2 and E3 — Σ of E2's step allowances for a section == E3's section `allowance_seconds`, **in every M3.5b branch** incl. no-open and negative. | DB |
| C13 | D11a: slice 72 min, closed pass burned 60 → open reassignment reports 12 min. Plus the negative case: slice 60 s, closed burned 100 s → **−40**, unclamped (B3/D14). | DB |
| C14 | P-FLAT + money: four roles → byte-identical bodies (`sha256`). Money walk **recurses dicts and lists at every depth**; assert no key matches `_minor`, `cost`, `price`, `currency`, `money`, `valuation`. **Named mutation: returning `serialize_item_cost_result(result)` for `final` must turn this red.** Do not copy the decorative top-level form at `test_budget_division_routes.py:163-168` (N6/P9). | DB |
| C15 | Tenant boundary → 404. Prove the fixture row exists by deleting the workspace filter and watching this go red (tenant-boundary-row rule). | DB |
| C16 | Degradation: unevaluated task → `budget.*` all null incl. `actual_worker_seconds`, every `share_state: "no_budget"`, typicals and `worked_seconds` still populated. | DB |
| C17 | Closed task: `final` from the frozen row, **except `percent_consumed`, which equals `budget.percent_consumed`** (B12/M3.8a); no monetary key. Fixture-only — `item_cost_results` is empty. | DB |
| C18 | Both route mirrors + README updated per T6, including B10's third dispatch branch; counts 24 → 25 in the one file that has them. | unit |
| C19 | HC-6, mechanically (P8): (a) the set of modules importing `divide_production_budget` is exactly {`get_task_budget_allocations`, `get_task_production_time`}; (b) neither service module's source contains `Fraction`, `ROUND_HALF_EVEN`, `largest`, or `//`; (c) `budget_division.__all__` exports exactly one allocator name. | unit |
| C27 | **P-PROP restatement** (S5): `test_uses_shared_typicals_for_two_section_proportional_split` asserts the ratio at the **section** unit (or over Σ step allowances per section), renamed accordingly, with a one-line comment citing §12.6 P1. Its value is unchanged; only its invariant moves. Strengthen — never loosen. | DB |
| C20 | E2's payload **shape** unchanged (key-set assertion at every depth), while its values move per T7b. | DB |
| C21 | Section set is this task's sections only — a workspace section the task never touches is absent (M3.1); typicals filtered accordingly (P10). | DB |
| C22 | **Soft-deleted section** (B8, new): a task with a live step on a soft-deleted section still yields its row — `section_name: null`, `order_list: null`, `typical_worker_seconds: null`, `sample_count: 0`, `section_name_snapshot` populated — and P-COVER holds. Reproduces `sanding`, which carries 5 live pending steps in production. | DB |
| C23 | **Leftover-unit agreement** (B6, new): on an indivisible fixture, E2 and E3 assign the leftover second to the **same** section. Mutate one caller's tie key to M3.2's order → red. | DB |
| C24 | **`allocation_method` literal** (P2, new): assert the exact string `static_proportional_section_v1`, and that E2 and E3 emit the identical value. No test pins it today. | DB |
| C25a | **M3.9 rename**: rename the section after the step exists → `section_name` is the new name, `section_name_snapshot` the old, on the same row. | DB |
| C25b | **Divergent snapshots within one group** (S4): two steps of one section carrying *different* snapshots — assert the row takes the **governing step's**, not the first-returned. r1's fixture gave both steps the same snapshot, so it could not see this. **Named mutation: take the first non-null snapshot in query order → C25b must go red.** | DB |
| C26 | E2's query count stays **11** (N5) — T3's split needs no new data. If a B9 repair routed `order_list` through E2 this breaks, which is the intended tripwire. | DB |

## Review log

- **projection r0 (2026-08-17, Opus 5)** — AMENDMENTS_REQUIRED. 12 blocking, 10
  amendments, 11 notes, 3 owner cards. §12.4 confirmed accurate on all 7 claims and
  extended by 4 counts. B5/B6/B7 recorded as **gate failures** under the
  mechanism-inventory waiver's condition (an ordering key, a remainder key and an
  admission filter, all uncontracted). All rows routed by the coordinator 2026-08-17;
  cards → D13/D14/D15. Coordinator independently re-verified B8, B2's 45/5 composition,
  B7's 0-of-2833, N9's zeroes and P5's partial unique index — all reproduce exactly.

- **implementation r1 (2026-08-17, Codex/GPT-5)** — IMPLEMENTED. The E3 service,
  time-only serializers, all-role route, route mirrors, README contract, and the
  section-level allocator projection are in place. T7b was closed by changing exactly
  the two `live_partition` expected-value rows: base pending/working/paused `20` with
  completed `0`, and `with_new` pending/working/paused/new `15` with completed `0`.
  Those values reflect removal of double-weighting and the fallback-median multiset
  change (a two-step section contributes its typical once). The shared typical-ratio
  test was unchanged in value.

  Judgment calls recorded for review: the E3 service composes the existing manager
  budget-status service and keeps all arithmetic in `budget_division.py`; absent active
  section attributes use the required outer-join/null metadata shape; and E2/E3 use the
  same section-id tie order for leftover seconds. No migrations, indexes, persisted
  calculation state, money fields, or `CALCULATION_VERSION` changes were made.

  Verification: the targeted phase suite passed 164 tests; the full suite completed at
  2337 selected, 2311 passed, 26 failed, and 1 deselected. The 26 failure IDs are
  byte-identical to the approved phase-2 start baseline. Seven named mutation probes
  (C5/C6/C14/C15/C22/C23/C25) each produced a red test and were reverted cleanly.

- **review r1 (2026-08-17, Opus 5)** — **CHANGES_REQUIRED**: 1 blocking, 6 should-fix, 8
  notes. **B1 (blocking)** M3.4/D12's governing-step rule is not implemented —
  `_governing_step` picks the most recently *created* step and never consults liveness;
  the documented `entered_at`/`created_at` precedence is also inverted. C6's fixture makes
  live and newest-created the same step, so its guard passes for the wrong reason and its
  DB half survives the named mutation. **S1** adjudicates F1: `share_state` moves to M3.3's
  total `worked_seconds`, `left_seconds` stays (owner card 1 ratifies). **S2** C1's `name`
  tie-break is unguarded and the insertion-reversal clause was never built. **S3** C6's DB
  row does not guard; `state_entered_at` has zero coverage anywhere. **S4**
  `section_name_snapshot` is taken from query order, not the governing step, and E3's step
  select has no `ORDER BY`. **S5** T7b's "restate, do not loosen" was not done on the
  P-PROP row. **S6** upholds F2. Verified correct and not to be re-derived: P-AGREE and
  P-SUM3 exact in all 8 M3.5b branches, HC-6, the time-only role-flat wire, T7b's two rows.
  Coordinator independently reproduced B1 (three deviating cases + control) and S2.

- **fix r2 (2026-08-17, Codex/GPT-5)** — **IMPLEMENTED**. B1 now partitions live
  steps before applying M3.4's `entered_at` DESC → `created_at` DESC → `client_id`
  ASC precedence; S1 compares total section worked time for `share_state`; S4 takes
  the snapshot from the governing step with a null fallback and orders E3 steps by
  `client_id`; C1b, C6a/b/c, C9, C25b and C27 now exercise the rewritten contracts.
  Targeted fix suite: 31 passed. Full suite: 2313 passed / 26 failed / 1 deselected;
  the 26 failure IDs match the phase-2 start baseline. Four named definition-site
  mutation probes all went red and were reverted byte-identically. Architecture graph
  source links were added in one batch; no review item was promoted, rejected or edited.

- **fix r2 (2026-08-17, Codex/GPT-5)** — all seven findings addressed; checkpoint `f904100`,
  6 files, all declared, nothing undeclared.
- **re-review r3 (2026-08-17, Opus 5)** — **APPROVED.** Seven of seven closed *and
  demonstrated by definition-site mutation*. Nothing loosened. Suite 2313/26/1, IDs
  byte-identical, re-derived independently. Phase-2 tests proven to leave zero DB residue
  and zero orphan FKs by isolation (3376→3376 steps, 8983→8983 records over 166 tests).
  Carried-forward notes recorded here so they are not rediscovered:
  - **N2** — C6c pins `entered_at` and `created_at` but **not** `client_id`: inverting that
    sort leaves 27 tests green. Same shape as C3's backstop — a determinism guarantee no
    fixture reaches. Build it at the next M3.4 touch.
  - **N3** — C27's section-unit restatement is **structural, not demonstrable**:
    `_seed_two_section_allocation` gives each section exactly one non-excluded step, so no
    mutation can make the step unit and the section unit disagree on that fixture.
  - **N9** — E3's `order_by` is **unguarded by design**: a test cannot observe an
    unspecified order. The class was closed by taking the snapshot from the governing step
    (C25b), not by the `order_by`, which is belt-and-braces.
  - **N1** — one `== 1800` pin was deleted from `test_budget_allocations_query.py`; proven
    to cost no coverage, but restore it at the next touch of that file.
  - **N6** — the C6a teardown's blanket `UPDATE … SET latest_state_record_id = NULL` is
    filtered by workspace, not by step id; correct only by fixture convention.
  - **N7** — three dead imports in `test_production_time_query.py` (`DivisionStep`,
    `_section_sort_key`, `divide_production_budget`), pre-existing; tidy at next touch.
