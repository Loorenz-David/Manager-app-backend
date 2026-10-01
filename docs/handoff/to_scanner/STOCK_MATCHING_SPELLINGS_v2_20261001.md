# Handoff to Scanner — read the purchase app's `material_type` as `wood_type` (v2)

```
from:       Manager backend (ManagerBeyo-app/backend) — Stock Report
to:         Scanner backend (Item-Scanner-Shopify/apps/backend)
version:    v2 — 2026-10-01
supersedes: nothing. STOCK_MATCHING_SPELLINGS_v1_20260928.md (this folder) stays in force; this
            file adds one more item spelling for the two apps to agree on.
status:     PUBLISHED. This file is never edited; a later change ships as v3.
read at:    Scanner 8f37b80 (all Scanner paths and quotes below are from that commit)
Manager:    already shipped — 9df4303e (matcher reads `material_type` when `wood_type` is absent)
webhooks:   no change. Paths, bodies and the three webhooks stay exactly as in
            STOCK_REPORT_WEBHOOKS_v3_20260928.md (this folder).
```

## The ask in one paragraph

For some categories, the purchase app sends an item's wood as **`material_type`**, not
`wood_type`. Article **0001728**, a teak cabinet, comes back as
`{"parts": "2", "door_type": "Opening doors", "material_type": "Teak"}`. Both apps derive
`wood_group` only from `wood_type`, so this cabinet matched neither a `wood_group: teak` rule nor
a `wood_type: teak` rule. Manager now treats `material_type` as the item's `wood_type` when the
item has no `wood_type` of its own. Please make Scanner do the same **when it takes the
attributes from the purchase app**, so both apps agree about which rule the item belongs to.
Otherwise Manager lets a worker assign the cabinet to the teak row, Scanner never counts it once
it is scanned, and the next `stock-demand` delivery asks for it again.

---

## 1. Evidence

### 1.1 What the purchase app sends

Manager's article lookup (`GET` item lookup → `external_source: "purchase_api"`) returned this
item for article 0001728:

```json
{ "article_number": "0001728", "quantity": 1,
  "properties": { "parts": "2", "door_type": "Opening doors", "material_type": "Teak" } }
```

Manager's match preview against a `wood_group: ["teak"]` row then reported
`{"key": "wood_group", "reason": "missing_on_item", "item_values": []}`.

We don't know which other categories use `material_type`, or how many items carry it. §4 step 1
asks you to measure that on your own data.

### 1.2 What Scanner does with it today

- `src/shared/item-properties/purchase-api.integration.ts` decodes `{ key, label, value }` entries
  keyed by `key`, so `material_type` arrives unchanged.
- `src/shared/item-properties/item-properties-resolver.service.ts` → `resolve()` drops
  `EXCLUDED_PURCHASE_ATTRIBUTE_KEYS` (`material_type` is not one), then stores
  `{ ...keptAttributes, ...input.metafieldProperties }`. Shopify wins collisions.
- `src/modules/stock/domain/best-match.ts` → `deriveWoodGroup` reads only
  `properties[WOOD_TYPE_KEY]`.

So unless the item's Shopify product has a `wood_type` metafield, the stored item has only
`material_type`, derives no `wood_group`, and matches no wood criterion.

### 1.3 What Manager does now (9df4303e)

`ITEM_KEY_ALIASES = {"wood_type": ("material_type",)}` in
`app/beyo_manager/domain/stock_report/scanner_property_tables.py`. When the item's property bag
is built for matching:

1. If the item already has `wood_type`, nothing changes. **`wood_type` always wins.**
2. Otherwise, if it has `material_type`, `wood_type` takes that value **unchanged** (the whole
   string, so `"Teak, Metal"` stays `"Teak, Metal"` and its first token decides the group, as
   for any `wood_type`).
3. `material_type` itself is kept.
4. A value that is no wood (`"Metal"`) derives no group. It then matches no wood criterion,
   which is the same outcome as any unknown wood today.

---

## 2. The change on Scanner

### 2.1 Where: when the purchase attributes are merged

