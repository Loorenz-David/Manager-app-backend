# Handoff to Scanner — Stock Report webhooks (v1)

```
from:      Manager backend (ManagerBeyo-app/backend) — Stock Report project
to:        Scanner backend (Item-Scanner-Shopify/apps/backend)
version:   v1 — 2026-09-18
status:    PUBLISHED. This file is never edited. A change to anything below ships as a new file,
           STOCK_REPORT_WEBHOOKS_v2_<date>.md, which lists what changed.
authority: Manager intention, §8, §8A, §14B
           (docs/architecture/under_construction/implementation/stock_report/planning/intention.md)
receiver:  NOT BUILT YET. Manager implements these two endpoints in parallel with you.
           Build against this document; there is nothing to call today.
```

Scanner tells Manager two things: **how much stock is missing** (demand), and **which repaired
items Scanner has now processed** (processed). Manager turns the first into a work board and uses
the second to clear finished work off it. Manager never calls Scanner for either.

---

## 1. What is stable and what may still move

| Stable — build on it | May tighten before Manager ships (a v2 file will say so) |
|---|---|
| Both paths, method, header name | The exact text inside `error` strings |
| Request body shapes and field names | The set of `reason` strings on the processed webhook (treat as free text for now) |
| Units, summed across locations, absolute values | Whether Manager adds an optional sent-at field to the demand entry (see §6.3) |
| `outcome` values: `applied`, `category_not_found`, `resolved`, `ignored` | |
| Status code classes: 2xx / 401 / 422 / 5xx | |
| Replays are harmless | |

---

## 2. Authentication

- Header: **`x-api-key: <secret>`** — the header `src/workers/outbound-webhook-worker.ts` already
  sends. `Content-Type: application/json`.
- The secret is **one shared value**, configured on the Manager side as
  `MANAGER_API_KEY_TO_LOCATION_TRACKER_APP`. It is a **new** secret: it is not
  `LOCATION_TRACKER_API_KEY`, the Bearer key Manager uses to call Scanner's `/api/manager-app`.
  The owner generates it and gives the same value to both applications.
- Manager compares it in constant time, before reading the body. Missing header, wrong value, or
  a Manager that has not been configured yet → **401**, nothing read, nothing written.
- Manager maps the key to one Manager workspace by its own configuration. **Scanner sends no
  workspace, shop or tenant id.** One key = one Scanner shop = one Manager workspace.
- No signature over the body, no timestamp header, no IP allow-list in v1.

---

## 3. Demand — how much stock is missing

```
POST {MANAGER_BASE_URL}/api/v1/location-tracker/webhooks/stock-demand
```

### 3.1 Request body — a JSON array, at least one entry

```json
[
  {
    "itemCategory": "Dining Chairs",
    "properties": { "quantity": ["4"], "upholstery": ["down"], "wood_group": ["teak"] },
    "quantityRequested": 8
  },
  {
    "itemCategory": "Coffee Tables",
    "properties": { "wood_group": ["dark"] },
    "quantityRequested": 0
  }
]
```

| Field | Type | Rule |
|---|---|---|
| `itemCategory` | string | The category **name** exactly as `LocationStock.itemCategory` holds it. Manager matches it case-insensitively against its own category names. Manager never creates a category. |
| `properties` | object | The rule's criteria — send `LocationStock.properties` (the normalized `StockCriteria`: key → sorted lowercase string list, or `null` for "any value"). `{}` is valid: a category-only rule. Send the derived keys (`wood_group`, `drawers_range`) and the `quantity` key as they are; Manager mirrors your matcher for them. |
| `quantityRequested` | integer ≥ 0 | **Units** still missing for this rule — see 3.2. |

### 3.2 The four rules that make the number right

1. **Summed across locations.** Manager's board has no location. Send **one entry per
   (`itemCategory`, `properties`)**, whose `quantityRequested` is the total missing across every
   `LocationStock` row sharing that pair. `LocationStock` is unique per location, so this is an
   aggregation you must do; do not send one entry per row.
