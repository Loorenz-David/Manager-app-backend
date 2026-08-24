---
plan: plan_4
role: reviewer
round: 2 (delta re-review)
date: 2026-08-24
model: Opus 5
---

# Delta re-review — phase 4, `narrow_typical_work_times`

You reviewed this phase in round 1 and returned `CHANGES_REQUESTED` — 2 blocking / 5 should-fix /
11 notes / 0 cards. Fix round 3 has run. **This is a delta re-review, not a fresh review.**

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine first, by absolute path:**
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

**Do not read `prompts/coordinator/`.**

## Review history — what is settled, and by whom

| established | by | do not re-derive |
|---|---|---|
| The production engineering is sound under every attack named | **you**, round 1 (`748e709`) — the `spec_index is None` fix on all three attacks, `apply_business_fallback` term-for-term, and the leaf-set golden diff showing **0 pre-existing numeric leaves changed** | reality checks 1–16 of your own handoff |
| The 21-ID set is composition-stable in serial | **you**, round 1's L4 — `-n 0` → 21 failed / 2686 passed / 2 skipped, set **∅/∅** | do not repeat the serial comparator |
| **B1 is closed and biting** | **coordinator**, this tree — your own B1 mutation went from **346 passed** (invisible) to **1 failed / 350 passed** on the new `test_c5b_reachable_zero_section_statistic_is_visible_on_both_surfaces` | you may cite this; re-measure only if you doubt it |
| **C8 and C11's mutations bite on THIS tree** | **coordinator**, this tree — C8 → 1 failed / 15 passed, `assert 'section_wide_uniform' == 'item_narrowed_uniform'`; C11 → `(600, 'section_wide', 7)` vs `(600, 'item_narrowed', 7)` plus the collateral `[27] == [7]` | your round-1 citations for these are **stale**: the tests moved from `:198`/`:290` to `:277`/`:351` |

## Gate check — stop and report if any fails

1. `git merge-base --is-ancestor 748e709 HEAD` succeeds (your round-1 tree is an ancestor).
   **Do not pin `HEAD`.**
2. `plans/plan_4.md` header reads **`state: REVIEWING`**, `master_plan.md` §4 row 4 agrees.
3. `plans/plan_4.md` §8 ends with **"2026-08-24 — fix round 3 consumed → delta re-review
   (coordinator)"**.
4. `git status --porcelain -- app/` is **empty**. Anything under `.archgraph/` is the owner's live
   work, expected whatever it contains.

`redis-cli ping` → `PONG` before any suite run.

## Step 1 — the verified perimeter, before anything else

`git diff --name-status 748e709 HEAD -- app/` must return exactly the **8** paths fix round 3
declared:

```
beyo_manager/domain/item_economics/budget_division.py
beyo_manager/domain/item_economics/division_serializers.py
beyo_manager/services/queries/item_economics/get_task_budget_allocations.py
tests/integration/services/queries/item_economics/_narrowing_fixture.py
tests/integration/services/queries/item_economics/test_narrowed_task_economics.py
tests/integration/services/queries/item_economics/test_production_time_query.py
tests/unit/domain/item_economics/test_budget_division.py
tests/unit/domain/item_economics/test_domain_purity.py
```

**An undeclared write is a finding whoever made it.** The coordinator ran four mutation probes on
this tree (`typical_filters.py`, `get_task_production_time.py`, `get_task_budget_allocations.py`)
and reverted each with matching `md5`; if any of those files shows a diff, say so.

## Step 2 — did each round-1 finding close, and does it bite?

**Closure is not the test.** For each, the question is whether the guard now fails under the
defect it names.

