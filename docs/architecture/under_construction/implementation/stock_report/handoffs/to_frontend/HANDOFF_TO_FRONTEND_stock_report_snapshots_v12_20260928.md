---
audience: frontend
subject: Stock Report — every quantity counts items; a set is one
date: 2026-09-28
status: CURRENT, as a delta. v11 stays the complete contract; this file changes one meaning in it.
supersedes: nothing. Read v11 (HANDOFF_TO_FRONTEND_stock_report_snapshots_v11_20260928.md), then this.
---

# Stock Report v12 — the unit is the item

## 1. What changed

Every stock-report quantity now counts **items**. A set of 6 chairs is **1**, not 6.

| Where | Before | From v12 |
|---|---|---|
| `quantity_requested` (row, snapshot, both requested sources), `quantity_missing` | the units Scanner sent (a set of 6 missing twice = 12) | items (the same = 2) |
| `quantity_in_queue`, `quantity_in_progress`, `quantity_awaiting`, `quantity_resolved` | the sum of each assignment's `quantity`, which was the item's set size | one per assignment |
| Assignment `quantity` (§6.2) | the item's `quantity`, at least 1 | **1** for every assignment created from now on |
| `progress` (§6.8) | units | items (it sums the fields above) |

No route, field, type, nullability or event changes. Only the meaning of the numbers changes.

## 2. Why

Scanner measures stock in items: its thresholds count a set of 6 as one. It used to multiply by the
set size before telling Manager, while Manager counted an assignment as the item's own `quantity`.
Now both sides count items. The set size is still visible: it is the row's `quantity` property
(`properties.quantity`, e.g. `["6"]`), which the board already renders with the other properties.
So "requested 2" on a row with `quantity: 6` reads as two sets of six.

## 3. What you do

- **Don't multiply anything by the set size.** If the app ever turned a count into units, or units
  into sets, remove that. Show the numbers as they come.
- **Keep reading assignment `quantity`; don't assume 1.** Assignments created before this change
  keep the quantity they were created with. The backend sums the field, and so should you if you
  sum anything.
- Labels that say "units" should say "items" (or nothing).
- `match-preview` is unchanged: its `quantity` input is still the item's set size, matched against
  the row's `quantity` criterion.

## 4. Switch-over you may see

Manager ships first, then Scanner resends every demand. Between the two deploys, set-of-N rows still
show Scanner's old unit figures, so they look under-covered. When Scanner's resend lands, each of those
rows receives a `stock_report_item:updated` with the item figure, plus a `quantity_requested_change`
history record. Rows without a set size don't move.
