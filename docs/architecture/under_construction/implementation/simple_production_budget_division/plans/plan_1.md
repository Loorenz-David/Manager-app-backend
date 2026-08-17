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

### Lettered rows for compound criteria (N-k fold, coordinator 2026-08-17)

Adopted per the §6 lettered-parts rule; these letters are the anchor for the
criterion→test maps in the fix handoffs and reviews.

- **C13a** — two-doors E2 assertions (removed step absent from rows AND from
  `actual_worker_seconds`; non-deleted excluded step charged).
- **C13b** — service-invoking door-mapping test (`remove_task_step` ⇒
  SKIPPED + is_deleted).
- **C13c** — byte-agreement: `get_task_budget_status.actual_worker_seconds`
  equality on the same fixture.
- **C14a** — statement-count equality between the 1-task and 3-task calls
  (absolute pin `== 11`).
- **C14b** — fixture property: the evaluation-less task carries a PRIMARY item +
  valuation so `resolve_economics_selection` runs in BOTH calls, guarded by an
  exact resolver-produced status assertion (see S6: `not_configured_no_cost_group`,
  which distinguishes from the short-circuit `not_evaluated`).
- **C14c** — batch semantics: unknown id omitted (covered).
- **C14d** — **tenant boundary** (split out of C14c per the r3 letter-verification
  + tenant-boundary-row rules, S7): a task belonging to ANOTHER workspace, passed
  in the id list, is omitted from `budget_allocations` — not returned as a
  degraded row. RED: delete `Task.workspace_id == ctx.workspace_id` from E2's
  visibility query (`get_task_budget_allocations.py:109-113`, definition site) —
  the foreign id must then appear and fail both the absence assertion and the
  existing `len(...) == 2` count.
- **C15a** — E1 role admission (four rows) + envelope.
- **C15b** — E1 service-identity assertion (P7 guard).
- **C15c** — E2 role admission (four rows) + envelope.
- **C17a** — E1 row exact key set.
- **C17b** — E2 task object exact key set + money scan.
- **C17c** — E2 step object exact key set + nested step money scan.

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

- **Round 1 consumption (coordinator, 2026-08-16)** — r1 handoff consumed
  adversarially; routed to FIX ROUND r1b before review. Findings:
  **K1 (defect, phase-caused):** the r1 claim "none of the 27 failure IDs is a
  phase failure" is FALSE for
  `test_item_economics_router.py::test_router_route_pairs_match_the_authoritative_route_table`
  — a second hand-written route mirror (`_ROUTES:14`, `_ALL_ROLE_ROUTES:48`)
  turned red by E2; coordinator reproduced the red (`Extra items in the left set:
  ('GET', '/tasks/budget-allocations')`). HC-1a extended 3→4 artifacts
  (intention round 6, D10 rationale).
  **K2 (decomposition, verified):** 27 = 23 baseline IDs byte-identical to the
  v1 list (`phase_1_worker_money_redaction.md:198-220`, diffed name-by-name)
  + 3 foreign (`test_seed_item_economics_configuration.py`, owner's untracked
  in-flight bootstrap work) + K1.
  **K3 (hard-field gap):** observed-red ledger covers 1 of ~20 named mutations
  (C1 only, honestly declared). C18's discipline requires the complete ledger.
  **K4 (missing criterion):** C13b's service-invoking door-mapping test absent.
  **K5 (perimeter note):** checkpoint `0b85701` committed
  `.archgraph/architecture.yml` whole, carrying the PRE-EXISTING foreign graph
  delta alongside the phase's 5-node/9-edge delta — flagged to owner; not
  splittable cheaply, recorded for the approval gate.
  **K6 (audit gap):** handoff maps no criterion→test-node table; r1b must
  provide it so review can audit C1–C21 coverage row-by-row.

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

