```
batch: C1
phases: [8, 11]
role: fix
round: 1
state: OWNER_DECISIONS_PENDING
date: 2026-09-21
actor: Sonnet
```

# Batch C1 fix round 1 handoff — production + verification, no tester/no independent reviewer

Fix prompt: `prompts/implementer/2026-09-21_batch_C1_fix_1.md`. Review consumed:
`handoffs/reviewer/2026-09-21_batch_C1_review_1_handoff.md`.

## 0. Gate check

- Intention `planning/intention.md` header: `RATIFIED` (round 9, 2026-09-19) — confirmed.
- Master plan §4A batch C1: `CHANGES_REQUESTED` at dispatch, predecessor batches A/B1/B2
  `APPROVED` — confirmed.
- `git status --porcelain` empty at start; HEAD `6023901` (as stated in the prompt).

**HEAD moved during this session.** A concurrent, unrelated commit (`30194a2`, "stock_report:
intention section 14G — match preview, MC-21, round 10 (additive)", docs-only, owner-authored)
landed on `main` while I worked. It touches no file in this round's perimeter; `git diff` against
my perimeter is unaffected. I did not rebase, merge or otherwise act on it. An untracked file also
appeared mid-session — `prompts/planner/2026-09-21_phase_8A_plan.md` (a planner prompt for a
different, unrelated phase) — not created by me, not part of my perimeter, left untouched and not
staged.

## 1. What I built

### B1 (blocking, fixed)

`create_stock_task_assignments.py:_phase3_reason` (definition site) now reads:
```python
task = locked_tasks.get(entry.task_id)
if task is None or task.is_deleted:
    return "task_not_found"
item = locked_items.get(entry.item_id)
if item is None or item.is_deleted:
    return "item_not_found"
```
`_locks.py` untouched, as the prompt required.

### B2 (blocking, fixed)

`delete_stock_task_assignments.py` (definition site, top of the function) now reads:
```python
ids = sorted(set(request.client_ids))
```
Discovery, the missing-check, the removal loop and the response all read this same
de-duplicated set (no other line changed) — de-duplicating in one place, not several,
per the owner's ruling on card 2.

### S1 (should-fix, fixed)

`bm/routers/api_v1/stock_report.py`: `model_config = ConfigDict(extra="forbid")` added to
`_StockTaskAssignmentEntryBody`, `_CreateStockTaskAssignmentsBody`, `_DeleteStockTaskAssignmentsBody`.

### S3 (should-fix, implemented and armed)

`test_property_mismatch_without_override_raises_409_with_sorted_failures` (plan 8 C3(a)) rebuilt
on the folded four-key fixture (`zone` added), asserting all four failures in alphabetical order,
matching the corrected outcome cell already in plan 8 §6 (S4's fix).

### S5 (should-fix, done — no stop-and-report cases)

`assert_stock_report_clean` added to all 27 rows the review named, none reddened:

- Plan 8 (10, across two files): C3(b) `test_override_on_a_mismatching_entry_creates_with_flag_true`,
  C3(c) `test_override_on_a_matching_entry_is_ignored`, C4(g) `test_c4g_quantity_is_copied_from_the_item`,
  C4(h) `test_quantity_floors_at_one`, C4(k) `test_two_entries_ascending_item_id_response_order_and_summed_counters`,
  C1(r) `test_c1r_a_new_task_for_the_same_item_is_not_affected`, C1(s) `test_c1s_a_soft_deleted_resolved_assignment_does_not_refuse`,
  C7(a) `test_two_entries_on_one_row_dispatch_two_created_and_one_coalesced_updated` (all in
  `test_create_stock_task_assignments.py`); C6(c) `test_deleting_resolved_assignment_leaves_counters_untouched`,
  C6(h) `test_two_assignments_on_one_row_coalesce_to_one_updated_event` (in
  `test_delete_stock_task_assignments.py`).
- Plan 11 (17, across two files): C1(b), C1(c) in `test_task_side_removals.py`; C2(b), C2(c),
  C3(b) in `test_item_side_removals.py`; C4(a)–(f), C4(i), C5(a)–(e) (12 tests) in
  `test_category_guard.py`.

C1(a), C2(a), C3(a), C4(g)-plan-11 already complied and were left unchanged. The three
drift-planted C6 trigger-string tests (plan 11) are exempt per §6's own preamble ("unless drift
is planted") and were not touched. **No test failed when the assertion was added — no
stop-and-report case, no drift found anywhere.**

### C1(v), C1(w), C6(j) — new criterion rows, built and armed

- **C1(v)** (`test_c1v_soft_deleted_task_is_refused_task_not_found`,
  `test_create_stock_task_assignments.py`): soft-deleted Task, otherwise valid — refused
  `task_not_found`; nothing written; row counters unchanged; task's `is_stock_assignment` stays
  false.
- **C1(w)** (`test_c1w_soft_deleted_item_is_refused_item_not_found`, same file): soft-deleted
  Item, otherwise valid — refused `item_not_found`; same non-write clauses.
- **C6(j)** (`test_c6j_the_same_assignment_named_twice_in_one_delete_is_removed_once`,
  `test_delete_stock_task_assignments.py`): built as `DL([A, A])` on a row that also holds an
  active, untouched B(4) — see the fixture-header defect note below. A removed once; counter
  falls by 4 (not 8), landing at B's remaining 4; exactly one `stock_task_assignment:deleted`
  event; response lists the id once; zero repair records.

**Plan defect found and worked around, not silently.** Plan 8 C6(j)'s fixture header literally
reads `DL([A, A, B])` (three ids: A twice, B once). Its own outcome cell — "R's quantity_in_queue
falls by 4, not 8, and ends at B's remaining 4" — is only arithmetically true if B is **not**
part of the delete request (deleting B too would land the row at 0, not 4). Master plan §9 rule
7's own citation of the measured B2 defect confirms the intended construction is `DL([A, A])`
with B present-but-untouched ("`DL([A, A])` on a row also holding an active B(4)"). Built that
way, per plan 8 §6's own preamble ("an outcome that disagrees with its own fixture is a plan
defect: report it, never reconcile it in the test") — reported here for the coordinator to
correct the row header, not reconciled silently. Recorded in plan 8's Review log too.

## 2. Mutation ledger — `executed == declared == 8`

**Declared, criterion-row-tied (5):** C1(v) 1, C1(w) 1, C6(j) 1, plus two retained rows whose
tests this round edited and which the closing protocol requires re-running: C3(a)/S3 1, C5(a)/S2
1. **Declared, S1's own fix (3):** one mutation per router body model. **Total declared = executed
= 5 + 3 = 8.**

| # | Row / fix | Mutation (site) | Scope | Command | Result | Reverted |
|---|---|---|---|---|---|---|
| 1 | C1(v) | drop `task.is_deleted` from `_phase3_reason` (`create_stock_task_assignments.py`, definition site) | L1 | `pytest tests/integration/.../test_create_stock_task_assignments.py` | **RED** — exactly `test_c1v_soft_deleted_task_is_refused_task_not_found` (41/42 others green) | yes, confirmed clean |
| 2 | C1(w) | drop `item.is_deleted`, same site | L1 | same file | **RED** — exactly `test_c1w_soft_deleted_item_is_refused_item_not_found` (41/42 others green) | yes |
| 3 | C6(j) | revert dedup to `ids = request.client_ids` (`delete_stock_task_assignments.py`, definition site) | L1 | `pytest tests/integration/.../test_delete_stock_task_assignments.py` | **RED** — exactly `test_c6j_the_same_assignment_named_twice_in_one_delete_is_removed_once` (11/12 others green) | yes |
| 4 | C3(a)/S3 (retained, test edited) | drop `sorted(...)` in `evaluate_stock_criteria` (`criteria_matcher.py`, definition site) | L2 (create test file + matcher unit test file) | `pytest test_create_stock_task_assignments.py tests/unit/domain/stock_report/test_criteria_matcher.py` | **RED** — `test_property_mismatch_without_override_raises_409_with_sorted_failures` **and** the pre-existing `test_matcher_reports_all_sorted_failures` (98/100 others green) | yes |
| 5 | C5(a)/S2 (retained, test edited) | "drop the Item lock, phase 2" — sited twice: (a) inline unlocked select in `create_stock_task_assignments.py` call site, (b) `_locks.py:lock_items` definition site rewritten unlocked; plus (c) a diagnostic variant of (a) with a forced 50 ms pause after the read | L1 | `pytest test_create_stock_task_assignments_race.py`, 5× for (a), 3× for (b), 1× for (c) | **GREEN every time** (9/9 runs) — did not reproduce red. See §3. | yes, all three code states confirmed via `git diff` empty |
| 6 | S1a | drop `extra="forbid"` from `_CreateStockTaskAssignmentsBody` | L1 | `pytest tests/unit/routers/api_v1/test_stock_report_router.py` | **RED** — exactly `test_create_assignments_route_refuses_unknown_top_level_field` (20/21 others green) | yes |
| 7 | S1b | drop `extra="forbid"` from `_StockTaskAssignmentEntryBody` | L1 | same file | **RED** — exactly `test_create_assignments_route_refuses_unknown_entry_field` | yes |
| 8 | S1c | drop `extra="forbid"` from `_DeleteStockTaskAssignmentsBody` | L1 | same file | **RED** — exactly `test_delete_assignments_route_refuses_unknown_top_level_field` | yes |

**7 of 8 mutations reddened exactly the row/test they were meant to arm. Row 5 (C5(a)/S2) is
reported as an executed-but-inconclusive result, not a silent gap** — see §3 for why, and owner
card 1 for the routing question.

## 3. S2 — attempted, could not reproduce a red in this environment

The owner-ratified clause on plan 8 C5(a) ("the losing call wrote nothing —
`count_writes(statements, {"stock_task_assignments"}) == 0` over it") was added to
`test_c5a_concurrent_create_on_the_same_item_leaves_exactly_one_active`. Because both sessions in
that test share the **one process-wide `_engine`** (`db_session` and the second session from
`get_db_session()` both bind to the same `AsyncEngine`), `record_statements`'s engine-level event
cannot be scoped to only the losing call's own connection without a custom per-connection filter.
I recorded across the whole barrier-released race instead and asserted the mathematically
equivalent race-scoped form: **total** writes to `stock_task_assignments` across both calls `== 1`
(exactly the winner's) — documented as a judgment call in the test's own comment.

Running the row's named mutation ("drop the Item lock, phase 2") at two independent sites, plus a
diagnostic variant forcing a 50 ms pause to rule out a scheduling artefact, **stayed green nine
times out of nine**. Reading the query log for the mutated run: session B's own `active_item_ids`
pre-check only ever executes **after** session A's commit, lock or no lock. Root cause, as far as
I can tell without further instrumentation: the test's two sessions are structurally asymmetric —
`db_session` (session A) reuses an already-open, warm connection, while session B acquires a
**fresh** connection through `get_db_session()`. That acquisition overhead reliably gives A's
continuation a head start after the shared `asyncio.Barrier` releases both coroutines, and once
ahead, A's remaining awaits (two SELECTs, one INSERT, COMMIT) resolve fast enough against this
local Postgres that B's own continuation never gets a chance to race it — independent of whether
the Item row lock is present. In other words: in this environment, session A wins by scheduling
asymmetry alone, which is exactly the failure mode the ratified `count_writes` clause exists to
catch, and which this specific test fixture cannot force regardless of what I do to
`create_stock_task_assignments.py` or `_locks.py`.

**I have not claimed this row armed.** The assertion is left in the test (it is correct, harmless,
and matches the ratified cell), but plan 8 C5(a)'s `count_writes` clause is reported
**NOT_VERIFIED-by-mutation** for this round, distinct from S3 which is fully armed. All three
probe states were reverted; `git diff` on `create_stock_task_assignments.py` and `_locks.py`
against the checkpoint below is empty of any probe residue.

## 4. L4 stamp

Tree: checkpoint `a7ece5a`, clean (`git status --porcelain` empty at commit, at the point this
handoff was written).

```
PYTHONPATH=. pytest -m 'not e2e'
21 failed, 3547 passed, 1 skipped, 2 warnings in 69.76s
```

Failure-ID diff against the published 21-ID baseline (`comm` both ways): **empty both
directions** — identical set. Pass-count arithmetic: baseline `3541` + `6` new tests
(`test_c1v_...`, `test_c1w_...` in `test_create_stock_task_assignments.py`; `test_c6j_...` in
`test_delete_stock_task_assignments.py`; 3 in `test_stock_report_router.py`) `= 3547`, exact.

Lint: `python3 -m ruff check <the 10 touched files>` → all clean. Full-repo `ruff check .` shows
140 pre-existing errors, none in files this round touched (documented pre-existing, unrelated to
this round).

## 5. Perimeter (cycle-scoped — this session's changes only)

**Production (3 files, ~10 net lines):**
- `app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py` (B1)
- `app/beyo_manager/services/commands/stock_report/delete_stock_task_assignments.py` (B2)
- `app/beyo_manager/routers/api_v1/stock_report.py` (S1)

**Tests (7 files):**
- `app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments.py`
  (C1(v), C1(w), C3(a)/S3 rebuild, 8× S5 additions)
- `app/tests/integration/services/commands/stock_report/test_delete_stock_task_assignments.py`
  (C6(j), 2× S5 additions)
- `app/tests/integration/services/commands/stock_report/test_create_stock_task_assignments_race.py`
  (S2 attempt — assertion added, no new test)
- `app/tests/integration/services/commands/stock_report/test_category_guard.py` (12× S5 additions)
- `app/tests/integration/services/commands/stock_report/test_task_side_removals.py` (2× S5 additions)
- `app/tests/integration/services/commands/stock_report/test_item_side_removals.py` (3× S5 additions)
- `app/tests/unit/routers/api_v1/test_stock_report_router.py` (S1, 3 new tests)

**Plans:** `plans/plan_8.md`, `plans/plan_11.md` — Review log entries only, no criteria cell
touched (confirmed by re-reading my own diff: only prose appended after the existing Review log
tail in each file).

**Master plan:** one new tracker row for batch C1 (`master_plan.md`), no other row touched.

**Mutation-probe files touched, applied and reverted, nothing left behind** (separate from the
fix's own changes above):
- `app/beyo_manager/services/commands/stock_report/create_stock_task_assignments.py` — the same
  file as B1's fix, additionally used for the C5(a)/S2 probe (temporary unlocked-select rewrite
  of phase 2's item lookup, twice: with and without a diagnostic sleep). `git diff` against the
  checkpoint shows only the B1 fix; the probe leaves nothing.
- `app/beyo_manager/services/commands/stock_report/_locks.py` — temporary unlocked rewrite of
  `lock_items` for the same C5(a)/S2 probe (second siting). `git diff` against the checkpoint is
  empty — confirmed clean.
- `app/beyo_manager/domain/stock_report/criteria_matcher.py` — temporary removal of the
  `sorted(...)` call for S3's mutation. `git diff` against the checkpoint is empty — confirmed
  clean.

Both `_locks.py` and `criteria_matcher.py` are already declared probe-authorized in plan 8 §7's
2026-09-21 perimeter extension.

**Not touched:** `_move_assignment.py`, `_remove_assignment.py`, `_goal_credit.py`,
`state_map.py`, `consistency.py` (the phases-4/5 files the prompt named as off-limits) — none
were probed or edited. The other 90 criterion rows' mutation ledger, plan 9-14, and the §9
fold-count note for the three new rows (still owed — C1(v)/C1(w)/C6(j) are not yet reflected in
the running 621/100 total; this is a coordinator fold action, not something my perimeter covers).

## 6. Architecture graph

Oriented: `.archgraph` initialized (228 nodes, 357 edges, 61 pending review). Searched for
`create_stock_task_assignments` and `delete_stock_task_assignments` — **neither has a node**.
Related lower-level nodes exist (`command-move-assignment`, `command-remove-assignment`,
`command-apply-goal-effect`, `infrastructure-stock-report-locks`, `table-stock-task-assignment`,
all `ai_inferred`/`pending`), but the two top-level batch commands this round's B1/B2 fixes live
inside were never authored as their own nodes in any prior phase. Authoring them properly
(description, evidence, relationships to the existing table/lock/event nodes) is real
architecture-authoring work, not a small delta from a two-line predicate fix — out of this round's
declared perimeter. **No `apply_changes` call made this round.** Flagging the gap for the
coordinator rather than opportunistically half-authoring two command nodes under this round's
time budget.

## ⚠ OWNER DECISIONS REQUIRED (1)

**Card 1 — is the C5(a) race test worth rebuilding to remove its own asymmetry?**

- **Question** — Should a future round rebuild plan 8 C5(a)'s fixture so **both** competing
  sessions open a fresh connection (neither reuses the already-connected `db_session`), so the
  `count_writes` clause can actually be shown to redden when the Item lock is removed?
- **Story** — Today the test proves "exactly one assignment survives, with the right refusal
  reason" reliably, and that part is real. But the *specific* new proof — "the loser touched the
  database zero times" — currently passes for the same reason it would pass even if someone
  deleted the Item lock outright: one session structurally finishes before the other gets a
  chance to run, so nobody would notice if a future refactor quietly removed the lock. The gap
  would surface, if ever, as a rare production race under real network latency, not in CI.
- **Branches** — Rebuild with two fresh sessions (removes the asymmetry; costs a small,
  self-contained fixture change, no production risk) · Accept as-is (the reason-clause check and
  the structural argument in the intention still stand; the new clause becomes a documented,
  known-unarmed check, same shape as plan 11's C4(b)/C5(b)) · Try a different forcing mechanism
  (e.g. a `pg_sleep` inside a monkeypatched query, more invasive, more coupling to internals).
- **Recommendation** — Accept as-is for now and record it as known-unarmed (cheapest, no risk,
  matches an existing precedent in this project) unless the coordinator judges the Item lock's
  correctness important enough to spend a small fixture-rebuild round on.
- **On silence** — The gate holds: S2's clause stays NOT_VERIFIED-by-mutation, recorded as such in
  plan 8's Review log; nothing else in this round depends on the answer.
- **Trace** — plan 8 C5(a); §2 row 5; §3 above.

## Owner layer

**What I did.** Fixed the two bugs the review found: assigning stock to something you just
deleted (an item or a task) is now refused instead of silently creating a phantom assignment, and
deleting the same board row twice in one request now removes it once instead of quietly
subtracting its quantity twice from the count. Also closed a smaller gap where the assignment
endpoints accepted unrecognized fields instead of rejecting the request, and strengthened a test
that could not previously have caught its own regression. Added a cleanliness check to 27 tests
across two files so a "passed" result can no longer be hiding a stuck repair.

**What I found and what it means for you.** One test I improved — the one proving two workers
racing to grab the same item never end up double-assigned — has a clause I could not prove would
catch a broken lock, because of how the test itself is built (one side always gets a head start).
The underlying behavior is still argued correctly elsewhere and the main race protection is
proven; this is about one extra safety net, not the core guarantee. I also found that one of the
three already-written test rows had a typo in its own setup description; I built it the way its
own expected outcome required, and flagged the typo rather than guessing silently.

**What happens next.** This fix is committed as a checkpoint, not yet approved. The full test
suite matches the expected pre-existing failures exactly, so nothing broke. The coordinator (or
you) will review this by hand instead of an independent reviewer this round.

**What needs you.** One card, above: whether it's worth a small follow-up to make that one race
test's extra safety-net clause independently provable, or to accept it as a documented,
known-limitation check for now.
