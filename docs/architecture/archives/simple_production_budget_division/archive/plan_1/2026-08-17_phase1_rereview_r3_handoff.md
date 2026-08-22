---
plan: 1
role: reviewer
round: 3
state: REVIEWED
verdict: CHANGES_REQUESTED
actor: Claude (Opus 5, plan-reviewer doctrine)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Phase 1 re-review round 3 — delta-scoped, minimal

## Summary

**Verdict: CHANGES_REQUESTED — one should-fix (S7), zero notes. Every item on this
round's acceptance list closed cleanly.**

Fix r3 did exactly what it was asked and nothing else. S6 is closed and now
self-guarding: my round-2 probe, which stayed green then, turns red now with the
exact distinguishing pair I prescribed (`'not_evaluated' == 'not_configured_no_cost_group'`).
N-i, N-j and N-l all close on hand-check, and the coordinator additionally closed
N-k — `plan_1.md` now carries the lettered criteria C13a-c / C14a-c / C15a-c /
C17a-c, so the fix handoffs' maps finally anchor to something. Perimeter is exactly
the declared five files. Suite reproduces 2287 / 26 / 1 with a failure set
byte-identical to my round-2 run. The no-weaker-assertions check passes: the E2 test
seam moved only in the strengthening direction (`!=` → `==`, plus one assertion
added).