- **Round 1b consumption (coordinator, 2026-08-16)** — routed to FIX ROUND r1c
  (test-only) before first review. Verified: checkpoint `d4d51af` perimeter clean
  (test files only, K5 respected — no architecture.yml); full suite re-run by
  coordinator = 26 failed / 2278 passed, failure decomposition 23 baseline + 3
  foreign confirmed (handoff said 2277 passed — one extra passing collected test,
  foreign-side drift, recorded). The complete F2 ledger did its job and exposed:
  **9 surviving mutations** (C6, C9c, C9d-statistic, C9d-rounding, C10a, C10b,
  C13b-door2, C16, C20) and **5 uncovered criteria** (C9b, C9c, C9d, C10, C11) —
  fourteen criterion-rows unproven, review would be a guaranteed
  CHANGES_REQUESTED. Special risk flagged for r1c: C9c/C9d survivals mean the
  D9 group-window admission and the cont+half-even statistic are UNPROVEN IN
  PRODUCTION — the missing fixtures must decide whether production violates M1
  as contracted (if so: production fix, recorded per-site). C16's survival is
  anomalous (an at-fifty test that tolerates `>=`) — site or fixture is wrong.
  C20's survival may mean the guard is naturally redundant — equivalence
  analysis required, not silent acceptance.

- **Round 1c (implementer, 2026-08-16, Codex)** — IMPLEMENTED (test-only).
  Added padded, teardown-owned M1 fixtures for per-(task, section) aggregation,
  group-level latest-close admission, continuous median plus half-even rounding,
  independent completed/accurate predicates, and the five-group boundary. Added
  M2 fixtures showing that all live non-excluded states participate and that a
  deleted skipped step is outside the universe while a live skipped step is charged.
  Corrected the 50-ID route test to execute the command rather than bypass it.
  The W2/W3 fixtures confirm production complies with M1, so no production changes
  were needed. Mutations for C6, C9b–d, C10, C11, and C16 now turn red. C13b-door2
  and C20 are formal equivalence STOPs: both mutations are downstream-redundant of
  the live-step partition, with identical observable results. Focused tests: 30
  passed. Full non-E2E suite: 2286 passed, 26 failed, 1 deselected (23 v1 baseline
  + 3 foreign bootstrap-seeding failures). No Architecture Graph mutation was made.

- **Round 1c consumption + STOP adjudication (coordinator, 2026-08-16)** —
  verified: checkpoint `fb48d13` perimeter test-only as declared; focused suite
  re-run by coordinator = 30 passed; full-suite failure list = 23 baseline + 3
  foreign (unchanged from r1b, re-verified there). Ledger CLOSED: every
  criterion-row has an observed-red record except two adjudicated equivalences:
  **C13b-door2 ACCEPTED** — `excluded` is constructed from `live_steps`, which
  already filters `is_deleted`; the named mutation site is unreachable by
  construction, and the protective red lives at C13a (loader filter) with the W8
  fixture pinning both observables (deleted+skipped invisible; live skipped
  charged). The door-2 named mutation is recorded as subsumed by C13a.
  **C20 ACCEPTED** — with an empty allocated set, every downstream loop (weights,
  raw shares, floors, remainder, allocation rows) is vacuously empty and the
  output is identical with or without the guard; the guard stays as a readable
  fast path, the criterion is satisfied by its behavior-pinning test, and the
  named-mutation requirement is waived by this record.
  W2/W3 production verdicts: **complied** (group-by task+section, MAX(closed_at)
  admission, percentile_cont, half-even double rounding — each now pinned by a
  red-proven fixture). C16 root cause: the old test asserted through the
  monkeypatched service, bypassing the cap; now invokes the real command.
  Phase → REVIEWING; review r1 compiled LIGHT-SCOPED (owner-ratified in
  conversation after r1b: projection r0 did the deep semantic walk, the closed
  ledger is auditable — the review verifies rather than re-derives).