| finding | what the fix claims |
|---|---|
| **B1** C5(a)/(b)/(c) | three real-session fixtures: below-floor count **3**; reachable zero `(0, "section_wide", 5)` on both surfaces; `insufficient_sample >= 1` on row (a)'s task. Ledger rows 25–26 |
| **B2** C1(c) + C13(c) | both shipped. **C13(c) verified strong by the coordinator** (`assert files`, `assert hits`, named exceptions, count pin). **C1(c) is the open item — see step 3** |
| **S1** tolerance branch | branch deleted, 23 literals converted to `SelectedTypical`, `step()`'s `typical=None` removed. **Is the `Mapping[str, SelectedTypical]` annotation now load-bearing — i.e. does passing an int fail?** |
| **S2** recursive-walk guard | builds a nested module under `tmp_path` and asserts it is found. Ledger row 23. **Re-run the `glob` revert alone** — that is what caught it last time |
| **S3** C2 production-time | `test_production_time_query.py:206` now asserts on `e3`. Coordinator verified the line |
| **S4** ledger count | **still wrong in the handoff**: it claims C8/C11 are transcribed and its 26-row table contains neither. The coordinator supplied current-tree evidence (above). **Judge whether the record is now adequate** |
| **S5** C1(a)/(b) | exact per-section allowances `3200`/`1600`, both clocks, both surfaces, plus a DB re-read for HC-1A. **Is the non-emptiness guard present?** |
| **N1–N10** | all claimed closed; N3 verified reading the constants |

## Step 3 — the one open finding, and it is the coordinator's

**C1(c)'s second root never existed, and the plan has been amended to strike it.**

L9 narrowed the row to *"`typical_filters.py` and **this phase's evidence-construction helper**"*
without checking such a helper would be written. None was — evidence is built **inline** in
`get_task_production_time` and `get_task_budget_allocations`, both of which **must** contain
`total_working_seconds=live_seconds[...]` because that is the live-clock contract. Round 3 bound
the phrase to `inspect.getsource(selected)`, a **test-local** helper at
`test_narrowed_task_economics.py:53`, making that half an assertion about the test's own source.
Its `assert roots` is `assert [<one literal>]`, not a walk guard.

**Your job on this one:** decide whether striking the void root is the whole fix, or whether the
amended C1(c) still needs a test change — and if the latter, say exactly what it should assert.
Consider whether any *mechanically checkable* absence claim over the two services is available at
all, or whether C1's mutations (i)/(ii) are and were always the only real guard. **If the honest
answer is "the row should never have had a second root", say that** — the coordinator has already
recorded authoring the defect and does not need protecting from it.

## Step 4 — attack what is new, not what you already cleared

Round 3 added ~290 lines. The new surfaces are: two real-session C5 fixtures, two committed
absence tests, the converted `test_budget_division.py`, and the rewritten purity guard.
**Apply your round-1 lenses to these and only these:**

- **A row that cannot fail** — green under the very defect it names. This phase has produced three
  (C9(a)'s self-writing baseline, C5(b)'s pass-through, the `f(x) == f(x)` purity guard) and each
  was written to close the previous one.
- **A row that fails for the wrong reason** — two independent sufficient causes.
- **A guard whose own preconditions are unasserted** — the shape that has now appeared four times.

Particular attention: **the two new C5 fixtures seed real history.** Do their counts (3 and 5)
sit where the criterion needs them relative to `TYPICAL_MIN_SAMPLE_SIZE`, and is the zero-median
fixture actually producing a zero *median* rather than a zero from an empty population?

## Evidence budget

**L4: exactly 1 run** — the closing stamp on the tree you hand over, with the programmatic 21-ID
diff. The implementer's parallel stamp (`2692/21/1`) is on this tree; **your serial comparator from
round 1 is spent and must not be repeated.** If you judge the stamp sufficient by citation and
would rather spend your L4 on variation, name the variation and the question before running it.
Any additional L4 requires the charter's authorization line, written before the run.

## Output

Verdict: **`APPROVED`** or **`CHANGES_REQUESTED`**.

Delta-scoped ledger: one row per finding that is **not** closed, plus any **new** defect in the
~290 changed lines. For findings you confirm closed, a single line each is enough — do not
re-argue them. Then reality checks (new ones only), refutations, and lessons for the plans.

If the verdict is `APPROVED`, state explicitly: **which of your round-1 findings are closed and
biting** (not merely closed), and **what this phase's evidence does NOT cover** — the coordinator
has recorded that the byte-goldens contain only `insufficient_sample` / null typicals by design,
and plan 5 needs to know precisely where the coverage ends.

Handoff at `<project>/handoffs/reviewer/20260824_plan4_rereview_handoff.md`, frontmatter `plan`,
`role`, `round`, `date`, `actor`, `verdict`. Include the tree (`git log --oneline -1`) and a
mutation-probe declaration with before/after checksums for every file you touched.

Final chat message is the charter's **owner layer**: what you did → what it means → what happens
next → what needs the owner. One pointer line naming the handoff.