What holds the gate came out of this round's own instruction to spot-check the
lettered rows. **C14c** — newly lettered as "unknown id omitted, **other-workspace
omitted**" — has no other-workspace row behind it, and never has: the original C14
demanded it since r1 (`plan_1.md:187-188`, "3 ids: one ok, one unknown (omitted),
one other-workspace (omitted)"). I probed it: deleting E2's
`Task.workspace_id == ctx.workspace_id` filter leaves all 26 phase tests green. The
production filter is present and correct — this is a coverage hole, not a live
defect — but it is the workspace boundary on an all-roles endpoint, and the letter
now asserts coverage that does not exist. I own having missed this in rounds 1 and 2;
my C14 attention went to the constancy proof and the resolver path. The correction
is one extra workspace + task in the fixture and one assertion.

⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs an owner answer. No graph adjudication requested; K5 remains recorded
for the approval gate.

## Write perimeter (this session)

- `docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase1_rereview_r3_handoff.md`
  — this file, and nothing else.

No plan, master-plan, code, test or architecture-graph mutation was made.

## Verified perimeter

The prompt's span `7f09637 → 99ade31` contains two commits; diffed separately so the
fix is judged on its own files:

- `git diff --stat d1d302e 99ade31` (fix only) = **5 files**: the E2 test file, the
  README, one comment line in the mirror test, `master_plan.md`, `plans/plan_1.md`.
  All five are on the fix handoff's declared fix-owned list; the sixth declared entry
  is the handoff itself.
- The extra file in the wider span — `handoffs/implementer/2026-08-17_phase1_fix_r2_handoff.md`
  (+149) — belongs to `d1d302e`, the coordinator's record commit that predates the
  fix. **Not a perimeter violation.**
- **No production file changed** — confirmed against the diff, matching the handoff's
  claim. HC-2 clean; no migration, no schema diff.
- HC-1a artifact touched: `test_phase9_item_economics_route_mirror.py`, one added
  comment line.

**No-weaker-assertions check (master plan §6, earned last round): PASSES.** The only
assertion changes in the E2 seam are `!= "ok"` → `== "not_configured_no_cost_group"`
(×2) and one *added* assertion pinning the evaluated task to `== "ok"` in the
three-task call. Everything else in that file is the N-l rename. Nothing weakened.

## Closure table

| Item | Closed? | Evidence |
|---|---|---|
| **S6** — exact status assertions / fixture property unguarded | ✅ **CLOSED** | `test_budget_allocations_query.py:192-194` pins all three values exactly, including the evaluated-task `== "ok"` row that did not exist before. Probe below turns red. |
| **N-i** — E2 README section out of path order | ✅ **CLOSED** | Moved to `routers/README.md:1646`, in the `/api/v1/item-…` region immediately before `### GET /api/v1/item-upholsteries` (`:1691`) — exactly the landing spot named in r2. The working-sections block is whole again: `GET /working-sections` (`:4012`) → `GET /working-sections/typical-times` (`:4041`) → `PUT /working-sections` (`:4078`), no interruption. Both Quick Index rows intact (`:79`, `:155`). |
| **N-j** — missing 422 separator + lost mirror sentence | ✅ **CLOSED** | The E2 422 table now carries its `\| --- \| --- \| --- \| --- \|` header-separator row and renders as a table. The worker-service sentence is restored as its own comment line directly above the budget-status row (`test_phase9_item_economics_route_mirror.py:61`), with E2's own comment retained above its row — both routes now documented, neither comment misattributed. |
| **N-l** — misleading fixture names | ✅ **CLOSED** | `no_item_*` → `unevaluated_*` throughout `_seed`, its return tuple, all three unpackings and `_cleanup`. Consistent; no stragglers. |
| **N-k** — plan letters not anchored (routed to coordinator in r2) | ✅ **CLOSED** | `plans/plan_1.md:215-237` now carries C13a-c / C14a-c / C15a-c / C17a-c with the lettered-parts rule cited. C14b is stated as a fixture-property criterion carrying its own guard value — a good use of the rule. |
| Master plan §6 | ✅ | Absorbed both r2 lessons (no-weaker-assertions; fixture-property-gets-its-own-exact-assertion, with the `not_configured_no_cost_group` vs `not_evaluated` pair recorded). |

## New finding

### S7 (should-fix) — C14c's other-workspace row does not exist; E2's workspace filter is unguarded

`plans/plan_1.md:231` letters C14c as *"batch semantics rows: unknown id omitted,
other-workspace omitted"*, and the original C14 has demanded that third row since r1
(`:187-188`). `test_budget_allocation_constant_query_count_for_one_and_three_tasks`
passes `[task, unevaluated_task, "tsk_unknown"]` — an evaluated task, an
evaluation-less task, and an unknown id. **No test in the phase seeds a second
workspace at all** (`grep` for `other_workspace` / `ws_other` across the E2 and route
test files returns nothing).

**Probe (confirmed):** deleting `Task.workspace_id == ctx.workspace_id` from E2's
visibility query (`get_task_budget_allocations.py:109-113`) leaves **all 26 phase
tests green**.

Blast radius if that filter ever regresses, stated precisely: every *downstream*
query (`TaskItem`, `Item`, `ItemCostEvaluation`, `TaskStep`, valuations) carries its
own `workspace_id == ctx.workspace_id` predicate, so a foreign task id would return
a row with `status: "not_evaluated"`, no steps and null figures — **task-existence
disclosure, not time or budget disclosure**. It is nonetheless a violation of
intention §5's batch-read contract ("Unknown/deleted task ids are omitted… Tasks
visible to the caller by the same workspace scoping every task read uses"): the
foreign task would appear as a row instead of being omitted. Authority: intention
§5; charter rule 2 (enumerate, never sample); master plan §6 guard-is-the-reason rule.

Correction: seed a second `Workspace` + `Task` in `_seed`, pass its id as a fourth
element of the three-task call, and assert it is absent from
`{row["task_id"] for row in result["budget_allocations"]}` — one row, and the probe
above must turn red. (The call already asserts `len(...) == 2`, so extending the id
list to four while keeping that count assertion gives the red for free.)

## Probe results

| # | Item | Mutation (site) | Observed | Reverted |
|---|---|---|---|---|
| 1 | **S6** (my r2 probe 5, re-applied) | `test_budget_allocations_query.py::_seed` — drop `unevaluated_task_item` / `unevaluated_valuation` from `add_all`, restoring the shape where `resolve_economics_selection` never runs | **RED** — `AssertionError: assert 'not_evaluated' == 'not_configured_no_cost_group'` (was 4 passed in r2) | ✅ |
| 2 | **S7** (passing glance) | `get_task_budget_allocations.py:109-113` — remove `Task.workspace_id == ctx.workspace_id` | **NO RED — 26 passed** | ✅ |
| 3 | passing glance | shared builder — remove outer `WorkingSection.workspace_id` filter | **RED** — M1 grouped rows return a foreign section (`assert 'wsec_01KVX0G…' == 'wsec_groups_33f6cf28b9'`); the section-enumeration boundary **is** guarded | ✅ |
| 4 | passing glance | shared builder — remove subquery `TaskStep.workspace_id` filter | 12 passed — **not a finding**: `working_section_id` holds globally-unique section client_ids, so foreign steps cannot join to this workspace's sections. Behaviour-equivalent defence-in-depth, same class as the adjudicated C13b-door2 / C20 equivalences. Recorded so a later round does not re-open it. | ✅ |

Probe 1 confirms the fix handoff's one-probe ledger row exactly, including the
observed assertion text.

## Suite (P-L — re-measured)

`PYTHONPATH=. pytest -q -m 'not e2e'` from `backend/app/`:

**2287 passed, 26 failed, 1 deselected, 2 warnings in 136.20s** — matches the fix
handoff.

Failure-list diff, computed mechanically:
- vs the 23 v1 baseline IDs: **all 23 present, none missing, byte-identical**;
- extra: **exactly the 3 foreign** `test_seed_item_economics_configuration.py` IDs;
- vs my round-2 run: **`diff` reports the two sets identical.**

Focused re-run at HEAD after all probes: **140 passed** across the four phase files
plus the two v1 mirror files.

## Mutation-probe declaration

Files touched by probes, each applied-and-reverted and verified **byte-identical**
afterwards (`git diff 99ade31 -- app/beyo_manager app/tests` empty):

| File | SHA-256 (before == after) |
|---|---|
| `app/tests/integration/services/queries/item_economics/test_budget_allocations_query.py` | `9e3967a68aeaffeb1ad8769b830a74845e88cc0be6f53f67894626bb43ae0f2d` |
| `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `4d05f41543bee2988825c5aec3026f19083d936c7743b2a23eb0609732010e9d` |
| `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `8b133d04a9acb5e4876065c846e53743453c3950fc04efe60c26cb31a42ca09c` |

Database/state side effects: **none** — every probe ran through the phase's own
teardown-owning fixtures; no schema change, no migration, configured DB left at head.
The only uncommitted tree content is the coordinator's docs and the unchanged foreign
bootstrap work.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| **S7** | fix round r4 (test-only; one fixture workspace + task, one absence assertion) |
| Probe-4 equivalence (subquery `TaskStep.workspace_id` redundant with globally-unique section ids) | recorded here; no action — do not re-open |

## Lessons for the plans

1. **Lettering a compound criterion is the moment to verify each new letter has a
   test, not just a name.** C14c was created this round from C14's original text and
   immediately inherited a claim that had never been implemented. When the
   lettered-parts rule is applied retroactively, each new letter should be checked
   against the test body in the same pass — otherwise the lettering converts an
   invisible gap into a documented false assurance, which is worse.
2. **Tenant-boundary predicates deserve an explicit enumerated row, like error codes
   do.** Charter rule 2 already requires one row per case for ordered rules and error
   contracts; workspace scoping on any batch-read endpoint belongs in that list. Every
   other workspace-filtered query in E2 happens to be covered by the same omission,
   and only the top-level one is load-bearing — which is exactly the kind of
   distinction a criterion row forces you to work out in advance.

## Human-authorization backlog

None. No architecture-graph adjudication is requested by this review, and no owner
decision is required to act on S7.
