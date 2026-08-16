# Plan 1 — typical section times + per-step budget allocations (E1, E2, M1, M2)

```
plan: 1
state: PROMPT_READY (projection r0 ran — AMENDMENTS_REQUIRED, ledger routed; implementer r1 prompt compiled)
date: 2026-08-16
```

## Goal

Implement intention §3–§6 completely in one phase: the `budget_division` domain
module (M1 constants + M2 pure function), the two query services, the two routes, and
the full test set. Read-only; zero migrations; zero edits to closed v1 modules —
except the three HC-1a-authorized additions (D10), enumerated in T5 and nowhere else.

## Read first (self-contained session list)

1. `../planning/intention.md` — ALL sections; §4 (M2) and §2.5 (mutation surfaces)
   are the semantic core.
2. `../master_plan.md` — §4 naming registry (final name authority), §6 standing
   rules, §7 environment.
3. Code: `services/queries/item_economics/get_task_budget_status.py` (loader +
   status-resolution pattern to reuse), `domain/item_economics/calculator.py` (guard
   style for the pure function), `models/tables/tasks/task_step.py`,
   `routers/api_v1/item_economics.py` + `routers/api_v1/working_sections.py` (mount
   points), `domain/item_economics/serializers.py` (`_decimal` convention — read,
   do not edit).

## Out of scope

Frontend handoff documents (coordinator closeout), migrations (HC-2 STOP rule),
`serialize_step` and every existing payload (HC-1), dynamic reallocation, configured
typicals, per-category typicals (intention §7).

## Tasks

- **T1** — `domain/item_economics/budget_division.py`: constants per registry;
  `divide_production_budget(...)` implementing M2 exactly as amended in intention
  round 5 (B_seconds half-even quantization pre-`C`; partition by
  `EXCLUDED_STEP_STATES` over non-deleted steps; charged `C`, `D = max(0, B−C)`;
  weight ladder requiring `t_i > 0`; empty-allocated-set rule; **exact
  `fractions.Fraction` arithmetic for weights/shares/fractional parts — no float**;
  largest-remainder rounding with tie order `(sequence_order ASC NULLS LAST,
  client_id ASC)` implemented via the NULL-safe sort key
  `(seq is None, seq if seq is not None else 0, client_id)` — the naive tuple key
  raises `TypeError` on mixed None/int (projection P6); `share_state` values
  `no_budget/excluded/on_track/over_share`). Entry guards in the calculator's style.
- **T2** — E1 query service (M1): one `percentile_cont(0.5)`-based grouped query with
  the four exclusion predicates and the window; every non-deleted section of the
  workspace in the output; `null` typical below `TYPICAL_MIN_SAMPLE_SIZE`; optional
  `working_section_ids` filter.
- **T3** — E2 query service: batch load tasks (workspace-scoped), committed-current
  evaluations (`.in_` is safe: `uix_item_cost_evaluations_current` is unique per
  task, projection N9), non-deleted steps, and section typicals in **constant query
  count**. For evaluation-less tasks, **mirror
  `get_task_budget_status.py:111-125` in full** (projection P9): no PRIMARY item →
  `NOT_EVALUATED` without calling the resolver; otherwise selection + valuation +
  terms → `resolve_item_economics_status`. **Do NOT call `_load_preview_inputs` per
  task** (projection N8: 3–4 workspace-wide queries per call): hoist the
  groups/basis/model/terms loads once per request — keeping the loader's exact query
  shapes, including their absence of `ORDER BY`, so E2 and budget-status can never
  select different versions — and call the pure `resolve_economics_selection` /
  `resolve_item_economics_status` per item in Python. Call T1 per task.
- **T4** — `division_serializers.py`: E1/E2 payload builders per intention §5 shapes;
  decimal minutes as strings, seconds as ints; **no monetary field exists in these
  serializers at all** (HC-3 — nothing to role-gate).
