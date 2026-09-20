---
plan: batch B1 — plans/plan_4.md, plans/plan_5.md (master_plan.md §3A)
role: implementer
round: batch_B1-implement-1
date: 2026-09-21
skill: implementation-executor
base: a306298
---

# Batch B1 implementation: phases 4 → 5 (`stock_report`)

You implement **two phases in one session**, in the order 4 → 5, and write **one batch handoff**.
Crossing the phase boundary does not return control to anyone and triggers no review: finish phase
4, run its evidence, commit a checkpoint, continue to phase 5.

Plans 4 and 5 are the specification. This prompt frames the session and carries the orchestrator's
projection. **Where this prompt and a plan disagree, this prompt wins** — it was written after a
full projection of the shipped code and the plans were not. Where the plan and the intention
disagree, the intention wins.

Paths are relative to the repo root `backend/` (`git rev-parse --show-toplevel`). `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.
Run tests from `app/`.

## Gate check (stop and report `BLOCKED` if any line fails)

1. `SR/planning/intention.md` header begins `status: RATIFIED`.
2. `SR/master_plan.md` §4A shows batch B1 `IMPLEMENTATION_PROMPT_READY`, and batch A `APPROVED`.
3. `git status --porcelain` is empty at start.
4. `git log --oneline -1` is `a306298` or a later orchestrator commit.

**Dependency rule.** Plan 4's `depends_on: 3 (APPROVED)` is satisfied — batch A is APPROVED. Plan
5 depends on phase 4, which **you** implement earlier in this same session; that is satisfied when
phase 4's tests are green and its mutations have run. Do not wait for anyone.

## Read, in this order

1. Your `implementation-executor` doctrine and the pipeline charter.
2. `SR/master_plan.md` §5 (contracts), §6.1, §6.5 (the naming registry — **amended 2026-09-20**),
   §6.7, §6.8, §9 (standing rules; rule 16: never hand-type a state list — read from
   `ACTIVE_ASSIGNMENT_STATES` / `TERMINAL_ASSIGNMENT_STATES`), §10 (commands, baseline, hazards).
3. `SR/planning/intention.md` §5A MC-1, §6A MC-5/MC-6, §4B MC-15, MC-16, MC-17, §9D MC-19, §12A,
   §14C, §14F.
4. `SR/plans/plan_4.md` in full, then implement it. Then `SR/plans/plan_5.md`.
5. The shipped batch A code you build on (signatures in §2 below).

**Both plans were amended today** — 22 fixture and mutation cells were corrected because they
specified guards that could not fail. Each amended plan carries a **Fold note** explaining why. Read
the fold notes; they are the difference between a passing test and a real one.

## 1. Seven blockers — resolved. These override the plans.

The projection found seven things that stop a literal implementer. Each resolution below is
**binding**.

**B1 — plan 4 task 2 calls `recompute_task_stock_flag` with the wrong number of arguments.**
Plan 4 line 91 says `recompute_task_stock_flag(session, assignment.task_id)`. The shipped function
is `async def recompute_task_stock_flag(session, workspace_id, task_id)` — **three positional
arguments** (`_task_flag.py:16`). The plan predates the owner's ruling that restored the workspace
filter. Call the three-argument form. `remove_assignment` already receives `workspace_id` as a
keyword argument, so it threads through with no signature change.

**B2 — the inline repair warning must carry the delta, and `write_repair_record` cannot.**
Intention §5A MC-1 requires one `logger.warning` per record naming the row, field, stored and
recomputed values **and the move's delta for that column**. Plan 4 C5(a) asserts "one warning whose
message contains the delta `-4`"; plan 5 C2(a) the same. The shipped `write_repair_record`
(`_repair_records.py:44-52`) has no `delta` parameter and passes a literal `None` into its
`delta=%s` slot — phase 3's manual repair has no delta, so the gap was invisible.
**Do this:** add `delta=None` as a **keyword-only** parameter to `write_repair_record` and pass it
into the existing `logger.warning` slot. Phase 3's three existing call sites omit it and keep
working unchanged — verify that they do. Phase 4 passes the per-column delta of the statement that
tripped; phase 5 passes `−q`.
**`_repair_records.py` is therefore added to phase 4's perimeter**, overriding plan 4 §4's
"Nothing else." Report the new signature in your handoff; I amend master plan §6.5, not you.

**B7 — the task-flag divergence.** This one would have failed roughly fifty of your rows, so read
it even though the plans are already fixed. `move_assignment` never writes
`tasks.is_stock_assignment`; only `remove_assignment` does. The shipped consistency check compares
**every** task in the workspace against "does a non-deleted assignment name it", with no state
predicate (`consistency.py:223-245`). The kit seeds the flag `false`. So the moment one of your
fixtures puts a live assignment on the seeded task, `assert_stock_report_clean` reports a
`task_flag` divergence and every row whose outcome says "clean" fails.
**The rule, now in both plans' fixture preambles:** a scenario that **ends with a live
(non-deleted) assignment on T** seeds `T.is_stock_assignment = true` by raw SQL before the call; a
scenario that **ends with A soft-deleted** leaves it `false`.
**If you see an unexpected `task_flag` divergence, this is why. Do not "fix" it by weakening
`assert_stock_report_clean`** — that helper is the instrument every remaining phase depends on, and
weakening it would silently disarm master plan §9 rule 2 for the rest of the project. Fix the
fixture's flag seeding instead. If you believe a specific row genuinely cannot be seeded either
way, stop and report it as a blocker rather than touching the helper.

B3, B4, B5 and B6 belong to phases 6 and 7 and are not your problem.

## 2. Shipped batch A signatures you depend on — exact, verified

Do not guess these and do not re-derive them from the plans; the plans predate two amendments.

| Symbol | Exact shipped signature |
|---|---|
| `recompute_row_counters` | `(session, stock_report_item_id: str) -> dict[str, int]` — keys `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`; filters `is_deleted false` **and** `state.in_(ACTIVE_ASSIGNMENT_STATES)`; **no workspace filter** (keyed by row id) |
| `recompute_goal_total` | `(session, history_record_id: str) -> int` — Σ `quantity` over `credited_history_record_id == id`; **no `is_deleted` filter, no state filter, no workspace filter**. This is exactly what makes plan 5 C2(b) and C2(d) true |
| `recompute_task_stock_flag` | `(session, workspace_id, task_id) -> bool` — **three positional args** (B1) |
| `expected_task_flag` | `(session, workspace_id: str, task_id: str) -> bool` — "a non-deleted assignment of this workspace names this task"; **no state predicate**, so a `resolved`/`failed`/`resolved_early` assignment keeps the flag `true` |
| `set_task_stock_flag` | `(session, task_id, value, *, require_update=False) -> None` — predicate is `client_id` + `is_distinct_from(value)`. **You change this — see §3.** |
| `write_repair_record` | `(session, *, workspace_id, target_kind, target_client_id, field, stored_value, recomputed_value, trigger, created_by_id, now)` — **you add `delta` (B2)**. `_text` maps `bool → "true"/"false"`, `None → None`, else `str(...)` |
| `_locks.py` helpers | `(session, workspace_id, client_ids) -> dict[str, Model]`, positional, already sorted with `ORDER BY client_id` and `populate_existing`; return `{}` for an empty set — do not re-sort at call sites |
| test kit | `seed_stock_report_workspace(session, *, suffix=None) -> SeededWorkspace(workspace, manager, worker, categories, item, task)`; `make_ctx`; `capture_dispatch(monkeypatch, import_site)`; `assert_stock_report_clean(session, workspace_id)`; `purge_stock_report_workspace(session, workspace_id)` |
| kit values | item `quantity=4`, properties `{"wood_type": "Teak", "upholstery": "Down"}`, categories[0] "Dining Chairs", task `PENDING` with a PRIMARY `TaskItem`, `is_stock_assignment` **false** |

**The kit does not create R, G or A.** Master plan §6.8 describes F0 as including them; it is wrong.
`seed_stock_report_workspace` returns only the six fields above. Build R, G and A as ORM instances
in each test — precedent at `app/tests/integration/services/queries/stock_report/test_consistency_check.py:70-93`.

## 3. Three routed decisions — ruled by the orchestrator

**N-S3 — close it. `set_task_stock_flag` gains a workspace predicate.**
Change it to `async def set_task_stock_flag(session, workspace_id, task_id, value, *,
require_update=False)` with `Task.workspace_id == workspace_id` added to the `WHERE`, and thread
`workspace_id` from `recompute_task_stock_flag` (its only caller, which already has it). Two lines,
one call site, zero behaviour change today.
*Why I ruled this rather than parking it:* the owner ruled the identical question on the read half
of this boundary on 2026-09-20 — "a tenancy boundary that holds only while every other file stays
correct is the kind that fails silently and late" — and the reviewer routed the write half to phase
4 as "the phase that makes it reachable is the phase to decide it". Phase 4 makes it reachable.
**No criterion pins this**, so declare it in plan 4's Review log as both a deviation and a
**candidate criterion**: "the guard that `set_task_stock_flag` cannot cross a tenancy line has no
test." Do not invent a criterion row for it yourself. Report the new signature; I amend §6.5.

**N-R1 — do nothing to `apply_goal_effect`, and explicitly do not add a lock on `R`.**
Intention §6A MC-5's round-7 re-check settles it: no lock is taken on `R` itself; what protects `R`
is the moving assignment's **row** lock, which every writer of that row's goal totals holds. Phase
5 adds a second writer, so your obligation is to **prove the premise, not add a lock**:
`apply_goal_effect` must be unreachable except under the caller's row lock, and plan 5's tests hold
row + assignment `FOR UPDATE` before calling. The residual window is a defect in
`repair_stock_report`'s lock-set computation — **phase 3 code, outside your perimeter**. Carry it
forward in your handoff; do not fix it here.

**N-R3 — confirm the discharge explicitly.** Three §6.5 helpers shipped in batch A with zero
callers. You give two of them their first: `recompute_row_counters` (phase 4's inline counter
self-heal) and `recompute_task_stock_flag` (phase 4's `remove_assignment`). Phase 5 gives
`recompute_goal_total` its first, in `apply_goal_effect`'s self-heal. State this in your handoff —
charter rule 4's discharge is otherwise invisible.

## 4. Hazards — read every one before writing code

**H1 — F0 is not what the kit returns.** See §2. Do not hunt for a helper that creates R, G or A.

**H2 — the seeded task's flag.** B7 above. This is the one that costs you the night if you miss it.

**H3 — the partial unique indexes bite in multi-assignment fixtures.**
`uix_stock_task_assignments_item_active` and `…_task_active` are unique on `(workspace_id, item_id)`
and `(workspace_id, task_id)` `WHERE is_deleted = false AND state IN ('in_queue','in_progress','awaiting')`.
Two **active** assignments therefore need a second `Item` **and** a second `Task` (plan 4 C4(b)).
Terminal or soft-deleted assignments are exempt and may share the kit's pair — but order matters:
plan 5 C2(d) must create A1, move it to `resolved_early`, and only then create A2.

**H4 — `ck_stock_report_items_*_nonneg` fires immediately, not at commit.** That is what makes the
"drop the guard" mutations redden as `IntegrityError`. Do not add `DEFERRABLE`.

**H5 — the ORM instance is stale after every Core `UPDATE`.** `expire_on_commit=False`, and a raw
`session.execute(text(...))` does not expire the identity map. Read back with a fresh `SELECT`,
never from the instance. **Plan 4 C4(c) depends on this staleness for its mutation to bite** — do
not "fix" it by refreshing inside production code.

**H6 — `remove_assignment` writes `tasks` after the row and assignment locks, which inverts MC-1's
lock order** (tasks are step 3). MC-16's cascade resolves this by locking the tasks first, up front.
`remove_assignment`'s contract is therefore *the caller already holds the task lock*; plan 4 never
says so. **In phase 4's tests, take the task `FOR UPDATE` before the row lock**, so the test models
the caller. Record the premise in your handoff.

**H7 — `Task.updated_at` carries `onupdate=lambda: datetime.now(timezone.utc)`.** That is why
`set_task_stock_flag`'s `values(is_stock_assignment=value, updated_at=Task.updated_at)` is a Core
self-assignment. It also means **any ORM attribute write on a `Task` anywhere silently moves
`updated_at`** — use raw SQL when a fixture needs to set task columns without stamping.

**H8 — `set_task_stock_flag` no-ops when the value already matches** (`is_distinct_from`). A fixture
that leaves the flag at its target value makes every flag mutation inert. This is H2 restated as a
mutation-arming rule, and it is why plan 4 C6(a)/(c) now seed the flag `true`.

**H9 — the event `extra` may not carry an enum.** `RETURNING StockReportItem.priority` yields a
`StockReportPriorityEnum` member. `event_bus.dispatch` never serializes, and phase 4's tests
monkeypatch dispatch away — so a non-JSON-serializable payload **passes every test in this batch and
fails in production**. Emit `priority.value` (or `None`) in the `:updated` payload. No criterion
pins this; declare it in your handoff as a candidate criterion.

**H10 — `_locks.py` helpers** take `(session, workspace_id, client_ids)` positionally and already
sort. See §2.

**H11 — `apply_goal_effect`'s registered signature has no `workspace_id`**, but the repair record it
writes needs one. Use `assignment.workspace_id`. Record the choice.

**H12 — `build_workspace_event(entity, event_name, *, workspace_id, extra)` takes an object with
`.client_id`**, while §6.5 registers `_events.py`'s builders with a `client_id: str` parameter.
Construct `WorkspaceEvent(event_name=…, client_id=…, workspace_id=…, extra=…)` directly inside
`_events.py` and say so. Do not invent a `SimpleNamespace` shim.

**H13 — never run `alembic upgrade` or `downgrade` against the dev database, and add no revision.**
Master plan §9 rule 12: the schema is fixed in phase 1. Phases 4 and 5 need no schema change —
verified, every column and index they use exists at `e548d1f`.

## 5. Mutation discipline

**Standing rule, because most cells do not say it:** every named mutation is applied at the
**definition site** of the function named in the plan's task section unless the cell says otherwise.
Record the file and the site in the ledger for every mutation. Batch A's first fix round lost five
mutations to exactly this ambiguity.

- Run **every** named mutation in both plans' criteria tables, at the scope the row needs, and
  revert each one. Report `executed == declared` with the per-criterion summands, the site, and the
  observed failing test id and assertion.
- Cells marked `—` are not run. Plan 5's `—` cells now say which row they mirror; record them as
  mirrors so the `declared` count stays honest.
- Several cells are now **enumerated** (i)/(ii)/(iii) — run each sub-mutation and record which
  reddened which sub-check. They were enumerated because one mutation could not reach all of a
  row's sub-checks.
- Some cells now name a mutation as an **equivalent mutant** and say which row carries the real
  bite. Do not run those; record them as equivalent, with the reason.
- **If a mutation you run does not redden anything, that is a finding, not a nuisance.** Report it.
  Do not quietly adjust the test to make it bite, and do not skip it.

## 6. Evidence

- **L1 per test file as it lands**, whole file, never `-k`.
- **Per phase, before moving on:** that phase's L1 files green and every named mutation run.
- **Do not** run L4 at the phase-4 boundary.
- **Batch end, once:** L2 over the batch's test folders plus
  `tests/integration/services/commands/reset`, and **one L4**
  (`PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile`), diffing the failure-ID set **in both
  directions** against the 21-ID baseline (§10; list in
  `docs/architecture/archives/test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md` §3).
  The current stamp is **21 failed / 3264 passed / 2 skipped**. Expected: the same 21, and passed
  ≥ 3264 plus your new rows.
- **Record the tree SHA each stamp ran on.**
- **Workspace isolation (master plan §9 rule 1):** every test scopes its assertions to its own
  workspace and asserts no global total. Any test that commits purges in `finally` via
  `purge_stock_report_workspace`. Measured 2026-09-19: ~819 rows already leak per run from other
  files — do not add to it.
- **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19): assert input → outcome at a
  public boundary. Where a plan row itself names a statement-level instrument (`count_writes`),
  implement it as written; add such assertions nowhere else.

## 7. Git

Commit a checkpoint at the end of each phase:
`CHECKPOINT (not approved): stock_report phase <n> — <one line>`, **perimeter paths only**
(`git add <paths>`, then `git commit -m "…" -- <paths>`). Never `add -A`, `add .` or `commit -a`.
Never push, amend, rebase or reset. List every SHA in the handoff. Write no tracker row.

## 8. Do not touch

The intention; the master plan (report signature changes to me instead); the Scanner repository or
its handoffs; plans other than 4 and 5, and those only by appending one **Review log** entry each;
other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`; phase 3's shipped code
except the two amendments §1 B2 and §3 N-S3 explicitly authorize; the 21 baseline failures. No graph
write — that gate is mine. No new Alembic revision.

