---
plan: plan_2
role: implementer
round: 1
date: 2026-08-22
---

# Session prompt — implementation-executor, phase 2 of `narrow_typical_work_times`

## Role and workspace

You are the **implementer** for phase 2: extend `typical_times_statement` to compute both
populations in one pass for K specs, translate a spec into an item-match predicate in one
new query-layer module, keep the no-spec form byte-identical, and measure the query cost.
You build exactly what the plan says and prove it with the plan's named mutations — you do
not improvise contracts.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** Commits use **explicit paths only, never `git add -A`**.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## Gate check (stop-and-report if any fails)

1. `<project>/master_plan.md` §4: phase 1 **`APPROVED`**, phase 2 `PROJECTED`.
2. `git status` clean at start (only `?? .archgraph/contexts/` is expected).
3. `<project>/plans/plan_2.md` header reads `state: PROJECTED`.

## ⚠ TASK 0 — TESTS FIRST. This is the change that defines this phase.

**Before you write a single line of production code**, transcribe **every criterion row
and every prose clause** of `plans/plan_2.md` §6 — **as corrected by §6A** — into the test
files as executable cases. Run them. They must be **red for the right reason** (a missing
function, a wrong value — not an import error or a typo). Only then implement to green,
and only then run the named mutations.

**Why this is task 0 and not a style note.** Phase 1 took four implementation rounds, and
**eleven of its thirteen audit findings were transcription failures** — a row the plan
enumerated that never reached the test file, or a row that reached it with the criterion's
own field projected away. That class is nearly invisible when auditing finished tests and
obvious while transcribing with the plan open. The three audit passes that caught them
were each re-deriving a comparison you can make in your first hour.

**A row you cannot transcribe is a PLAN DEFECT — stop and report it.** Do not invent the
missing value, do not pick a "reasonable" fixture. The projection already removed nine
such rows; if a tenth survives, it is worth more as a report than as a guess.

**§6A wins over §6 wherever they differ.** Read §6 first for intent, then §6A for what is
actually binding. Six criteria are untouched and transcribable as written: **C2, C4, C5,
C6, C7, C11**. Everything else carries a correction.

## The three traps the projection measured — know them before you start

1. **C1's mutation must be the corrected one.** "Make the item joins unconditional"
   **cannot redden** the `len(specs) == 0` branch task 3 mandates — item joins only exist
   on the `K ≥ 1` path. Use **"delete the `len(specs) == 0` branch"**. This is the same
   inert-mutation shape §11A repaired as T11 one phase ago; do not re-create it.
2. **Fixtures below the sample floor prove nothing.** `narrowed_typical` /
   `section_typical` are `NULL` below `TYPICAL_MIN_SAMPLE_SIZE`
   (`get_working_section_typical_times.py:49-52`), so a one-task fixture yields `None` on
   *both* sides of a mutation. And at exactly five groups, tripling **one** leaves
   `median({S,S,S,S,3S}) = S`. **Every fixture asserting a typical value clears the floor
   and moves every element it needs to move.** §6A names C8, C9 and C13 specifically.
3. **The K-multiplication hazard, and which criterion owns it.** Materialise `spec_index`
   as a **cross join in the OUTER select**, added to its `GROUP BY` — putting it inside
   `grouped_steps` without adding it to *that* subquery's `GROUP BY` multiplies
   `SUM(total_working_seconds)` by K. **C5 is the guard**: it pins `section_sample_count`
   at every index and against the `K == 0` call. §6A carries the worked-out shape.

## Decided for you (do not re-litigate)

- **One execution strategy this phase**, on **§4A K4's axis** (inner vs outer attachment)
  — not §4.2's `bool_or`/GROUPING SETS taxonomy, which the criteria do not bind. GROUPING
  SETS as named cannot produce K2's cardinality; it is dropped for V1 (§6A).
- **`build_item_match` keeps its `(bool, predicate | None)` tuple.** The projection checked
  whether the bool was dead and concluded it is not.
