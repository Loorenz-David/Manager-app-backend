```
batch: C2
phases: [9, 10]
role: review
round: 1
verdict: CHANGES_REQUESTED
state: OWNER_DECISIONS_PENDING
date: 2026-09-21
actor: Opus (plan-reviewer)
```

# Batch C2 review 1 — plans 9 and 10

## 0. Summary

**Verdict: CHANGES_REQUESTED.** 81 criterion rows in scope (plan 9: 45, plan 10: 36 — after the
mid-review fold that authored plan 9 C8(d) and plan 10 C8(a)). **79 PASS · 0 FAIL · 2 NOT_VERIFIED**
(the two OWED rows).

**No row failed.** Every row in both plans holds, and the tester's ledger is sound where I sampled
it. The verdict comes entirely from **three measured defects that sit past the rows**, in the
authority the rows were derived from — the same division of labour batch C1 produced:

1. **One blocking production defect (F-1).** `sync_task_stock_assignments` does not implement MC-2
   step 3. It looks up *any* non-deleted assignment of the task rather than the **active** one, with
   `session.scalar` rather than the specified `scalar_one_or_none`. **Measured end to end:** with a
   `failed` assignment and an active one on the same task — a state the ratified §14F F1 and the
   partial unique index both permit, and which phase 8's `already_processed_by_scanner` check does
   **not** block for `failed` — the sync picked the terminal one, skipped, and left the active
   assignment at `in_queue` while the task moved to `working`. Silent, permanent board drift. No row
   covers it (F-5).
2. **The write-site guard is materially weaker than MC-2 says (F-2).** The single best use of my
   budget, per the prompt. The tester proved the collector *observes six planted things*; I probed
   whether it *misses a seventh class*. It misses **five** — four of them inside MC-2's own
   collection classes, and one of those is a form the collector's own docstring claims to cover.
   Guard stayed **green (6 passed)** with all five planted at once.
3. **Plan 10 C2(a)'s declared evidence does not exist (F-3).** The owner ruling makes C2(a)
   UNFORCEABLE and delegates its real evidence to "the C4 registry guard, which refuses a sync call
   inside the three helpers". It does not. I planted `sync_task_stock_assignments(...)` inside
   `maybe_evaluate_task_ready` — the exact construction MC-2's "why command level" forbids — and the
   guard stayed **green**. C2(a) currently has no evidence of any kind.

Production code was otherwise right everywhere I looked, the C5 referee choreography is real, the
perimeter is clean, and the phase-8A overlap is a single additive `enums.py` append that collides
with nothing.

**Six findings · four owner cards · six notes.** Tracker rows are **not** written by me — master
plan §3A reserves them to the orchestrator.

---

## ⚠ OWNER DECISIONS REQUIRED (4)

### Card 1 — Should a criterion row cover a task that carries an old, finished assignment as well as a live one?

**Question.** Add a criterion row to plan 10 for a task with one terminal and one active
assignment — yes or no?

**Story.** A chair's repair job fails, so the board marks its line failed. A week later someone
removes a step from that job, which puts it back in the queue, and a new Scanner request re-assigns
the same chair to the same job. The job now carries two lines: the old failed one and the live one.
From that moment the board stops following the job. A worker starts the chair, finishes it, the job
goes ready — and the board still shows the chair as queued, forever, with no error anywhere.

**Branches.**
- *Add the row*: the two-line case is pinned, and the fix for it cannot silently regress.
- *Do not add it*: the fix ships unwatched, and the same class returns the next time anything
  leaves a finished line on a job.

**Recommendation.** Add it — I reproduced the failure on this tree, so this is writing down a
measured defect, not guarding a hypothetical.

**On silence.** No row is added; finding F-1 is still routed to the implementer as blocking, but
nothing pins the repair. The gate holds; I guessed nothing.

**Trace.** intention §5B MC-2 step 3; §14F F1; plan 10 §5 task 1 and C1; finding F-1/F-5.

---

### Card 2 — Plan 10 C2(a) was ruled unfailable and pointed at a guard that does not perform the check. How should it be fixed?

**Question.** Should the write-site guard be extended so it actually refuses a sync call placed
inside the three task-state helpers — or should C2(a) be restated?

**Story.** The rule that keeps the board honest is "sync once, at the end of the command, never
inside the little helpers that flip a job's state halfway through". Break it and a job that goes
ready → queued → ready inside one save would credit and un-credit the same units, possibly against
two different goals. You were told this rule is watched by a checked-in guard. I planted exactly
that mistake and the guard passed without a word.

**Branches.**
- *Extend the guard*: one added assertion — no sync call inside the three helpers or the shared
  step core — and the rule is watched for the first time.
