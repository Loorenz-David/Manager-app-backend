# Handoff to Scanner — Stock Report webhooks (v2)

```
from:       Manager backend (ManagerBeyo-app/backend) — Stock Report project
to:         Scanner backend (Item-Scanner-Shopify/apps/backend)
version:    v2 — 2026-09-19
supersedes: STOCK_REPORT_WEBHOOKS_v1_20260918.md (this folder), which stays as handed over.
            This file is COMPLETE on its own — build from v2 only. The table below lists what
            changed since v1.
status:     PUBLISHED. This file is never edited; a later change ships as v3.
authority:  Manager intention, §8, §8A, §8B (MC-8, MC-9, MC-10), §14B, §14D, §14E, §14F
            (docs/architecture/under_construction/implementation/stock_report/planning/intention.md)
receiver:   NOT BUILT YET. Manager implements these three endpoints in parallel with you.
            Build against this document; there is nothing to call today.
```

## What changed since v1

| # | Section | v1 said | v2 says | What you do differently |
|---|---|---|---|---|
| 1 | **§4A (new)** | "no delete webhook"; a deleted rule is sent as a final `0` | a **third webhook** deletes a board row when a rule's criteria change or the rule is removed; destructive for Manager's assignments on it | delete changed/removed rules through §4A — only when no location still holds the old pair, one stock message at a time per shop, re-checked at send time |
| 2 | §3.2 rule 4 | deleted rule → send `0` | satisfied rule → `0`; changed or removed rule → §4A | stop sending `0` for removed rules |
| 3 | **§4.2, §4.3** | a report for an item Manager is still working on is ignored (`not_awaiting`) and not remembered | it **closes the item early** (`resolved`, reason `early`); `not_awaiting` no longer exists | report each item once; never re-report |
| 4 | §4.3 | `reason` is free text | a closed set of codes | match codes if you use them |
| 5 | §4.1 | article number "exactly as stored" | outer whitespace trimmed, then exact and case-sensitive | — |
| 6 | **§3.5 (new)**, §3.4 | 5xx = retry | Manager **never commits a demand or delete call later than 5 s** after it arrived; answers 503 (whole request) or 500 (one statement) | keep your client timeout above 5 s (8 s today) |
| 7 | **§6.6 (new)** | — | Scanner's worker **drops** a delivery on its own timeout instead of retrying it (`isRetryableError` checks the message, not the name) | apply the fix in §6.6 |
| 8 | §6.3 | a sent-at field "may be added" | **decided: not added**; building the payload at send time is **required** | build demand payloads when the job runs |
| 9 | §3.1.1 (new), §3.1 | category matched case-insensitively | exact first, case-insensitive only if a single match; `Serving Trolleys` is missing in Manager; unknown fields are ignored | — |
| 10 | §2, §3.4 | — | every 401 has the same body; an empty array is 422 | — |
| 11 | §7 | — | checklist items for all of the above | — |

Nothing in v1 was taken away except the two retired behaviours in rows 2 and 3: every other request
that was correct under v1 is still correct.

---

Scanner tells Manager three things: **how much stock is missing** (demand), **which rules no
longer exist** (delete), and **which repaired items Scanner has now processed** (processed).
Manager turns the first into a work board, removes rows with the second, and uses the third to
clear finished work off it. Manager never calls Scanner for any of them.

---

## 1. What is stable and what may still move

| Stable — build on it | May tighten before Manager ships (a v3 file will say so) |
|---|---|
| All three paths, method, header name | The exact text inside `error` strings |
| Request body shapes and field names | |
| Units, summed across locations, absolute values | |
| `outcome` values: `applied`, `category_not_found`, `deleted`, `not_found`, `resolved`, `ignored` | |
| The processed `reason` codes (§4.3) | |
| Status code classes: 2xx / 401 / 422 / 5xx | |
| Replays are harmless | |
| Manager's 5-second limit on demand and delete calls (§3.5) | |
| No send-time / sent-at field — decided, not coming (§6.3) | |

---

## 2. Authentication

- Header: **`x-api-key: <secret>`** — the header `src/workers/outbound-webhook-worker.ts` already
  sends. `Content-Type: application/json`.
- The secret is **one shared value**, configured on the Manager side as
  `MANAGER_API_KEY_TO_LOCATION_TRACKER_APP`. It is a **new** secret: it is not
  `LOCATION_TRACKER_API_KEY`, the Bearer key Manager uses to call Scanner's `/api/manager-app`.
  The owner generates it and gives the same value to both applications.
- Manager compares it in constant time, before reading the body. Missing header, wrong value, or
  a Manager that has not been configured yet → **401**, nothing read, nothing written. Every 401
  has the same body, whatever the cause.
- Manager maps the key to one Manager workspace by its own configuration. **Scanner sends no
  workspace, shop or tenant id.** One key = one Scanner shop = one Manager workspace.