- **Round 1 (review, 2026-08-16, Opus 5) — CHANGES_REQUESTED (0 blocking / 5
  should-fix / 8 notes).** Both rule-6 mechanisms verified CORRECT line-by-line
  (M1 generated SQL + M2 function, full walk recorded in the handoff's
  "Verified correct" section — settled ground, do not re-derive); ledger sampled
  honest on six rows; perimeter over `0b85701^..fb48d13` clean; suite reproduced
  2286/26/1 with mechanical 23+3 decomposition; both equivalence adjudications
  upheld. Findings (all coverage, all probe-confirmed):
  **S1** E2 inlines a second unproven copy of the M1 aggregation
  (`_load_typicals` — `return {}` leaves 33 tests green; no E2 fixture has two
  sections with differing typicals) → extract shared statement builder + E2
  two-section 2:1 row. **S2** C14's fixture never runs the resolver path (the
  N8-site mutation passes green) → evaluation-less task WITH primary item in
  both calls. **S3** C17's E2 step key-set assertion missing (HC-3 hole:
  `consumed_cost_minor` on steps passes green) → third key-set + step-wide money
  scan. **S4** C15's E1 row can't detect P7 shadowing (declaration below the
  param route passes green) → service-identity assertion. **S5** C13's
  byte-agreement clause unasserted → budget-status comparison on the fixture.
  Notes: N-a README detail sections incomplete/misplaced; N-b mirror-comment now
  false for E2's row; N-c dead `_binding`; N-d/N-e minor unasserted clauses;
  N-f/N-g cosmetics; **N-h routed to intention round 7** (fifth null field on
  unevaluated E2 tasks + §6 qualifier; carries to the frontend handoff at
  closeout). Handoff:
  `../handoffs/reviewer/2026-08-16_phase1_review_r1_handoff.md`. Fix r2 prompt
  compiled; re-review r2 will be delta-scoped per charter.

