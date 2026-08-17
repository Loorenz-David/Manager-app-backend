---
plan: 1
role: reviewer
round: 4
state: REVIEWED
verdict: APPROVED
actor: Claude (Opus 5, plan-reviewer doctrine)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Phase 1 re-review round 4 — S7 only, final gate

## Summary

**Verdict: APPROVED.**

S7 closes. The tenant-boundary row exists, it guards the boundary the finding named,
and my own re-applied probe proves it: deleting `Task.workspace_id ==
ctx.workspace_id` from E2's visibility query now turns the C14 test red with
`assert 3 == 2` — the foreign task comes back as a third row, exactly the §5
batch-read violation S7 described. Teardown is clean, verified empirically against
the configured database rather than by reading: every table count is identical
before and after a run of the file, and zero rows survive matching any of the
fixture's id patterns, including the new foreign workspace and foreign task.
Perimeter is one test file plus pipeline docs, no production file touched. The E2
test seam moved only additively. Suite reproduces 2287 / 26 / 1 with a failure set
byte-identical to my round-3 run.

Nothing new crossed my path. Across four rounds, both rule-6 mechanisms were verified
correct line-by-line and never needed a production change; every finding I raised was
a coverage hole, and all seven are now closed with a probe behind each one.

⚠ OWNER DECISIONS REQUIRED (0)

## Write perimeter (this session)

- `docs/architecture/under_construction/implementation/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase1_rereview_r4_handoff.md`
  — this file, and nothing else.

No plan, master-plan, code, test or architecture-graph mutation was made.

## Verified perimeter

The prompt's span `99ade31 → 1290cc0` again contains two commits; diffed separately:

- `git diff --stat 83f853c 1290cc0` (fix only) = **3 files**: the E2 test file,
  `master_plan.md`, `plans/plan_1.md` — all on the declared fix-owned list, whose
  fourth entry is the handoff itself (committed in `e42d544`).
- The extra file in the wider span —
  `handoffs/implementer/2026-08-17_phase1_fix_r3_handoff.md` (+123) — belongs to
  `83f853c`, the coordinator's record commit predating the fix. Not a violation.
- **No production file changed** ✅ — `git diff 99ade31 1290cc0 -- app/beyo_manager`
  is empty for the phase's own paths. The implementer's note is correct and was worth
  making: the broader `-- app/beyo_manager` check is non-empty only because the
  worktree carries the owner's unrelated `bootstrap_app.py` edit, which predates this
  round and is untouched by it. I confirmed that independently: `git diff 1290cc0 --
  stat -- app/beyo_manager app/tests` reports that one foreign file and nothing else.
- HC-2 clean: no migration, no schema diff, no index.

**No-weaker-assertions check (§6): PASSES.** The only assertion movement in the E2
seam is one *added* line (`assert foreign_task.client_id not in {…}`); `len(...) == 2`,
`first_count == 11` and all three exact status pins are retained verbatim. Everything
else is tuple-unpacking arity.

## S7 / C14d closure

Fixture (`test_budget_allocations_query.py:34,39,68-70,77`): a second `Workspace`
(`ws_foreign_<token>`) and a `Task` on it (`tsk_foreign_<token>`) with no item, no
evaluation and no steps — deliberately bare, so the row proves omission and not some
downstream filter doing the work.

Call and assertions (`:192-194`): the batch now sends four ids —
`[task, unevaluated_task, "tsk_unknown", foreign_task]` — and asserts
`len(...) == 2`, `foreign_task.client_id not in {row["task_id"] …}`, and the
unchanged `first_count == 11`. The query-count pin did not move with the extra id,
which is itself a small confirmation that the visibility query is still one batched
statement.

**Does it guard the boundary S7 named?** Yes — probe below. One accuracy note on
`plan_1.md:232-238`, which says the mutation "must then appear and fail both the
absence assertion and the existing `len(...) == 2` count": pytest stops at the first
failing assert, so in practice the count assertion is what fires (`assert 3 == 2`)
and the absence assertion is the belt to its braces. Both are correct to keep — if
the count pin were ever relaxed, the absence assertion still catches the leak. No
action; recorded so a future reader is not surprised that only one of the two shows
in the traceback.