- *Restate C2(a)*: accept that the rule is unguarded and say so plainly, so no future reviewer
  counts it as covered.

**Recommendation.** Extend the guard — the machinery already exists in the guard (it checks the
positive form today), so this is one line, not a new instrument.

**On silence.** C2(a) keeps a regression test that cannot fail and an evidence claim that is not
true. The gate holds.

**Trace.** intention §5B MC-2 "why command level" and "The guard"; plan 10 C2(a), C4; finding F-3.

---

### Card 3 — The new plan 9 C8(d) names an example that cannot happen. Restate it?

**Question.** Restate C8(d)'s fixture to a **finished** assignment, and correct the behaviour it
says was measured — yes or no?

**Story.** The row was written from a report that the grouped Scanner write "silently wrote an
impossible move". Reading the code, it does not: that function works out the destination itself
from the line's real current state, so the destination is always a legal one. What actually went
wrong in the measurement was the *answer sent back to Scanner* — the right thing was saved, the
wrong reason was reported. The row's example (a chair being worked on) therefore cannot produce an
impossible move at all, so a test written to it would pass for the wrong reason.

**Branches.**
- *Restate*: the fixture becomes an already-finished line, which genuinely is an impossible move,
  and the row becomes provable.
- *Leave it*: the fix round writes a test against an example that cannot fail, which is the exact
  defect family this project keeps paying for.

**Recommendation.** Restate — the row's intent is right and worth keeping; only its example and its
cited evidence are wrong.

**On silence.** The row stays unprovable as exemplified and the fix round inherits it. The gate
holds.

**Trace.** plan 9 C8(d); tester CC-1 and its owner card 1; `_move_assignment.py:resolve_processed_group`;
finding F-4.

---

### Card 4 — Should the write-site guard also watch raw SQL?

**Question.** Extend MC-2's guard specification to a sixth collected class — raw SQL touching the
tasks table — yes or no?

**Story.** The guard's job is that nobody can change a job's state without the board being told.
Its checked list covers the five ways our code does that today. When the rule was first written the
author also searched for raw SQL and found none, but that search was a one-off and never became
part of the guard. I wrote a raw SQL update of a job's state into a live file and the guard passed.
Nothing in the codebase does this today, so this is a door left open, not a leak.

**Branches.**
- *Extend*: raw SQL naming the tasks table becomes a collected, registered site; a handful of
  existing raw statements may need registering.
- *Do not*: the door stays open, documented here.

**Recommendation.** Extend — it closes the only class the original audit looked for and then
dropped, and the codebase currently has nothing to register, so it is cheap today and expensive
later.

**On silence.** Nothing changes; the gap is recorded here only. The gate holds.

**Trace.** intention §5B MC-2 "Write-site audit" (its `text\(` term) and "The guard" (a)–(e);
finding F-6.

---

## 1. Gate check

| Check | Result |
|---|---|
| Intention `status: RATIFIED` (round 9, round-10 additive) | PASS |
| Plans 9 and 10 present, criteria tables addressable | PASS |
| `git status --porcelain` clean at session start and at close | PASS |
| `HEAD` contains both implementer checkpoints `8a5ebc2`, `ffa591e`, and the tester's `a00d858` | PASS |
| **Production diff implementer → tester → now:** `git diff ffa591e..HEAD -- app/beyo_manager/` | **PASS — empty** |
| Tester left no production change | PASS |
| `BEYO_TEST_SLOT=c2` on every pytest invocation of this session | PASS (3 runs, all slotted) |
| Gate condition = 23 failures (21 published + the 2 named `test_database_isolation` IDs) | PASS — consumed by citation, not re-run |

## 2. Tree identity and evidence policy

- Review tree: **`4581209`**, `git status --porcelain` empty.
- The tester's stamp was taken at `a00d858`: `BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest -m 'not e2e'` →
  **23 failed / 3661 passed / 1 skipped**, failure-ID delta empty in both directions against
  (21 published + 2 slot IDs), pass arithmetic `3619 + 42 = 3661`.
- **My tree differs from that stamp by exactly one commit**, `4581209` (phase 8A fix round 1),
  which touches only `app/tests/unit/domain/stock_report/test_stock_report_assignment_checks.py`
  (+6/−5: `SimpleNamespace` stand-ins replaced with transient ORM instances). That is the parallel
  workstream's file, not this batch's, and it is not mine to report.
- **I did not re-take an L4.** Instead I bridged the one-commit gap at L1:
  `BEYO_TEST_SLOT=c2 … pytest tests/unit/domain/stock_report/test_stock_report_assignment_checks.py`
  → **1 passed**, and the diff adds no test and removes none, so the stamp's counts still describe
  my tree. Authorization line, written before the run: *narrower evidence is sufficient because the
  only delta between the stamped tree and mine is one unit-test file whose collected-test count is
  unchanged; an L4 would purchase no variation.*
