# Plan 3 — the carried repairs from phase 2's review

```
plan: 3
state: PROMPT_READY
date: 2026-08-19
gate: projection WAIVED — no new mechanism; every expected value was computed by review r1
      and is quoted below. Justification recorded per charter.
runs in parallel with: plan 4 (the frontend handoff). No shared files — plan 3 touches
      only app/, plan 4 only docs/handoff/.
```

## 1. Goal

Close the seven notes phase 2's review raised and deliberately did not spend a fix cycle on.
**None is a behaviour defect** — review r1 applied 34 mutations and recorded that *no mutation
produced a wrong-but-green payload*. Six of these are missing evidence or tidy-ups; one (F9)
is latency.

The reviewer computed every expected value. This phase writes them down, it does not
rediscover them.

## 2. Files — exactly two

| Path | |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | F3, F6, F9 |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | F2, F4, F5, F8 |

**Nothing else.** Not `price_scenario.py`, not `calculator.py`, not `cases/serializers.py`,
not `serializers.py`, not the router, not any mirror artifact — phases 1 and 2 are APPROVED
and their files are closed. **If a repair appears to need a third file, that is a STOP and a
report, not a judgement call.** (This project has produced three implement blockers, all on
coordinator artifacts, all correct. The presumption is with you.)

## 3. Tasks

### F4 — the one with teeth. Do this first.

`_current_valuation` (`:71-79`) filters `superseded_at IS NULL AND is_deleted = false`. The
code is **correct**; nothing asserts it. Review r1's probe: **deleting
`superseded_at.is_(None)` leaves the entire phase test file green** — no fixture builds a
supersession chain.

Why it matters here specifically: the previous pipeline (`inline_valuation_versioning`) made
re-pricing write a **new chain row** rather than refuse, so supersession chains are a common
live state in this system. Unguarded, a regression reads the byline and the saved price from
an arbitrary historical row — a stale price under the wrong person's name, with no error.

**Fixture:** one item, two valuation rows, the older superseded (`superseded_at` set,
`superseded_by_id` pointing at the newer). **Assert `saved.valuation_id` is the current row**,
and that `saved.expected_sale_price_minor` is the current row's.
**Named mutation (definition site, `_current_valuation`):** drop `superseded_at.is_(None)`
→ this row red.

### F3 — one line

`_has_purchase_term` (`:63-68`) tests every term in the list; `collapse_terms`
(`price_scenario.py:71-72`) skips `is_deleted is True`. **Both consume the same `terms` list
in the same call.** Intention §3.1B and §9A.2 both scope the purchase term to *non-deleted*
rows.

Unreachable today — `_load_preview_inputs` (`_common.py:207-215`) filters
`CostModelTerm.is_deleted.is_(False)` in SQL. The failure it would produce if a future caller
passes unfiltered terms: `can_commit: false` demanding a purchase cost for a term the model
correctly ignores — a disabled button whose press would in fact have succeeded.

**Change:** skip `term.is_deleted is True`, mirroring `collapse_terms`.
**Row:** a deleted purchase term present → `can_commit` is `true` and the model collapses.
**Named mutation:** restore the unfiltered `any(...)` → this row red.

### F5 — the rounding mode is unguarded

C4's fixture (usable typicals `10, 11` → median `10.5`) yields `41` under half-even **and**
under truncation, because `10.5` rounds to the even `10` either way. Review r1 measured it:
truncation reddened **nothing**; half-up and sum-quantisation each reddened C4. So C4 pins
per-section-vs-sum, which is what it was written for, and not half-even-vs-truncation, which
§5.3A also contracts.

**Change:** add usable typicals `{11, 12}` alongside the existing pair — median `11.5`,
half-even `12`, truncation `11`.
**Named mutation (definition site):** `int(resolved)` in place of `round_half_even(...)` →
the new row red, and record that it currently reddens nothing.

### F2 — delete the duplicate

`test_c16_discriminating_literal_is_exact` (`:731`) duplicates the assertion that
`test_price_scenario.py:379-386` owns. It is the direct cause of review r1's F1 — the
implementer's ledger recorded one reddened test where two is the true set.

**Change: delete it.** `test_price_scenario.py` owns the guard. It adds only that the query
module binds `slider_domain` from the right module, which every anchors assertion in the same
file already implies; against that it splits ownership of a guard the plan deliberately placed
in one file, and it carries `@pytest.mark.integration` while opening no session.

