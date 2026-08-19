# Plan 1 — inline valuation versioning on task creation

```
plan: 1
state: PROMPT_READY
date: 2026-08-19
```

## Goal

Implement intention §3 (M1) completely: the compare-inherit-version branch in
`create_task`, the retirement of `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`, and the nine
acceptance rows. No migration, no new module, no second valuation writer.

## Read first

1. `../planning/intention.md` — all of it; §3 is the mechanism, §2 the grounding.
2. `../planning/owner_decisions.md` — D-AUTH, **D17** (inherit), **D18** (currency counts).
3. `../master_plan.md` — §4 naming, §5 standing rules, §6 environment and baseline, §7 gates.
4. Code, read before writing:
   - `services/commands/tasks/create_task.py:317-370` — the trigger, the guard being
     replaced, and the `auto_commit` call that follows it
   - `services/commands/item_economics/_common.py:117-169` — the writer; note it stores
     `None` verbatim, which is what D17 exists to prevent
   - `services/commands/item_economics/set_item_valuation.py:71-80` — the wholesale
     replace this path deliberately does **not** copy
   - `services/commands/tasks/requests/__init__.py:39-61` — the request fields and the
     validator that makes `item.currency` mandatory alongside a price
   - `tests/unit/docs/test_item_economics_handoff_accuracy.py:97` and its
     `test_every_literal_identity_is_greppable_in_the_package`

## Tasks

- **T1 — the branch.** Replace `create_task.py:324-342`. When the trigger fires and the
  item was not created by this request: load the current valuation; if none, write as
  today; else build the effective triple per D17 (request value if not `None`, else the
  current value; currency from the request) and compare against the current row's triple
  including currency (D18). Identical → **write nothing at all** (no row, no supersede,
  no audit). Different → call the existing writer with the effective triple and
  `created_by_id = ctx.user_id`.
- **T2 — retire the identity.** Remove the raise and remove the entry at
  `test_item_economics_handoff_accuracy.py:97`. After T2 the string must appear **nowhere**
  in the package.
- **T3 — tests.** The nine rows below, in
  `test_phase8b_inline_task_prices.py`. The existing rejection test is replaced; say in
  the handoff which new row covers each behaviour it used to pin (deleted-assertion rule).

## Acceptance criteria

Exact literals. Fixtures own their teardown (rule 11½).

| # | Criterion |
|---|---|
| C1 | Existing item + current valuation + both prices sent, different → new version; old row `superseded_at` set and `superseded_by_id` = the new id; new row's `created_by_id` is the task creator |
| C2 | Identical values → **no-op**: valuation row count for the item is the same integer before and after, `client_id` unchanged, `superseded_at` still `NULL`. **Named mutation: delete the equality check → red** |
| C3 | Partial request: current 400/1200, send purchase 450 only → new row is 450 / **1200**. **Named mutation: pass the request value through unmerged → red** (stores `None`) |
| C4 | Partial request, effectively identical: current 400/1200, send purchase **400** only → no-op. Neither C2 nor C3 can fail in this shape — that is why it exists |
| C5 | Currency-only change → new version. **Named mutation: compare amounts only → red** |
| C6 | Existing item, no current valuation → first valuation written |
| C7 | Item created by this request + prices → unchanged behaviour |
| C8 | No inline price on an existing priced item → zero valuation rows touched |
| C9 | `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` is absent from the whole package; docs-accuracy suite green |

## Out of scope

`set_item_valuation`'s wholesale-replace semantics (intention §5). `auto_commit`. Any
document edit — verified unnecessary, the identity is published nowhere.

## Review log

(empty — plan authored 2026-08-19)