- No signature over the body, no timestamp header, no IP allow-list.

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
| `itemCategory` | string | The category **name** exactly as `LocationStock.itemCategory` holds it. See 3.1.1 for how Manager matches it. Manager never creates a category. |
| `properties` | object | The rule's criteria — send `LocationStock.properties` (the normalized `StockCriteria`: key → sorted lowercase string list, or `null` for "any value"). `{}` is valid: a category-only rule. Send the derived keys (`wood_group`, `drawers_range`) and the `quantity` key as they are; Manager mirrors your matcher for them. |
| `quantityRequested` | integer ≥ 0 | **Units** still missing for this rule — see 3.2. |

A field Manager does not know, in an entry, is **ignored**, not rejected. You may add fields for
your own use without breaking the call.

#### 3.1.1 Category matching

Manager first looks for a category whose name equals `itemCategory` **exactly**. Only if there is
none does it compare case-insensitively, and only a **single** match counts: several case-variant
matches read as `category_not_found` rather than an arbitrary pick. Scanner's category names match
Manager's seeded names exactly, with one exception known today: **`Serving Trolleys` does not
exist in Manager** and will come back `category_not_found` until someone creates it there.

### 3.2 The four rules that make the number right

1. **Summed across locations.** Manager's board has no location. Send **one entry per
   (`itemCategory`, `properties`)**, whose `quantityRequested` is the total missing across every
   `LocationStock` row sharing that pair. `LocationStock` is unique per location, so this is an
   aggregation you must do; do not send one entry per row.
2. **Units, not items.** The same currency as `LocationStock.quantity` — a set of 8 chairs is 8,
   never 1 (`instanceCount` is the wrong column).
3. **Absolute, not a change.** Send the number that is true now. Manager overwrites; it never adds.
4. **Absent means untouched.** A rule you leave out keeps its last value in Manager forever. When a
   rule is satisfied, **send it with `0`** — the row stays, at zero. When a rule's criteria
   change, or the rule is removed, **delete it through §4A** — never by leaving it out, and not
   with a `0`.

How "missing" is computed from thresholds and current quantity is Scanner's decision entirely.

### 3.3 Identity — what makes two entries "the same rule" to Manager

Category + `properties` after Manager normalizes them: key order ignored; a bare string treated as
a one-element list; list values trimmed, lowercased, de-duplicated and sorted. So
`{"wood_group":["Teak","Dark"]}` and `{"wood_group":["dark","teak"]}` are one rule.
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

- One result per entry, **in request order**, echoing `itemCategory` and `properties` as you sent
  them.
- `applied` — Manager now holds this number (creating the board row if it was new).
- `category_not_found` — Manager has no category of that name (3.1.1). **That entry wrote nothing;
  every other entry was still applied.** Surface it (log / alert / admin view): the fix is a human
  one, on the Manager side, and the entry will succeed on the next push after that.

| Status | Meaning | Anything written? | Retry? |
|---|---|---|---|
| 200 | accepted; per-entry outcomes in the body | yes, the `applied` ones | — |
| 401 | key missing/wrong, or Manager not configured | no | not until configuration is fixed |
| 422 | malformed body (not an array, empty array, wrong types, negative number, `properties` not an object) **or** duplicate identity | **no — the whole request is rejected** | no; it is a sender bug |
| 503 | the request ran past Manager's 5 s limit (3.5) | **no** | **yes** — replay is harmless |
| 500 | a single database statement or lock wait ran past the limit, or any other Manager fault | **no** | **yes** |
| timeout / connection error | — | treat as not delivered (see 3.5) | **yes** |

Failure body: `{"error": "<human-readable message>", "ok": false}`. The message is for logs; do
not parse it.

### 3.5 Manager's 5-second limit

Manager will **not commit a demand request later than 5 s after it arrived.** Past that, it rolls
the whole request back — nothing is written — and answers 503 (or 500 if one database statement
or lock wait was the one that ran over). Both are 5xx: retry.

Why: a demand call still running inside Manager after you gave up on it could otherwise commit
*after* your fresher retry and write an old number back (6.3). The limit sits **below your
worker's 8 s client timeout** (`DISPATCH_TIMEOUT_MS = 8_000`), so a call you abandoned can no
longer finish later.

What that asks of you:
- **Keep your client timeout above Manager's limit.** If the stock-demand sender uses a timeout
  other than 8 s, tell the Manager side; Manager's limit (a setting, default 5 s) must stay below
  yours.
- **A timeout on your side means "not applied".** Rarely, a request can still outlive your 8 s:
  Manager checks its limit just before committing, so it never commits late, but it may be late to
  *answer*. In that case Manager wrote nothing and you must **retry** — see 6.6: today your worker
  does not.

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
Manager's users clear those by hand. Unknown fields in an entry are ignored.

