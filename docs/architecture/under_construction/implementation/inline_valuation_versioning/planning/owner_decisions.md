# Owner decisions — inline_valuation_versioning

Verbatim register.

---

## Settled (owner conversation, 2026-08-19)

**D-AUTH — the v1 change is authorized.** Owner asked for the behaviour directly:
*"can we make it so that if the item exist and has a valuation we create a new verison if
different values on purchase price and expected sold price, that version will be credited
to the user creating the task. and only if purchase or expected sold price was passed."*
The coordinator flagged that this changes closed item-cost v1 code and retires a
registered error identity, and the owner proceeded. Scope is the three enumerated files
in intention HC-1 — verified to be the only references to that identity, with none in
`Application_contracts` or the published handoffs.

**D17 — a field omitted from the request inherits its current value (answers card 1).**
Owner: *"recomended is correct"* → branch A, inherit.

Card as relayed: *a chair is already priced — bought for 400, expected to sell for 1200. A
colleague creates a new task for it and passes only the purchase cost, 450, because they
found the real receipt. They say nothing about the sale price.* Branch A keeps 1200 and
records 450, so the chair stays priced and the budget just moves. Branch B (replace, as
the dedicated valuation endpoint does) would leave the chair with no sale price and
silently collapse its budget to `item_missing_expected_price` — a successful task creation
that quietly unprices the item.

Recorded consequence: this deliberately makes the inline path behave **differently** from
`PUT /items/{id}/valuation`, which continues to replace wholesale. The two are different
acts — one is a convenience while creating work, the other is a deliberate re-pricing —
and intention §5 records the divergence as intended, not as drift to be reconciled later.

**D18 — currency counts as a difference (answers card 2).** Owner: *"recommended is
correct also"* → branch A. The comparison is over
`(expected_sale_price_minor, purchase_cost_minor, currency)`. 400 EUR is not 400 SEK;
comparing amounts alone would ignore a genuine currency correction and leave the item
priced in the wrong currency, which the budget's own currency-equality check
(`calculator.py:376-383`) would later reject with a less traceable status.

## Open

None.
