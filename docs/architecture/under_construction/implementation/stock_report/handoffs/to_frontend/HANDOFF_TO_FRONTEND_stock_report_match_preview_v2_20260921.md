---
audience: frontend
subject: Stock Report — assignment match preview (specified contract)
date: 2026-09-21
status: RATIFIED contract, implementation in flight
supersedes: HANDOFF_TO_FRONTEND_stock_report_match_preview_20260921.md (design intent, v1)
companion: HANDOFF_TO_FRONTEND_stock_report_api_20260921.md (the twelve board endpoints)
---

# Match preview — v2, the specified contract

## 0. What changed since v1, and how much you can trust this

v1 was a sketch written before the design was settled. **This version is the ratified contract**
(intention §14G + contract MC-21) with a written build plan (plan 8A, 20 criterion rows). The
code is being implemented now.

Read this file, not v1. v1 is superseded and several of its details are now wrong — in
particular it omitted a **required** request field and said the reverse query was coming.

| Tier | Meaning |
|---|---|
| **FIXED** | Already true of shipped, reviewed code. Cannot change. |
| **RATIFIED** | Settled in the intention and pinned by a criterion row. Will ship as written unless review finds a defect — build against it. |
| **OPEN** | Still undecided. Do not build against it. |

Only two small things are OPEN this time. Everything load-bearing is RATIFIED or FIXED.

## 1. What it is — RATIFIED

```http
POST /api/v1/stock-report/items/{stock_report_item_client_id}/match-preview
```

One question, answered before anything is written: **would this item be accepted on this board
row?** Roles **ADMIN, MANAGER, WORKER** — the same set that may create an assignment. Read-only:
it writes nothing, locks nothing, and **reserves nothing**.

It exists because two of the create endpoint's refusals — `category_mismatch` and
`item_has_no_category` — have **no override**. Without a preview, your user discovers them only
after creating an item they cannot use.

**Single, not batch.** If your form ever previews several rows at once, say so before the phase
ships — retrofitting batch is a new endpoint version, not a free change.

## 2. Request — RATIFIED

```jsonc
{
  "task_id": null,                  // null = "I am creating the task in this same form"
  "article_number": "ABC-123",      // optional; identifies an EXISTING item
  "sku": null,                      // alternative to article_number — never both
  "item_category_id": "cat_...",
  "properties": { "wood_group": "teak", "upholstery": "down" },
  "quantity": 4                     // REQUIRED — see below
}
```

**`quantity` is required, and it is matched like any other criterion.** This is the field v1 got
wrong. Board rows routinely constrain quantity, and the matcher builds it into the property bag
alongside `wood_group` and the rest. Omit it and every quantity rule is evaluated against
nothing.

**Sending both `article_number` and `sku` is a 422.** They are alternatives.

## 3. The rule most likely to surprise you — RATIFIED, read this twice

**If `article_number` or `sku` resolves to a live item, the preview evaluates that item's STORED
category, properties and quantity — and ignores the ones you sent.**

The values you send are used **only** when no item resolves.

This is deliberate and it is the whole point of the endpoint. `create` always reads the stored
item; if the preview answered on your typed values it could say "accepted" and have `create`
refuse a second later. That is the exact failure this endpoint was added to remove, so the
contract forbids it (MC-21: one evaluation, two callers).

**The response tells you which happened:**

```jsonc
"values_source": "stored" | "supplied"
```

If you let a user edit properties on a form that also carries an article number, expect
`"stored"` and show it. A user who typed new values, got "accepted", and doesn't realise the
*old* values were evaluated will be confused, and `values_source` is how you avoid that.

## 4. Response — RATIFIED (field names OPEN at the margin)

```jsonc
{
  "can_proceed": true,
  "override_required": true,
  "refusal_reason": null,                 // what `create` would refuse with, or null
  "property_failures": [ { "key": "wood_group", "reason": "missing_on_item" } ],
  "matched_item_client_id": "itm_...",    // or null
  "values_source": "stored",
  "checks": [ { "check": "category_mismatch", "result": "pass", "advisory": false } ]
}
```

**`refusal_reason` is the same value `create` would return** for the same triple. That equality
is pinned by its own criterion row — if it ever drifts, a test fails.

