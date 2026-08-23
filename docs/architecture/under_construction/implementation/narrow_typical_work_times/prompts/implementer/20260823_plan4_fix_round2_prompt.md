---
plan: plan_4
role: implementer
round: 2
date: 2026-08-23
---

# Fix round 2 — phase 4, `narrow_typical_work_times`

You implemented phase 4 in round 1. **The production code is not in question** — both consumers
derive a spec, call the statement once, reconcile through `uniform_basis_v1`, and feed the same
`SelectedTypical`s to display and to weights, and the goldens prove the refactor moved no
number. Your perimeter was exact and you did task 9c even though nothing would have gone red if
you had skipped it. **This round is owed entirely for evidence.**

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine, by absolute path, before anything else:**
- `/Users/davidloorenz/agent-skills/pipeline-charter.md`
- `/Users/davidloorenz/agent-skills/implementation-executor.md`

**`plans/plan_4.md` is your task list. Where this prompt differs from it, the plan file wins.**

## Gate check — stop and report if any fails

1. `git merge-base --is-ancestor 0efbbd4 HEAD` succeeds (your round-1 checkpoint is an
   ancestor). Do not pin `HEAD` to a SHA.
2. `plans/plan_4.md` header reads **`state: CHANGES_REQUESTED`**, and `master_plan.md` §4 row 4
   agrees. Both were flipped by the coordinator's fold.
3. `plans/plan_4.md` §8 carries the **2026-08-23 coordinator consumption entry** ending in the
   six "verified correct" rows. That entry is your finding list; this prompt summarizes it and
   the plan wins.
4. `git status --porcelain -- app/` is **empty**. Anything under `.archgraph/` is the owner's
   live work and is expected whatever it contains — do not enumerate it, diff it, or halt on it.

`redis-cli ping` → `PONG` before any suite run.

## Scope

**Resolve the four blocking and two should-fix findings. Add nothing beyond them.** Do not
relitigate; do not refactor production code. If a finding seems wrong, say so in your report
with the measurement — do not silently do something else.

**Allowed file perimeter for this round:**
- `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py`
- `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py`
- `app/tests/integration/services/queries/item_economics/snapshots/no_category_task_prerefactor.json`
- `app/tests/integration/services/queries/item_economics/test_production_time_query.py` (S2 only)
- `plans/plan_4.md` §8 (your round-2 entry) and the §4 tracker row

**Production code is out of perimeter this round.** If a finding cannot be closed without
touching it, **stop and report** — that is a plan defect, not a fix.

## The findings

### B1 — C9(a) cannot fail. This is the one that matters.

Your test writes the baseline it then asserts against:

```python
if not SNAPSHOT.exists():
    SNAPSHOT.write_text(json.dumps(current, sort_keys=True, indent=2) + "\n")
expected = json.loads(SNAPSHOT.read_text())
```

**Measured by the coordinator:** snapshot removed → **8 passed**, no failure. The test
re-created the file from post-refactor output, and the regenerated copy contained
`typical_resolution` — a key that does not exist pre-refactor. The original was restored,
`md5` `96f91c9c0b9b105763a0256e0745f002`, tree clean.

Plan §4 states the rule this breaks, verbatim: *"Written once, before any production edit, and
**never regenerated** — re-capturing from a refactored tree restores exactly the `f(x) == f(x)`
vacuity §11A repaired T11 to remove."*

Your handoff also records: *"its numeric values were reconciled manually to the task-0
pre-refactor payload rather than regenerated."* **A hand-edited baseline behind a self-healing
read is two independent reasons the row cannot discriminate.**

**Correction, both halves:**
1. **The test reads, never writes.** Replace the write branch with
   `assert SNAPSHOT.exists(), "pre-refactor baseline missing — see plan 4 §4"`. Removing the
   file must make this test **red**.
2. **Re-capture the baseline honestly, from a pre-refactor tree.** `git worktree add` (or check
   out) a tree at **`b988b8c`** — the last commit before your production edits — seed the same
   fixture there, produce both payloads, and write those numbers into the snapshot. Then record
   **in §8 the commit you captured from**, so the provenance is checkable rather than asserted.
   If the fixture as it now stands cannot be seeded on that tree, **stop and report** — that is
   the real finding and it belongs to the plan, not to you.

**Prove it bites:** temporarily delete the snapshot, run the file, record the failing id and
count, restore it, and put both numbers in your ledger.

### B2 — C8, C10 and C11 have no committed test