**How it is matched:** leading and trailing whitespace is trimmed; everything else is compared
**exactly and case-sensitively** — inner spaces, slashes and leading zeros included.
`"04 2 001 0034"` matches only an item stored as exactly `04 2 001 0034`. Do not reformat it.

### 4.2 What Manager does

Finds its item by that article number, then that item's open board assignment, and **closes it**:
- if Manager's work is finished (the assignment is waiting for Scanner), it is closed normally;
- if Manager's work is **not** finished yet — typically a worker forgot to complete a step and the
  item went on through the pipeline anyway — it is closed **early**. Manager keeps it marked as
  such so its users can see which items reached you before their task was completed. You never
  need to report the item again.

**Everything else is ignored, never an error**: an article number Manager does not know, an item
that was never put on the board, one already closed. You may therefore report **every** placement
(e.g. reuse `item_placed`) without filtering for "was this a Manager item". Report each item
**once**: once closed, Manager will not put the same task and item back on the board.

### 4.3 Responses

```json
{
  "data": {
    "results": [
      { "article_number": "0000612",       "outcome": "resolved", "reason": null },
      { "article_number": "0000613",       "outcome": "resolved", "reason": "early" },
      { "article_number": "04 2 001 0034", "outcome": "ignored",  "reason": "no_open_assignment" }
    ]
  },
  "ok": true,
  "warnings": []
}
```

One result per entry, in request order. `reason` is one of these, and only these (the first that
applies, in this order):

| `outcome` | `reason` | Meaning |
|---|---|---|
| `ignored` | `item_not_found` | No Manager item has that article number. |
| `ignored` | `no_open_assignment` | The item exists but is not on the board (never assigned, or already closed — this is what a replay reads). |
| `resolved` | `null` | Manager closed the item's board assignment; Manager's work was finished. |
| `resolved` | `early` | Manager closed the item's board assignment although Manager's task was not finished yet (4.2). Nothing more is needed from you; the reason is for your logs. |

The same article number twice in one request is not an error: the second is evaluated after the
first has taken effect, so it reads `no_open_assignment`. Status codes and retry rules are the
table in 3.4 (without 503 and `category_not_found`, which are demand-only).

---

## 4A. Delete — a rule's criteria changed, or the rule was removed

```
POST {MANAGER_BASE_URL}/api/v1/location-tracker/webhooks/stock-demand-deleted
```

Send this when a Scanner user **changes a rule's criteria** (delete the old rule here, then send
the new one through demand, §3) or **removes a rule**. It is **destructive** on Manager's side:
Manager finds the board row for that rule and deletes it together with every work assignment on
it, whatever their state. Manager's tasks themselves keep running; Manager's users re-add the
assignments to the new row by hand. It is expected to be rare — mostly while the rules are first
being set up.

### 4A.1 Request body — a JSON array, at least one entry

```json
[ { "itemCategory": "Dining Chairs", "properties": { "wood_group": ["teak"] } } ]
```

The demand entry without `quantityRequested` (sent anyway, it is ignored). Manager finds the row
**exactly as demand does**: same category matching (3.1.1), same identity (3.3). Two entries with
the same identity in one request → **422**, nothing deleted. Empty array → 422.

### 4A.2 Two rules only the sender can keep

1. **Only when no location still holds it.** Manager's row is the **sum across all your
   locations** for one (`itemCategory`, `properties`) (3.2 rule 1). If a user changes the rule at
   one location while another location still tracks the old (`itemCategory`, `properties`), do
   **not** send a delete — that would wipe the other location's live demand and its assignments.
   Send the new, lower sum through demand instead. Send the delete only when **no** location holds
   the old pair any more.
2. **Order, and a check at send time.** A delete and the demand for the new rule can otherwise
   arrive in the wrong order. The case that hurts: a user changes Teak → Light and back to Teak;
   a retried "delete Teak" landing after the new "create Teak" would erase the rule the user
   wants. So:
   - per shop, send **stock messages (demand and delete) one at a time**, in the order you
     produced them; the next waits until the previous has a final answer (2xx, 4xx, or retries
     exhausted);
   - **re-check a delete just before sending it**: if any location holds the old pair again,
     **skip** the delete.

   Manager does not defend against a wrong order itself (beyond its 5 s limit, 3.5).

### 4A.3 Responses

```json
{
  "data": {
    "results": [
      { "itemCategory": "Dining Chairs", "properties": { "wood_group": ["teak"] }, "outcome": "deleted" }
    ]
  },
  "ok": true,
  "warnings": []
}
```

One result per entry, in request order, echoing what you sent:

| `outcome` | Meaning |
|---|---|
| `deleted` | the row and all its assignments are gone from the board |
| `not_found` | no live row has that identity — never created, or already deleted (this is what a replay reads) |
| `category_not_found` | Manager has no such category (3.1.1) |

