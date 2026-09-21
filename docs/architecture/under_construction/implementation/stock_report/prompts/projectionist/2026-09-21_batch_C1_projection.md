---
batch: C1
phases: [8, 11]
role: projection
round: 0
state: PROMPT_READY
date: 2026-09-21
actor: orchestrator
model: Opus
---

# Batch C1 projection + lesson fold — plans 8 and 11

You are the round-0 projection for batch C1. Follow the `plan-projection` skill and
`/Users/davidloorenz/agent-skills/pipeline-charter.md` as session doctrine; read both by absolute
path before you start. This prompt frames the session — **where it and a plan file differ, the
plan file wins.**

Project root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Project dir: `docs/architecture/under_construction/implementation/stock_report/` (below, `SR/`)
HEAD at dispatch: `05ec920`, clean tree.

## Scope

**Plans 8 and 11 only.** Plan 8 = batch assignment create/override/delete, the matcher, the race
row, role cells. Plan 11 = removal hooks (task, item, PRIMARY unlink) and the category guard on
both item writers. Inside C1, 11 depends on 8 (§7.2); 9 and 10 are batch C2 and are **out of
scope** — do not read, fold, or comment on them.

Phases 1–7 are **APPROVED and VERIFIED**. Their code is shipped and on disk. This matters for you:
most of the mutation sites below are in **real code you can open and check**, not in code that
does not exist yet. Use that.

## Why this session exists, and what makes it different

This project now runs the charter's **tester role** (master plan §3B). The implementer no longer
designs mutations or writes the coverage map; a separate Opus tester does, on finished code,
before the reviewer. Your fold is what makes that handoff cheap: a mutation cell you get right
here is one the tester does not have to invent and the reviewer does not have to re-derive.

Read master plan **§3B** in full before you act on anything else in this prompt.

## Task 1 — the mutation-cell classification (the main deliverable)

Master plan §3B's amended *Mutation cells* bullet defines three classes for an empty (`—`)
mutation cell. **Read that bullet; it is the specification for this task.** Briefly:

1. **Plan-determined** — derivable from the row's own text, no knowledge of unwritten code needed.
2. **Site-undetermined** — the outcome is real, the line that makes it true is an implementation
   choice. Stays `—` **plus a one-line note that the blank is deliberate.**
3. **Reveals a defect** — the attempt exposes a bad row.

A prior pass over plans 8, 9, 10 and 11 produced the classification in **Appendix A** below.
**Treat it as a hypothesis to verify, not as fact.** It was produced from the plan text alone by a
single agent, and a wrong mutation cell is *binding* — it costs a review round. For every row:

- confirm the class is right;
- for class 1, **open the file the proposed mutation names and confirm the site exists, that the
  symbol/line is really there, and that it executes under this row's own fixture** (lesson L-31).
  Correct the proposal, or demote it to class 2, wherever it does not hold;
- add any row the prior pass missed, and delete any it invented.

Expected: plan 8 has 26 empty cells (21/1/4), plan 11 has 8 (8/0/0). **Verify those counts
yourself by script and report the real ones.** A third count discrepancy exists in this project
(a row-shape regex disagrees with the published per-phase totals: plan 8 is published at 67 rows,
the prior pass counted 60) — **report what you measure and how you measured it; do not reconcile
it or re-publish a total.** That is a separate owner item.

**You do not edit the plan files.** Output a patch table (below) and the orchestrator applies it.
That is §3B's authority boundary and lesson L-20's; keep it.

## Task 2 — the lesson fold (master plan §9A)

§9A is the register. Fold **only** the rows it marks foldable, and **only** those whose Targets
column names plan 8 or plan 11.

**Order is fixed and not free:**
1. **L-20 first** — it defines which cells an agent may touch. Land it as a §9 standing rule
   proposal before anything else, then apply it to 8.
2. **L-17 second** — highest yield. Its **fixture-preamble half is yours**; where you find an
   outcome that is *arithmetically wrong* against its own fixture, that is an **owner card**, not
   a fold.
3. Then the rest targeting 8 or 11: L-9, L-10, L-12, L-13, L-15, L-16, L-21, L-23, L-24, L-25,
   L-28, L-30.

**Owner-only — draft as cards, never fold:** L-2, L-5, L-17's outcome half, L-29.
**Already handled by the orchestrator, do not touch:** L-8 (becoming a §9 standing rule).

## Task 3 — the owner cards

Three are already known and **must come back with proposed text written**, ready to ratify:

- **Card A — plan 8 C1(k), and C1(j) with it.** The row cannot fail: dropping the phase-3
  `item_already_assigned` pre-check still ends in 422 `item_already_assigned`, because the partial
  unique index on `(workspace_id, item_id)` over the active states makes task 2's `IntegrityError`
  backstop produce the same outcome with nothing written. Verify that claim against the shipped
  index and the shipped router before you draft. Proposed remedy: a statement-level clause (no
  `INSERT` on `stock_task_assignments`, via the MC-9 statement listener / `count_writes == 0`), or
  folding (j) and (k) into one row carrying it. Draft both options with the exact row text.
