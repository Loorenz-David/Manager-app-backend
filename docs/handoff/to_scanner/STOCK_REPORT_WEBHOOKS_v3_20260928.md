# Handoff to Scanner — Stock Report webhooks (v3)

```
from:       Manager backend (ManagerBeyo-app/backend) — Stock Report
to:         Scanner backend (Item-Scanner-Shopify/apps/backend)
version:    v3 — 2026-09-28
supersedes: STOCK_REPORT_WEBHOOKS_v2_20260919.md (this folder), which stays as handed over.
            This file is a DELTA: v2 remains in force everywhere except the three places
            listed below. Read v2, then apply this.
status:     PUBLISHED. This file is never edited; a later change ships as v4.
receiver:   Manager ships its side FIRST. By the time you deploy, Manager already counts
            every stock-report figure in items (see §3).
```

## What changed since v2

| # | v2 section | v2 said | v3 says | What you do differently |
|---|---|---|---|---|
| 1 | §3.2 rule 2 | **Units, not items.** A set of 8 chairs is 8, never 1. | **Items, not units.** A set of 8 chairs is **1**. | Stop multiplying by the rule's set size (§2 below). |
| 2 | §3.1 field table, `quantityRequested` | **Units** still missing for this rule | **Items** still missing for this rule, in the same count as the thresholds | none beyond row 1 |
| 3 | §7 checklist, line 2 | "… across all locations, in units." | "… across all locations, in items." | none beyond row 1 |

Nothing else moves: the paths, header, body shape, field names, the `properties` object (including
the `quantity` key), identity, responses, the delete webhook and the processed webhook are exactly
as v2 describes. No new field and no version flag. Manager's receiving code does not change;
only the meaning of the number changes.

---

## 1. Why

Scanner measures stock in items. Thresholds, `instanceCount` and `missingItems` all count a
set of 6 chairs as one item. Under v2, Scanner converted that into chairs just before sending
(`missingItems × set size`), while Manager counted a task assignment by the item's own
`quantity`. So the two apps were never guaranteed to be counting in the same currency.

From v3 both sides count **items**:

- **Scanner** sends the missing count it already uses for its thresholds.
- **Manager** counts every task assignment as **1**, whatever the item's set size (Manager's
  side of this change).

The set size is not lost. It stays in `properties.quantity`, so each set size is still its own
Manager row. The Manager board already shows a row's properties, so "2 requested" on a
`quantity: ["6"]` row reads as two sets of six.

---

## 2. The change on Scanner

### 2.1 `src/modules/stock/domain/stock-demand.ts`

`computeStockDemand` sums `missingItems(row)` only:

```ts
// v2
entry.quantityRequested += missingItems(row) * unitsPerItem(row.properties);
// v3
entry.quantityRequested += missingItems(row);
```

`unitsPerItem` and `hasAmbiguousSetSize` then have no caller that needs them. Remove both, and
update the docstrings that cite §12A.2's "set size" multiplication.

### 2.2 `src/modules/outbound-webhook/manager/stock-sync.service.ts`

Remove the loop that warns `"Stock rule states no single set size; counting one unit per item"`
(it calls `hasAmbiguousSetSize`), along with its import. It only guarded the multiplication.

### 2.3 What stays exactly as it is

- `resolveQuantity` (metafield → "set of N" in a chair title → 1) and the copy of that value into
  the item's `properties.quantity`. It still decides which rule an item matches.
- `validateStockCriteria`'s "A stock definition can use only one set size". It is still a sound
  rule for identity, and removing it is not part of this change.
- The ledger (`managerStockLedgerRepository`) and the delta filter need no change. See §3 for
  why the switch-over converges without any special handling.
- The processed webhook (`[{ "article_number": … }]`) and the delete webhook.

### 2.4 `scripts/verify-manager-signals.ts`

Three checks encode the v2 multiplication:

| Check | Today | After v3 |
|---|---|---|
| `1 (M1) worked fixture …` | `quantityRequested: 8` (2 missing sets × `quantity: ["4"]`) | `quantityRequested: 2` |
| `2 (M1) unitsPerItem` | table of `unitsPerItem` cases | remove it, or replace it with: a `quantity: ["4"]` row missing 2 sends `2` |
| `23 (M1) targeted aggregate deltas …` | `quantityRequested: 20` (5 missing sets × 4) | `quantityRequested: 5`. The zero case stays `0`. |

Recompute any other expected `quantityRequested` in that file that sits on a row whose
properties carry `quantity`. The others (`{}`, `wood_group` only) were already multiplied by 1
and do not change.

---

## 3. Switch-over

1. **Manager deploys first.** From then on, Manager counts assignments as 1 each. Until Scanner
   deploys, Manager's rows still hold v2's unit figures, so a set-of-N row looks under-covered.
   That is a temporary display state; nothing is written wrong.
2. **Scanner deploys.** The outbound worker's startup full sync (`enqueueFullStockSyncs("startup")`
   → `runStockSync(…, "full")`) sends every group with its item count, and Manager overwrites
   each row. A delta would also resend every set-of-N group, because the ledger's
   `lastAppliedQuantity` (units) no longer equals the new item count.
3. Rows without a `quantity` key were already sent × 1, so their figures do not move.

Expect Manager to record one `quantity_requested_change` history entry per set-of-N row at
step 2 (for example 12 → 2). That is the correct record of the change.

---

## 4. How to check it after deploy

- In the outbound delivery log, the first `stock_demand` delivery after startup: for a rule with
  `quantity: ["6"]` that is missing 2 sets across all locations, the body entry says
  `"quantityRequested": 2`, and its result says `"outcome": "applied"`.
- Scanner's own stock report (`unitsToRestockTarget`, which is `missingItems`) and the demand sent
  for that rule's group now agree for set-of-N rules too.
- `npm run typecheck` passes, and `scripts/verify-manager-signals.ts` (run the way you ran it
  for v2) passes with the updated checks.

---

## 5. Checklist

- [ ] `computeStockDemand` sums `missingItems(row)` with no multiplier.
- [ ] `unitsPerItem`, `hasAmbiguousSetSize` and the "no single set size" warning are removed.
- [ ] `properties` (including `quantity`) is still sent unchanged.
- [ ] `verify-manager-signals` checks 1, 2 and 23 are updated, and any other `quantity`-bearing
      fixture is recomputed; the script passes.
- [ ] Deployed **after** Manager; the startup full sync is seen delivering item counts.
