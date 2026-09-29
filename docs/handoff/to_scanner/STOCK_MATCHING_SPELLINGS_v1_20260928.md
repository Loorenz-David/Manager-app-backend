# Handoff to Scanner — two item spellings the stock matcher should accept (v1)

```
from:       Manager backend (ManagerBeyo-app/backend) — Stock Report
to:         Scanner backend (Item-Scanner-Shopify/apps/backend)
version:    v1 — 2026-09-28
status:     PUBLISHED. This file is never edited; a later change ships as v2.
read at:    Scanner 8f37b80 (all Scanner paths and quotes below are from that commit)
Manager:    already shipped — 5c53033 (Rosewood → Dark), be98365 (Squared → square)
webhooks:   no change. Paths, bodies and the three webhooks stay exactly as in
            STOCK_REPORT_WEBHOOKS_v3_20260928.md (this folder).
```

## The ask in one paragraph

Manager items are recorded as `wood_type: "Rosewood"` and `shape: "Squared"`. Your
vocabulary says `Santos Rosewood` and `Square`. Manager now accepts both spellings when a
worker assigns an item to a stock-report row. Your matcher (`resolveBestMatch`) does not, so
once one of these items arrives and is scanned, it never counts toward the `Dark` or `square`
rule. The rule's missing count stays where it was, the next `stock-demand` delivery asks for the
item again, and Manager's next version or refresh re-requests something already made. Please
make your matcher accept the same two spellings, with the same semantics as Manager, so both
apps agree about which rule an item belongs to.

---

## 1. Evidence

### 1.1 What Manager stores

A read-only query on Manager's **local development database** (856 items, created 2026-06-24 to
2026-09-26). These are not production figures; §4 step 1 asks you to measure your own data.

| Property | Stored value | Items | Your vocabulary (`item-property-options.ts`) |
|---|---|---|---|
| `wood_type` | `Rosewood` | 47 | not listed |
| `wood_type` | `Rosewood,Walnut` | 2 | not listed (first token is `Rosewood`) |
| `wood_type` | `Santos Rosewood` | **0** | listed, and the only rosewood in `WOOD_GROUPS` |
| `shape` | `Squared` | 7 | not listed |
| `shape` | `Square` | 1 | listed |
| `shape` | `Rectangular` / `Oval` / `Round` / `Other` | 83 / 55 / 27 / 4 | listed, except `Other` |

The stock-report rows Scanner has sent Manager use `shape: ["square"]` (with `oval`, `round`,
`rectangular`). So a `square` rule exists, and the only items that could fill it on the Manager
side were mostly spelled `Squared`.

### 1.2 What Scanner does with those spellings today

- `src/shared/item-properties/wood-groups.ts`, `WOOD_GROUPS.Dark` =
  `["Mahogany", "Santos Rosewood", "Dark Oak", "Dark Teak", "Walnut"]`. The file's comment
  says: "`Santos Rosewood` is the stored spelling — plain `Rosewood` appears nowhere, so it is
  not listed." `woodGroupOfToken("rosewood")` therefore returns `null`, and `deriveItemProperties`
  (`src/modules/stock/domain/best-match.ts`) adds no `wood_group`. The item matches no group
  criterion.
- `src/modules/stock/domain/property-criteria.ts`, `matchesCriteria`, compares the item's
  lowercased tokens to the accepted values exactly. `squared` ≠ `square`, so the item fails a
  `shape: ["square"]` rule. Because `resolveBestMatch` picks the most specific rule that
  matches, the item falls to a broader rule without a `shape` criterion, if there is one, or
  matches nothing.

### 1.3 What Manager does now

`app/beyo_manager/domain/stock_report/scanner_property_tables.py` in Manager:

```python
WOOD_GROUPS = {
    "Dark": ["Mahogany", "Santos Rosewood", "Rosewood", "Dark Oak", "Dark Teak", "Walnut"],
    "Teak": ["Teak", "Cherry"],
    "Light": ["Oak", "Beech", "Pine", "Birch", "Elm"],
}
# Manager-side, not read from Scanner: item spellings that mean a Scanner criterion
# value, per property key. Lower-case tokens on both sides.
ITEM_VALUE_ALIASES = {
    "shape": {"squared": "square"},
}
```

`criteria_matcher.py` translates each item token through `ITEM_VALUE_ALIASES[key]` before
comparing it with the criterion. The wood group is still derived from the first `wood_type`
token only, as in yours.

---

## 2. The change on Scanner

Both changes apply at match time, like the wood groups: no stored value changes, and there is
no migration or backfill.

### 2.1 `src/shared/item-properties/wood-groups.ts`

Add `"Rosewood"` to `Dark`, next to `"Santos Rosewood"`:

```ts
Dark: ["Mahogany", "Santos Rosewood", "Rosewood", "Dark Oak", "Dark Teak", "Walnut"],
```

Replace the comment's "plain `Rosewood` appears nowhere, so it is not listed" with the reason it
is listed now: Manager records rosewood as plain `Rosewood`, and this handoff is the source. The
table's own validation still holds: `rosewood` and `santos rosewood` are different tokens, so
neither appears in two groups.

### 2.2 Item-value aliases (new, next to the wood groups)

Add a table of item spellings, keyed by property and holding lowercase tokens, for example in
`src/shared/item-properties/item-value-aliases.ts`:

```ts
/** Item spellings that mean a criterion value, per property key. Applied to the
 * ITEM side at match time only; criteria and stored properties are untouched.
 * Mirrors Manager's ITEM_VALUE_ALIASES — keep the two tables identical. */
export const ITEM_VALUE_ALIASES: Readonly<Record<string, Readonly<Record<string, string>>>> = {
  shape: { squared: "square" },
};
```

Apply it in `deriveItemProperties` (`best-match.ts`). It is already the one place item
properties are adjusted before `matchesCriteria`, and its comment notes that the scan path and the
reconciliation path cannot disagree because `resolveBestMatch` is its only caller. For each key in
the table that the item has, rewrite the value token by token and join it back with `,`:

```ts
// "Oval/Squared" -> "oval,square"; tokens not in the table pass through unchanged.
orderedPropertyTokens(value).map((token) => aliases[token] ?? token).join(",")
```

Two rules keep this equivalent to Manager:

1. **Aliases are per key.** `squared` under any key other than `shape` stays `squared`.
2. **Aliases apply before the derived keys.** Today no alias touches `wood_type` or
   `drawers_qty`, but if one ever does, `wood_group` and `drawers_range` must be derived from the
   aliased value. Manager can't reach that case yet, so this fixes the order now.

Do **not** add `Rosewood` or `Squared` to `ITEM_PROPERTY_OPTIONS`. Those are the values a stock
definition can be built from. Definitions keep using `Santos Rosewood` and `Square`, and the new
table only makes the item side understand the other spelling.

### 2.3 `scripts/verify-stock-domain.ts`

The `WG.C1(a)` and `WG.C1(b)` checks loop over `WOOD_GROUPS`, so they cover `Rosewood` without
changes. Add these cases:

| Case | Input | Expected |
|---|---|---|
| plain rosewood is Dark | `woodGroupOfToken("Rosewood")` | `"Dark"` |
| first token still decides | `deriveItemProperties({ wood_type: "Rosewood, Walnut" }).wood_group` | `"Dark"` |
| alias matches | `matchesCriteria(deriveItemProperties({ shape: "Squared" }), { shape: ["square"] })` | `true` |
| alias is per key | `matchesCriteria(deriveItemProperties({ finish: "Squared" }), { finish: ["square"] })` | `false` |
| alias does not widen the rule | `matchesCriteria(deriveItemProperties({ shape: "Squared" }), { shape: ["round"] })` | `false` |
| best match moves | `resolveBestMatch([anyShape, square], { location, properties: { shape: "Squared" } })` | the `square` candidate |

The existing reconciliation fixtures (`verify-stock-reconciliation.ts` WG1) use
`Santos Rosewood`, so their figures do not change.

---

## 3. What moves when you deploy

- **Items move between rules, not only into them.** A `Squared` or `Rosewood` item that today
  sits in a broader rule (no `shape` criterion, or a named wood of its second token) may now match
  a narrower `square` or `Dark` rule and move there. One rule's count goes down while another's
  goes up. That is the intended correction.
- **Counts follow on the next reconcile**, exactly as `wood-groups.ts` says for any edit to
  that table. Until a reconcile runs, the old counts stand.
- **Manager records the effect.** The following `stock-demand` delivery carries the corrected
  `quantityRequested` per group, and Manager logs one `quantity_requested_change` history entry
  per group that moved. Manager does not need to deploy anything for this; its side is already
  live.

---

## 4. Steps and checks

1. **Measure first.** Run `SHOP_ID=<shop_id> npx tsx scripts/report-stock-property-drift.ts`
   on the live shop and record how many stored values are `Rosewood`/`rosewood` and
   `Squared`/`squared`.
   - If both are **zero**, the shop already uses your spellings and the mismatch lives only in
     Manager's data. Ship §2 anyway: it costs nothing while the spellings are absent, like `Dark
     Oak` today, and it keeps the two apps identical if they ever arrive. Send the zero result
     back to Manager, because it means Manager's item data, not your matcher, is where the
     spellings diverge.
   - If either is **non-zero**, §2 fixes real miscounts; include the counts in the reply.
2. Apply §2.1 and §2.2, and add the §2.3 cases.
3. `npm run typecheck` passes, and `verify-stock-domain.ts` and `verify-stock-reconciliation.ts`
   pass (run them the way you ran them for v3).
4. After deploy, trigger a reconcile. In the outbound delivery log, the first `stock_demand`
   delivery after it should show the `square` and `Dark` groups' `quantityRequested` lower by the
   Squared/Rosewood items now counted, each with `"outcome": "applied"`.

## 5. Reply to Manager

Send back:

- the drift counts from step 1;
- the Scanner commit that ships §2.

Manager then repoints `SCANNER_SOURCE_COMMIT` in `scanner_property_tables.py` to that commit,
because the table there is pinned as a copy of yours and pinned by a test.

## 6. Checklist

- [ ] Drift report run; counts recorded.
- [ ] `Rosewood` added to `WOOD_GROUPS.Dark`; comment updated.
- [ ] `ITEM_VALUE_ALIASES` added with `shape: { squared: "square" }`, applied in
      `deriveItemProperties`, per key, before the derived keys.
- [ ] `ITEM_PROPERTY_OPTIONS` unchanged.
- [ ] §2.3 cases added; typecheck and verify scripts pass.
- [ ] Reconcile run after deploy; the `stock_demand` delivery checked.
- [ ] Commit and drift counts sent to Manager.
