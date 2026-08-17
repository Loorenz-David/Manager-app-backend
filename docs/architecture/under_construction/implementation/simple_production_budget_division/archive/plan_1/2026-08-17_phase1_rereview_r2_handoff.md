---
plan: 1
role: reviewer
round: 2
state: REVIEWED
verdict: CHANGES_REQUESTED
actor: Claude (Opus 5, plan-reviewer doctrine)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Phase 1 re-review round 2 — delta-scoped

## Summary

**Verdict: CHANGES_REQUESTED — one should-fix (S6), two notes. All five round-1
findings (S1–S5) are CLOSED and probe-confirmed; six of seven notes are closed.**

The fix round did the substantive work correctly. The S1 refactor is clean: the M1
grouped-median statement now has exactly one implementation in the codebase
(`percentile_cont` appears at exactly one site repo-wide), it is registered in master
plan §4, E1's ordering and filter live outside the shared builder, and the extraction
is semantically identical to the SQL I verified in round 1. All four of the mutations
that sailed through green in round 1 now bite. My independent suite reproduces
2287 / 26 / 1 with a failure set byte-identical to my own round-1 run.

What holds the gate is narrow and new: **the F2 fix weakened two previously-exact
status assertions to `!= "ok"`**, and I confirmed by probe that this makes S2's
fixture property silently degradable — deleting the evaluation-less task's PRIMARY
item, which restores the exact round-1 shape where `resolve_economics_selection`
never runs, leaves all four tests green. The defect S2 named is genuinely closed
today; what is not closed is the fixture's ability to stay closed. This is a
disjunction assertion of the kind charter standing rule 2 forbids, and it misses the
**rationale-site rule** the master plan earned from round 1 and recorded in §6 this
very cycle. The correction is two exact values, both of which I measured for the
implementer and record below.

⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs an owner answer. No graph adjudication requested; K5 remains recorded
for the approval gate as agreed.

## Write perimeter (this session)

- `docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase1_rereview_r2_handoff.md`
  — this file, and nothing else.

No plan, master-plan, code, test or architecture-graph mutation was made.

## Verified perimeter

The prompt's span `fb48d13 → 7f09637` contains **two** commits: `baa108b` (the
coordinator's r1c hash-record) and `7f09637` (the fix). Diffed separately so the fix
is judged on its own files:

- `git diff --stat baa108b 7f09637` = **11 files**, and every one is on the fix
  handoff's declared fix-owned list. The twelfth declared entry is the handoff
  itself, committed in `d1d302e`.
- The one file in the wider span that is *not* on the declared list —
  `handoffs/implementer/2026-08-16_phase1_implement_r1c_handoff.md` (4 lines) —
  belongs to `baa108b`, the coordinator's own hash-record commit that predates the
  fix. **Not a perimeter violation.**
- Production files touched: 4. Three are the round-1 notes (`budget_division.py`
  N-f hoist, `item_economics.py` N-g import order, plus the mirror comment N-b in a
  test) and one is the S1 seam. Each read and confirmed behaviour-preserving.
- HC-1a artifact touched: `test_phase9_item_economics_route_mirror.py` only (the
  N-b comment). HC-2 clean: no migration, no schema diff.
- Uncommitted at review time: the coordinator's fix-r2 consumption entry in
  `master_plan.md` / `plan_1.md`, plus the unchanged foreign dirt
  (`.archgraph/architecture.yml`, `bootstrap_app.py`, the untracked bootstrap-seed
  files and `to_implement_the_accurate_costs_and_projections/`). All accounted for;
  none of it mine.

## The S1 seam — full adversarial depth

`typical_times_statement(workspace_id)` in
`get_working_section_typical_times.py:21-64`, diffed against the round-1 verified
SQL rather than re-derived:

| M1 clause | Preserved? |
|---|---|
| `cutoff = now() − TYPICAL_WINDOW_DAYS`, computed **per call** | ✅ inside the function — no module-level staleness |
| subquery columns `(working_section_id, task_id, sum, max(closed_at))` | ✅ identical |
| four contributing predicates (workspace, `state='completed'`, `is_deleted`, `recorded_time_marked_wrong`) | ✅ identical; E2's old string literal `"completed"` is now the enum, same rendered SQL |
| `GROUP BY (working_section_id, task_id)` | ✅ identical |
| group-level window admission via `FILTER (WHERE max(closed_at) >= cutoff)` on both count and percentile | ✅ identical; still no per-step `closed_at` predicate |
| `percentile_cont(0.5) WITHIN GROUP (ORDER BY group_seconds)` | ✅ identical |
| `CAST(round(<double>) AS INTEGER)` — no `::numeric` | ✅ identical |
| `sample_count >= TYPICAL_MIN_SAMPLE_SIZE` gate | ✅ identical |
| `LEFT OUTER JOIN` from `working_sections` + outer workspace/`is_deleted` filter + `GROUP BY (client_id, name)` | ✅ identical |