### Probe

| # | Mutation (definition site) | Observed | Reverted |
|---|---|---|---|
| 1 | `get_task_budget_allocations.py:65-69` — remove `Task.workspace_id == ctx.workspace_id` from the E2 visibility query | **RED** — `AssertionError: assert 3 == 2` at `test_budget_allocations_query.py:193`; the returned third row is the foreign task (`allowed_worker_minutes: None`, no steps), matching the existence-disclosure blast radius S7 described | ✅ byte-identical, SHA-256 `4d05f41543bee2988825c5aec3026f19083d936c7743b2a23eb0609732010e9d` before and after |

This reproduces the implementer's ledger row exactly, including the assertion text
and line.

## Teardown judgement (rule 11½)

Verified empirically against the configured DB with nothing else running:

| Table | Before | After |
|---|---|---|
| `workspaces` | 1509 | 1509 |
| `tasks` | 763 | 763 |
| `task_steps` | 3344 | 3344 |
| `item_valuations` | 0 | 0 |
| `items` | 507 | 507 |
| `working_sections` | 275 | 275 |
| `users` | 1325 | 1325 |

Targeted pattern check after the run: `ws_foreign_%` = 0, `tsk_foreign_%` = 0,
`tsk_unevaluated_%` = 0, `ival_unevaluated_%` = 0.

Ordering is FK-safe by construction: `_cleanup:222-239` deletes the foreign task
(`:228`) before the foreign workspace (`:239`), and the main workspace's tasks before
its workspace. The handoff's declared residue table list matches what the fixture
actually commits — I checked each named table against the fixture's `add_all` calls;
nothing the fixture writes is missing from the list.

(Method note: an earlier count showed +1 workspace / +1 task. That was a concurrent
full-suite run of my own writing rows in parallel, not fixture residue; the table
above is from a quiescent database, and the suite figures below are likewise from a
run on the verified-clean tree after all probing finished.)

## Suite (P-L — re-measured on the clean tree)

`PYTHONPATH=. pytest -q -m 'not e2e'` from `backend/app/`:

**2287 passed, 26 failed, 1 deselected, 2 warnings in 114.84s.**

Failure-list diff, computed mechanically:
- vs the 23 v1 baseline IDs: **all 23 present, none missing, byte-identical**;
- extra: **exactly the 3 foreign** `test_seed_item_economics_configuration.py` IDs;
- vs my round-3 run: **`diff` reports the two sets identical.**

Focused re-run at HEAD after all probes: **140 passed**. Working tree byte-identical
to `1290cc0` across `app/beyo_manager` and `app/tests` apart from the owner's
pre-existing `bootstrap_app.py` edit.

## Mutation-probe declaration

One probe file, applied-and-reverted, checksum-verified byte-identical:

| File | SHA-256 (before == after) |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `4d05f41543bee2988825c5aec3026f19083d936c7743b2a23eb0609732010e9d` |

Database/state side effects: **none** — proven by the before/after table above, not
asserted. No schema change, no migration, configured DB left at head.

## Phase finding record (all four rounds)

| Finding | Round raised | Closed | Behavioural defect? |
|---|---|---|---|
| S1 E2's unproven M1 copy | r1 | r2 | no — coverage |
| S2 C14 never ran the resolver path | r1 | r2 | no — coverage |
| S3 C17 step key-set missing (HC-3 hole) | r1 | r2 | no — coverage |
| S4 C15 could not detect P7 shadowing | r1 | r2 | no — coverage |
| S5 C13 byte-agreement unasserted | r1 | r2 | no — coverage |
| S6 exact status pins weakened / fixture regressable | r2 | r3 | no — coverage |
| S7 tenant boundary unguarded | r3 | r4 | no — coverage |
| N-a…N-l (12 notes) | r1–r2 | r2–r3 | docs / cosmetics |

**Zero production defects were found in four rounds.** M1's SQL and M2's function
were correct as first written and were never changed except for the S1 extraction
(behaviour-preserving) and two cosmetic edits. Every finding was a guard that did not
guard.

## Closeout inputs

Things the coordinator should carry into the approval gate; the phase's own record
already lives in `plans/plan_1.md`.

