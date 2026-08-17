---
plan: 2
role: implementer
round: 1
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Implement round 1 — plan 2 (task-scoped section-keyed production-time view, E3 + M3)

You are the implementer (implementation-executor doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md`). You implement plan 2 exactly as
amended after projection round 0 — every decision you might be tempted to make in code has
already been made. Where you find one that has not, **STOP and report** rather than
settling it silently.

**This phase modifies an approved, shipped mechanism.** Phase 1 closed 2026-08-17 with
zero production defects; D11 changes the unit `divide_production_budget` allocates to, and
E2 — which real frontend work is waiting on — reads it. Precision about what must *not*
move matters as much as what must.

## Read first (in this order; paths repo-root-relative to `backend/`)

1. `docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md`
   — **§12 at round 10 is your contract.** §12.4 (all 14 measured counts), §12.5
   (M3.1 outer join · M3.5 charging-vs-weighting · M3.5b the split · M3.5c the label ·
   M3.8a `percent_consumed`), §12.6 (properties, incl. P1's scoping), §12.7 (E3 shape).
   §3–§6 stay in force for M1/M2 semantics phase 2 does not change.
   **Round 9's M3.5b and its "exclusion is decided at the allocated unit" clause are
   SUPERSEDED.** Building either reverses D8 and rewrites five phase-1 assertions.
2. `…/planning/owner_decisions.md` — D9, D11, D11a, D12, **D13, D14, D15**.
3. `…/master_plan.md` — §4 naming registry (names are final), §6 standing rules + the nine
   earned rules + the MVP calibration rule, **§7 environment and the phase-2 baseline**.
4. `…/plans/plan_2.md` — T1–T7b, criteria **C1–C26**. The criteria are your test list.
5. `…/handoffs/reviewer/2026-08-17_phase2_projection_r0_handoff.md` — §1's measured table,
   **§3's per-test impact table (column (ii) is your T7b work list)**, and the exact
   named-mutation wording in P8/P9. **Do not read its appendix** (non-authoritative by
   doctrine).
6. Code precedents, read before writing:
   - `domain/item_economics/budget_division.py` — whole file
   - `services/queries/item_economics/get_task_budget_status.py` — **E3 calls this**
   - `domain/task_steps/constants.py:4-9` — `TERMINAL_STEP_STATES`
   - `domain/item_economics/serializers.py:193,243-249` (the `percent_consumed`
     injection precedent) and `:207-217` (`_serialize_result` — the money hazard)
   - `models/tables/tasks/task_step.py:117-121` — `latest_state_record`, lazy
   - `tests/unit/routers/api_v1/test_item_economics_router.py:126-139`

## Hard constraints (violating any one is a failed round)

- **HC-8:** zero migrations, zero new indexes, zero persisted state, no
  `CALCULATION_VERSION` bump. If you believe you need a migration: **STOP, report.**
- **HC-1/HC-1a — the ONLY pre-existing files you may modify:**
  1. `app/beyo_manager/domain/item_economics/budget_division.py` — T1/T2/T3 (this
     pipeline's own phase-1 file; evolving it is authorized, see T7b)
  2. `app/beyo_manager/domain/item_economics/division_serializers.py` — T5
  3. `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` —
     only as B1 requires (it keeps reading `division["steps"]`)
  4. `app/beyo_manager/routers/api_v1/item_economics.py` — the E3 route
  5. `app/tests/unit/routers/test_phase9_item_economics_route_mirror.py` — one row,
     counts **24 → 25**
  6. `app/tests/unit/routers/api_v1/test_item_economics_router.py` — one row **plus
     B10's third dispatch branch**
  7. `app/beyo_manager/routers/README.md` — Quick Index row (24 → 25) + detail section
  8. the phase-1 test files, **only** as T7b enumerates
  Everything else must be NEW, per master plan §4.
- **HC-6 — one allocator.** No second function computes an allowance. The per-step split
  lives in `budget_division.py`, **never in E2**. C19 is the mechanical check.
- **HC-7 — time only, role-flat.** No monetary key at any depth. No role branching in the
  new serializer — E3 calls the **manager** budget-status variant for all four roles and
  never emits its monetary fields. **Do not reuse `serialize_item_cost_result` for
  `final`**; write a time-only builder (it would put money at depth 2 with one import).
- **`C` does not move to the group unit** (B4/D15): it stays Σ worked over non-deleted
  excluded **steps**. M3.5b's residual subtracts only **completed** steps' seconds.
- **Liveness is `state NOT IN TERMINAL_STEP_STATES`**, imported, never re-listed (B7).
- **Grouped-unit remainder tie key is `working_section_id` ASC** for both callers (B6) —
  deliberately not M3.2's render order.
- **Exact rational arithmetic** — `fractions.Fraction`, no float anywhere in the division.
- **No return-type annotation on the route; set `response_model=None` explicitly** (N4).

## Deliverables (master plan §4 names, verbatim)

New: `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`;
tests for C1–C26 under the existing phase-1 test locations plus
`app/tests/integration/services/queries/item_economics/test_production_time_query.py`
and `app/tests/unit/routers/api_v1/test_production_time_routes.py`.
Modified: the eight files enumerated above, nothing else.
Route: `GET /api/v1/item-economics/tasks/{task_client_id}/production-time`, roles
ADMIN/MANAGER/WORKER/SELLER. Label: `ALLOCATION_METHOD` →
**`static_proportional_section_v1`** (M3.5c).

## Non-negotiable test discipline

- Every named RED mutation must actually turn its test red: **mutate → observe red →
  revert → confirm the file is byte-identical (`sha256`)**. Record each observed-red
  output in the handoff. This is a HARD handoff field. The mutations you must run at
  minimum: C5 (restore per-step weighting), C6 (delete the governing-step rule), C14
  (`final` via `serialize_item_cost_result`), C15 (delete the workspace filter), C22
  (inner-join the section attributes), C23 (switch one caller's tie key to M3.2's order),
  C25 (emit the live name twice).
- Tests that commit rows own their teardown (charter 11½); name the tables your residue
  check scanned.
- Key-set assertions are exact set equality; fixture values pairwise distinct.
- **No weaker assertions, ever** — if a phase-1 assertion goes red, either the contract
  says its value changed (T7b lists exactly two such tests) or you have a defect. Loosening
  it is a failed round.
- **T7b is closed and enumerated: exactly two phase-1 tests change value** —
  `test_live_partition_includes_working_paused_and_completed_steps` at `:105` and `:120`.
  `test_uses_shared_typicals_for_two_section_proportional_split` (`:160`) keeps its values
  but its invariant becomes section-level (P1) — restate it, do not loosen it. If any other
  phase-1 test moves, **stop and report**: you have built something other than this
  contract.

## Suite and baseline (verified by the coordinator 2026-08-17 — do not trust, re-verify)

From `backend/app/`, containers healthy (`make dev-up`):
`PYTHONPATH=. pytest -m 'not e2e'`.

**Start baseline: 2287 passed / 26 failed / 1 deselected**, head `c1d2e3f4a5b6`. The 26
IDs are byte-identical to the phase-1 closeout list (23 long-standing inherited + 3 from
the owner's bootstrap item-economics seeding). Before you change anything, run the suite
and confirm you reproduce that set.

**Diff failure IDs, never totals.** One of three coordinator runs reported 25 failed /
2288 passed, and that run's IDs were not captured, so one test in the suite is
order/state-sensitive and is **not named**. A run showing 25 is not "better than
baseline" — it means a test moved and you must identify which one before claiming
green-per-baseline. A run that cannot reach the DB is never a baseline.

Expected at handoff: 2287 + your added tests passed, the same 26 failures, 1 deselected,
zero new failures. Record exact totals **and** the failure-ID diff.

## Checkpoint commit (standing owner authorization)

When green-per-baseline, commit everything with subject prefix
`CHECKPOINT (not approved): plan2 implement r1 — section-keyed production time`.
Do not push. The handoff cites the hash.

## Handoff

Write `…/handoffs/implementer/2026-08-17_phase2_implement_r1_handoff.md`:
frontmatter (`plan: 2, role: implementer, round: 1, state: IMPLEMENTED, actor: <model>`);
the checkpoint hash; your **full write perimeter** (every file created or modified — it
will be diffed against git); the suite totals and failure-ID diff; the observed-red output
for every named mutation; a criterion-by-criterion table (C1–C26 → test name → pass);
T7b's enumeration with old and new literals and the cause of each change; and an explicit
statement of the five properties (P-SUM3, P-ORDER, P-COVER, P-AGREE, P-FLAT) as
**verified, not assumed**, each with the test that verifies it.

Anything you had to decide that the artifacts did not decide goes in a **DECISIONS I HAD
TO MAKE** section, flagged, not buried.
