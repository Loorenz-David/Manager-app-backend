# Source evidence — Scanner (Item-Scanner-Shopify) as the upstream of Stock Report

```
role: source evidence doc (beside the intention; values here are source-contract facts)
verified: 2026-09-18, by reading the Scanner repository on disk
repo: /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify  (apps/backend)
scope: what Scanner holds and how it already talks to Manager. The Scanner-side SENDER of the
       two webhooks in the intention does not exist yet — nothing here describes it.
```

## E1 — Scanner's stock rule is per LOCATION

`prisma/schema.prisma:419-439`, model `LocationStock`:

| Field | Meaning |
|---|---|
| `shopId` | Scanner's tenant (Scanner is multi-shop) |
| `location` | the stock location/zone the rule belongs to |
| `itemCategory` | `String` — a category **name**, not an id |
| `properties` | `Json` — the rule's criteria |
| `propertiesCanonical` | `String` — canonical JSON of the criteria |
| `quantity` | **units** currently counted by the rule |
| `instanceCount` | **items** (listings) currently counted by the rule |
| `stockState` | `out_of_stock / low_in_stock / medium_in_stock / high_in_stock` |

Identity: `@@unique([shopId, location, itemCategory, propertiesCanonical])`.
**The same (category, properties) pair can exist once per location.** Thresholds live in
`StockThresholdsLocation` (`:441-456`), one row per (rule, state).

Consequence for Manager: an identity of (category, properties) alone is coarser than Scanner's.

## E2 — Units and items are different numbers in Scanner

`LC-STOCK-REPORT.md` (Scanner repo root, generated from the live database 2026-09-08):
"Rule — Set size: 8 · Upholstery: Up & Down · Wood group: Teak · counts **8 units across 1 item**".
A set of chairs is one item (one article number) carrying `quantity` 8.
Manager mirrors this: `Item.quantity` (`models/tables/items/item.py:34`, Integer, default 1).

## E3 — Rule properties are CRITERIA, not an item's property snapshot

`src/modules/stock/domain/property-criteria.ts`:
- shape `Record<string, string[] | null>` — every value is a list of strings, or null;
- `normalizeCriteria` sorts keys, trims + lowercases values, dedupes and **sorts** each list;
- `canonicalCriteriaString` = `JSON.stringify` of that key-sorted object.

Criteria include **derived groups** that no item carries verbatim: the live report shows rules on
"Wood group: Dark / Light / Teak" while the items carry "Wood type: Walnut / Oak / Beech".

Consequences for Manager:
- a rule's `properties` can never be compared for equality with `Item.properties`; only the
  category is comparable between a requirement and an item;
- Scanner already sends lists in sorted order, so Manager's list-order-significant signature
  (`domain/items/properties_signature.py`) is stable for Scanner-originated payloads.

## E4 — How Scanner already authenticates to a receiver

`src/workers/outbound-webhook-worker.ts:45-47`: outbound webhooks send the per-target secret in
the header **`x-api-key`**. Targets are rows of `OutboundWebhookTarget`
(`schema.prisma:268-283`: `targetUrl`, `secret`, `eventType`, `active`), and the only event type
today is `item_placed` (`schema.prisma:63-65`).

## E5 — How Manager already talks to Scanner (the opposite direction)

Manager → Scanner uses `Authorization: Bearer <LOCATION_TRACKER_API_KEY>`
(`app/beyo_manager/services/infra/location_tracker/constants.py`, `client.py`), against Scanner's
`/api/manager-app` router (`apps/backend/src/server.ts:149`). Items are addressed by
`article_number` or `sku` (`modules/external-api/contracts/external-api.contract.ts`).
That key is outbound-only; it is not the inbound key the intention introduces.

## E6 — Not every Scanner item has an article number

`LC-STOCK-REPORT.md`: 3 of 116 live LC items have no barcode (article number) on file. Such an
item cannot be named by an `article_number`-only webhook.

## E7 — How Scanner decides that an item satisfies a rule

`src/modules/stock/domain/property-criteria.ts` `matchesCriteria`, fed by
`deriveItemProperties` (`src/modules/stock/domain/best-match.ts:99-117`):

- Item properties are a flat bag `Record<string, string>`; a rule's criteria are
  `Record<string, string[] | null>`.
