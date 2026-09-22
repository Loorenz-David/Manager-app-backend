```
batch: C2
phases: [9, 10]
role: fix
round: 1
state: DONE
date: 2026-09-21
actor: Sonnet
```

# Batch C2 fix round 1 handoff — F-1, the write-site guard, five owed rows

Fix prompt: `prompts/implementer/2026-09-21_batch_C2_fix_1.md`. Review consumed:
`handoffs/reviewer/2026-09-21_batch_C2_review_1_handoff.md`. This round owned the tests as well
as the code — there is no separate tester behind it for the five new rows (stated explicitly in
the prompt).

## 0. Gate check

- Intention `planning/intention.md` header: `RATIFIED` (round 9, 2026-09-19; round 10 additive) —
  confirmed.
- Master plan §4A batch C2: `CHANGES_REQUESTED` at dispatch (review 1), predecessor batches A/B1/
  B2/C1 `APPROVED` — confirmed.
- `git status --porcelain` empty at start; HEAD `ae11ea2` (as stated in the prompt).

**HEAD moved repeatedly during this session, from a concurrent, out-of-scope phase-8A
workstream.** Commits `74e3830`/`42aa917`/`efaf9f6` (phase 8A round 2 — reopened for a different
finding, "the supplied `item_category_id` must take effect"), `eb682e6` (owner fold, touches only
`master_plan.md`'s totals/tracker text) and, after my last commit, `7c4b0c2` (a draft frontend
addendum, docs-only, unsent) all landed on `main` while I worked. **None touches any file in this
round's perimeter** — verified by `git diff <before>..<after> --stat` at each point I noticed a
shift (shown inline below where it mattered for a mutation's line-shift check). I did not rebase,
merge or act on any of them; every commit I made names only the file paths I intended.

## 1. F-1's fix, and the test that now fails without it

**The bug** (`sync_task_stock_assignments.py:57-63`, before): the step-3 discovery query dropped
both `StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES)` and `scalar_one_or_none()`. A task
carrying a terminal assignment (e.g. `failed`) *and* an active one — permitted, since
`uix_stock_task_assignments_task_active`'s partial index constrains only the three active states,
per §14F F1 — could have its discovery return the terminal row; the post-lock terminal skip then
fired and the genuinely active assignment never synced again, on this or any future state change,
silently.

**The fix**: both halves restored —

```python
assignment = (
    await session.execute(
        select(StockTaskAssignment).where(
            StockTaskAssignment.workspace_id == workspace_id,
            StockTaskAssignment.task_id == task.client_id,
            StockTaskAssignment.is_deleted.is_(False),
            StockTaskAssignment.state.in_(ACTIVE_ASSIGNMENT_STATES),
        )
    )
).scalar_one_or_none()
```

The post-lock terminal skip (`assignment.is_deleted or assignment.state in TERMINAL_ASSIGNMENT_STATES:
continue`) is untouched — C5(a)/C5(c) depend on it guarding the state-changed-between-discovery-
and-lock case, which is a different job.

**The test**: `test_c1m_sync_selects_the_active_assignment_over_a_terminal_one`
(`test_task_state_sync.py`) — this is plan 10's new **C1(m)**, covered fully in §3 below together
with its named mutation, since the row and the fix are one and the same story.

Checkpoint: `7d33c9a`.

## 2. The five owed rows — test and named mutation, each

Per-row summary; full narrative in each plan's Review log (plan 9 §8, plan 10 §8).

| Row | Test | Mutation site | Observed red | Reverted |
|---|---|---|---|---|
| plan 10 **C1(m)** | `test_c1m_sync_selects_the_active_assignment_over_a_terminal_one` (`test_task_state_sync.py`) | `sync_task_stock_assignments.py` — drop `state.in_(ACTIVE_ASSIGNMENT_STATES)`, keep `scalar_one_or_none` | `sqlalchemy.exc.MultipleResultsFound` (not the row's narrated "discovery returns A1" — see note below) | md5 identical |
| plan 10 **C4(i)** | `test_c4i_no_sync_call_inside_the_task_state_helpers_or_the_shared_core` (`test_task_state_write_sites_are_registered.py`) | plant a `sync_task_stock_assignments` call inside `maybe_evaluate_task_ready` (`_task_state_transitions.py`, after its existing `task.state = READY` write) | `AssertionError: maybe_evaluate_task_ready: calls sync_task_stock_assignments directly …` | md5 identical |
| plan 10 **C4(j)** | guard run whole-file, no permanent test (see §4) | five constructs planted at once in `update_task.py` (EOF) | `AssertionError: unregistered site(s): […:131, …:132, …:133, …:134, …:135]` — all five named in one assertion | md5 identical |
| plan 9 **C8(d)** | `test_c8d_resolve_processed_group_refuses_a_terminal_assignment` (`test_process_items_processed.py`) | remove the `_assert_allowed_move` call from `resolve_processed_group` (`_move_assignment.py`, definition site) | `KeyError: <StockTaskAssignmentStateEnum.RESOLVED: 'resolved'>` at `_COUNTER_COLUMN[from_state]` — not `IllegalAssignmentMove`; this **is** the review's own correction (F-4(b)) of what today's code actually does without the guard | md5 identical |
| plan 10 **C8(a)** | `test_c8a_sync_task_stock_assignments_contract` (`test_task_state_sync.py`) | drop the row event from the return (`sync_task_stock_assignments.py`, definition site) | 4 failed (this test plus 3 others in the same file that assert `:updated` counts — the mutation strips every row event the function ever returns, not just this test's; recorded per §9 rule 8) | md5 identical |

**Not yet discussed — C1(m)'s mutation shape.** The plan cell narrates "discovery returns A1, the
post-lock terminal skip fires, A2 stays `in_queue`, zero events" — that is what the **original**
bug (missing filter **and** `scalar` instead of `scalar_one_or_none`) produced. This fix keeps
`scalar_one_or_none()` (the row's own text asks for both halves, and rule 16 forbids reverting a
correct half just to arm the other), so dropping only the state filter makes the query return two
rows and `scalar_one_or_none()` raises `MultipleResultsFound` instead of silently picking one. The
row still fully discharges: A2 is provably never synced and zero events are dispatched either way,
and the louder failure is in fact `scalar_one_or_none`'s whole point (F-1's own text: "what makes a
future breach of MC-4's 'at most one' promise loud instead of a coin flip").

**C4(j)'s mutation was not shipped as a permanent test**, on the same footing as the six inherited
MC-2 probes (C4(b)-(h)), which this project's own precedent already treats as arm-and-revert
evidence rather than committed regression tests (grep of the whole test tree finds no
`test_c4b`...`test_c4h` function — see plan 10's Review log for the citation).

Full per-mutation narrative, including exact commands and file-run scope (whole-file, never `-k`,
per §9 rule 8), is in each plan's Review log entry (plan 9 §8, plan 10 §8). Every probe was
applied, run, and reverted with an md5 (or `git diff --quiet`) check before moving to the next.

Checkpoints: `ba3166e` (C8(d) + N-5 production), `b15f6e3` (C4(i)/C4(j) guard + registry),
`046d8dc` (the five rows' + N-1's + N-5's tests).

## 3. The collector's five extensions, and the grep

`_task_state_write_scanner.py` now collects, however written (owner card 4's by-construct clause):
- `visit_AnnAssign` — `task.state: T = …` (class (a));
- tuple/list/starred assignment targets walked in `visit_Assign` (class (a));
- an import-alias table (`_collect_import_aliases`), built per file from that file's own
  `ImportFrom` nodes, resolving `update`/`insert`/`Task`/the four helper names before either a
  callee or an `update(Task)`-style argument is matched against its expected spelling (classes
  (c)/(e), and the `Task` argument of (c));
- new class **(f)**: a `text(...)` or `.execute(...)` call whose first argument is a string (or
  f-string) literal naming both `tasks` and `state` (case-insensitive).

**Grep of the whole scanned corpus** (`app/beyo_manager/**/*.py`, `app/scripts/**/*.py`, excluding
tests/migrations), one form at a time:
- annotated `.state:` assignment: none (`grep -rn '\.state\s*:'` returns only comparisons, no
  writes);
- tuple-target `.state` assignment: none;
- `import Task as …`: none;
- `import (any of the four helpers) as …`: none;
- `text(` literal naming both `tasks` and `state`: none (one unrelated hit,
  `postgresql_where=text("exited_at IS NULL")`, matches neither term).

**Live impact today: none** — matches the reviewer's own grep (F-2). The extension guards the next
writer, not a live leak. The 85 registered sites are unaffected: the full guard suite (7 tests) is
green on the shipped tree both before and after the collector change, and I confirmed no new site
appeared from the extension itself (only from the C4(j) probe, reverted).

## 4. One L4, both ID diffs, pass-count arithmetic

Tree: `d72f2e9` (my last commit at the time of the run), `git status --porcelain` empty.

```
cd app && BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'
→ 23 failed, 3669 passed, 1 skipped, 2 warnings in 70.98s
```

**Failure-ID diff, both directions, against the gate condition** (21 published + the two
`test_database_isolation.py` slot IDs, per master plan §10's ruling): **empty**. I extracted the 23
observed ids and the 23 expected ids into two sorted files and ran `diff` — `IDENTICAL SETS`, no
extra id, no missing id, no 22nd or 24th anything.

**Pass-count arithmetic.** The batch C2 tester's last enumerated stamp was **23 / 3661 / 1** (tree
`a00d858`). `3669 - 3661 = 8`. I can verify **5** of those 8 directly, by my own isolated per-file
runs before and after each edit (all cited in §2's table and in the plans' Review logs):

- `test_task_state_write_sites_are_registered.py`: 6 → 7 (**+1**, C4(i))
- `test_task_state_sync.py`: 26 → 28 (**+2**, C1(m), C8(a))
- `test_process_items_processed.py`: 41 → 43 (**+2**, C8(d), the N-5 short-circuit test)

**The remaining +3 is not mine and I did not derive it independently** — it is the concurrent,
out-of-scope phase-8A round-2 workstream's own new tests (its checkpoint `efaf9f6` cites "C3(g)
armed with 3 new cases"), which landed on the same branch between the tester's stamp and my L4 and
is not something batch C2's fix round is asked to audit (phase 8A is APPROVED, out of scope, and a
different phase entirely). `5 + 3 = 8` reconciles the arithmetic exactly, with the 3 attributed by
citation to the other workstream's own commit message, not re-measured by me — consistent with the
charter's "spend budget on your own hypothesis" and this round's scope fence.

**The invariant that actually gates this round is the ID set, not the pass count** (master plan
§10: "the invariant is the 21-ID failure set … the pass count rises with every batch and is never
itself the comparator") — and that invariant is exactly satisfied.

Lint: `ruff check` on all 8 touched files — clean.

L2 (domain folders for both plans plus the tasks/task_steps trees phase 10 edits):
`tests/unit/services/commands/stock_report tests/integration/services/commands/stock_report
tests/unit/services/commands/tasks tests/integration/services/commands/tasks
tests/integration/services/commands/task_steps tests/integration/services/tasks/task_steps` — 488
passed.

## 5. The six routed notes, disposed by name

- **N-1** — disposed. `test_numbers_are_echoed_as_received_not_stripped`
  (`test_items_processed_request.py`) now carries a docstring declaring its trace to C3(g),
  naming C3(g)'s own command-level test as the row's real evidence and this one as a deliberate
  parser-level companion (the same two-surface pattern N-2 already accepts). Not retired.
- **N-2** — no action this round, as the review itself ruled ("not a finding this round … flag for
  a later retirement pass"). Recorded, left to the project's cleanup backlog.
- **N-3** — no action. Already closed by the reviewer's own reading (`remove_task_steps` is
  byte-symmetric with the singular caller); nothing to build.
- **N-4** — **left as is, recorded.** Validating a `not_task: <model>` registry claim (rather than
  only that the field is present) needs type information the AST sweep does not have — the
  collector sees `x.state = …` and a target expression's *text*, never `x`'s runtime type. A sound
  check would need either a type-inference pass over the whole corpus or a curated allowlist of
  known non-`Task` variable names — either is materially larger than this round's perimeter
  (F-2/C4(j)) and was not asked for by name. No criterion row demands it and no live
  mis-registration is known to exist (confirmed by the same grep as §3). Flagged for the
  coordinator as a possible future guard enhancement, not built here.
- **N-5** — folded into C8(d)'s production change. `resolve_processed_group` now (a) skips an
  assignment already at its computed target (`from_state == target`, mirroring `move_assignment`'s
  own short-circuit — no write, no event for it) and (b) guards the row's `:updated` event on
  `any(delta != 0)`, mirroring `move_assignment`. Neither is reachable through the webhook today
  (discovery only ever hands the function active-state assignments), so both are the function's own
  defence for a future or direct caller. Armed by
  `test_resolve_processed_group_short_circuits_an_assignment_already_at_target`: named mutation
  (remove the short-circuit) reddened exactly this test — `1 failed, 42 passed` — with the same
  `KeyError` shape as C8(d)'s mutation (from `RESOLVED_EARLY` having no `_COUNTER_COLUMN` entry
  either). Reverted, md5 identical. Declared here per rule 16 since it traces to no lettered row.
- **N-6** — **left as is, recorded.** `test_c5a_…` inlines the referee choreography instead of
  calling the shared `_run_forced_order` helper C5(b)/(c) use; both forms observe both participant
  blocks identically. Cosmetic only; not touched, to keep this round's perimeter to what the six
  findings and five owed rows ask for.

## 6. Judgment calls

1. **C1(m)'s fixture builds A1 via `move_assignment` directly, not through a second Scanner
   report.** The row's own text authorizes this ("A1 failed (terminal) and A2 in_queue (active),
   both on row R") without specifying how A1 got there; the file's own precedent
   (`test_sync_never_moves_a_resolved_early_assignment`, etc.) already builds terminal fixtures this
   way where driving the real command path is out of this round's budget. The row's own
   command-driven half — driving T through S1 — **is** built through the real
   `transition_step_state` command, which is what the row actually asks to be proven.
2. **C8(a)'s fixture drives the sync directly** (not through one of the nine call sites), per the
   row's own text ("Call `sync_task_stock_assignments` directly … The contract only"). C1/C4 already
   own the nine call sites' behaviour; this row would duplicate them if built any other way.
3. **The registry line-number fix in `task_state_write_site_registry.py`** (`_move_assignment.py`
   NOT_TASK entry, `292` → `302`) is a mechanical consequence of C8(d)'s production edit adding
   lines ahead of a registered site in the same file — not a judgment call so much as a required
   correction, caught by running plan 10's guard suite immediately after the plan 9 edit, before
   writing any new test (generalizing rule 19's lesson: run the collection-sensitive suite, not
   just the file you think you touched).
4. **C4(j)'s probe was planted in `update_task.py`, plan 10's already-authorized perimeter-
   extension file** (plan 10 §7, "Perimeter extension … `update_task.py` (probes P-a…P-d)"), at
   EOF, after every registered line in that file, so no registered site's line number moved — the
   same siting discipline the review's own F-2 probe used (and its md5 before/after matches mine:
   `a9d1d5242e6bf18d7ac35225c13064b9`, confirming the same starting tree).

No judgment call required an owner decision; none is carried as a card.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner from this round. All five owed rows are armed, F-1 is fixed and proven, the
guard's two owner-ratified gaps (C4(i), C4(j)) are closed, and the six notes are each disposed by
name above.

## 7. Full write perimeter of this session

**Production code (2 files):**
- `app/beyo_manager/services/commands/stock_report/sync_task_stock_assignments.py` — F-1 (the
  discovery query).
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` — C8(d)'s
  `_assert_allowed_move` call + N-5's short-circuit and zero-delta guard, both in
  `resolve_processed_group`.

**Test-support code (2 files):**
- `app/tests/unit/services/commands/stock_report/_task_state_write_scanner.py` — the five collector
  extensions (§3).
- `app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py` — one line, the
  registry key shifted by the C8(d) edit (§6.3).

**Test files (4 files):**
- `app/tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py` —
  C4(i)'s new negative-assertion test.
- `app/tests/integration/services/commands/stock_report/test_task_state_sync.py` — C1(m), C8(a).
- `app/tests/integration/services/commands/stock_report/test_process_items_processed.py` — C8(d),
  N-5's short-circuit test.
- `app/tests/unit/services/commands/stock_report/test_items_processed_request.py` — N-1's docstring
  (no assertion change).

**Plan documents (2 files, Review log entries only — no criterion cell, no §7 note, no tracker
row):**
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_9.md`
- `docs/architecture/under_construction/implementation/stock_report/plans/plan_10.md`

**Every mutation-probe file, touched and reverted (applied-and-reverted, listed separately from the
fix's own changes above, per the closing protocol):**
- `app/beyo_manager/services/commands/stock_report/_move_assignment.py` — twice: (i) removed
  `_assert_allowed_move`'s call for C8(d); (ii) removed the `from_state == target` short-circuit for
  N-5. Both reverted, md5 `b5089815aa87550eaa2c56cfd204d0fa` before and after each.
- `app/beyo_manager/services/commands/stock_report/sync_task_stock_assignments.py` — twice: (i)
  dropped the state filter for C1(m); (ii) stripped the row event from the return for C8(a). Both
  reverted, md5 `46fdd1b570469ddb3186cae9cb3508cf` before and after each.
- `app/beyo_manager/services/commands/tasks/_task_state_transitions.py` — planted the forbidden sync
  call inside `maybe_evaluate_task_ready` for C4(i). Reverted, md5 `c2cde4318bd089dc6783b712548babb1`
  before and after.
- `app/beyo_manager/services/commands/tasks/update_task.py` — planted the five C4(j) constructs at
  EOF. Reverted, md5 `a9d1d5242e6bf18d7ac35225c13064b9` before and after (matches the reviewer's own
  probe md5, confirming the same starting tree).

**Architecture graph:** no `archgraph_*` call of any kind this session — no read, no write, no
review decision. (This project's earlier sessions have used the graph; this fix round's changes are
implementation-internal — a bugfix, a test-support extension, and new tests inside already-recorded
command boundaries — and did not seem to me to warrant a new architectural delta. Flagged here
rather than silently skipped, in case the coordinator judges otherwise.)

**Commits (5, all on `main`, none pushed):**
1. `7d33c9a` — F-1 (`sync_task_stock_assignments.py`).
2. `ba3166e` — C8(d) + N-5 (`_move_assignment.py`).
3. `b15f6e3` — C4(i)/C4(j) guard + registry fix (3 files).
4. `046d8dc` — the tests for C1(m), C8(a), C8(d), N-1, N-5 (3 files).
5. `d72f2e9` — plan 9 and plan 10 Review log entries (2 files).

**Tracker rows: none written by me** — master plan §3A/§4A reserves them to the orchestrator; §4
and §4A are untouched by me.

**No push, no history rewrite, no edit to `master_plan.md`, the intention, or any criterion cell.**