- **Under outer attachment, the `TaskItem` `ON` clause needs `workspace_id`, which
  `grouped_steps` does not select** — bound parameter or extra column, your choice, `K ≥ 1`
  only so C1 is unaffected. **Say which you chose in the handoff.**
- **No performance threshold** (D26 / intention §12A). Measure honestly; no number blocks
  you. But a result an **order of magnitude outside expectation goes in the handoff as a
  flagged observation**, not silently into the doc.

## The measurement matrix (task 8) — read §12A before you seed

**20-task pages, not 50** — the frontend paginates at 20; 50 is only the API cap. Ten
cells: {single task, 20×5, 20×10, 20×20, no-spec} × {current, new}, **plus one 50×20 row
on the new statement only**, labelled *API ceiling, not a realistic page*.
**State which cells are copies:** the current statement is spec-blind, so its cost is the
same query in all five of its rows, and the new no-spec row equals it by C1 — five of ten
are constant by construction, and unrecorded a reviewer cannot tell a measurement from a
copy. **Record exact seed cardinalities**, every section clearing
`TYPICAL_MIN_SAMPLE_SIZE`. The harness is **committed** at
`app/tests/integration/services/queries/working_sections/_narrowing_seed.py`.

## Environment (master plan §10 is authoritative)

From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`; xdist 6 workers is in `addopts`,
`-n 0` is the serial comparator. **Redis must be reachable** or the baseline reads 23
failed / 2 errors instead of 21. The comparator is the **21-ID set**, not the count.
Databases: server `localhost:5433`, per-process disposable templates — **never run two
suite sessions concurrently in this checkout**. Phase 1's approved suite was **2617 passed
/ 21 failed / 2638 collected**; that is your starting point.

Orient the graph read-only at start (`archgraph_status` + `.archgraph/contexts/current-task.md`,
untracked and not to be rebuilt or committed); record the phase's delta at the end as
**one batched `archgraph_apply_changes`** — expected: the new query module and the
typical-times projection's changed contract. Never promote, reject or edit a review item.

## Evidence budget

- Every named mutation runs at **L1 hypothesis scope** — whole files, **never `-k`**.
  §6 names the scopes; C7/C8/C9 name cross-file bite sets and run at L2.
- **Exactly one L4 stamp** closes the cycle, on the tree you hand over, with the
  failing-ID delta against the 21-ID set **in both directions**. Check Redis first.
- **State, per named mutation, which test id failed.** Not "the file reddened" — the id.
  Phase 1 paid twice for attributions written from the finding instead of from the
  repaired code (master plan §9); you have the pytest output in hand and it costs one
  column.
- The docs guard is a **no-op for this phase** — `query_cost_measurements.md` lands
  outside its roots (§6A). Run it if you like; do not report it as having checked that file.

## Closing protocol

1. Tests green at the perimeter; every named mutation run with both sides and its failing
   test id recorded.
2. Update `<project>/master_plan.md` §4 row 2 and `plans/plan_2.md` (`state:` + Review log).
3. **Checkpoint commit** at `IMPLEMENTED`: subject prefixed `CHECKPOINT (not approved): `,
   explicit paths. Never squash, never push.
4. Handoff at `<project>/handoffs/implementer/20260822_plan2_implementation_handoff.md`,
   frontmatter `plan: plan_2`, `role: implementer`, `round: 1`, `date`, `actor`. Body:
   owner-readable opening (3–5 sentences, plain words); **a task-0 section stating what
   you transcribed, what was red before implementation, and any row you could not
   transcribe**; the criteria ledger with per-mutation both-sides + failing test id; the
   measurement doc's headline numbers with anything surprising flagged; the L4 stamp; the
   full write perimeter from `git status`; the checkpoint SHA.
5. Final chat message is the charter's **owner layer**: what you did → what it means →
   what happens next → what needs the owner; one pointer line naming the handoff.