**E2-specific concerns live outside the builder** ✅ — E1 alone appends
`.order_by(order_list NULLS LAST, created_at)` and the `working_section_ids` filter
(`:66-73`); E2 calls the bare statement (`:45`). SQLAlchemy `select()` is generative,
so E1's post-hoc `.order_by()`/`.where()` cannot leak into E2's statement, and each
call builds a fresh object.

**One-copy rule (master plan §6) satisfied** ✅ — `grep -rn percentile_cont
app/beyo_manager/` returns exactly one hit. E2's dict-shaping keeps only the three
fields it consumes; the drift surface is gone. Registered in master plan §4 as "the
ONLY implementation of the M1 aggregation".

Behaviour-preservation of the other three production edits: `budget_division.py:104`
hoists the excluded-state value set above the comprehension (same membership test);
`item_economics.py:34` moves an import into alphabetical order; the mirror comment is
prose. None alters a code path.

## Round-1 finding closure

| Finding | Closed? | Evidence |
|---|---|---|
| **S1** — E2's unproven M1 copy | ✅ **CLOSED** | Shared `typical_times_statement` extracted + registered (§4); `percentile_cont` at one site repo-wide; new `test_budget_allocation_uses_shared_typicals_for_two_section_proportional_split` pins typicals **3600** and **1800** exactly (5 qualifying groups each) and the 2:1 split. Probe 1 red. |
| **S2** — C14 fixture never ran the resolver path | ✅ **CLOSED** (durability gap → S6) | `no_item_task` now carries a PRIMARY `TaskItem` + `ItemValuation`, and it is the task used in **both** the 1-task and 3-task calls, so `resolve_economics_selection` executes in both. Probe 2 red (`12 == 11`). |
| **S3** — C17's E2 step key-set assertion missing | ✅ **CLOSED** | `test_budget_division_routes.py:158-168` adds the exact 8-key `serialize_budget_step` set **and** a nested step-wide money scan. Probe 3 red. |
| **S4** — C15's E1 row couldn't detect P7 shadowing | ✅ **CLOSED** | `:50-51` asserts `calls[0][0] is working_sections.get_working_section_typical_times`. Probe 4 red on all four role rows. |
| **S5** — C13's byte-agreement clause unasserted | ✅ **CLOSED** | `test_budget_allocations_query.py:144-151` invokes `get_task_budget_status` on the same fixture and asserts `row["actual_worker_seconds"] == status.actual_worker_seconds`. |
| **N-a** README | ⚠️ **HALF-CLOSED** | Request Body / Responses blocks now present in house format with full payload-key tables for both routes ✅. Path ordering **not** fixed — see N-i. |
| **N-b** mirror comment | ✅ **CLOSED** | Re-worded to "The all-role read-only route; its payload is time-only for every identity" — accurate for budget-allocations. See N-j for a small side effect. |
| **N-c** dead `_binding` | ✅ **CLOSED** | Computation and the pop loop both removed (`get_task_budget_allocations.py:176-232`). |
| **N-d** C3 `on_track` clause | ✅ **CLOSED** | `test_budget_division.py:53`. |
| **N-e** C5b both integers | ✅ **CLOSED** | `test_budget_division.py:88` adds `rows["a"] == 1`. |
| **N-f** hoisted state set | ✅ **CLOSED** | `budget_division.py:104`. |
| **N-g** import order | ✅ **CLOSED** | `item_economics.py:34`. |
| **N-h** intention fold | ✅ **CLOSED** (coordinator) | intention round 7: §5's null list gains `actual_worker_seconds`; §6's sum-equality qualified to evaluated tasks. |

## New finding

### S6 (should-fix) — the F2 fix replaced two exact status assertions with `!= "ok"`, and the fixture property S2 depends on is now unguarded

`test_budget_allocations_query.py:193-194`. Before this fix the test asserted
`status == "ok"` and `status == "not_evaluated"`; it now asserts `!= "ok"` on both.

Charter standing rule 2 is explicit that an assertion accepting a disjunction of
outcomes hides mislabeling and that each case row asserts its **one exact expected
outcome**; `!= "ok"` admits all eleven non-`ok` statuses. The consequence is not
stylistic — it is exactly the failure the master plan's new **rationale-site rule**
(§6, earned from round 1 this cycle) exists to prevent: *"a criterion that specifies
a fixture property is checked as a fixture property."*