2. **Units, not items.** The same currency as `LocationStock.quantity` — a set of 8 chairs is 8,
   never 1 (`instanceCount` is the wrong column).
3. **Absolute, not a change.** Send the number that is true now. Manager overwrites; it never adds.
4. **Absent means untouched.** A rule you leave out keeps its last value in Manager forever. When a
   rule is satisfied, **send it with `0`**. When a rule is deleted in Scanner, send a final `0`
   for it — Manager keeps the row (with its history) at zero; it has no "delete" webhook.

How "missing" is computed from thresholds and current quantity is Scanner's decision entirely.

### 3.3 Identity — what makes two entries "the same rule" to Manager

Category (case-insensitive) + `properties` after Manager normalizes them: key order ignored; a
bare string treated as a one-element list; list values trimmed, lowercased, de-duplicated and
sorted. So `{"wood_group":["Teak","Dark"]}` and `{"wood_group":["dark","teak"]}` are one rule.
**Two entries in one request that resolve to the same identity reject the whole request (422)** —
that is the guard against the per-location mistake of 3.2 rule 1.

### 3.4 Responses

**200** — the request was accepted. **Read the body: 200 does not mean every entry was taken.**

```json
{
  "data": {
    "results": [
      { "itemCategory": "Dining Chairs", "properties": { "…": "…" }, "outcome": "applied" },
      { "itemCategory": "Bar Cabinets",  "properties": {},            "outcome": "category_not_found" }
    ]
  },
  "ok": true,
  "warnings": []
}
```

- One result per entry, **in request order**, echoing `itemCategory` and `properties`.
- `applied` — Manager now holds this number (creating the board row if it was new).
- `category_not_found` — Manager has no category of that name. **That entry wrote nothing; every
  other entry was still applied.** Surface it (log / alert / admin view): the fix is a human one,
  on the Manager side, and the entry will succeed on the next push after that.

| Status | Meaning | Anything written? | Retry? |
|---|---|---|---|
| 200 | accepted; per-entry outcomes in the body | yes, the `applied` ones | — |
| 401 | key missing/wrong, or Manager not configured | no | not until configuration is fixed |
| 422 | malformed body (not an array, wrong types, negative number, `properties` not an object) **or** duplicate identity | **no — the whole request is rejected** | no; it is a sender bug |
| 5xx / timeout / connection error | Manager fault | unknown — treat as not delivered | **yes** — replay is harmless |

Failure body: `{"error": "<human-readable message>", "ok": false}`. The message is for logs; do
not parse it.

---

## 4. Processed — Scanner has dealt with a repaired item

```
POST {MANAGER_BASE_URL}/api/v1/location-tracker/webhooks/items-processed
```

Send this when an item that came back from repair has completed its Scanner-side life: placed in
the requested location, placed anywhere else, or sold before placement. Manager does not need to
know which.

### 4.1 Request body — a JSON array, at least one entry

```json
[ { "article_number": "0000612" }, { "article_number": "04 2 001 0034" } ]
```

`article_number` — string, sent **exactly as stored**, internal spaces included. It is the only
identifier Manager accepts here (not `sku`). An item with no article number cannot be reported;
Manager's users clear those by hand.

### 4.2 What Manager does

