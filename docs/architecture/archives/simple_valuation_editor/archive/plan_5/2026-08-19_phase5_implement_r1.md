---
plan: 5
role: implement
round: 1
date: 2026-08-19
project: simple_valuation_editor
kind: implement — two test rows and two comment edits
---

# Session prompt — implement r1, phase 5 (`simple_valuation_editor`)

## 1. What this phase is, in one paragraph

`get_task_price_scenario.py` currently ships two comments that tell a reader, in as many words,
that `ItemValuation.item_id` and `TaskStep.task_id` are **load-bearing but NOT proven**. That
is true and it was the honest thing to write. **This phase makes it false**, then updates the
comments to say so.

Read `plans/plan_5.md` — **§1C only**. §1 and §1B in that file are struck through: they were
set aside by owner decision and moved to
`docs/architecture/under_construction/set_aside/PLAN_item_economics_deferred_coverage_20260819.md`.
**They are not yours. Do not implement them, and do not touch the three files they name.**

## 2. Perimeter — exactly two files

| Path | What changes |
|---|---|
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | two new rows, additive |
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | **comment-only** — two `WHERE` comments, after the rows exist and pass |

**Nothing else.** Not `price_scenario.py`, not `test_price_scenario.py`, not
`test_item_economics_handoff_accuracy.py` (all three are set aside), not the serializers, not
the router, not any handoff.

**This is a declared, narrow reopening of an APPROVED phase.** Phase 3 closed with
**zero executable-line changes in `get_task_price_scenario.py` since `ef55f6d`** across four
rounds. Your comment edits must not break that — verify it, do not assume it. **If a task
appears to need a third file or an executable change, that is a STOP and a report, not a
judgement call.** This project has produced three implement blockers, all on coordinator
artifacts, all correct. The presumption is with you.

**The working tree carries an uncommitted owner change** to
`app/beyo_manager/services/queries/items/lookup/purchase_api.py`, its unit test and
`.archgraph/architecture.yml`, unrelated to this pipeline. **Do not touch, revert, stage,
commit or count it.** It is why the suite reads 2431 rather than 2428.

## 3. The two gaps, and why nothing catches them today

Both were measured at re-review r4, one mutation at a time, across the whole non-e2e suite,
ID-diffed. **Both returned 0 added, 0 removed.** The `item_id` result was reproduced by the
coordinator with a repeat run.

### Row 1 — `ItemValuation.item_id == item_id`

**Why nothing catches it:** every fixture in the suite holds one item per workspace, so there
is never a second item's valuation to be returned instead.

**What a regression does:** `_current_valuation` returns *whichever* current, non-deleted
valuation the scan reaches first **in the workspace** — another item's price under another
colleague's byline, on this item's screen. That is a **wider** blast radius than either
predicate that *is* proven: `superseded_at` and `is_deleted` return the wrong row for the right
item; this one returns a row for the wrong item.

**Fixture:** one workspace, **two items**, each with its own current valuation (distinct
prices, and ideally distinct `created_by` users so the byline discriminates too).
**Assert** `saved.valuation_id` and `saved.expected_sale_price_minor` are **the requested
item's**.
**Named mutation (definition site, `_current_valuation`):** drop
`ItemValuation.item_id == item_id` → this row red.

⚠ **The trap phase 3 hit on its first attempt, so you do not hit it again.** With the predicate
dropped, which row PostgreSQL returns is **heap order**, not a guarantee. Phase 3's C1 row
reached for planner GUCs (`SET LOCAL enable_indexscan = off`) that were later measured to do
**nothing** — the determinism came entirely from the order of two UPDATEs. Read
`test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain`'s comment before writing
this fixture; it explains the mechanism that actually works. **If your first fixture form does
not discriminate, say so in the handoff** — phase 3 did, and that candour is what let the
measurement be trusted.

### Row 2 — `TaskStep.task_id == task_id`

**Why nothing catches it:** all eight `_typical_block` tests use `_TypicalSession`, whose
`async def execute(self, _statement)` **discards the statement** and pops pre-built results. The
`WHERE` is never evaluated. `test_c5_deleted_steps_do_not_create_a_participating_section` reads
exactly like coverage of this query and proves a **Python** filter in
`group_steps_by_section` instead.