**`checks[].result` has four values — RATIFIED:**

| Result | Meaning |
|---|---|
| `pass` | evaluated, and it passed |
| `fail` | evaluated, and it failed |
| `pass_by_construction` | **not measured** — it cannot fail given what you sent |
| `not_evaluated` | could not be answered with the information available |

Treat `pass` and `pass_by_construction` as visually different if you show the checks. The second
means "assumed", and the distinction is the reason the field exists.

## 5. Two situations, two different answers — RATIFIED

### You are creating the task in the same form (`task_id: null`)

Four checks report **`pass_by_construction`**, because a task that is about to be created cannot
fail them: `task_not_found`, `task_failed_or_cancelled`, `item_not_task_primary`,
`already_processed_by_scanner`.

**A preview taken with `task_id: null` does not license a create against an existing task.** If
your form later attaches to an existing task, preview again with its id.

### No item exists yet (identifier matches nothing, or you sent neither)

Not an error, **not a 404**. This is the case the endpoint exists for. The four item-dependent
checks report **`not_evaluated`**, `can_proceed` stays **true**, and the category, property and
quantity checks still run against what you sent, with `values_source: "supplied"`.

So: "nothing stands in your way except these property problems" — which is exactly what a
creation form needs to hear.

## 6. Using it — RATIFIED

1. User types or scans an article number / SKU.
2. Preview with the identifier plus the category, properties and quantity you looked up.
3. **`can_proceed: false`** → block, show `refusal_reason`. This is the case that stops your user
   creating an item they cannot use.
4. **`can_proceed: true` and `override_required: true`** → show `property_failures` as a warning
   the user can accept, then send **`override_property_mismatch: true` on the *first* create
   call.** *(That flag already exists on the create request — **FIXED** — so this saves the whole
   409-then-retry round trip.)*
5. **`can_proceed: true`, no failures** → proceed.

## 7. The two vocabularies — FIXED

Shipped enums. The preview reuses them rather than inventing parallel ones, so **one renderer
serves both the preview and the real 409.**

`property_failures[].reason` — exactly four values:

| Value | Means |
|---|---|
| `missing_on_item` | the row requires this property; the item has no value for it |
| `value_not_accepted` | the item has a value, but not one this row accepts |
| `no_group_for_value` | the value exists but maps to no known group |
| `criterion_not_understood` | the row's criterion is malformed (empty accepted list) |

The element shape `{key, reason}` is **identical** to `details[].failures[]` in the create
endpoint's 409.

`checks[].check` uses the create endpoint's existing refusal names. No second vocabulary.

## 8. What it will not do — RATIFIED

- **`item_already_assigned` is advisory** (`advisory: true`). Someone else can take the item
  between your preview and your create. A later refusal is correct behaviour, not a bug in either
  call. Every other check is stable between the two.
- **It is not a reservation.** Don't cache a result across a navigation.
- **It is not a promise that create will succeed.** It answers "would this be accepted right
  now?".
- **A deleted, foreign or absent row in the path is `NotFound`**, like every other read.
- **The reverse query is dropped.** *"Given this item, which rows does it match?"* was considered
  and **rejected** — no caller, and it would need ordering and pagination decisions over every
  row. v1 said it was coming; that was superseded. If you want it, that is a new decision, not a
  waiting item.

## 9. Still OPEN — two things

- **Exact response field names** may shift slightly in review. The structure and the four
  `result` values will not.
- **Whether the standard envelope wraps this response.** Note the companion handoff's warning
  still applies regardless: **`403` returns `{"detail": ...}`, not the project envelope.**

## 10. One known gap, stated rather than hidden

There is no automated test proving the path's `client_id` reaches the service. This repo's router
tests fake the database layer, so the only available proof would assert against the fake. A
criterion row for it was withdrawn to a backlog note rather than shipped as theatre.

**Practical consequence:** if that wiring ever breaks, it breaks silently and no test catches it.
If you see a preview answering about the wrong board row, suspect that first — it is the one
failure in this endpoint with no guard behind it.

---

This file is **never edited in place.** If the contract changes, a new dated handoff supersedes
it and says so in its frontmatter.