- **Card B — plan 8 ↔ plan 11 C1(c) contradiction.** Plan 11 C1(c) builds its two-assignment task
  as "A resolved on R via `PR`, then `CR` on R2 for the same item"; plan 8 C1(p)/C1(q) refuse
  exactly that with `already_processed_by_scanner`, "on any row". One must give. Establish which
  plan is right on the semantics (the intention decides, not convenience), then draft the fix for
  the other.
- **Card C — L-29 on plan 8.** §9A names plan 8 explicitly. This is the batch B1 finding: the S2
  lock fixture *ran and could not fail* — the reviewer dropped the task lock, reversed the order,
  and all 63 tests still passed, because one transaction cannot contend with itself. Plan 8 is
  where the caller's lock order must actually be proven. Draft **the criterion row** (5 columns,
  house format) for the owner to author — including whether it is forceable with two real
  sessions under this project's two-session rule (§9 rule 9), or whether it is honestly
  `UNFORCEABLE` with a structural check.

Add further cards only where a fold is genuinely blocked by an outcome, a task cell or a
contradiction. Each card: what is wrong, why only the owner can settle it, and the options with
proposed text. **Never author a criterion row yourself** — draft it for the owner's signature.

## Task 4 — the standing projection checks

Per the `plan-projection` skill, on plans 8 and 11: every cited path exists; every cited contract,
registry signature and §6.5 name exists and matches; task text does not contradict its own
criterion; fixtures are constructible **under the rules this plan itself imposes** (plan 8 §7's
CR-only rule already broke one fixture — plan 8 C6(g) — look for others); externally-derived
fixtures (rule 17) are re-grounded against the real dependency.

Two specific things to rule on, because batch B2 lost a round to the first:

- **Perimeter extensions.** Several proposed mutation sites live in files belonging to closed,
  approved phases: `domain/stock_report/state_map.py` (plan 1), `_remove_assignment.py` (plans
  4/5), and others you may find. The tester doctrine permits probing approved out-of-perimeter
  files — applying and reverting is not an edit — but B2 saw seven mutations **declined** for
  exactly this reason. **Enumerate every such site and propose an explicit §7 declaration** in the
  owning plan, the way plan 8 §7 already declares `apply_stock_demand.py` for C4(m). Note where a
  mutant will also redden a closed phase's own tests (e.g. `state_map.py` is guarded by plan 1
  C6(a)/C6(j)) so nobody reads that as a regression.
- **Foreign load-bearing sites.** Master plan §6.1b is the registry, earned when a stock-report
  identity guarantee turned out to be armed by one argument in `properties_signature.py`, a file
  no plan named. If a row in 8 or 11 depends on a site in a file no plan names, it goes in §6.1b —
  propose the entry.

## Deliverable

One handoff at `SR/handoffs/projectionist/2026-09-21_batch_C1_projection_handoff.md`, frontmatter
(`batch: C1`, `phases: [8, 11]`, `role: projection`, `round: 0`, `state`, `date`, `actor`),
containing:

1. **Counts**, measured by script, with the command shown.
2. **The patch table** — the whole point of the session. One row per cell to change:

   | Plan | Row | Cell (mutation / fixture / note) | Current text (verbatim) | Proposed text (verbatim) | Class | Lesson(s) | Site verified? |

   The *current text* must be copy-pasteable so the orchestrator can apply it mechanically.
   For class 2, the proposed text is the deliberate-blank note, and the cell stays `—`.
3. **Class-3 rows in full** — defect, minimal fix, and whose authority it is.
4. **Owner cards** in a section headed `⚠ OWNER DECISIONS REQUIRED (n)`, cards A–C first.
5. **Perimeter extensions and §6.1b entries**, as proposed text.
6. **Blockers** — anything that must be settled before the implementer prompt is compiled, ranked.
7. **What you did not check**, so the tester and reviewer know where their budget buys something.

## Boundaries

- **Read-only on plan files and production code.** You write exactly one file: your handoff. No
  commits, no edits to plans, the master plan, tests or source. No `git add`.
- Do not run the test suite. Do not run mutations. You are before implementation; there is nothing
  to mutate yet. Checking that a *site exists* means reading the file.
- Do not design the implementation. Do not propose new criteria beyond drafting the owner's cards.
- Do not re-litigate phases 1–7. They are APPROVED. If you see something wrong in one, it is a
  note in your handoff, never a blocker on C1.
- Report what you could not do, and anything you are uncertain about, plainly. An honest
  "I could not verify this site" is worth more than a confident wrong cell — the cell is binding.

## Appendix A — prior classification (hypothesis, verify it)

### plan 8 — 26 empty cells: 21 class 1, 1 class 2, 4 class 3