- **T5** — Routes: E1 on the working-sections router **declared above the
  `/{working_section_id}` route at `:128`** (P7 — declared after it, E1 is shadowed
  and 404s; precedent `/me` `:93`; the file is tab-indented, match it); E2 on the
  item-economics router declared above the parameterized `/tasks/{…}` block with the
  ordering comment; both `require_roles([ADMIN, MANAGER, WORKER, SELLER])`; E2
  enforces the 50-id cap with `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`; query params
  are repeatable per master plan §4 (P12). **Plus the HC-1a authorized v1 edits
  (D10, exactly these, nothing else):** `_EXPECTED_ROUTES` +1 row and count 23 → 24
  in `test_phase9_item_economics_route_mirror.py`; one Quick Index row + one detail
  section in `beyo_manager/routers/README.md` for EACH of E1 and E2 (P11 — E1's
  README rows are enforced by no test; the reviewer checks them by hand).
- **T6** — Tests per the registry's four files (criteria below).
- **T7** — Archgraph delta: one batched `apply_changes` recording the new module,
  services, routes, and their edges.

## Acceptance criteria (every criterion: automated test, configured DB, teardown owned)

Each criterion names its red-mutation and the mutation's site (charter rule 11).

**M2 pure function (`test_budget_division.py`):**
- **C1 P-SUM** — allowances sum to `D` exactly on a 3-step task with typicals
  producing non-integer raw shares. RED: in `budget_division.py`, replace
  largest-remainder with independent `round()` per share (definition site).
- **C2 P-SUM-charged** — failed step with 2400 worked seconds: `D = B − 2400`, its
  row `excluded`, allocated allowances sum to `D`. RED: delete the `C` subtraction
  (definition site).
- **C3 clamp** — excluded consumption > B ⇒ `D = 0`, every allocated allowance 0,
  zero-worked allocated steps `on_track`. RED: remove the `max(0, …)` clamp.
- **C4 P-PROP** — typicals 3600/1800 ⇒ allowances 2:1 (B chosen so no rounding
  residue); all-missing typicals ⇒ equal split. RED: use equal weights
  unconditionally (weight-resolution branch).
- **C5 P-DET tie order** (rewritten per projection P6 — `sequence_order` is NULL on
  3032/3032 production rows, so the NULL path IS production). Two enumerated rows,
  each with equal fractional parts (exactness guaranteed by the Fraction contract)
  and pinned integers for every step:
  (a) both steps `sequence_order NULL` ⇒ the remainder unit lands by `client_id ASC`.
  RED: reverse to `client_id DESC` (sort-key call site).
  (b) one step `sequence_order=1`, one NULL ⇒ the non-NULL sorts first regardless of
  `client_id`. RED: drop the NULLS-LAST handling from the sort key (same site) —
  with the naive tuple key this row raises `TypeError`, which also counts as red.
  This criterion is the rule-6 heart of the phase.
- **C6 P-FOLLOW** — same task re-divided after (a) adding a pending step, (b) a step
  turning `skipped` non-deleted: allowances shift exactly as M2 predicts, pinned
  integers both times. RED: freeze the step set by filtering to
  `state == PENDING` only (partition site).
- **C7 fallback median** (fixed per projection P5 — with two known values median ==
  mean and the mutation cannot bite) — one step's typical `null` among THREE known
  `{600, 1200, 6000}` ⇒ its weight is `1200`. RED: substitute mean (`2600`) for
  median in the fallback (fallback expression). Companion row: FOUR known
  `{600, 1200, 1800, 6000}` ⇒ interpolated even-count median `1500` (pins the B4
  even-count definition). RED: lower-middle instead of interpolation (same site).
- **C8 no_budget** — no committed evaluation ⇒ every step `no_budget`,
  null allowances, typicals still present. RED: default missing budget to 0 instead
  of the `no_budget` path (entry guard).
- **C19 B_seconds quantization (B2)** — `allowed_worker_minutes = Decimal("195.01")`
  ⇒ `B_seconds = 11701`, and P-SUM holds against 11701 with a 3-step division that
  produces rounding residue. RED: truncate instead of half-even (`int(x)` at the
  quantization site).
- **C20 empty allocated set (B3a)** — every step excluded, `B > 0` ⇒ no allowances
  produced, every step `excluded`, task-level figures present, no exception. RED:
  remove the empty-set guard so the weight division runs (`ZeroDivisionError`
  counts as red).