- Everything else the tester measured is tree-matched and is **consumed by citation**. My budget
  went entirely to variation the tester declared unspent (its §11).

## 3. Perimeter

**Batch C2's production+test perimeter** = `git diff b9e1d7f..ffa591e -- app/` (24 files; `9105f71`,
phase 8A, precedes `b9e1d7f`, so the two authorships are cleanly separable in git — I did not have
to guess).

- Plan 9 §4: all five new files and all four edited files present. ✓
- Plan 10 §4: all five new files and exactly the nine edited command files present. ✓
- **`_task_state_write_scanner.py`** is the one file beyond §4; declared as a judgment call in plan
  10's Review log. Accepted.
- **The one phase-8A overlap, `enums.py`, is clean.** This batch's change is a pure append at EOF
  (`ItemsProcessedOutcomeEnum`, `ItemsProcessedReasonEnum`, +17 lines), declared in plan 9 §4, and
  touches no 8A content.
- **None of 8A's other five files appears in this batch's diff.** No undeclared perimeter breach.

## 4. Findings

Severity · route · authority · correction.

---

### F-1 — BLOCKING · route `production` · the sync looks up the wrong assignment

**Authority.** Intention §5B MC-2 step 3 — *"a fresh query for the non-deleted **active**
assignment of that `task_id` (at most one, MC-4)"*. Plan 10 §5 task 1 — *"fresh query for the
non-deleted active assignment of `task_id` (`scalar_one_or_none`)"*.

**What is wrong.** `sync_task_stock_assignments.py:57-63`:

```python
assignment = await session.scalar(
    select(StockTaskAssignment).where(
        StockTaskAssignment.workspace_id == workspace_id,
        StockTaskAssignment.task_id == task.client_id,
        StockTaskAssignment.is_deleted.is_(False),
    )
)
```

Two deviations from the contract, compounding:
1. **The `state.in_(ACTIVE_ASSIGNMENT_STATES)` predicate is absent.** The query can return a
   terminal assignment.
2. **`session.scalar` replaces `scalar_one_or_none`.** With more than one row it does not raise; it
   returns whichever row Postgres hands back first, with no `ORDER BY`.

Line 81 then sees a terminal state and `continue`s — so the task's genuinely active assignment is
never synced, and nothing anywhere reports it.

**Why this is reachable, not theoretical** — every step is ratified and shipped:
- §14F F1 (ratified): `resolved_early` is *"not active: it holds no counter and **does not block a
  new assignment** under the one-active-per-item / per-task indexes (MC-4)"*.
- `uix_stock_task_assignments_task_active` is partial on
  `is_deleted = false AND state IN ('in_queue','in_progress','awaiting')`, so a task may carry any
  number of non-deleted terminal assignments beside one active one.
- Phase 8A's `_SCANNER_PROCESSED_STATES` is `{RESOLVED, RESOLVED_EARLY}` only, so the
  `already_processed_by_scanner` check does **not** block re-assigning a `(task, item)` pair whose
  earlier assignment is `failed`; `task_failed_or_cancelled` looks at the task's *current* state,
  and plan 10 C3(b)'s own X1 path (`remove_task_step` on a failed task → `pending`) un-fails it.

**Measured, not inferred.** Reviewer probe test (created, run, deleted — §6):

```
PROBE the sync's own discovery query picks: sta_01M32D04ZRJYD835Q5Z10FM71P FAILED
PROBE after sync: a2.state = IN_QUEUE  events = 0
AssertionError: MC-2 step 3 violated: the active assignment stayed IN_QUEUE
                (discovery picked sta_01M32D04ZRJYD835Q5Z10FM71P/FAILED)
```

The second `create_stock_task_assignments` call succeeded with no refusal, confirming the whole
chain, and the task's move to `working` produced **zero** stock events.

**Correction.** Restore both halves of the contract:

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

`ACTIVE_ASSIGNMENT_STATES` is the frozenset, never a spelled list (§9 rule 16). `scalar_one_or_none`
matters independently: it is what makes a future breach of MC-4's "at most one" loud instead of a
coin flip. The terminal-skip at line 81 stays — it still guards the post-lock re-read (C5(a)/C5(c)
depend on it).

**Not a finding against the tester.** No criterion row asks about this; see F-5.

---

### F-2 — SHOULD-FIX · route `production` · the MC-2 write-site collector misses four of MC-2's own site classes