Apply the alias in `item-properties-resolver.service.ts`, inside `resolve()`, to the purchase
attributes **after `dropExcludedAttributes` and before the Shopify merge**. That is the module
that owns the purchase-attribute policy ("Applied at merge time rather than at parse time, so the
integration stays a faithful decode of the API and this module owns the policy").

A sketch, in that module's style:

```ts
/**
 * Purchase-API attribute keys that stand in for a matcher key the item does not
 * carry itself, in order of preference. The purchase app sends some categories'
 * wood as `material_type`. Mirrors Manager's ITEM_KEY_ALIASES (9df4303e).
 */
const PURCHASE_ATTRIBUTE_KEY_ALIASES: ReadonlyArray<readonly [string, readonly string[]]> = [
  [WOOD_TYPE_KEY, ["material_type"]],
];

const aliasAttributeKeys = (attributes: ItemProperties): ItemProperties => {
  const aliased: ItemProperties = { ...attributes };
  for (const [key, aliases] of PURCHASE_ATTRIBUTE_KEY_ALIASES) {
    if (key in aliased) {
      continue;
    }
    const alias = aliases.find((candidate) => candidate in aliased);
    if (alias !== undefined) {
      aliased[key] = aliased[alias] as string;
    }
  }
  return aliased;
};

// in resolve():
const keptAttributes = aliasAttributeKeys(dropExcludedAttributes(attributes));
```

What this gives you:

| Purchase attributes | Shopify metafields | Stored after merge |
|---|---|---|
| `material_type: Teak` | no `wood_type` | `wood_type: Teak`, `material_type: Teak` |
| `material_type: Teak` | `wood_type: Oak` | `wood_type: Oak` (Shopify wins, as today), `material_type: Teak` |
| `wood_type: Walnut`, `material_type: Teak` | — | `wood_type: Walnut` (the purchase app's own `wood_type` wins) |
| `material_type: Metal` | — | `wood_type: Metal`, `material_type: Metal`. No group derives, so no wood rule matches, as before. |

The order of precedence is Shopify `wood_type` > purchase `wood_type` > purchase
`material_type`. Manager has no Shopify half, so for Manager it reduces to `wood_type` >
`material_type`, which is the same rule.

### 2.2 What stays as it is

- `deriveItemProperties` / `deriveWoodGroup` in `best-match.ts`: unchanged. They now find
  `wood_type` on the stored item.
- `EXCLUDED_PURCHASE_ATTRIBUTE_KEYS`: unchanged. `material_type` is **not** dropped, because
  Manager keeps it too.
- A Shopify metafield named `material_type`, if one ever exists, is **not** aliased. This change
  covers what Scanner obtains from the purchase app only.
- The stock-rule vocabulary (`item-property-options.ts`) and `WOOD_GROUPS`: unchanged.

### 2.3 Visible side effect

The item now shows a `wood_type` property in Scanner's own UI wherever properties are listed,
next to `material_type`. That is intended: it is the value the matcher uses.

---

## 3. What moves when you deploy

- **New and re-synced items:** every path that writes properties goes through
  `itemPropertiesResolver.resolve` (scans, order snapshots, products/update webhooks), so they pick
  up `wood_type` the next time they are touched.
- **Items already stored:** they converge only when touched. Run
  `scripts/backfill-item-properties.ts`, which resolves through the same `resolve()`, to rewrite
  them all at once. Then recompute location stock with the same reconcile or rebuild you used for
  spellings v1, so the newly matching items count toward their wood rules.
- **Demand:** the wood rules' `quantityRequested` goes **down** by the `material_type` items now
  counted. Manager receives that as ordinary demand on the existing webhook; Manager needs no action.

---

## 4. Steps and checks

1. **Measure first.** Count stored `ScanHistory` rows whose `properties` contain `material_type`
   and **no** `wood_type`, grouped by `itemCategory` and by `material_type` value. The query in
   `report-stock-property-drift.ts` is a good starting point. Also count, after the backfill
   dry run, how many of those values derive a wood group (`woodGroupOfToken` of the first token).
   - If the first count is **zero**, the shop's Shopify metafields already supply `wood_type` for
     these items. Ship §2 anyway (it costs nothing when the key is absent) and send the zero back.
   - If it is **non-zero**, §2 fixes real miscounts. Include the counts in the reply.
2. Apply §2.1.
3. `npm run typecheck` passes. Add a resolver case to your verify scripts (the way you ran them
   for spellings v1) for each row of the §2.1 table, plus one end-to-end case: an item stored with
   only purchase `material_type: Teak` matches a `wood_group: ["teak"]` rule in `resolveBestMatch`.
4. Run `DRY_RUN=true npx tsx scripts/backfill-item-properties.ts`, check that the rows it would
   change are the ones from step 1, then run it for real and reconcile.
5. After deploy, in the outbound delivery log, the first `stock_demand` delivery after the
   reconcile shows the affected wood groups' `quantityRequested` lower by the items now counted,
   each with `"outcome": "applied"`.

## 5. Reply to Manager

Send back:

- the step 1 counts: rows with `material_type` and no `wood_type`, by category and value;
- any `material_type` value that is **not** a wood (for example metal, glass, marble), so Manager
  knows whether the alias ever fills `wood_type` with a non-wood;
- the Scanner commit that ships §2.1.

## 6. Checklist

- [ ] Step 1 counts measured and recorded.
- [ ] `material_type` fills `wood_type` in `resolve()`, only when `wood_type` is absent from the
      purchase attributes; Shopify's `wood_type` still wins the merge.
- [ ] `material_type` is still stored; `EXCLUDED_PURCHASE_ATTRIBUTE_KEYS` unchanged.
- [ ] Verify cases for the four rows of the §2.1 table and the `resolveBestMatch` case pass.
- [ ] Backfill run (dry, then real), location stock reconciled.
- [ ] Reply sent to Manager (§5).