- **Round 2 (implementer fix, 2026-08-17, Codex) — IMPLEMENTED.** F1 extracted
  the registered `typical_times_statement(...)` grouped-median builder into the
  E1 query module and made E2 call it; the E2 fixture now has two sections with
  pinned 3600/1800 typicals and a 2:1 allowance split. F2 made C14's
  evaluation-less task carry a PRIMARY item and valuation, and both calls execute
  the resolver path; the local query-count fixture pins the eleven-statement
  batch shape. F3 adds the E2 step exact-key-set assertion and scans nested step
  keys for money terms. F4 pins E1 route service identity. F5 compares E2's
  `actual_worker_seconds` with `get_task_budget_status` on the same C13 fixture.
  F6 completes both README detail contracts, rewords the route-mirror comment,
  removes dead `_binding`, hoists the excluded-state set, restores the new
  import's order, and pins C3/C5b clauses. No production behavior changed except
  the F1 shared-builder refactor; `division_serializers.py` was untouched by the
  fix itself. Focused phase/mirror suite: 140 passed. Full non-E2E suite:
  2287 passed, 26 failed, 1 deselected; the 26 are exactly the 23 inherited
  baseline IDs plus the three foreign bootstrap-seeding IDs in
  `test_seed_item_economics_configuration.py`.

  **Criterion → test map (lettered compound rows):**

  | Criterion row | Exact test node |
  |---|---|
  | C13a — deleted/excluded row set and charged consumption | `tests/integration/services/queries/item_economics/test_budget_allocations_query.py::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
  | C13b — remove-service state/deletion mapping | `...::test_remove_service_maps_a_removed_step_to_deleted_skipped` |
  | C13c — E2/status actual-seconds agreement | `...::test_budget_allocation_keeps_excluded_consumption_and_deleted_steps_distinct` |
  | C14a — one/three-call query-count equality | `...::test_budget_allocation_constant_query_count_for_one_and_three_tasks` |
  | C14b — eval-less PRIMARY item + valuation resolver path | same C14 test node (fixture property) |
  | C14c — unknown task omission and status degradation | same C14 test node |
  | C14d — other-workspace task omitted from the batch result | same C14 test node |
  | C15a — E1 all-role admission/envelope | `tests/unit/routers/api_v1/test_budget_division_routes.py::test_both_surfaces_admit_every_role_and_use_the_standard_envelope` |
  | C15b — E1 service identity/order | same C15 test node |
  | C15c — E2 all-role admission/envelope | same C15 test node |
  | C17a — E1 exact key set | `...::test_time_payload_serializers_have_exact_money_free_key_sets` |
  | C17b — E2 task exact key set | same C17 test node |
  | C17c — E2 step exact key set + nested money scan | same C17 test node |

  **Round-2 mutation ledger (all probes applied at the named site, observed red,
  and reverted byte-for-byte):**

  | # | Mutation/site | Test node and observed red | Reverted |
  |---|---|---|---|
  | 1 | `get_task_budget_allocations.py::_load_typicals`: `return {}` | `test_budget_allocation_uses_shared_typicals_for_two_section_proportional_split`; `None != 3600` | yes |
  | 2 | `get_task_budget_allocations.py` immediately before `resolve_economics_selection`: per-task workspace-wide `ProductionCostGroup` SELECT | `test_budget_allocation_constant_query_count_for_one_and_three_tasks`; `assert 12 == 11` | yes |
  | 3 | `division_serializers.py::serialize_budget_step`: add `consumed_cost_minor` | `test_time_payload_serializers_have_exact_money_free_key_sets`; extra key in exact-set assertion | yes |
  | 4 | `working_sections.py`: move E1 declaration below `/{working_section_id}` | `test_both_surfaces_admit_every_role_and_use_the_standard_envelope`; captured command was `get_working_section` instead of E1 service | yes |
  | 5 | `get_working_section_typical_times.py::typical_times_statement`: remove `(working_section_id, task_id)` GROUP BY | `test_typical_query_aggregates_same_task_section_steps_before_sampling`; PostgreSQL grouping error at the shared builder | yes |

- **Fix r2 consumption (coordinator, 2026-08-17)** — verified: checkpoint
  `7f09637` file set matches the declared fix perimeter exactly (E2 −55 lines =
  the deleted inline M1 copy; shared `typical_times_statement` extraction
  landed); focused suite re-run by coordinator = 140 passed. Delta ledger: five
  probes, five reds, including the two review-r1 green-survivors now biting
  (S1 `return {}` → `None != 3600`; S2 rationale-site query → 12 != 11).
  Lettered map delivered (C13a-c, C14a-c, C15a-c, C17a-c). Suite 2287/26/1 =
  23 baseline (enumerated in the handoff, byte-identical) + 3 foreign.
  Phase → REVIEWING; re-review r2 compiled DELTA-SCOPED per charter.

- **Re-review r2 (2026-08-17, Opus 5) — CHANGES_REQUESTED (1 should-fix / 2 doc
  notes).** ALL round-1 findings S1–S5 CLOSED and probe-confirmed (probes 1–4
  re-applied, red with matching values); S1 seam verified clause-by-clause
  (percentile_cont at exactly ONE site repo-wide; E2 specifics outside the
  builder; generative select — no leak); suite 2287/26/1 reproduced, failure set
  byte-identical to reviewer's r1 run; lettered-map spot-checks accurate;
  perimeter clean (the extra file in the span belongs to the coordinator's
  hash-record commit `baa108b`, not the fix). NEW: **S6** — F2 weakened two exact
  status assertions to `!= "ok"`; reviewer's probe 5 regressed the fixture to the
  r1 shape (dropped the PRIMARY item) with all 4 tests green — the S2 defect is
  closed today but not durably. Correction measured by the reviewer:
  pin `not_configured_no_cost_group` (resolver-produced, distinguishes from the
  `not_evaluated` short-circuit) on both calls. N-i: E2 README section wedged
  inside the working-sections block (fix handoff's "path-ordered" claim
  inaccurate) — belongs before item-upholsteries `:1893`. N-j: E2 422 table
  missing header-separator row; restore the dropped worker-service sentence as a
  comment above the budget-status mirror row. N-k folded by coordinator (lettered
  rows now in this plan). N-l: rename `no_item_*` fixtures at next touch (r3
  touches that file — do it). Two rules earned → master plan §6
  (no-weaker-assertions; fixture-property-pin). Fix r3 prompt compiled
  (test/docs only); re-review r3 delta-scoped on S6+N-i/N-j.

- **Fix r3 (implementer, 2026-08-17, Codex) — IMPLEMENTED.** F1 strengthens the
  C14b fixture-property pins to `ok` for the evaluated task and
  `not_configured_no_cost_group` for the evaluation-less task on both calls; the
  single mandated fixture regression probe produced `not_evaluated` and was
  reverted. F2 moves the E2 README detail into `/api/v1/item-*` path order and
  F3 restores the E2 422 separator plus the budget-status worker-service
  comment. F4 renames the fixture family to `unevaluated_*`. No production or
  Architecture Graph changes. Focused phase/mirror suite: 140 passed. Full
  non-E2E suite: 2287 passed, 26 failed, 1 deselected, 2 warnings; failures are
  the unchanged 23 inherited baseline IDs plus 3 foreign bootstrap IDs. The
  checkpoint hash and complete ledger are recorded in the r3 implementer
  handoff.

- **Fix r3 consumption (coordinator, 2026-08-17)** — verified: checkpoint
  `99ade31` perimeter matches (test file, README, mirror comment, pipeline docs —
  no production files); the three exact pins present at
  `test_budget_allocations_query.py:192-194`
  (`not_configured_no_cost_group` / `ok` / `not_configured_no_cost_group`);
  coordinator re-ran the E2 test file green (4 passed). One-probe delta ledger:
  reviewer's probe 5 now bites (`'not_evaluated' == 'not_configured_no_cost_group'`
  red). Suite 2287/26/1 = 23 baseline + 3 foreign (unchanged shape).
  Phase → REVIEWING; re-review r3 compiled, delta-scoped to S6/N-i/N-j closure.

- **Re-review r3 (2026-08-17, Opus 5) — CHANGES_REQUESTED (1 should-fix / 0
  notes).** S6/N-i/N-j/N-l/N-k ALL CLOSED (probe 1 = r2's probe 5 re-applied,
  now red with the exact prescribed pair; README placement/table/mirror comment
  hand-checked; no-weaker-assertions PASSES — the E2 seam moved only
  `!=` → `==` plus one added assertion); perimeter exactly the declared five
  files; suite byte-identical to r2. NEW: **S7** — C14c's other-workspace row
  has never existed (demanded since r1); reviewer probe: deleting
  `Task.workspace_id == ctx.workspace_id` from E2's visibility query leaves all
  26 phase tests green. Production filter present and correct — coverage hole;
  blast radius if regressed = task-existence disclosure (downstream queries stay
  scoped), violating §5's batch-read omission contract. Owner heard the
  story-form assessment and chose to FIX (2026-08-17, "perfect, let's make the
  implementer prompt"). Also recorded: probe-4 EQUIVALENCE — the M1 subquery's
  `TaskStep.workspace_id` filter is redundant defence-in-depth (globally-unique
  section client_ids); do not re-open. Fix r4 prompt compiled (test-only, one
  row); re-review r4 minimal delta on S7 alone.

- **Fix r4 (implementer, 2026-08-17, Codex) — IMPLEMENTED.** F1 adds a second
  workspace and task with no dependent item/evaluation/step rows to `_seed`,
  passes that foreign task id in the existing C14 batch, and asserts its id is
  absent while retaining the exact `len(...) == 2` and `first_count == 11` pins.
  `_cleanup` deletes the foreign task before the foreign workspace. The one
  named definition-site mutation (remove `Task.workspace_id == ctx.workspace_id`
  from the E2 visibility query) produced `AssertionError: assert 3 == 2` at
  `test_budget_allocations_query.py:193` and was restored byte-for-byte. No
  production or Architecture Graph changes. Focused E2 file: 4 passed. Full
  non-E2E suite: 2287 passed, 26 failed, 1 deselected, 2 warnings; failures are
  the unchanged 23 inherited baseline IDs plus 3 foreign bootstrap IDs. The
  checkpoint and complete ledger are recorded in the r4 implementer handoff.