**Probe 5 (mine, confirmed):** removing `no_item_task_item` / `no_item_valuation`
from the fixture's `add_all` — which returns the evaluation-less task to the exact
round-1 shape where `item is None` short-circuits to `NOT_EVALUATED` at
`get_task_budget_allocations.py:180-181` and `resolve_economics_selection` never
runs — leaves **all 4 tests green**. Neither the `!= "ok"` assertions nor
`first_count == 11` can see the difference (the resolver is pure Python; the loads
are hoisted, so the count is 11 either way). S2 would silently re-open.

Correction — pin the exact values, which I measured on the current fixture:

- one-task call (`no_item_task`, resolver path): `status == "not_configured_no_cost_group"`
- three-task call: the evaluated task `== "ok"`, `no_item_task == "not_configured_no_cost_group"`

`not_configured_no_cost_group` is resolver-produced and therefore *distinguishes*
from `not_evaluated`, the short-circuit value — which is precisely what makes it a
valid fixture-property guard: with it in place, probe 5 turns red.

## Notes

- **N-i (documentation).** N-a's ordering half is not closed. The E2 detail section
  moved from *after* `GET /api/v1/working-sections/typical-times` to *before* it, so
  it now sits at `routers/README.md:3996`, wedged between `GET
  /api/v1/working-sections` (`:3967`) and `GET /api/v1/working-sections/typical-times`
  (`:4040`) — splitting the working-sections block. It is the file's only
  `### GET /api/v1/item-economics/…` detail section; in the file's path order it
  belongs near the `/api/v1/item-…` region (before `### GET
  /api/v1/item-upholsteries/…` at `:1893`). The fix handoff's claim "path-ordered"
  is inaccurate for this section. E1's section is correctly placed.
- **N-j (documentation).** Two small defects in the new README blocks: (1) the E2
  **422** response table at `:4033` is missing its markdown header-separator row
  (`| --- | --- | --- | --- |`), so that table will not render as a table — E1's 422
  block at `:4070` has it; (2) the N-b re-wording dropped the v1 sentence explaining
  that the budget-status handler picks the money-free worker service for WORKER and
  SELLER, which no longer appears anywhere in the mirror. Reviewer-requested change,
  so not a perimeter violation — but consider restoring that sentence as its own
  comment line above the budget-status row.
- **N-k (plan hygiene, coordinator).** The lettered rows C13a-c / C14a-c / C15a-c /
  C17a-c exist only in the fix handoff's map; `plans/plan_1.md` still carries the
  unlettered C13 / C13b / C14 / C15 / C17 criteria (`:174-207`). The lettered-parts
  rule was recorded in master plan §6 this round but not applied to the plan's own
  criteria text, so the map's letters are not anchored to anything a future session
  can read.
- **N-l (cosmetic).** `no_item_task` / `no_item_item` / `no_item_task_item` are now
  misleading names — that task has an item; what it lacks is an evaluation. Rename
  to `unevaluated_task` at the next touch.
- Positive observation worth keeping: the new `first_count == 11` absolute pin is a
  stronger guard than the equality alone — it independently caught probe 1
  (`10 == 11`) as well as probe 2 (`12 == 11`). And the widened workspace-scoped
  `_cleanup` correctly sweeps the new two-section fixture's historical tasks, steps
  and second section (rule 11½ satisfied).

## Probe results (prompt required ≥3; five run)

Every mutation applied at its named site, run, observed red, reverted.

| # | Finding | Mutation (site) | Observed red | Reverted |
|---|---|---|---|---|
| 1 | **S1** | `get_task_budget_allocations.py::_load_typicals` → `return {}` | `test_budget_allocation_uses_shared_typicals_for_two_section_proportional_split` FAILED `assert None == 3600`; also `…constant_query_count…` FAILED `assert 10 == 11` | ✅ |
| 2 | **S2** | per-task workspace-wide `ProductionCostGroup` SELECT immediately before `resolve_economics_selection` (`:184`) — the rationale site | `test_budget_allocation_constant_query_count_for_one_and_three_tasks` FAILED `assert 12 == 11` | ✅ |
| 3 | **S3** | `division_serializers.py::serialize_budget_step` + `consumed_cost_minor: 4321` | `test_time_payload_serializers_have_exact_money_free_key_sets` FAILED — `Extra items in the left set: 'consumed_cost_minor'` | ✅ |
| 4 | **S4** | `working_sections.py` — E1 declaration moved below `@router.get("/{working_section_id}")` | `test_both_surfaces_admit_every_role_and_use_the_standard_envelope` FAILED on all four role rows: `<function get_working_section> is <function get_working_section_typical_times>` | ✅ |
| 5 | **mine (→ S6)** | `test_budget_allocations_query.py::_seed` — drop `no_item_task_item` / `no_item_valuation` (fixture regressed to the round-1 shape) | **NO RED — 4 passed.** The fixture property is unguarded | ✅ |

