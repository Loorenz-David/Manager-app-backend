---
plan: 5
role: implement
round: 1
state: IMPLEMENTED
date: 2026-08-19
actor: Claude Opus 5 (implement r1)
project: simple_valuation_editor
---

# Handoff — implement r1, phase 5 (`simple_valuation_editor`)

## Summary

Plan 5 §1C is done. The two predicates whose shipped comments called them **NOT proven** —
`ItemValuation.item_id == item_id` and `TaskStep.task_id == task_id` — now each have one row,
both against a real session, and both named mutations were measured whole-suite, one at a
time, at the definition site: **each reddens exactly its own row and nothing else**, up from
0 added / 0 removed at re-review r4. The two `WHERE` comments were then updated to say so.

Suite **26 / 2433 / 1**, failure-ID set byte-identical to the start baseline. Perimeter is
exactly the two files plan 5 §2 allows. **No executable line of
`get_task_price_scenario.py` changed** — the §4 proof is empty, so phase 3's
zero-executable-lines-since-`ef55f6d` record still holds across five rounds.

No STOP was entered. No third file was touched.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this phase needs the owner.

## Criterion → test map

| C | Criterion | Where it is met |
|---|---|---|
| C1 | Both rows real-session; typical row does not use `_TypicalSession` | Both take the `db_session` fixture. `test_phase5_c3_…` calls `module._typical_block` with a real `ServiceContext`, so both of that function's statements are issued as SQL — the first real-SQL exercise `_typical_block` has ever had |
| C2 | Named mutation, definition site, whole-suite, both sides computed | Ledger row 1 below |
| C3 | Named mutation, separately and one at a time | Ledger row 2 below |
| C4 | Each row's own predicate is the only reason its outcome holds | Discrimination argument below, one per row |
| C5 | Rule 11½ teardown in `try/finally`, residue assertions outside | Both rows copy `test_phase3_c1_…` / `test_phase3_g2_…`: `finally` opens with `rollback()`, then `DELETE`s each table it wrote by name, then `commit()`; the residue `SELECT count(*)` assertions sit after the block, so they run on the failure path too |
| C6 | Both `WHERE` comments updated to name the new rows as proof | `get_task_price_scenario.py` `_current_valuation` and `_typical_block`; comment-only, proof below |
| C7 | `ruff check` and `ruff format --check` clean on both files | `All checks passed!` / `2 files already formatted` |
| C8 | Suite 26 / 2433 / 1, IDs diffed not counted | Below |

## Mutation ledger

Both mutations applied at the **definition site**, one at a time, each measured across the
**whole non-e2e suite** (`PYTHONPATH=. pytest -m 'not e2e'`, never `-k`), each reverted by
restoring a byte copy taken before the first mutation.

Pre-mutation file hash: `4b9745478eb87c9e41fc9d72c5f26c861ce8017054708dd3f165df4e6f22c187`
Post-revert hash after mutation 1: **identical**
Post-revert hash after mutation 2: **identical**

| # | Mutation | Site | Before (r4) | After | Observed-red set, complete |
|---|---|---|---|---|---|
| 1 | drop `ItemValuation.item_id == item_id` | `get_task_price_scenario.py:_current_valuation` | 0 added / 0 removed | **27 / 2432 / 1 — 1 added, 0 removed** | `test_price_scenario_query.py::test_phase5_c2_saved_uses_the_requested_items_own_valuation` — and nothing else |
| 2 | drop `TaskStep.task_id == task_id` | `get_task_price_scenario.py:_typical_block` | 0 added / 0 removed | **27 / 2432 / 1 — 1 added, 0 removed** | `test_price_scenario_query.py::test_phase5_c3_typical_counts_only_the_requested_tasks_steps` — and nothing else |

Both sides of each mutation are computed, not asserted: the before-state is r4's measured
0/0 (the `item_id` one reproduced by the coordinator with a repeat), the after-state is the
run above. Each mutant run moved the count by exactly +1 **with exactly one added ID**, so
neither reading is the ±1 flake — a bare count change would not have been evidence, per
master plan §6.

Neither mutation reddened the *other* row, which is the second thing the ledger shows:
the two rows are independent, not one fixture answering for both.

## Discrimination — C4, one argument per row

**`test_phase5_c2_saved_uses_the_requested_items_own_valuation`.** One workspace, two items,
each with its own **current** valuation — legal because `uix_item_valuations_current` is
unique per `item_id`, not per workspace. So the two predicates that *are* proven cannot
stand in for the one under test: both rows satisfy `superseded_at IS NULL` and
`is_deleted = false`, and both satisfy `workspace_id`. `item_id` is the only predicate that
separates them.

The trap phase 3 hit is handled the way phase 3 eventually handled it — by insert order, not
by planner GUCs. The neighbour's valuation is inserted first and **neither row is ever
updated**, so the neighbour's tuple sits earlier in the heap and the mutant's `scalar()`
takes it. This is written down in the fixture comment, including that heap order is not a
guarantee and is the thing to look at if the row ever stops discriminating. The assertions
themselves do not rest on it: unmutated, `item_id` is unique among current rows.

Three assertions, because the neighbour's row would show itself three ways on this item's
screen: the valuation ID, the price (855 000 vs 1 000 000), and the **byline** — a second
user authors the neighbour's valuation, and `get_task_price_scenario` looks the author up
from whichever row came back, so the wrong row brings the wrong colleague's name with it.

