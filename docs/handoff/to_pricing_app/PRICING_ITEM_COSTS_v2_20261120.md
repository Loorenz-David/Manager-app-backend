# Beyo Manager → pricing app: item costs contract v2 (2026-11-20)

This replaces the contract in the docstring of `backend/app/integrations/beyo_manager/client.py`,
which describes v1. **v2 adds fields and doesn't remove any.** A v1 client keeps working, but it
misses the new data and gets two error cases wrong. Section 4 lists what to change.

Server side: Beyo Manager backend, `GET /api/v1/pricing/item-costs`. Release status: v1 is live in
production. v2 goes live with the next backend release. Until then, production answers with the v1 shape.

---

## 1. What changed from v1

| # | Change | Effect on the client |
|---|---|---|
| 1 | `restorationCost` is now worked out from **recorded worker time**, even when the item has no expected sale price and was never evaluated. | More items return a restoration cost. Example: `Ch9-181126` returned `null` in v1 and an amount in v2. |
| 2 | `restorationCost.accuracy`: new object saying whether the recorded time was trustworthy, naming each section whose timing was marked inaccurate. | Read it and show it (section 4). |
| 3 | SKU lookup **ignores case** when the match is unique: `ch3-181126` finds `Ch3-181126`. | The response's `sku` is the stored spelling. Use it as the canonical SKU. |
| 4 | New **409 `ITEM_SKU_AMBIGUOUS`**: two items differ only by case and the request matches neither exactly. | 409 no longer always means a currency mismatch. Read the error body (section 3). |

---

## 2. Request and response

```
GET {base}/api/v1/pricing/item-costs?sku=<sku>
X-API-KEY: <key>
```

`sku`: 1–128 characters. Leading and trailing spaces are trimmed. An exact match wins. Otherwise a
case-insensitive match is used if it's unique.

### 200
```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "sku": "Ch9-181126",
    "currency": "SEK",
    "expectedSalePrice": {"amount": "15000.00", "updatedAt": "2026-11-19T13:03:38.838791+00:00"},
    "purchaseCost":      {"amount": "1800.00",  "updatedAt": "2026-11-02T09:12:04.120000+00:00"},
    "restorationCost": {
      "amount": "6840.49",
      "updatedAt": "2026-11-18T15:40:11.002000+00:00",
      "source": "actual",
      "accuracy": {
        "isAccurate": false,
        "recordedMinutes": "494.28",
        "estimatedMinutes": "31.07",
        "inaccurateSections": [
          {"name": "assembly",    "taskNumber": 1293, "discardedMinutes": "28.37", "estimatedMinutes": "24.73"},
          {"name": "photography", "taskNumber": 1293, "discardedMinutes": "12.02", "estimatedMinutes": "6.33"}
        ]
      }
    },
    "otherCosts": {"amount": "3420.00", "updatedAt": "2026-11-19T13:03:38.838791+00:00"}
  }
}
```

The amounts are illustrative. `Ch9-181126` has no expected sale price in production, so its real
response has `expectedSalePrice: null` and `otherCosts: null`.

### Field reference

Every cost field is either an object or `null`. **`null` means not recorded, never zero.** Amounts are
strings with exactly two decimals, in `currency`. Values are never converted between currencies.
Timestamps are ISO 8601 with an offset.

| Field | Type | Meaning |
|---|---|---|
| `sku` | string | The SKU **as stored** in Beyo Manager. It can differ in case from the request. |
| `currency` | `"SEK" \| "DKK" \| "EUR" \| null` | `null` only when every cost is `null`. |
| `expectedSalePrice` | `{amount, updatedAt} \| null` | The sale price set in Beyo Manager. |
| `purchaseCost` | `{amount, updatedAt} \| null` | What the item was bought for. |
| `otherCosts` | `{amount, updatedAt} \| null` | Beyo Manager's other cost deductions (fees, allocations), excluding purchase cost, at the current `expectedSalePrice`. `null` when there is no expected sale price. |
| `restorationCost` | object \| `null` | See below. |

`restorationCost`:

| Field | Type | Meaning |
|---|---|---|
| `amount` | string | Restoration (labour) cost. |
| `updatedAt` | string \| null | Last change to the recorded time (`actual`), or when the budget was committed (`planned`). |
| `source` | `"actual" \| "planned"` | `actual` = worked out from worker time recorded on the item's tasks. `planned` = no time recorded yet, so this is the production **budget** committed for the item. |
| `accuracy` | object \| `null` | Always an object when `source = "actual"`. Always `null` when `source = "planned"`. |

`restorationCost.accuracy`:

| Field | Type | Meaning |
|---|---|---|
| `isAccurate` | boolean | `true` when no section's timing was marked inaccurate. |
| `recordedMinutes` | string (2 dp) | Minutes taken from time recorded as accurate. |
| `estimatedMinutes` | string (2 dp) | Minutes that replace inaccurate timings. `"0.00"` when accurate. |
| `inaccurateSections` | array | One entry per section, per task, whose timing was marked inaccurate. Empty when accurate. |
| `inaccurateSections[].name` | string | Workshop section, e.g. `"assembly"`. |
| `inaccurateSections[].taskNumber` | integer | The Beyo Manager task number (as shown in the app, e.g. #1293). The same section can appear once per task. |
| `inaccurateSections[].discardedMinutes` | string (2 dp) | Recorded time that was thrown out as wrong. |
| `inaccurateSections[].estimatedMinutes` | string (2 dp) \| `null` | Typical time counted instead. **`null`** = the section has no typical time yet, so only its correctly recorded part (often 0) is counted, and the amount **understates** the real cost. |

How `amount` is built when `source = "actual"`:
- **Time:** recorded minutes plus estimated minutes, over every task where the item is the primary item.
- **Rate:** Beyo Manager's per-minute cost rate.
- A section marked inaccurate counts its typical time: the median of recent, correctly timed work in that section.
- Only finished time counts. A stretch of work running right now is added once it's paused or finished.

---

## 3. Status codes

| Status | Body | Meaning |
|---|---|---|
| 200 | `{"ok": true, "data": {...}}` | Found. Some cost fields can still be `null`. |
| 401 | `{"ok": false, "error": "Unauthorized."}` | Missing, wrong or unconfigured API key. The same body for every cause. |
| 404 | `{"ok": false, "error": "Item not found."}` | No item with that SKU. |
| 404 | `{"detail": "Not Found"}` | **The route doesn't exist.** Beyo Manager is running a release without this endpoint. This isn't an unknown SKU. |
| 409 | `{"ok": false, "error": "ITEM_COST_CURRENCY_MISMATCH: …"}` | The item's cost sources are recorded in different currencies. |
| 409 | `{"ok": false, "error": "ITEM_SKU_AMBIGUOUS: …"}` | **New.** Two items differ only by case and the request matched neither exactly. Ask for the exact spelling. Production has one such pair today: `CH7-160426` / `Ch7-160426`. |
| 422 | FastAPI validation body | `sku` missing or empty. |

---

## 4. Changes needed in the pricing app

1. **Parse `accuracy`** in `parse_costs` (`integrations/beyo_manager/client.py`). Carry it on the
   restoration `CostValue`, or on a new field, through `CostsResult` to the API and the UI. `accuracy` is
   absent from v1 responses, so treat a missing key as `null`.
2. **Show it** next to the restoration cost when `source = "actual"` and `isAccurate = false`. Show
   the estimated share (`estimatedMinutes` out of the total minutes) and list each section with its
   task number. Warn more strongly for any section whose `estimatedMinutes` is `null`, because that
   amount is too low. When `source = "planned"`, say it's a budget, not recorded time.
3. **409:** stop mapping every 409 to "cost sources disagree on the currency". Read `error`:
   - starts with `ITEM_SKU_AMBIGUOUS` → "More than one item matches this SKU when case is ignored. Enter it with its exact capitalisation."
   - starts with `ITEM_COST_CURRENCY_MISMATCH` → the current currency message.
4. **404:** tell the two kinds apart.
   - `{"ok": false, ...}` = unknown SKU. This is `ManagerNotFound`, which is the current behaviour.
   - `{"detail": ...}` = the route is missing. Raise `ManagerError("Beyo Manager doesn't have the item-costs endpoint (backend release missing)")`.
   - Apply the same rule in `health()`. Today the probe treats any 404 as reachable, which hid a missing release once already.
5. **Canonical SKU:** use `data.sku` from the response when you display or store the SKU. The cache
   key stays as is. Different spellings just cache separately for the 5-minute TTL, which is harmless.
6. **Update the client docstring** to this contract, v2.

No changes are needed to authentication, the base URL, the API key or the other cost fields.

---

## 5. Test cases (production data, 2026-11-20)

| SKU sent | Expected |
|---|---|
| `Ch3-181126` | 200. `source: "actual"`, about 4,640.84 SEK. `isAccurate: true`, unless a section has since been marked inaccurate. |
| `ch3-181126` | v2: same as above, with `sku: "Ch3-181126"`. v1: 404. |
| `Ch9-181126` | v2: 200, `expectedSalePrice: null`, `purchaseCost: 1800.00`, `restorationCost` about 6,840 SEK `actual`, `isAccurate: false`, sections assembly and photography (task 1293), `otherCosts: null`. v1: `restorationCost: null`. |
| `ch7-160426` | v2: 409 `ITEM_SKU_AMBIGUOUS`. v1: 404. |
| `CH7-160426` | 200 (exact match). |
| `__beyo_pricing_connection_test__` | 404 `{"ok": false, "error": "Item not found."}`, which means connected and the key works. |

The amounts depend on live data: typical times and recorded time change. Assert on shape and on
`source`, `isAccurate` and section names, not on exact amounts.
