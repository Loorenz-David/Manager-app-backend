---
plan: batch A — plans/plan_1.md, plans/plan_2.md, plans/plan_3.md (master_plan.md §3A)
role: reviewer (Claude Opus, skill `plan-reviewer`) — re-review after fix round 1
round: batch_A-rereview-1
date: 2026-09-20
tree: 983d774
scope: light and delta-scoped (§3A), widened for shared foundations and the declared mutation gap
---

# Batch A re-review 1 — after fix round 1

This is a **delta-scoped re-review**, not a second full review. Batch A's first review
(`SR/handoffs/reviewer/2026-09-20_batch_A_review_1_handoff.md`, tree `0d5d31d`) returned
CHANGES_REQUESTED with 125 PASS / 30 FAIL / 15 NOT_VERIFIED of 170 rows. One grouped fix round ran
against `SR/prompts/implementer/2026-09-20_batch_A_fix_1.md`. Your job is to decide whether batch A
is now APPROVED.

If you wrote the first review, you have no memory of it — read it. It is your own prior work and its
verdict table is the baseline this re-review is a delta against.

Paths are relative to the repo root `backend/`. `SR/` =
`docs/architecture/under_construction/implementation/stock_report/`. `bm/` = `app/beyo_manager/`.
Run tests from `app/`.

## Scope

**The delta is `git diff 0d5d31d..983d774`** — 8 production files, 8 test files (two deletions),
three plan Review logs, plus docs. HEAD is `983d774` and the working tree is clean.

**In scope:**

1. The **45 rows** the first review failed or could not verify (30 FAIL + 15 NOT_VERIFIED), listed
   in §"What to re-verdict" below. Give each a fresh verdict.
2. The **six production corrections** (F-B1, F-B2, F-S1, F-S2, F-S6, F-S7) and the **registry
   restoration** (F-S8) — these changed behaviour, so verify the behaviour, not just the diff.