Class 1, with proposed mutation:
- `C1(a)` delete the phase-3 `stock_report_item_not_found` existence check → an absent row id falls through to `task_not_found`
- `C1(d)` delete the phase-3 task-existence check → an absent `task_id` falls through to `item_not_task_primary`
- `C1(e)` delete the phase-3 item-existence check → an absent `item_id` falls through to `item_not_task_primary`
- `C1(h)` drop `failed` from the refused task-state set of the `task_failed_or_cancelled` check → the entry is created
- `C1(l)` delete the `item_has_no_category` check → a NULL-category item falls through to `category_mismatch`
- `C1(m)` drop the row-category ↔ item-category comparison in phase 3 → a K2 item is created on a K row
- `C2(b)` drop the repeated-`task_id` detection from phase 1 (keep only `item_id`) → both entries reach phase 3
- `C3(f)` remove the `min_length=1` constraint on `entries` in the create request model → `{"entries": []}` returns 200
- `C4(a)` set the `pending` cell of `ASSIGNMENT_STATE_BY_TASK_STATE` (`domain/stock_report/state_map.py`) to `awaiting`
- `C4(b)` set the `assigned` cell of the same map to `in_progress`
- `C4(d)` set the `stalled` cell to `in_queue`
- `C4(e)` set the `ready` cell to `in_queue` → kills state, `(0,0,4)` and the `G == 4` credit at once
- `C4(g)` replace `max(item.quantity, 1)` with the literal `1` at the phase-5 insert
- `C6(a)` in `_remove_assignment.py`, drop the `set_task_stock_flag(..., False)` call
- `C6(b)` in the removal's goal step, skip the un-credit for an `awaiting` assignment
- `C6(c)` in `_remove_assignment.py`, treat a terminal assignment like an active one — same mutant C6(i) names
- `C6(e)` drop the `is_deleted IS NULL` filter from the delete command's discovery/re-read
- `C6(h)` dispatch the delete events without `coalesce_stock_report_events` → two `:updated` for R. **Caveat flagged: the `[A, B]` list order is not pinned by the fixture — assert as a set, or fix the `client_id` order. Rule on this.**
- `C8(a)–C8(d)` add `seller` to the allowed-role set of `POST /api/v1/stock-report/assignments`
- `C8(e)–C8(h)` same on `POST /api/v1/stock-report/assignments/delete`
- `C8(j)` remove `StockAssignmentPropertyMismatch` from the router's explicit-rendering branch

Class 2: `C3(d)` — "re-evaluated from scratch" has no site; each request is stateless, so the only
mutation invents a branch no task mandates, and the observable equals C1(i)'s.

Class 3: `C1(k)` (card A), `C4(k)` (ordering clause undiscriminating — the fixture never fixes
input order, so request order equals ascending-id order; proposed fix: supply the two entries in
**descending** `item_id` and say so), `C4(l)` (contradicts task 2 as amended by the owner ruling
of 2026-09-21 — the create response is the fourteen-key `serialize_stock_task_assignment` shape
with nested `item`/`task`, not "the seven keys of task 2"; master plan records that such rows are
re-stated at this fold), `C6(g)` (fixture not constructible as ordered under plan 8 §7's CR-only
rule — the partial unique index on `(workspace_id, task_id)` forbids a second assignment on T
while A is active; needs the build order spelled out, or an exemption).

### plan 11 — 8 empty cells: 8 class 1, 0 class 2, 0 class 3

- `C2(c)` remove the PRIMARY-unlink removal hook from `remove_item_from_task.py` → the old assignment survives the swap and `CR([J on R])` hits the `(workspace_id, task_id)` active unique index (same mutant as C2(a))
- `C3(b)` restrict the `delete_item` hook to `ACTIVE_ASSIGNMENT_STATES` → the `failed` assignment is left non-deleted (twin of C1(b))
- `C5(b)` drop the `incoming == current` no-op short-circuit in `assert_item_category_change_allowed` → 409 on an unchanged category
- `C5(d)` delete the guard's active-assignment lookup and refuse on any differing category. **Caveat flagged: if the fixture instead gives I a terminal assignment, "widen the lookup to any non-deleted assignment" also kills it — the row should say which. Rule on this.**
- `C5(e)` delete the guard call from `find_or_create_item.py`'s existing branch
- `C6(a)` pass a different trigger at `delete_task`'s `remove_assignment` call → record trigger ≠ `inline:delete_task`
- `C6(b)` same at `remove_item_from_task` → ≠ `inline:remove_item_from_task`
- `C6(c)` same at `delete_item` → ≠ `inline:delete_item`

Plus, flagged for card B: **`C1(c)` (a filled cell)** prescribes a fixture plan 8 refuses.

### Flags carried from the prior pass

*Outcome names a different boundary than the fixture operates at:* plan 8 `C4(m)` (fixture is the
phase-7 demand path; §7 already extends the perimeter for it); plan 11 `C4(h)`, `C5(a)`, `C5(e)`.

*Concurrency rows (special rules — §3B and §9 rule 9):* plan 8 `C5(a)` (two sessions, Item lock,
barrier-forced; §7 records the `IntegrityError` backstop has no deterministic row); plan 11
`C7(a)`, `C7(b)` (declared unable to force their interleaving — they stay `UNFORCEABLE`; do not
try to make them bite).

*Fixture-side files no plan names (both verified to exist):* `commands/tasks/add_item_to_task.py`
(plan 11 C2(c)), `commands/task_post_handling/complete_task_post_handling.py` (plan 11 C4(h)).
