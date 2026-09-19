# Handoff to Scanner — Stock Report webhooks (v2)

```
from:      Manager backend (ManagerBeyo-app/backend) — Stock Report project
to:        Scanner backend (Item-Scanner-Shopify/apps/backend)
version:   v2 — 2026-09-19
status:    PUBLISHED. This file is never edited. A later change ships as v3.
builds on: STOCK_REPORT_WEBHOOKS_v1_20260918.md (this folder) — still valid; read it first.
           v2 only ADDS: nothing in v1 is removed or changed in meaning. Every request that
           was correct under v1 is correct under v2.
authority: Manager intention §8B (MC-8, MC-9, MC-10), §14D D4–D5
           (docs/architecture/under_construction/implementation/stock_report/planning/intention.md)
receiver:  NOT BUILT YET. Manager implements these endpoints in parallel with you.
```

## What changed since v1

| # | Area | v1 said | v2 says | Do you need to change anything? |
|---|---|---|---|---|
| 1 | Processed `reason` | free text, "may tighten" | a **closed set of codes** (§1) | only if you want to act on the reason |
| 2 | Demand time limit | — | Manager gives up on a demand call after **5 s** and answers 5xx (§2) | keep your client timeout above 5 s |
| 3 | Your worker's timeout | — | Scanner's worker **drops** a delivery on its own timeout instead of retrying it (§3) | **yes — a one-line fix** |
| 4 | Sent-at field | "may be added (v1 §6.3)" | **decided: not added.** No `x-sent-at`, no extra field | no — but v1 §6.3 point 1 (build the payload at send time) is now the *only* protection, so it is required, not advised |
| 5 | Category matching | "case-insensitive" | exact name first; case-insensitive only when that finds exactly one category (§4) | no |
| 6 | Unknown fields | not stated | ignored (§4) | no |

---

## 1. Processed webhook — the `reason` codes are now fixed

v1 §4.3 told you to treat `reason` as free text. It is now one of these, and only these:

| `outcome` | `reason` | Meaning |
|---|---|---|
| `resolved` | `null` | Manager closed the item's board assignment. |
| `ignored` | `item_not_found` | No Manager item has that article number. |
| `ignored` | `no_open_assignment` | The item exists but is not on the board (never assigned, or already closed — this is what a replay reads). |
| `ignored` | `not_awaiting` | The item is on the board but Manager's work on it is not finished yet. The report is **not remembered** (v1 §4.2): report it again after the work is done, or the board keeps it. |

Evaluated in that order: the first that applies is the answer.

**How the article number is matched:** leading and trailing whitespace is trimmed; everything else
is compared **exactly and case-sensitively** — inner spaces, slashes and leading zeros included.
`"04 2 001 0034"` matches only an item stored as exactly `04 2 001 0034`. Send the barcode as
stored; do not reformat it.

Two identical article numbers in one request are still not an error: the second is evaluated after
the first has taken effect, so it reads `no_open_assignment`.

## 2. Demand webhook — Manager's 5-second limit

Manager will **not commit a demand request later than 5 s after it arrived.** Past that, it rolls
the whole request back — nothing is written — and answers:

| Status | When |
|---|---|
| **503** | the request as a whole ran past 5 s |
| **500** | a single database statement or lock wait ran past 5 s |

Both are 5xx, so both fall under v1 §3.4's "retry — replay is harmless". No new status class.

Why: an old demand call still running inside Manager after you gave up on it could otherwise commit
*after* your fresher retry and write an old number back (v1 §6.3). The limit sits **below your
worker's 8 s client timeout** (`DISPATCH_TIMEOUT_MS = 8_000`), so a call you abandoned can no
longer finish later.

What that asks of you:
- **Keep your client timeout above Manager's limit.** If the stock-demand sender uses a timeout
  other than 8 s, tell the Manager side; Manager's limit (a setting, default 5 s) must stay below
  yours.
- **A timeout on your side means "not applied".** A demand request can still, rarely, outlive your
  8 s (Manager checks its limit just before committing, so it never commits late — but it may be
  late to *answer*). In that case Manager wrote nothing, and you must **retry**. See §3: today your
  worker does not.

## 3. Fix needed in Scanner's worker: its own timeout is not retried

`src/workers/outbound-webhook-worker.ts:14-25`, `isRetryableError`, decides retryability by
searching the error **message** for `"TimeoutError"`. But the timeout from
`AbortSignal.timeout(DISPATCH_TIMEOUT_MS)` rejects with:

```
error.name    === "TimeoutError"
error.message === "The operation was aborted due to timeout"
```

The message never contains `"TimeoutError"`, so the check never matches. **A delivery that times
out is treated as non-retryable: the job completes and the push is lost.** For stock demand, that
rule's number stays stale in Manager until the next scheduled full re-push (v1 §6.3 point 2). The
same bug affects the existing `item_placed` webhook.

Reproduced on Node 22.22.3 (the repo pins no Node version). The fix is to classify by name:

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

## 4. Two clarifications of v1 (no change in behaviour you can rely on)

- **Category matching** (v1 §3.1 said "case-insensitive"). Manager first looks for a category
  whose name equals `itemCategory` exactly. Only if there is none does it compare
  case-insensitively, and only a **single** match counts; several case-variant matches read as
  `category_not_found` rather than an arbitrary pick. Scanner's category names match Manager's
  seeded names exactly, with one exception known today: **`Serving Trolleys` does not exist in
  Manager** and will come back `category_not_found` until someone creates it there.
- **Unknown fields are ignored.** A field Manager does not know, in a demand or processed entry,
  is skipped, not rejected. You may add fields for your own use without breaking the call.

---

## Checklist additions (to v1 §7)

- [ ] `isRetryableError` recognises the timeout by `error.name` (§3); verified against a
      non-answering target.
- [ ] Stock-demand client timeout is above Manager's 5 s limit (8 s today).
- [ ] Demand payload built at send time — **required** now that no sent-at field exists.
- [ ] If the processed `reason` is used, it is matched against the four codes of §1; a
      `not_awaiting` item is reported again once Manager's work is done.