Task 0 required every row of C0–C13 transcribed. Your file has **8** tests covering C1, C3, C4,
C5, C6, C7, C9, C12, C13. Write the three that are missing, to the plan's rows as written:

- **C8** — the no-budget branch reconciles (F-D). A task outside `{OK, INFEASIBLE}`;
  production-time still returns a **complete** `typical_resolution` (all six keys),
  `task_typical_basis == "item_narrowed_uniform"`, a complete per-section `typical` block,
  `allowance_seconds: null`, `share_state: "no_budget"`. **`no_budget` currently appears 0× in
  your file.** Note §6A's amended fixture precondition: C8's task uses only the **two
  well-sampled sections**, or the basis is `section_wide_uniform` and the row fails for a reason
  that is not the defect. The mutation is the **one-line** form the fold substituted — guard the
  evidence/reconcile block with the same `status.status in {OK, INFEASIBLE}` condition already
  used for the budget argument.
- **C10** — the 50-task batch (20 chair / 15 table / 10 stool / 5 no-category). All four rows.
  Row (b)'s instrument is the `wraps`-style spy on
  `get_task_budget_allocations.typical_times_statement`, which counts the single call **and**
  captures the `specs=` sequence while delegating, so rows (a) and (b) share one instrument.
  Row (c)'s subject is pinned: **the chair task at fixture position 0**. The three category
  populations must **differ** — that is what makes mutation (ii) move.
- **C11** — production-time and budget-allocations agree. For every participating section of the
  same task at the same frozen `ctx.now`, the triple
  `(typical_worker_seconds, typical_basis, sample_count)` asserted as **exact literals on both
  sides**, never as an equality between two calls.

### B3 — the mutation ledger is short: 16 rows against 21 named mutations

Missing: **C0's two standing regression probes** (`import hashlib` in `typical_filters.py`; the
`Item` model-table import), **C9(ii)**, and **C10(i) and C10(ii)**.

C10's two were declared *"verified by source inspection"*. Master plan §9: **a never-run
mutation is not evidence of anything, including of what it would catch.** C10(ii) has now been
corrected twice — once by the projection (L6), once by the fold — and executed zero times. Run
it in the form the plan carries: map each task to `(spec_index + 1) % K`.

**One ledger row per mutation, not per criterion**, each naming the mutation, the site, and the
**observed** failing test id and count — never the expected one.

### B4 — task 0's red baseline was recorded nowhere

Neither §8 nor the handoff carries the failing ids and count from before the first production
edit. **Reconstruct it honestly or say plainly that it was not captured.** Do not
back-fill a number you did not measure at the time — a fabricated baseline is worse than an
absent one. If it was not captured, write that sentence in §8 and move on; the three new tests
in B2 are the real remedy.

### S1 — compare the baseline by id, not by count

Your stamp reported `2684 passed / 21 failed / 1 skipped` and *"the 21 failures are the
inherited baseline set"*. Master plan §10: the comparator is **the 21-ID set, not the count**.
Diff the ids programmatically against the published set (frontend handoff §7) and report the
delta as **∅/∅** or name the difference.

### S2 — C2's budget-allocations half rests on the golden alone

The exact-literal v2 assertion exists for production-time
(`test_production_time_query.py:206`). C2 requires it *"on production-time's task block **and
on every budget-allocations task entry**"*. Add the budget-allocations assertion.

## Evidence budget

**This session's L4 budget is exactly 1 run** — the closing stamp, taken on the tree you hand
over, with the id diff of S1 computed from it. Everything else runs at L1/L2 against
`tests/integration/services/queries/item_economics/` and `tests/unit/domain/item_economics/`.
Any additional L4 requires the charter's authorization line, written before the run.

## Closing protocol

1. Run every mutation above, both sides, and record **observed** ids.
2. The single L4 stamp, with the programmatic 21-ID diff.
3. Append your round-2 entry to `plans/plan_4.md` §8; set the header and `master_plan.md` §4
   row 4 to **`IMPLEMENTED`** — **both**, they are two records of one state and the next
   session's gate reads the header.
4. Checkpoint commit with **explicit paths** — never `git add -A`, never push.
5. No architecture-graph delta is expected this round; if you record one, declare it.

## Report back

- What you changed, per finding, and what you did **not** change and why.
- **Your full write perimeter** — documents, code, tool-recorded state. It will be diffed.
- The mutation ledger: one row per mutation, observed ids.
- The L4 stamp and the id diff.
- **B1's bite proof:** the failing id and count with the snapshot removed, and the commit you
  re-captured the baseline from.