**Authority.** Intention §5B "The guard" (a)–(e); charter rule 15; the collector's own module
docstring, `_task_state_write_scanner.py:6-7`, which states class (a) as
*"every attribute assignment whose target attribute is named `state` (`x.state = ...` **or
`x.state: T = ...`**)"*.

**What is wrong.** I appended one function to `app/beyo_manager/services/commands/tasks/update_task.py`
(at EOF, so no registered line number shifted) containing five distinct writers of `Task.state`,
and ran the guard:

```
BEYO_TEST_SLOT=c2 PYTHONPATH=. pytest tests/unit/.../test_task_state_write_sites_are_registered.py
→ 6 passed in 12.22s
```

**Green with all five planted.** Because any single collected site would have reddened
`test_c4a_every_collected_site_has_a_registry_entry`, one run proves all five are invisible:

| Planted construct | MC-2 class | Why missed |
|---|---|---|
| `task.state: TaskStateEnum = TaskStateEnum.STALLED` | (a) — **and the docstring claims it** | there is no `visit_AnnAssign`; `ast.AnnAssign` falls through `generic_visit` |
| `task.state, task.updated_at = STALLED, now` | (a) | `visit_Assign` tests `isinstance(target, ast.Attribute)` and never descends into an `ast.Tuple` target |
| `update(TaskModel).values(state=...)` (`Task` imported as `TaskModel`) | (c) | the matcher requires `node.args[0].id == "Task"` literally |
| `_probe_helper(task)` (`maybe_evaluate_task_ready` imported under an alias) | (e) | `_call_func_name` resolves the alias, not the target |
| `text("UPDATE tasks SET state = 'ready' …")` | — (not in (a)–(e)) | see F-6 |

Two further latent gaps of the same shape, not planted because the first three settle the class:
`sa.update(Task)` / `models.Task(state=...)` are rejected by the same `isinstance(node.func, ast.Name)`
requirement in classes (c) and (d).

**Live impact today: none.** I grepped the whole scanned corpus for every one of these forms —
`sa.`/`sqlalchemy.`-qualified `update`/`insert`, `text(` naming `tasks`, annotated `.state:`
assignment, tuple-target `.state`, module-qualified `Task(` — and the codebase contains **none** of
them. The registry's 85 sites are correct as of this tree. The defect is that the instrument cannot
see the next one.

**Load-bearing?** Less than the prompt feared, and that is worth recording: the implementer's §6
said plan 10 C1(b),(c),(e),(f),(i),(j),(l) were proven *only* by this guard, but the **tester closed
that gap** — each of those rows now has its own end-to-end test (t_sync, per the tester's table 2).
So no shipped row rests on the blind spot. What rests on it is the guard's forward-looking job.

**Correction.** In `_task_state_write_scanner.py`: add `visit_AnnAssign`; make `visit_Assign` (and
`visit_AugAssign`) walk tuple/list/starred targets; resolve `update`/`insert`/`Task`/the four helper
names through the module's own import aliases (or match on the last attribute segment as
`_call_func_name` already does for methods). Then re-run the six existing probes plus these four as
new C4 rows — but the rows are the owner's to author, so route the row-authoring through card 2's
neighbour, not this finding.

---

### F-3 — SHOULD-FIX · route `plan` · plan 10 C2(a)'s "real evidence" does not perform the check

**Authority.** Plan 10 C2(a) (owner ruling, card 2, 2026-09-21): *"The row is kept as a cheap
regression guard; **its real evidence is the C4 registry guard**, which refuses a sync call inside
the three helpers."* Intention §5B *"Why command level and not inside the three helpers"*.

**What is wrong.** The C4 guard has six assertions: every collected site is registered; every
registry entry is still produced; classifications are recognized; every `task_write`'s named sync
function **contains** a call to `sync_task_stock_assignments`; every `paused_driver` passes the
literal `PAUSED`; `no_sync`/`not_task` carry their field. **None of them is a negative assertion.**
Nothing forbids a sync call anywhere.

**Measured.** I planted precisely the forbidden construction inside
`_task_state_transitions.py:maybe_evaluate_task_ready` (after line 114, so no registered line
shifted):

```python
await sync_task_stock_assignments(
    session, [(task, None)], workspace_id=workspace_id, actor_user_id=updated_by_id, now=now
)
```

Guard result: **6 passed.** The construct is not one of the five collected classes, so the collector
never sees it and no assertion can bite.

**Consequence.** C2(a) is an `UNFORCEABLE` regression test whose declared substitute evidence does
not exist. The MC-2 invariant it stands for — the one whose violation would un-credit and re-credit
a goal within one transaction, possibly onto a different goal record — is currently unguarded.

**Correction (owner card 2).** The remedy is one assertion inside the existing guard, using
machinery it already has:

```python
for helper in ("maybe_advance_task_to_working", "maybe_reopen_task_to_working",
               "maybe_evaluate_task_ready", "_apply_step_transition"):
    assert not function_contains_call(None, helper, "sync_task_stock_assignments")
```

This is the mirror of `test_c4a_every_task_write_sync_function_exists_and_calls_the_sync` and stays
inside the guard's own idiom, so it is not an implementation-coupled test demand (owner rule
2026-09-19): the observable is the shipped source the guard already reads.

---

### F-4 — SHOULD-FIX · route `plan` · plan 9 C8(d)'s example fixture cannot produce an illegal target, and its cited measurement misdescribes what happened

**Authority.** Plan 9 C8(d) (authored 2026-09-21 from tester card 1); tester §7 F-6 and §10 CC-1;
`_move_assignment.py:271-300`.

**What is wrong — two things.**

*(a) The example is unproducible.* C8(d) says: *"an assignment whose re-read state makes its
computed target an **illegal** transition … (e.g. an `in_progress` assignment presented for the
`awaiting → resolved` decision)"*. `resolve_processed_group` takes **no decision from its caller**;
it computes each target itself, from `assignment.state` at call time (`:286-291`):

```python
from_state = assignment.state
target = RESOLVED if from_state == AWAITING else RESOLVED_EARLY
```

An `in_progress` assignment therefore yields `RESOLVED_EARLY`, which §14F F2 makes **legal**. The
example cannot fail. The provable fixture is a **terminal** assignment (`resolved`, `failed`,
`resolved_early`), whose computed target is `resolved_early` — illegal under MC-1/F1.

*(b) Today's behaviour is not "written silently".* Card 1's story and CC-1 both state the command
wrote an `awaiting → resolved` transition silently under P27. It did not. Under P27 the *stored
state* was correct (`resolved_early`, derived from the real current state) and the *counter column*
and *goal credit* were correct too; what was stale was the **`reason` field of the response**
(`null` where `"early"` was due) — which is exactly the assertion the tester observed red. The
user-visible harm is real (Scanner reconciles on that field) but it is a wrong report, not a wrong
write.

For a genuinely terminal input, today's code sets `assignment.state = resolved_early`, **flushes
it**, and then dies on a bare `KeyError` at `_COUNTER_COLUMN[from_state]` (`:300`) — the transaction
aborts, so nothing commits, but the failure mode is an unhandled `KeyError`, not
`IllegalAssignmentMove`. This makes C8(d)'s *"and nothing is written"* clause genuinely
load-bearing, which is worth saying in the cell.

**Correction (owner card 3).** Restate C8(d)'s fixture to a terminal assignment; restate the
observed-today behaviour as "the illegal state is flushed and the call fails with an unhandled
`KeyError`"; and correct owner card 1's story before it is used again. The row's substance — the
grouped path must refuse on its own, with no caller re-read in front of it — is right and should
survive verbatim.

---

### F-5 — SHOULD-FIX · route `plan` · no row covers a task with more than one non-deleted assignment

**Authority.** MC-2 step 3's parenthetical *"(at most one, MC-4)"*; §14F F1's explicit statement
that a terminal assignment does not block a new one.

**What is wrong.** Plan 10's fixture preamble is *"A created through `CR`"* — singular — and all 36
rows are built on exactly one assignment per task. The premise MC-2 step 3 leans on is therefore
never exercised, and F-1 shipped through the gap. This is the missing-row half of F-1 and is why the
tester, correctly working from the rows, could not have found it.

**Correction (owner card 1).** One row: task T with a terminal non-deleted assignment A1 and an
active A2; a state-changing command; A2 ends at `MAP[T.state]`, counters follow, one `:updated`.
Named mutation: drop the `state.in_(ACTIVE_ASSIGNMENT_STATES)` predicate from the sync's discovery
query — today's code — and the row reddens.

---

### F-6 — SHOULD-FIX · route `plan` · MC-2's guard specification omits the raw-SQL class its own audit searched for

**Authority.** Intention §5B "Write-site audit": the 2026-09-18 search terms include
*"`text\(` containing `tasks`"*. Intention §5B "The guard": the collected classes are (a)–(e), and
raw SQL is not among them.

**What is wrong.** The one-off audit looked for raw SQL; the standing guard does not. Measured: a
planted `await session.execute(text("UPDATE tasks SET state = 'ready' WHERE id = 1"))` inside
`update_task` left the guard green (same run as F-2). Nothing in the scanned corpus writes task
state this way today (grepped), so this is an open door, not a leak.

**Correction (owner card 4).** Amend §5B's guard list with a class (f): every `text(...)` call whose
literal names the `tasks` table and contains `state`. Amending the intention is the owner's.