**`test_phase5_c3_typical_counts_only_the_requested_tasks_steps`.** One workspace, two tasks,
each working a **different** section. The requested task's section has a typical of 300 s,
the other task's 900 s.

I took the **richer** of the two fixture forms the prompt allowed. Five history tasks give
each section exactly `TYPICAL_MIN_SAMPLE_SIZE` completed groups, so
`typical_times_statement` returns a real median for both sections instead of a null sample.
The reason: with no sample, both sections resolve to the zero fallback and `total_seconds`
is **0 under the contract and 0 under the mutant** — only `sections_total` would
discriminate, and `total_seconds` is the member that actually reaches
`break_even_price_minor`, the slider domain and the suggested price. With the samples in
place both fields bite:

| | `sections_total` | `total_seconds` |
|---|---|---|
| contract | 1 | 300 |
| mutant (no `task_id`) | 2 | 1200 |

The mutant reads every step in the workspace, so the other task's section and all ten
history steps join the participating set — which is exactly the described regression
(*"sums every task's steps in the workspace into one task's typical time"*) reproduced,
not merely named.

## Comment-only proof (prompt §4)

```
git diff -U0 ef55f6d -- app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py \
  | grep '^[+-]' | grep -v '^[+-][+-]' | grep -v '^[+-] *#'
```

**Empty.** Run again against `HEAD` (this session's own delta) — also **empty**. The file's
diff is `+20 / −13`, all of it comment. Phase 3's record stands: zero executable-line changes
in this file since `ef55f6d`, now across five rounds.

`TaskStep.is_deleted.is_(False)` is still described as defence-in-depth and still has no test,
per prompt §4 and re-review r4's N-3. Its comment now says dropping it reddened nothing **and
that this is the correct outcome for that one, not a gap** — the old wording lumped it in with
the two real gaps.

One wording judgement, recorded because it is a claim: I first wrote *"no test of it is
possible"* for `is_deleted` and softened it to the measured statement. r4 measured that
dropping it reddens nothing and reasoned that it cannot change a result; it did not establish
that no test could exist. A comment asserting a property inherits rule 2, and I was not going
to ship a fresh absolute in the same edit that removes two stale ones.

## Test counts

| Run | Result |
|---|---|
| Start baseline, clean tree, before any edit | **26 / 2431 / 1** — matches the prompt exactly, 26 IDs captured |
| Focused file | 52 passed in 0.73 s (was 50, +2) |
| After both rows, before the comment edits | **26 / 2433 / 1** — 0 added, 0 removed vs baseline |
| **Final, comments included** | **26 / 2433 / 1** — ID set byte-identical to *both* prior clean runs |

No run in this session read anything but 26. Neither named flaky ID appeared as an addition
in any of the five full runs.

## Write perimeter

From the closing `git status --porcelain --untracked-files=all`:

**Mine — exactly plan 5 §2's two files:**

| Path | Change |
|---|---|
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | `+338 / −0` — purely additive: two test rows and one `WorkingSection` import |
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | `+20 / −13` — comment-only, proven above |

Plus this document, untracked, the session's only other write:
`docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/implementer/2026-08-19_phase5_implement_r1_handoff.md`.
It sits under a guarded root, so per the master plan's standing rule the guard was run after
writing it rather than assumed: `pytest tests/unit/docs/` — **59 passed**. No archgraph write
was made, so there is no tool-recorded state in this perimeter.

**Not mine — the owner's three concurrent paths, untouched, uncounted, unstaged:**
`.archgraph/architecture.yml`, `app/beyo_manager/services/queries/items/lookup/purchase_api.py`,
`app/tests/unit/services/queries/items/test_lookup_item_by_article_number.py`. All three were
already modified when this session opened. They are why the suite reads 2431 rather than 2428.

**Mutation-probe files (applied and reverted):** `get_task_price_scenario.py` only, twice,
hash-verified identical after each. No probe touched any other file.

**Not done, per prompt §7:** master plan tracker, plan 5 Review log, and the commit are all
the coordinator's. Nothing was committed.

## Architecture graph — drift reported, nothing repaired

No delta was recorded: this phase adds no boundary, adapter or orchestration. Two test rows
and two comments are not architectural granularity.

**Drift to report.** Node `projection-item-economics-task-price-scenario` (pending
`ai_inferred`) carries two evidence entries and two `sourceLinks`, both anchored by line span
into files in this perimeter. **Both were already drifted before this session** — which is
consistent with the prompt's eleven pending items — and this session's additive change widens
them:

| Anchor | Graph says | At `HEAD`, before me | Now |
|---|---|---|---|
| `get_task_price_scenario.py:get_task_price_scenario` | 149–273 | **174–304** (already off by 25) | 181–311 |
| `test_price_scenario_query.py:test_c1_status_matrix_has_twelve_exact_rows` | 387–419 | **434** (already off by 47) | 601 |

Both `sourceLinks` also carry a `contentHash` over the drifted span, so the staleness signal
for this node is pointed at the wrong lines in both files. Per prompt §8 I repaired nothing:
maintenance refuses pending items and `repair_anchors` returns `INTERNAL_ERROR` on them, and
the review path is the coordinator's. Recorded here so it is not rediscovered.

## For the coordinator

1. The two comments are the deliverable as much as the tests are; they are worth a read on
   their own terms, since reviewer/implementer prose has entered this tree unread twice.
2. The `is_deleted` softening above is the one judgement call in the session.
3. The graph drift table is a report, not a request.