Probes 1–4 confirm the fix handoff's delta ledger rows 1–4 exactly, including the
observed values. Ledger row 5 (`typical_times_statement` GROUP BY removal) was not
re-run — the equivalent M1 grouping mutation is already covered by my round-1 sample
(C9b, `assert 6 == 5`) and the builder's grouping clause is unchanged.

## Suite (P-L — re-measured)

`PYTHONPATH=. pytest -q -m 'not e2e'` from `backend/app/`:

**2287 passed, 26 failed, 1 deselected, 2 warnings in 128.01s** — matches the fix
handoff exactly. The +1 pass versus my round-1 run is the one added test.

Failure-list diff, computed mechanically:
- vs the 23 v1 baseline IDs: **all 23 present, none missing, byte-identical**;
- extra: **exactly the 3 foreign** `test_seed_item_economics_configuration.py` IDs;
- vs my own round-1 failure set: **`diff` reports the two sets identical.**

Focused re-run at HEAD after all probes: **140 passed** across the four phase files
plus the two v1 mirror files.

## Lettered-map spot-checks (prompt item 6)

- **C15b (E1 service identity)** → `test_budget_division_routes.py:44-51`. Accurate:
  the row asserts `calls[0][0] is working_sections.get_working_section_typical_times`
  under the `path == "/api/v1/working-sections/typical-times"` branch, and probe 4
  proves it bites.
- **C17c (E2 step key set)** → `test_budget_division_routes.py:158-168`. Accurate:
  exact 8-key equality on `serialize_budget_step` plus the nested step money scan,
  and probe 3 proves it bites.

Both map rows check out against the actual test bodies.

## Mutation-probe declaration

Files touched by probes, each applied-and-reverted and verified **byte-identical**
afterwards (`git diff 7f09637 -- app/beyo_manager app/tests` empty; SHA-256 re-checked
against the pre-probe baseline):

| File | SHA-256 (before == after) |
|---|---|
| `beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `4d05f41543bee2988825c5aec3026f19083d936c7743b2a23eb0609732010e9d` |
| `beyo_manager/domain/item_economics/division_serializers.py` | `bb5413be30f7a353498a171c157d7f4d0e16bd5a8964c5e319c781322832bdc9` |
| `beyo_manager/routers/api_v1/working_sections.py` | `fd23d4f2cfea4d12f64a75c0c64cc19f01c0c5abdcac94f3e6c58c70ef790c97` |
| `beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `8b133d04a9acb5e4876065c846e53743453c3950fc04efe60c26cb31a42ca09c` |
| `tests/integration/services/queries/item_economics/test_budget_allocations_query.py` | `f2118608c58bfa09428d19189db5815a6a9215452f2b67379dbebed3a35606cc` |

Database/state side effects: **none** — every probe ran through the phase's own
teardown-owning fixtures; no schema change, no migration, configured DB left at head.
The temporary `print` used to measure the exact status values was applied to the test
file and reverted (checksum above confirms).

## Carry-forward dispositions

| Item | Destination |
|---|---|
| **S6** | fix round r3 (test-only; two exact status values, given above) |
| N-i, N-j | fix round r3 alongside S6 — same README/mirror artifacts, one edit pass |
| N-k | coordinator, before closeout: letter `plan_1.md`'s C13/C14/C15/C17 criteria to match the delivered map |
| N-l | opportunistic rename at the next touch of the E2 fixture; no round of its own |
| N-h (closed) | already folded to intention round 7; carries to the frontend-handoff fold at closeout |

## Lessons for the plans

1. **A fix that satisfies a criterion by changing the fixture must strengthen, never
   weaken, the assertions that pin the fixture.** F2 met C14's fixture requirement
   and simultaneously removed the two assertions that could have detected the
   fixture regressing back. Fix prompts should carry an explicit "no assertion may
   become weaker than it was at the previous checkpoint" clause; it is cheaply
   checkable by diffing `==` → `!=` in the changed test seam.
2. The **rationale-site rule** (§6, earned last round) needs its companion stated:
   when a criterion's fixture property is what makes a guard meaningful, the fixture
   property gets its **own** exact assertion, chosen so that the degenerate fixture
   produces a *different* value. Here `not_configured_no_cost_group` vs
   `not_evaluated` is exactly such a pair.
3. Register lettered criterion rows in the **plan** at the moment the lettered-parts
   rule is adopted, not only in the handoff map (N-k) — otherwise the next session
   reads letters that resolve to nothing.

## Human-authorization backlog

None. No architecture-graph adjudication is requested by this review, and no owner
decision is required to act on S6 or on any note.