None of these is an error; the other entries are still applied. Status codes, the 5 s limit and
retry rules are demand's (3.4, 3.5): 401 / 422 not retried; 5xx and timeouts retried — a replay is
harmless.

---

## 5. Replays, retries, batching

- **All three webhooks are idempotent.** Sending the same request twice leaves Manager exactly as
  sending it once. Retry freely on 5xx, timeouts and connection errors.
- **Do not retry 401 or 422** — nothing will change until a human does.
- No batch-size limit is defined. Keep requests reasonable (hundreds of entries, not tens of
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
queue runs five jobs at once. Manager does **not** defend against this with a sent-at stamp (the
owner decided against it), so both of these are **required**:
1. **Build the demand payload when the job runs, not when it is enqueued** — the job carries
   "push demand for shop X", and the worker reads current state just before sending. A retry then
   sends fresh numbers by construction.
2. **Re-push the full set periodically** (and after every stock reconcile). Because values are
   absolute and replays are harmless, a full push heals any entry that ever went stale or was
   lost. This is the cheapest correctness you can buy.

Send **one stock message at a time per shop** — demand and delete in the same lane, in order
(a per-shop job id or concurrency 1 for these event types); deletes also need the send-time check
of 4A.2. Manager's side of the same hazard is its 5 s limit (3.5).

### 6.4 New event types
`OutboundEventType` has only `item_placed`. Demand needs a new type (e.g. `stock_demand`), and so
does delete (e.g. `stock_demand_deleted`), in the same per-shop lane;
processed can be a new type or a reuse of `item_placed` with the payload reshaped to
`[{ "article_number": … }]` — the current `item_placed` payload shape is **not** what Manager
accepts. `OutboundWebhookTarget.secret` holds the shared key; `targetUrl` holds the full path.

### 6.5 The grouping tables are now mirrored
Manager copies `WOOD_GROUPS` (`shared/item-properties/wood-groups.ts`), `DRAWER_RANGES`
(`drawer-ranges.ts`) and the tokenizer/matching rules of `property-criteria.ts`, to warn its users
when they put an item on a board row it does not satisfy. **Editing either table in Scanner
without the same edit in Manager makes the two applications disagree.** `wood-groups.ts` is marked
provisional — tell the Manager side when it changes.

### 6.6 The worker does not retry its own timeout — fix needed
`src/workers/outbound-webhook-worker.ts:14-25`, `isRetryableError`, decides retryability by
searching the error **message** for `"TimeoutError"`. But the timeout from
`AbortSignal.timeout(DISPATCH_TIMEOUT_MS)` rejects with:

```
error.name    === "TimeoutError"
error.message === "The operation was aborted due to timeout"
```

The message never contains `"TimeoutError"`, so the check never matches. **A delivery that times
out is treated as non-retryable: the job completes and the push is lost.** For stock demand that
rule's number stays stale in Manager until the next full re-push (6.3 point 2). The same bug
affects the existing `item_placed` webhook. Reproduced on Node 22.22.3 (the repo pins no Node
version). Classify by name:

```ts
const isRetryableError = (error: unknown): boolean => {
  if (error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError")) {
    return true;
  }
  const message = error instanceof Error ? error.message : String(error ?? "unknown");
  return (
    message.includes("fetch failed") ||
    message.includes("ECONNREFUSED") ||
    message.includes("ECONNRESET") ||
    message.includes("socket hang up")
  );
};
```

Test it by pointing a target at a server that never answers: the job must be retried, not
completed.

---

## 7. A checklist for the Scanner implementation

- [ ] One shared secret configured on both sides; sent as `x-api-key`.
- [ ] Demand aggregated per (`itemCategory`, `properties`) across all locations, in units.
- [ ] Zero sent explicitly for satisfied rules.
- [ ] Changed or removed rules deleted through §4A — only when no location still holds the old
      pair; re-checked at send time and skipped if it exists again.
- [ ] Demand and delete sent one at a time per shop, in order.
- [ ] Demand payload built at send time (**required**); full re-push on a schedule and after reconcile.
- [ ] Demand response body read; `category_not_found` surfaced to a human.
- [ ] 401 alarms; 422 treated as a bug, not retried; 5xx/timeouts retried.
- [ ] `isRetryableError` recognises the timeout by `error.name` (6.6); verified against a
      non-answering target.
- [ ] Stock-demand client timeout stays above Manager's 5 s limit (8 s today).
- [ ] Processed webhook sends `article_number` verbatim; items without one are skipped knowingly.
- [ ] If the processed `reason` is used, it is matched against the codes of 4.3; each item is
      reported once.
- [ ] A change to `WOOD_GROUPS` / `DRAWER_RANGES` is communicated to Manager.