**Confirm afterwards** that the `max(1, quantity) → max(6, quantity)` mutation reddens
**exactly one** test again — measured across the **suite**, per master plan §5's widened rule.

### F6 — dead code

```python
if budget_status.item_binding == "detached":
    can_commit = False
```

`detached ⟺ item is None` (`get_task_budget_status.py:111`) and `can_commit` already requires
`item is not None` (`:185`) — the two predicates are the same fact, and removing the block
reddens nothing. **Your call:** keep it with a one-line comment naming it as belt-and-braces
for §9.2A, or remove it. Say which and why in the handoff. Do not leave it looking like a live
guard.

### F8 — decide the marker, then record it

Eight of the file's thirteen functions run through `_run_scenario`, which monkeypatches every
dependency; only `test_c10_…` opens a session. Review r1 measured the consequence: dropping
`TaskStep.workspace_id == ctx.workspace_id` from `_typical_block`, and
`ItemValuation.workspace_id == ctx.workspace_id` from `_current_valuation`, each reddened
**nothing**.

Both predicates are **redundant** by reading: `task_id` and `item_id` are resolved
workspace-scoped upstream by `_load_task_and_item`, and client_ids are prefixed ULIDs. The
endpoint's real tenant boundary is that resolution, and C10 covers it with three rows against
a live database including the cross-workspace row.

**This is a decision, not necessarily a change.** Either (a) add rows that exercise the two
predicates against a real session, or (b) record them in a comment at both sites as redundant
defence-in-depth whose boundary is proven by C10. **State which you chose and why.** Do not
silently leave a reader thinking they are load-bearing.

### F9 — latency, and a judgement you may decline

`get_task_price_scenario` calls `get_task_budget_status(ctx)` — which itself runs
`_load_task_and_item`, and on the no-evaluation branch `_load_preview_inputs` **and** the
current-valuation select — then repeats `_load_task_and_item` at `:153`, the valuation at
`:161` and `_load_preview_inputs` at `:166`. On the **common** branch (a task with no
committed evaluation — the state this screen exists to resolve) that is roughly eight
redundant round trips per open.

Correctness is unaffected, and D-6's reuse of `get_task_budget_status` is exactly what keeps
the status, the binding and the tenant boundary identical to the other screens. **Collapsing
the duplicates must not weaken that.** Either collapse them, or **accept with a recorded
reason** — both are acceptable outcomes; an unrecorded one is not.

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | **F4**: the supersession row asserts `saved.valuation_id` and `saved.expected_sale_price_minor` are the current row's. **Named mutation** at `_current_valuation`'s definition: drop `superseded_at.is_(None)` → red. Record that it reddened nothing before this row existed. |
| C2 | **F3**: a deleted purchase term → `can_commit: true`, model collapses. **Named mutation**: unfiltered `any(...)` → red. |
| C3 | **F5**: the `{11, 12}` median row. **Named mutation**: `int(resolved)` for `round_half_even(...)` → red. |
| C4 | **F2**: `test_c16_discriminating_literal_is_exact` is gone, and the `max(6, quantity)` mutation's observed-red set is **one** test, measured **across the suite**. |
| C5 | **F6** and **F8**: each decided, each recorded in the handoff with its reason. F6's block is either commented or absent. |
| C6 | **F9**: collapsed, or accepted with a recorded reason. If collapsed, the C1/C2/C9/C10 rows of phase 2 still pass unchanged — the status, binding and tenant boundary must be identical. |
| C7 | Suite at or above **2425 / 26 / 1**, minus the one test deleted by F2, plus the rows added. Failure IDs **diffed, not counted**. |

## 5. Standing rules that bite here

- **Every named mutation: compute both sides, run the WHOLE SUITE, record every test that
  reddens** (master plan §5, widened at phase 2's F1 — this is the round that rule was earned
  for). A `-k` run is not an observation.
- **Rule 2's companion** — each new row's fixture makes its own predicate the only reason its
  outcome holds. F4's fixture must have a chain; F5's must have a median the modes disagree on.
- **Rule 11½** — tests that commit own their teardown in `try/finally`, naming their tables.
- **No new mechanism.** If a repair seems to need one, STOP.

## 6. Review log

*(empty)*
