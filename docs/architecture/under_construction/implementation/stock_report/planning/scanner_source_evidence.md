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