3. **The mutation sweep** — see the gap below. This is the widening.
4. **Rows previously PASS whose foundation the fix moved** (§3A's widening clause): every row whose
   test or source path touches a changed §6.5 signature (`recompute_row_counters`,
   `recompute_goal_total`, `expected_task_flag`, `recompute_task_stock_flag`,
   `write_repair_record`), `_locks.py`, `consistency.py`, `criteria_normalization.py`,
   `scanner_property_tables.py` or `reset_app.py`. Name the rows you pulled in and why. Do not
   re-verdict the rest.

**Out of scope:** the 125 rows the first review passed whose foundation did not move; re-deriving
the Scanner conformance record (§3 of the first review — done, and the wood-group casing finding it
produced is in this delta); backlog notes N-1, N-2, N-3, N-6, N-8, N-9; the 21 baseline failures;
the nine plan lessons L-1…L-9 (mine to fold, not yours to restate).

## The gap that widened this re-review

The fix handoff (`SR/handoffs/implementer/2026-09-20_batch_A_fix_1_handoff.md`) is honest about its
own limit and states `state: IMPLEMENTED_WITH_MUTATION_GAPS`:

> The remaining declared sites … were not independently mutated; they are explicitly not represented
> as executed. … No claim of `executed == declared` is made.

It armed roughly 45 rows and ran **8** mutations (§5 of that handoff: F-B2, P1 C5(g), P1 C7(a),
P2 C3(d), F-S1/P2 C7(a), F-S2, F-B1/P3 C3(h), P3 C7(a)). For every other row it armed, we have a
test that passes and **no evidence it can fail** — which is precisely the defect family that caused
the first review's 26 "the test is weaker than the row" FAILs. A fix round that re-creates the
defect it was sent to remove would be the worst outcome available here, so closing this is the
substance of your re-review.

**Run the named mutation for every row you re-verdict**, at the scope the row requires, unless:
- the fix handoff's §5 already records it red (then cite it — same tree, consume it); or
- one mutation reddens several rows (then say which, and run it once); or
- the plan marks the row `—` or "cannot isolate" (plan 1 C4(f)).

Report a line per declared site, and name explicitly any you could not run and why. The distinct
declared-site count is **35 / 37 / 22 = 94** (your first review's count, and mine).

## What I already verified (consume by citation, do not re-run)

- **L4 on `983d774`**, my own run: `PYTHONPATH=. pytest -m 'not e2e' -n 6 --dist loadfile` →
  **21 failed, 3265 passed, 2 skipped in 64.89s**. Failure IDs **identical to the 21-ID baseline in
  both directions**. Passing count 3103 → 3265. No stock-report test fails; nothing that passed
  before broke. **Do not run L4.**
- **Perimeter:** `git diff --name-status 0d5d31d..983d774 -- app/` is 17 paths, all inside the
  batch A perimeter, with exactly two deletions —
  `app/tests/unit/domain/stock_report/test_settings.py` and
  `app/tests/unit/domain/stock_report/__init__.py`. No escape.
- The three plan files received Review-log entries only; no criteria table, task list or §4 list was
  edited.

## What to re-verdict

Give each row `PASS | FAIL | NOT_VERIFIED` with its test id, and state whether its named mutation
was run and what reddened.

**Plan 1 (13).** C1(c), C1(d), C1(e), C1(f), C1(g), C1(h), C1(j) — the index rows that must each
name **one** index (the first review's F-S4: the old test matched a disjunction over two index
names on a fixture violating both). C2(a) — the row's `compare_metadata` instrument, which the fix
claims replaced the migration source grep. C3(a) — the reset row, which must now assert the
workspace row is gone, use the kit's `capture_dispatch`, and purge in `finally`. C5(a), C5(b),
C5(c), C5(d) — the signature clauses: two spellings → **two different signatures**, idempotence over
**every** C4/C5 payload, **six** golden vectors.

**Plan 2 (11).** C2(c), C2(h), C3(d), C4(a), C4(b), C4(d), C5(d), C5(e), C5(n), C6(j), C7(a).
C3(d) matters most: its mutant **survived** L1 and L2 in the first review (probe P1), so re-run that
mutation yourself and confirm it now bites. C2(h)/C4(a)/(b)/(d) turn on the wood-group casing fix —
confirm the bag now carries Scanner's declared `"Dark"` / `"Teak"` / `"Light"`.

**Plan 3 (21).** C1(a), C1(d), C1(e), C1(f), C1(g), C1(h), C1(i), C1(j), C1(k), C2(a), C3(a),
C3(b), C3(c), C3(d), C3(f), C3(g), C3(h), C6(d), C6(e), C7(a) — and C6(a), which the first review
failed on its unasserted `target_kind` clause. The bar is intention §12A's own words: one planted
drift per `kind`, **each producing exactly one divergence of that kind with the exact stored and
expected values**. A kind-set assertion still does not meet it. C2(a) must now follow the owner's
restatement (master plan §7.4 item 5): every row of the four MC-9 tables plus
`stock_report_repair_records` in W equal before and after — not a write count. C5(a) legitimately
keeps `count_writes`.

## Specific things to check on the corrections

- **F-B1.** A row with `priority = NULL` and `priority_order` set must now be repaired — order set
  to NULL, **one** `stock_report_item` repair record with the old order as `stored_value` and NULL
  as `recomputed_value` — and the post-repair re-check must not raise. Probe the original crash
  (the first review's P10) and confirm it is gone. Also confirm the nullness step still runs
  **before** the density renumber.
- **F-B2.** `{'k': ['Teak', '  ', 'Dark']}` → `['dark', 'teak']`. `CRITERIA_NORMALIZATION_VERSION`
  must still be **1** — the owner ruled it stays (master plan §4A). A bump is a FAIL.
- **F-S2.** `expected` is `max(group) + 1`. Re-run the first review's P5 shape: a `[1, 7]` group with
  a null-order row must report 8, not 3. Confirm plan 3 C1(g) has a dense fixture **and** a sparse
  neighbour, so the row can tell `max+1` from `len+1`.
- **F-S6.** `lock_stock_report_history_records` exists, is taken **after** the assignment locks, and
  the goal-total UPDATE no longer touches an unlocked row. Report its exact signature — I add it to
  master plan §6.5; the implementer was told not to edit the master plan.
- **F-S7.** `rowcount == 1` on all four repair-path statements, with the task-flag helper's
  idempotent 0 still legitimate **outside** the repair path. Check the guard actually fires.
- **F-S8 (registry).** The six registered signatures are what callers use. Per-row helpers must be
  genuinely per-row (`recompute_row_counters(session, stock_report_item_id)`), with any
  workspace-wide variant private and separately named. `write_repair_record` takes `now` and
  `created_at` is the operation's `now`, not wall-clock. The `Divergence` TypedDict exists. This is
  the group most likely to have been satisfied in name only — check the call sites, not the `def`
  lines.
- **The two deletions.** `test_settings.py` was deleted as an orphan (plan 1 says settings carry no
  criterion) and `__init__.py` was deleted per note N-5 — and the fix handoff reports that removing
  the `__init__.py` exposed a duplicate-module collection error against
  `tests/helpers/test_settings.py`, which the deletion resolved. Confirm that story: that nothing
  else was being shadowed, that no surviving test lost coverage, and that collection is now correct.
  A collection error that was silently present before is worth a note.

## Rules

- **Outcomes, not internals** (charter rule 2, owner rule 2026-09-19). A finding that only asks for
  an implementation-coupled assertion is a **backlog note**, never CHANGES_REQUESTED.
- Do not redesign, do not weaken a row to make it pass, do not invent rows the plans lack.
- Do not modify source or tests; revert every mutation probe and prove the file is byte-identical.
- A row armed but never mutated is not automatically a FAIL — run the mutation and decide on what
  you observe. `NOT_VERIFIED` is the honest verdict when you could not run it.
- **Owner stop (§3A):** if this re-review returns CHANGES_REQUESTED, work halts and the owner rules
  on each finding before any second fix round. So rank findings by whether they must block APPROVED,
  and be explicit about which are genuinely blocking.

## Do not touch

The intention; the Scanner repository (read-only); the Scanner handoffs; the plan files except one
appended Review-log entry each; the master plan (tracker rows and §6.5 are mine — report, don't
edit); other roles' prompts or handoffs; `docs/archgraph-anchor-observations.md`. Make no commits
and no graph write.

## Handoff

Write it to `SR/handoffs/reviewer/2026-09-20_batch_A_rereview_1_handoff.md`. Frontmatter: `plan:
batch A (1, 2, 3)`, `role: review`, `round: batch_A-rereview-1`, `state: APPROVED |
CHANGES_REQUESTED`, `date`, `actor`, `tree: 983d774`. Structure:

1. **Verdict**, with the batch's row totals now (of 170) and the delta against the first review's
   125/30/15.
2. **Re-verdict table** for the 45 rows plus any row you pulled in under the widening clause.
3. **Mutation sweep**: one line per declared site — run here, cited from the fix handoff, subsumed
   by another mutation, or not run and why. State plainly whether `executed == declared` now holds.
4. **Correction-by-correction confirmation** (F-B1, F-B2, F-S1…F-S14), each CONFIRMED, PARTIAL or
   NOT_DONE.
5. `lock_stock_report_history_records`'s signature for master plan §6.5.
6. **Findings**, if any, ranked blocking first, each with the row it belongs to.
7. **Backlog notes**, separate.
8. **What you ran.**
9. **Mutation-probe declaration** (files mutated and restored, hashes; scratch under `/tmp`).
10. `⚠ OWNER DECISIONS REQUIRED (n)` in the charter's card format, or `(0)`.

Your final message's first line is the `HANDOFF: … | STATE: … | OWNER_CARDS: n` line, followed by
the owner layer.