**What a regression does:** sums **every task's steps in the workspace** into one task's typical
time — a wrong break-even, a wrong slider domain and a wrong suggested price, with no error.

**Fixture:** a real session. One workspace, **two tasks**, each with its own `TaskStep` rows on
distinct working sections. Call `_typical_block(ctx, task_a)` and **assert the result reflects
only task A's sections** — `sections_total` is the discriminating field, and `total_seconds`
with it.
**This row cannot use `_TypicalSession`.** That fake is the entire reason the gap exists; using
it would reproduce the gap rather than close it.
**Named mutation (definition site, `_typical_block`):** drop `TaskStep.task_id == task_id` →
this row red.

Note `_typical_block` issues a **second** query — `typical_times_statement(...)` against
`WorkingSection` — so your fixture needs whatever rows that statement reads, or the sections
resolve to no sample. **Either is fine for discrimination** as long as the two tasks differ in
`sections_total`; say which you did and why.

## 4. Then, and only then, the comments

After both rows exist and pass, update the two `WHERE` comments so they stop saying "NOT
proven". Name the new tests the way the existing lines name theirs
(`test_price_scenario_query.py:test_name` — the house convention, and **never a bare line
number**, which is the form re-review r4 struck out of these very comments).

`TaskStep.is_deleted.is_(False)` **stays described as defence-in-depth** — it duplicates
`group_steps_by_section`'s Python filter and genuinely cannot change a result. Do not "fix" it
by adding a test or deleting the predicate. Re-review r4's N-3 recorded exactly this so a later
round would not.

**Comment-only.** After editing, run:

```
git diff -U0 ef55f6d -- app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py \
  | grep '^[+-]' | grep -v '^[+-][+-]' | grep -v '^[+-] *#'
```

**It must be empty.** Put that in the handoff.

## 5. Acceptance criteria

Plan 5 §4, C1–C8. In particular:

- **C2/C3**: both named mutations, **one at a time**, at the definition site, measured across
  the **whole non-e2e suite** (never `-k`), reverted, SHA-256 checked byte-identical. Both
  before-states are **0 added / 0 removed** — record that, since it is what the criterion is
  against.
- **C4**: each row's own predicate is the only reason its outcome holds. A fixture whose
  expected value is the same under the defect proves nothing **even when the assertion beside it
  bites** — this project has recorded that four times.
- **C5**: rule 11½ — teardown in `try/finally` naming its tables, residue assertions outside it.
  Copy `test_phase3_c1_…` / `test_phase3_g2_…`, whose shape two review rounds confirmed correct
  on the failure path.
- **C8**: suite **26 / 2433 / 1**.

## 6. The suite has at least two flaky tests

Master plan §6 carries 21 observations and two named IDs. **If your count disagrees, repeat and
ID-diff before concluding.** At re-review r4 a coordinator run read 27 on an unrelated shopify
flake; the immediate repeat came back 26 with the baseline byte-identical. A single 27 would
have been read as the mutation biting, and the finding would have been wrong.

If either named ID appears in your runs, **report it as another observation and move on.** Both
are outside this perimeter.

## 7. Closing protocol

Deposit at `handoffs/implementer/2026-08-19_phase5_implement_r1_handoff.md`, charter
frontmatter.

Include: the criterion → test map; the mutation ledger with both sides computed, the **complete**
observed-red set measured across the suite, and revert hashes; the empty-non-comment-diff proof
from §4; and the full write perimeter from the closing
`git status --porcelain --untracked-files=all`, listing the owner's three concurrent paths
separately as not-yours.

Owner cards story-shaped and ≤120 words if any arise; none is expected.

Do not update the master plan tracker or plan 5's Review log. Do not commit.

## 8. Environment

- Working directory `backend/app/`; `PYTHONPATH=. pytest -m 'not e2e'` (the bare `make test`
  form fails collection with `ModuleNotFoundError: beyo_manager` under some shells).
- Start baseline **26 / 2431 / 1**, head `b01d2eb`.
- Focused file: `pytest tests/integration/services/queries/item_economics/test_price_scenario_query.py`
  — 50 tests, under a second.
- **Architecture graph**: 11 pending `ai_inferred` items with drifted anchors, coordinator-owned.
  **Report drift, repair nothing.** Maintenance refuses pending items and `repair_anchors`
  returns `INTERNAL_ERROR` on them; the review path is the only door and it is not yours.