---

## 5. Notes (carry-forward dispositions)

| Id | Note | Route | Destination |
|---|---|---|---|
| N-1 | `t_ipr::test_numbers_are_echoed_as_received_not_stripped` traces to plan 9 task 1's echo clause, not to a lettered row, and is not declared as a candidate criterion (the tester declared CC-4's two router tests and table 3's two sync tests, but not this one). Charter rule 16 makes it a should-fix orphan; it is a one-line parser sibling of C3(g), so: declare it against C3(g) or retire it | `verification` | batch C2 fix round |
| N-2 | The eight plan 9 C2 rows carry **two** test surfaces each (parser + command). The tester's D-1 justifies the command layer soundly (the row's boundary is `PR`, and "nothing written" needs the command) and mirrors the APPROVED plan-7 precedent, so this is not a finding against this round — but the parser layer is now redundant against the rows as stated. Retire in a later cleanup pass, or record the precedent as deliberate | `verification` | project cleanup (post-C2) |
| N-3 | Tester CC-6 (`remove_task_steps`, the plural S8 caller, never driven) **closed by reading**: the plural command's sync block is byte-symmetric with the singular's, including the `stock_report_events` argument into `_dispatch_remove_step_events`. No test owed | — | closed here |
| N-4 | The registry guard never validates a `not_task: <model>` claim — `test_c4a_no_sync_and_not_task_entries_carry_their_required_field` asserts only that the string is non-empty. A real `Task.state` write mis-registered as `not_task` passes. Lower risk than F-2 (it needs an active mis-registration, not an omission), but it is the same instrument | `verification` | fold with F-2's fix |
| N-5 | `resolve_processed_group` has no `from_state == target` short-circuit (unlike `move_assignment:195-200`) and no `any(delta != 0)` guard on its row event (tester CC-2, confirmed at `:332`). Both fold into C8(d)'s fix rather than standing alone | `production` | C8(d) fix round |
| N-6 | `test_c5a_…` inlines the referee choreography instead of using the shared `_run_forced_order` helper that C5(b)/C5(c) use. Cosmetic; both forms observe both blocks | `verification` | optional |

## 5A. Write perimeter of this session (full)

**Documents written (3, all uncommitted — I made no commit):**
- `SR/handoffs/reviewer/2026-09-21_batch_C2_review_1_handoff.md` (new — this file)
- `SR/plans/plan_9.md` (§8 Review log entry appended; no criteria cell, no §7 note, no other section touched)
- `SR/plans/plan_10.md` (§8 Review log entry appended; same restriction)

**Code and tests written: none.** `git diff -- app/` is **empty** at close; every probe was
reverted and the one probe test file was deleted (§6).

**Tracker rows: none.** Master plan §3A/§4A reserves tracker rows to the orchestrator; §4 and §4A
are untouched by me. The orchestrator owes rows for phases 9 and 10 and for batch C2
(`REVIEWING → CHANGES_REQUESTED`) from this handoff.

**Architecture graph: no `archgraph_*` call of any kind** — no read, no write, no review decision.

**No commit, no push, no history rewrite.**

## 6. Mutation-probe declaration

Every probe applied and reverted inside this session. Tree verified clean at close
(`git status --porcelain` empty).

| File | Probes | Revert proof |
|---|---|---|
| `app/beyo_manager/services/commands/tasks/update_task.py` | 1 appended block carrying 5 constructs (AnnAssign `.state`, tuple-target `.state`, `update(TaskModel)`, raw-SQL `text(...)`, aliased helper call) — **out of perimeter, plan 10 §7 authorizes probes in this file** | `git checkout --`; md5 `a9d1d5242e6bf18d7ac35225c13064b9` before and after |
| `app/beyo_manager/services/commands/tasks/_task_state_transitions.py` | 1 (a `sync_task_stock_assignments` call inside `maybe_evaluate_task_ready`) — **out of perimeter; not covered by either plan's §7, declared here** | `git checkout --`; `git status --porcelain` empty after |

**Files created and deleted:**
`app/tests/integration/services/commands/stock_report/test_zzz_reviewer_probe_two_assignments.py`
(the F-1 reproduction) — created, run, **deleted**; confirmed absent and the tree clean.

**Database / state side effects:** the F-1 probe test ran on slot `c2`, seeded its own workspace and
purged it in `finally` (`purge_stock_report_workspace` + commit, observed in the run log). No other
state was written. No `archgraph_*` write of any kind this session.