## 9. If you get stuck

You are running unattended; the owner is asleep and I am orchestrating. If something genuinely
blocks you:

- **Do not** weaken a criterion, a helper, or an assertion to get past it.
- **Do not** invent a criterion row or delete a failing test.
- Implement everything you *can*, and report the blocker precisely: what you tried, the exact error,
  and what you think the resolution is.
- A partial batch with an honest blocker report is a good outcome. A complete-looking batch with a
  quietly weakened instrument is the worst one.

## 10. Handoff

Write it to `SR/handoffs/implementer/2026-09-21_batch_B1_implement_1_handoff.md`. Frontmatter:
`plan: batch B1 (4, 5)`, `role: implement`, `round: batch_B1-implement-1`, `state`, `date`, `actor`,
`tree`. Structure:

1. **Gate check record** (the four lines with their outputs).
2. **Phase 4**, then **Phase 5**, each with: the Task 0 coverage map (one line per criterion row →
   test id → whether the assertion has the shape the row specifies); test files and L1 results; the
   named-mutation ledger (`executed == declared`, with summands, sites, and the red test id per
   mutation); judgment calls and deviations with reasons.
3. **The three amendments**: `write_repair_record`'s new signature (B2), `set_task_stock_flag`'s new
   signature (N-S3), and the H12 event-builder decision — each with its exact final signature, for
   master plan §6.5.
4. **N-R3 discharge**: which helper got its first caller where.
5. **Candidate criteria** you are declaring: N-S3's tenancy guard, H9's enum serialization, H11's
   `workspace_id` source, and anything else you had to decide without a row.
6. **Batch level:** cross-phase integration evidence, contract compliance against §5, the L2 and L4
   stamps with tree SHAs and the two-way baseline diff, the commits, blockers and limitations.
7. **Write perimeter:** every path created or changed, checked against `git status --porcelain` and
   `git diff --stat a306298..`, listing separately every file a mutation probe touched (applied,
   reverted, confirmed byte-identical).
8. `⚠ OWNER DECISIONS REQUIRED (n)` in the charter's card format, or `(0)`.

Your final message's first line is `HANDOFF: … | STATE: … | OWNER_CARDS: n`, followed by a short
summary of what landed, what did not, and the single most important thing I should know.