- **C21 all-zero typicals (B3b)** — every allocated step's typical is `0` (legal M1
  output) ⇒ weight ladder falls through to the equal split, allowances sum to `D`.
  RED: admit `t_i = 0` as a weight (first ladder rule's `> 0` guard).

**M1 query (`test_typical_times_query.py`, under `tests/integration/` per P8)** —
one fixture family; each row's predicate is the ONLY reason its outcome holds
(charter rule 2 companion). Samples are **(task, section) group totals** (intention
M1 as amended by D9/round 5). **P1 fixture-padding rule:** `TYPICAL_MIN_SAMPLE_SIZE
= 5` forces every under-5 fixture to NULL, so each criterion pads to ≥5 qualifying
groups with a shared filler helper whose values place the group under test AT the
median (worked example, C9b: fillers `{1000, 2000, 5000, 6000}` + target `4200` ⇒
median `4200`; the dropped-GROUP-BY mutation splits the target into 3600+600 ⇒ six
samples, median `2800` ≠ `4200` — still bites):
- **C9** median over group values: groups {600, 1200, 6000} ⇒ 1200 (median ≠ mean by
  construction). RED: replace `percentile_cont` with `avg` (query expression).
- **C9b group aggregation (D9)** — one task with a 3600s first pass AND a 600s
  rework step in the same section ⇒ ONE sample of 4200, never two samples. RED:
  remove the (task, section) GROUP BY so each step samples individually (query
  grouping site).
- **C9c group-window integrity (D9)** — first pass closed 100 days ago, rework
  closed yesterday, same task+section ⇒ one in-window sample of the FULL sum (both
  steps). RED: move the window predicate from `MAX(closed_at)` group admission to
  per-step admission (window predicate site) — the sample degrades to rework-only
  and the pinned total goes wrong.
- **C10** each contributing-step exclusion bites independently: a non-`completed`
  step, a `recorded_time_marked_wrong` step — each present inside a group and
  excluded from its sum; removing any one predicate (query site, one per row) turns
  exactly its row red.
- **C9d even-count interpolation + rounding locus (P2/P3)** — six qualifying groups
  per row, two fixture rows: (row 1) middle pair `{1000, 1003}` ⇒ interpolated
  median `1001.5` ⇒ half-even `1002`; RED: `percentile_cont` → `percentile_disc`
  (statistic site) ⇒ `1000`. (row 2) middle pair `{1000, 1001}` ⇒ interpolated
  `1000.5` ⇒ half-even `1000`; RED: rounding routed through `::numeric` (rounding
  site) ⇒ half-away `1001`. All four expected/wrong integers enumerated in the test;
  each mutation bites exactly one row with a distinct wrong value.
- **C9e window exclusion (P4)** — a group whose `MAX(closed_at)` is 91 days old
  vanishes: absent from the median AND from `sample_count`. RED: drop the window
  predicate entirely (window site).
- **C11** boundary: 4 qualifying groups ⇒ `typical: null` + `sample_count: 4`; a 5th
  group ⇒ non-null. RED: `<` → `<=` on the min-sample comparison.
- **C12** zero-sample section appears with `null`/0; `working_section_ids` filter
  returns only requested; unknown id silently absent. RED: inner-join sections to
  samples (drops empty sections).

**E2 read model (`test_budget_allocations_query.py`):**
- **C13 two-doors (intention §2.5)** — same worked seconds: endpoint-removed step
  (deleted+skipped) in NO row and absent from `actual_worker_seconds`,
  byte-agreeing with `get_task_budget_status` on the same fixture; force-ready-style
  skipped (non-deleted) present as `excluded` and charged. RED for door 1: drop the
  `is_deleted` filter (query site); RED for door 2: add `is_deleted` exclusion to
  the charged-set predicate (partition call site).
- **C13b door-mapping guard (projection N11)** — ONE service-invoking test pinning
  that `remove_task_step` produces `state=SKIPPED AND is_deleted=True` on the
  removed row — without it, C13's row-constructed fixtures outlive the behaviour
  they model. RED: the mapping test fails if removal stops setting either field.
  (C13's E2 assertions themselves use row-constructed fixtures — the cheap path —
  per N11's verified evidence that neither removal nor force-ready recomputes
  `total_working_seconds` inline.)
- **C14 batch semantics + constancy (rewritten per projection P10)** — 3 ids: one
  ok, one unknown (omitted), one other-workspace (omitted). Query-count constancy is
  proven by EQUALITY between a 1-task call and a 3-task call — each including an
  evaluation-less task so the status path runs in both — using the LOCAL
  `executed_statements` fixture pattern
  (`test_list_users_floor_identification.py:173-193`;
  `test_reassigned_steps_integration.py:86-100`). The shared `count_queries`
  fixture in `tests/conftest.py:63-76` is broken (session-scoped engine resolves
  before `init_db()`; raises on first use) — do NOT use it. RED: per-task loop
  issuing one evaluation query each (loop site) — the 3-task count exceeds the
  1-task count.

**Routes (`test_budget_division_routes.py`):**
- **C15** all four roles admitted on both routes (one row per role per route — eight
  rows, enumerate-never-sample); envelope `{data, ok, warnings}`.
- **C16** E2 51 ids ⇒ 422 `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`; 50 ⇒ 200. RED:
  `>` → `>=` on the cap comparison.
- **C17 no-money key-set** — exact key-set equality assertions on an E1 row, an E2
  task object, and an E2 step object (set-assertion rule; any monetary key appearing
  fails by construction). Fixture seconds/minutes values pairwise distinct
  (distinct-values rule).

**Suite:**
- **C18** — full suite `PYTHONPATH=. pytest -m 'not e2e'`: 23-failure list
  byte-identical to the v1 phase-1 list; selected count grows by exactly this
  phase's added tests; totals recorded in the handoff (P-L: reviewer re-measures).

## Review log

- **Round 0 (projection, 2026-08-16, Opus 5)** — verdict AMENDMENTS_REQUIRED: 4
  BLOCKING (B1 v1 tripwire → D10/HC-1a; B2 fractional B_seconds; B3 Σw=0; B4
  arithmetic type + even median), 12 PLAN-FIX (P1–P12), 12 NOTES; inventory sweep
  fired the waived-gate condition on mechanisms 5/12/17/18/25 — all now contracted
  (intention round 5). Ledger fully routed same day: intention round 5, master plan
  §3/§4/§7, this plan (T1/T3/T5 amended; C5/C7/C14 rewritten; C9d/C9e/C13b/C19/C20/
  C21 added; M1 P1 padding rule). Handoff:
  `../handoffs/reviewer/2026-08-16_phase1_projection_r0_handoff.md`. Coordinator
  spot-verified B1 (mirror literal + count at
  `test_phase9_item_economics_route_mirror.py:110-126`) and P7
  (`working_sections.py:128` param route; `/me` precedent `:93`) before routing.

- **Round 1 (implementer, 2026-08-16, Codex)** — IMPLEMENTED. Added the pure
  M2 budget-division module and serializers, the batched E1 typical-times and
  E2 budget-allocation query services, fixed-path all-role routes, route-mirror
  coverage, README contracts, and the required unit/integration tests. The
  implementation preserves exact `Fraction` allocation arithmetic, SQL
  `percentile_cont(0.5)` group medians with the 90-day/latest-close admission
  rule, explicit eval-less degradation, workspace/deletion filtering, and
  time-only payloads. Focused phase tests: 28 passed. Full non-E2E suite:
  2272 passed, 27 failed, 1 deselected; the 27 failures are outside this phase
  surface and are listed in the implementer handoff. Architecture Graph delta
  applied in one batch: 5 nodes and 9 relationships, revision
  `ab1a4935ea94bc00544837222cc0cf638e3054898157de4985765805537f3a6c`.
- **Round 1b (implementer fix, 2026-08-16, Codex)** — IMPLEMENTED. Added the
  E2 row to the fourth authorized route mirror, including its required query
  parameter and service assertion; added the C20 all-excluded unit fixture.
  The requested C13b service-invoking test was already present at checkpoint
  `0b85701`, so it was verified and not duplicated. Focused fix suite: 131
  passed. Full suite: 2277 passed, 26 failed, 1 deselected; the failure set is
  exactly the 23 v1 baseline IDs plus the 3 foreign bootstrap-seeding IDs.
  The r1b handoff records every attempted named mutation, including surviving
  mutations as STOP items, and maps every C1–C21 row to an exact test node or
  an explicit NOT COVERED — STOP item. No production behavior was changed and
  no Architecture Graph mutation was made; the r1 graph delta remains the
  authoritative graph state.