**Commands run this session** (all slotted, per the prompt):
1. `BEYO_TEST_SLOT=c2 … pytest tests/unit/.../test_task_state_write_sites_are_registered.py` — F-2 probe set planted → **6 passed**.
2. `BEYO_TEST_SLOT=c2 … pytest tests/unit/.../test_task_state_write_sites_are_registered.py` — F-3 probe planted → **6 passed**.
3. `BEYO_TEST_SLOT=c2 … pytest tests/integration/.../test_zzz_reviewer_probe_two_assignments.py` — F-1 reproduction → **1 failed** (the intended red).
4. `BEYO_TEST_SLOT=c2 … pytest tests/unit/domain/stock_report/test_stock_report_assignment_checks.py` — the §2 bridge → **1 passed**.

No L4 was taken (§2).

## 7. Per-row dispositions

Consumed by citation from the tester's ledger where tree-matched; **bold** marks a row I
independently adjudicated beyond the ledger.

### Plan 9 — 45 rows: 44 PASS · 0 FAIL · 1 NOT_VERIFIED

| Rows | Disposition |
|---|---|
| C1(a)–(e) | PASS (5). C1(e)'s API-key twin repair (tester F-3) sampled: the twin now sends the same blank value, so the zero-statement clause is the only sufficient cause. |
| C2(a)–(h) | PASS (8). C2(a) `EQUIVALENT` accepted — the class-2 note is correct and the isolating mutant genuinely lands on the surviving clause. C2(d) correctly re-armed (B-2). |
| C3(a)–(l) | PASS (12). C3(c)'s repair sampled: the three sub-cases are parametrized and M17 reddens `[resolved-early]` alone, which is the proof the split was needed. B-3/B-4/B-5's two-site correction verified against `process_items_processed.py:101` (discovery) and `:139` (the in-loop ladder) — both really are needed, the ladder absorbs the discovery-site mutant. |
| C4(a)–(g) | PASS (7). C4(c)'s `populate_existing` repair sampled and correct (the session runs `expire_on_commit=False`). |
| C5(a)–(b) | PASS (2). `ARMED-SHARED` on M36 audited: each row's own second-result assertion is the one that fires. |
| C6(a)–(b) | PASS (2). The re-siting (M38→M38b) and the `ARMED-SHARED` on M17 both hold. |
| C7(a)–(e) | PASS (5). **C7(b) independently checked against owner card 1**: the test asserts counters and exactly-one-`:updated`-per-row, and asserts **no** statement count and **no** runtime row ordering. Correctly built. |
| C8(a) | PASS. |
| C8(b) | **PASS — structural check discharged by me.** `_locks.py:_lock` issues exactly one `SELECT … WHERE client_id IN (…) ORDER BY client_id … FOR UPDATE` per model class, and `process_items_processed.py:113-120` passes the whole candidate set to `lock_stock_report_items` and `lock_stock_task_assignments` **once each**, with `sorted(...)`. No request can interleave acquisitions per entry. The plan's `UNFORCEABLE` declaration is honest and the structural check genuinely discharges what the row promises (§9 rule 9). |
| C8(c) | PASS, read per the orchestrator's `:state-changed` ruling. **Checked for over-verification (§9 rule 18's second instance):** `test_c8c_resolve_processed_group_contract` asserts the signature and the event-kind set only, and does **not** duplicate C3–C7's behavioural coverage. Correctly scoped. |
| **C8(d)** | **NOT_VERIFIED — OWED** by a fix round (plan 9 §7, authored mid-review). Red by construction on this tree: `resolve_processed_group:271-339` never calls `_assert_allowed_move`. See **F-4** for a defect in the row's own text. |

### Plan 10 — 36 rows: 35 PASS · 0 FAIL · 1 NOT_VERIFIED