**1. K5 — architecture-graph delta needs owner visibility.** Checkpoint `0b85701`
committed `.archgraph/architecture.yml` whole, so the phase's 5-node / 9-edge delta
(revision `ab1a4935…`) is bundled with a **pre-existing foreign graph delta** that was
already in the worktree. It was judged not cheaply splittable and recorded for this
gate. No later round touched the graph — r1b, r1c, r2, r3 and r4 all declare zero
graph mutation, and I confirmed the revision string is unchanged across every handoff.
The post-approval graph pass is the coordinator's under standing authorization.

**2. Recorded equivalences — do not re-open.** Three constructions in this phase are
formally output-equivalent to their named mutation, each with the reasoning recorded.
A future session that probes them will see green and must not read that as a gap:
- **C13b-door2** — `excluded` is built from `live_steps`, which already filtered
  `is_deleted`, so an `is_deleted` check inside the excluded comprehension is
  unreachable; the protective red lives at C13a.
- **C20** — with an empty allocated set every downstream loop is vacuously empty, so
  the guard is a readable fast path, not behaviour.
- **probe-4 (r3)** — the M1 subquery's `TaskStep.workspace_id` filter is redundant
  defence-in-depth: `working_section_id` holds globally-unique section client_ids, so
  foreign steps cannot join to this workspace's sections. The *load-bearing* section
  boundary (the outer `WorkingSection.workspace_id` filter) **is** guarded and turns
  the M1 tests red when removed.

**3. Contract text the frontend-handoff fold must state.** Beyond the payload shapes
in intention §5:
- **N-h, the fifth null (intention round 7):** on a task whose `status` is not
  `ok`/`infeasible`, E2 returns `actual_worker_seconds: null` — *in addition to* the
  four fields §5 originally enumerated — while `steps[].worked_seconds` stay
  populated. A client that wants consumed time on an unevaluated task must sum
  `steps[]`. This mirrors budget-status's `_empty_status`, so the two surfaces agree
  by construction; §6's "equals the sum of its own steps by construction" now holds
  **only for evaluated tasks**, and the handoff should say so in those words.
- **`share_state` precedence:** on a no-budget task every step reports `no_budget`,
  including steps that are skipped/cancelled/failed — `excluded` appears only when a
  budget exists. Both components read `share_state` from the server (HC-4); neither
  re-derives it.
- **Absence semantics:** unknown, deleted and other-workspace task ids are *omitted*
  from `budget_allocations` (the client notices by key), and E1 rows below five
  qualifying groups appear with `typical_worker_seconds: null` and their real
  `sample_count` — absence-with-reason, so a young section renders "no typical yet"
  rather than vanishing.
- **Swappability labels (HC-5):** every E1 row carries `method` /`window_days` /
  `min_sample_size` and every E2 task carries `allocation_method`; future refinements
  change those values, never the shape. Worth stating so the frontend keys off them
  rather than hard-coding "90-day median".
- **Batch contract:** `task_ids` is a repeatable query param, 1–50 per call;
  51 ids → 422 `BUDGET_ALLOCATIONS_TOO_MANY_TASK_IDS`; `?task_ids=` degenerates to
  one unknown id and is omitted.

**4. Suite baseline for the next pipeline.** Master plan §7 still carries the v1
closure baseline (2249 / 23 / 1). This phase closes at **2287 passed / 26 failed /
1 deselected**, where the 26 = the same 23 v1 IDs byte-identical + 3 foreign
`test_seed_item_economics_configuration.py` failures from the owner's untracked
in-flight bootstrap work. The next pipeline should inherit **2287 / 23 (+3 foreign,
expected to disappear when the bootstrap work lands) / 1**, and §7 updated at closeout
so the successor does not diff against a stale figure.

**5. Doctrine earned this phase**, already in master plan §6 and worth promoting to
the shared rule library: rationale-site, lettered-parts, service-identity, one-copy,
guard-is-the-reason, no-weaker-assertions, fixture-property-gets-its-own-exact-assertion,
and (new from r3) letter-verification + the tenant-boundary row.

## Human-authorization backlog

Only K5 above, which is a record-and-acknowledge item at the gate, not a decision.
No architecture-graph adjudication is requested by this review.