Finds its item by that article number, then that item's open board assignment. If the assignment
is **waiting for Scanner** (Manager's work is finished), it is closed. **Everything else is
ignored, never an error**: an article number Manager does not know, an item that was never put on
the board, one still being worked on, one already closed. You may therefore report **every**
placement (e.g. reuse `item_placed`) without filtering for "was this a Manager item".

One consequence to know: if you report an item while Manager still has it in progress, the report
is ignored and **not remembered**. If that item is finished later and you do not report it again,
it waits on Manager's board until a user removes it.

### 4.3 Responses

```json
{
  "data": {
    "results": [
      { "article_number": "0000612",       "outcome": "resolved", "reason": null },
      { "article_number": "04 2 001 0034", "outcome": "ignored",  "reason": "no open assignment" }
    ]
  },
  "ok": true,
  "warnings": []
}
```

One result per entry, in request order. `reason` is informational free text in v1. Status codes
and retry rules are the table in 3.4; `category_not_found` does not exist here, and duplicate
article numbers in one request are not an error.

---

## 5. Replays, retries, batching

- **Both webhooks are idempotent.** Sending the same request twice leaves Manager exactly as
  sending it once. Retry freely on 5xx, timeouts and connection errors.
- **Do not retry 401 or 422** — nothing will change until a human does.
- No batch-size limit is defined in v1. Keep requests reasonable (hundreds of entries, not tens of
  thousands); one request per reconcile is the expected shape.
- A request is processed in one Manager transaction: a 5xx means none of it was applied.

---

## 6. Fitting this onto Scanner's existing outbound-webhook module

Read before reusing `enqueueOutboundEventService` + `outbound-webhook-worker.ts` as they are:

### 6.1 The worker throws the response body away
It logs the status and returns. For **demand** you must read the body, or `category_not_found`
entries vanish silently — a rule Manager never took, with a green log line. Either extend the
worker to hand the parsed body to a per-event handler, or send demand through a dedicated sender.

### 6.2 The worker treats every 4xx as "done"
Correct for 422 here. For **401** it means a misconfigured secret drops every push with one
warning line each. Make 401 loud.

### 6.3 Order of arrival — the one real hazard
Demand is absolute, so a **stale request that lands after a fresh one leaves the wrong number in
Manager until the next push for that rule**. The existing worker makes this possible: the payload
is frozen when the job is enqueued, a failed job is retried later with that old payload, and the
queue runs five jobs at once. Do both of these:
1. **Build the demand payload when the job runs, not when it is enqueued** — the job carries
   "push demand for shop X", and the worker reads current state just before sending. A retry then
   sends fresh numbers by construction.
2. **Re-push the full set periodically** (and after every stock reconcile). Because values are
   absolute and replays are harmless, a full push heals any entry that ever went stale or was
   lost. This is the cheapest correctness you can buy.

Avoid running two demand pushes for the same shop concurrently (a per-shop job id or concurrency 1
for this event type).

### 6.4 New event types
`OutboundEventType` has only `item_placed`. Demand needs a new type (e.g. `stock_demand`);
processed can be a new type or a reuse of `item_placed` with the payload reshaped to
`[{ "article_number": … }]` — the current `item_placed` payload shape is **not** what Manager
accepts. `OutboundWebhookTarget.secret` holds the shared key; `targetUrl` holds the full path.

### 6.5 The grouping tables are now mirrored
Manager copies `WOOD_GROUPS` (`shared/item-properties/wood-groups.ts`), `DRAWER_RANGES`
(`drawer-ranges.ts`) and the tokenizer/matching rules of `property-criteria.ts`, to warn its users
when they put an item on a board row it does not satisfy. **Editing either table in Scanner
without the same edit in Manager makes the two applications disagree.** `wood-groups.ts` is marked
provisional — tell the Manager side when it changes.

---

## 7. A checklist for the Scanner implementation

- [ ] One shared secret configured on both sides; sent as `x-api-key`.
- [ ] Demand aggregated per (`itemCategory`, `properties`) across all locations, in units.
- [ ] Zero sent explicitly for satisfied and for deleted rules.
- [ ] Demand payload built at send time; full re-push on a schedule and after reconcile.
- [ ] Demand response body read; `category_not_found` surfaced to a human.
- [ ] 401 alarms; 422 treated as a bug, not retried; 5xx/timeouts retried.
- [ ] Processed webhook sends `article_number` verbatim; items without one are skipped knowingly.
- [ ] A change to `WOOD_GROUPS` / `DRAWER_RANGES` is communicated to Manager.