| Rows | Disposition |
|---|---|
| C1(a)–(l) | PASS (12). Every one of the nine call sites read: each sits after its command's **last** `Task.state` write, inside the command's transaction, passes only net-changed tasks, and appends its events to the command's single dispatch. S4/S5 verified line by line; S8 verified in **both** callers; S9 verified ctx-less with `payload["performed_by_user_id"]`. C1(g)/C1(h)'s pre-state repairs (tester F-4) sampled and correct. |
| **C2(a)** | PASS **as a row** (the test exists and the outcome holds), but its declared evidence is void — see **F-3**. Not a row failure; a plan defect. |
| C3(a)–(f) | PASS (6). The `ARMED-SHARED` sets (P13 for C3(a)/(c); P16 for C3(d)/(e)/(f)) audited: each row's own task exit is separately named in the observed-red set, which is the measurement §9 rule 8 asks for rather than an assertion. |
| C4(a)–(h) | PASS (8) **as rows** — the six MC-2 probes fire and each names its own planted line, which the tester checked explicitly against the line-shift confound. C4(h)'s `EQUIVALENT` (B-9) accepted. **But the instrument they arm has five blind spots — see F-2.** C4(a)'s control-row status is unaffected; what is affected is what a green C4(a) means. |
| C5(a)–(c) | PASS (3). **Choreography independently verified:** `test_two_writers_on_one_assignment.py` observes **both** participant blocks in every order — C5(a) at `:212-217`, C5(b)/C5(c) through the shared `_run_forced_order` at `:412-417` — each with `pytest.raises(asyncio.TimeoutError)` around `asyncio.shield`. Referee lock, no barrier, no sleep, `finally` release and purge. The B1 anti-pattern (a lock test inside one transaction) is not present. C5(b)'s corrected failure mode (B-8) is right as far as it goes; see F-4(b) for the part that is still wrong. |
| C6(a)–(b) | PASS (2). C6(a)'s repair (tester F-5) sampled: the fixture now has a manager performing and a distinct worker credited, with an explicit `manager != worker` precondition, so "use the credited user" finally has something to read. C6(b) proven at S8 — the only site with an injectable `now`; accepted as a fixture choice, not a narrowed surface. |
| C7(a) | PASS. |
| C7(b) | PASS — **structural check discharged by me**: `resolve_task.py` raises `ConflictError` on its terminal pre-check *before* the first `Task.state` write and well before the sync call. The `UNFAILABLE BY DESIGN` label is accurate and correctly applied. |
| C7(c) | PASS. |
| **C8(a)** | **NOT_VERIFIED — OWED** (plan 10 §7, authored mid-review). **Not discharged by the two existing direct-call tests**: `test_sync_never_moves_a_resolved_early_assignment` and `test_sync_no_ops_when_the_assignment_is_already_at_target` both assert `events == []`, so neither exercises a moved assignment and neither pins the returned event kinds. The row text is well formed and provable as written. |

## 8. What I did not check — plainly

- **No L4 of my own** (§2 gives the reasoning and the authorization line). If the orchestrator wants
  one before the gate, the delta to watch is 8A's `4581209`, not this batch.
- **No condition variation.** Same `TZ`, same locale, same six xdist workers, same slot `c2`. The
  tester declared this unspent and I did not spend it either — I judged the collector blind spot and
  the MC-2 authority sweep the higher-yield buys, and one of them was blocking.
- **No second mutant shape** on any plan-named cell. I re-sited nothing the tester sited.
- **No HTTP-layer coverage.** Both routers are still exercised only by the wiring tests (CC-4).
- **No independent re-derivation of the 85 registry entries themselves.** I proved the *collector*
  has blind spots; I did not re-derive that the 85 classifications are individually right. N-4 is
  the part of that gap the guard cannot close for itself.
- **No `remove_task_steps` (plural) end-to-end run** — closed by reading instead (N-3).
- **Phase 8A's five files and its content are out of scope** and I neither reviewed, reverted nor
  reported them. `enums.py`, the one overlap, *was* in scope and is clean (§3).
- **I did not judge the absent implementations of C8(d) and C8(a)** — only their row text.

## 9. Lessons for the plans (the coordinator folds these upstream)

- **L-30 — a contract's parenthetical premise is a criterion, not a gloss.** MC-2 step 3 says
  "the non-deleted **active** assignment … (at most one, MC-4)". Both halves were dropped in
  implementation and neither was a row, so 32 executed mutations and a clean ledger sailed past a
  blocking defect. When a contract step states a *cardinality* or a *predicate* in passing, the
  planner owes it a row — because that is precisely the clause an implementer reads as prose.
- **L-31 — "its real evidence is X" must be checked against X, at the moment the ruling is
  written.** Plan 10 C2(a) was ruled unfailable and delegated to the C4 guard by a reader who
  believed the guard performed a check it has never performed. A delegation is an evidence claim and
  falls under charter rule 15: the ruling that makes a row unfailable owes a one-line probe of the
  instrument it hands the row to.
- **L-32 — a guard's docstring is not a guard.** `_task_state_write_scanner.py` states annotated
  attribute assignment as a collected form and does not collect it. Six planted probes all passed
  through the classes the collector *does* implement, so the probe set confirmed the implemented
  subset and nothing about the specified one. **Probe sets should be derived from the contract's
  class list, not from the collector's code** — otherwise the instrument grades its own homework.
- **L-33 — restate a measurement before you build a row on it.** The tester measured a stale
  *response field*; the finding was written up as a silent *illegal write*; the owner card repeated
  it; and the new C8(d) row inherited an example that cannot fail. The chain had three honest hops
  and still produced an unprovable row. A row authored from a measurement should quote the observed
  assertion, not a paraphrase of it.