- Empty criteria match every item. An item with no properties matches only empty criteria.
- **Every** criteria key must be satisfied. For a key: the item must carry that key with a
  non-empty string value; the value is tokenized; the key is satisfied when the accepted list is
  `null` (wildcard — "has any value") or **any** accepted value is among the item's tokens.
- Tokenizer (`orderedPropertyTokens`): split on `,` and `/` only — **never on `&`**
  (`"Up & Down"` is one value) — trim, drop empties, lowercase.
  `"Teak, Beech"` → `["teak", "beech"]`.

## E8 — The derived keys: exactly two

No item stores these; the matcher computes them before matching. Both are excluded from the
stored bag on both ingestion paths (`item-properties.ts`, `shopify-metafield-properties.ts:62-72`).

| Derived key | From | Rule | Source |
|---|---|---|---|
| `wood_group` | the **first** token of `wood_type` only | `Dark`: Mahogany, Santos Rosewood, Dark Oak, Dark Teak, Walnut · `Teak`: Teak, Cherry · `Light`: Oak, Beech, Pine, Birch, Elm · any other wood → no group, matches no `wood_group` criterion (wildcard included) | `shared/item-properties/wood-groups.ts` — marked **PROVISIONAL** in its own header |
| `drawers_range` | `drawers_qty` (whole non-negative number) | `1-2`, `3-5`, `6+`; `0`, blank or non-numeric → no range | `shared/item-properties/drawer-ranges.ts` |

A rule uses `wood_type` **or** `wood_group`, never both.

## E9 — The criteria keys a rule can use today

`shared/item-properties/item-property-options.ts`: `wood_type`, `wood_group`, `years`,
`weight_definition`, `country` (all categories); `shape`, `extension_type`,
`extension_quantity` (table categories); `upholstery`, **`quantity`** (chair categories);
`drawers_range` (storage categories).

**`quantity` is a properties key in Scanner** — the set size resolved from Shopify; the purchase
API's attribute of the same name is deliberately dropped (`item-properties.ts`). In Manager the
set size is the column `Item.quantity`, not a properties key.

## E10 — The two applications do not fill an item's properties from the same sources

Scanner: Shopify product metafields **∪** purchase-API attributes, Shopify winning collisions
(`item-properties.ts` header). Manager: purchase-API attributes only
(`app/beyo_manager/services/queries/items/lookup/purchase_api.py` `parse_purchase_api_attributes`)
or whatever the creating client sends. Same parsing rules for the purchase half (first key wins,
blank dropped, `label` ignored). **A key that Scanner gets only from Shopify can be absent on the
Manager item**, which reads as a mismatch even though the physical item is right. Not measured
here: which keys that affects in live data.

---

# Contract notes for the Scanner-side sender (decided with the owner, 2026-09-18)

For whoever builds the Scanner services that call Manager. The authoritative contract is the
Manager intention (`intention.md`, §8); these are the points that constrain Scanner.

1. **Demand is summed across locations.** Manager's board is location-free. Scanner sends **one
   entry per (itemCategory, properties)** whose `quantityRequested` is the total across every
   location carrying that rule. Two entries with the same identity in one request are rejected.
2. **Units, not items.** `quantityRequested` counts units (a set of 8 chairs is 8), the same
   currency as `LocationStock.quantity`.
3. **Absolute, not delta.** Send the resulting number. Re-sending is harmless.
4. **Absent means untouched.** A rule missing from a request is not a zero; send `0` explicitly.
5. **Malformed input rejects the whole request** (wrong shape or type, duplicate identity): nothing
   is written and the error names the offenders. **An unknown category name does not**: that entry
   is skipped, the rest is applied, and the response lists every entry as `applied` or
   `category_not_found` with its category name and properties echoed. Scanner must read the
   response — a 200 no longer means every rule was taken (corrected by the owner, round 3).
6. **Header `x-api-key`**, the same header the outbound-webhook worker already sends.
7. **Processed webhook** sends `article_number` only. Items with no article number cannot be
   reported. Reporting an item Manager never assigned is harmless (ignored, not an error).
8. **The derived-key tables are mirrored in Manager** (E8). Editing `WOOD_GROUPS` or
   `DRAWER_RANGES` in Scanner without the same edit in Manager makes Manager's assignment warning
   disagree with Scanner's counting.
