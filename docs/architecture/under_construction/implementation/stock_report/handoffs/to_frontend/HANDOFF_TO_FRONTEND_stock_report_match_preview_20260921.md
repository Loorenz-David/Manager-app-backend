---
audience: frontend
subject: Stock Report — assignment match preview (design intent, NOT BUILT)
date: 2026-09-21
status: DESIGN INTENT — no code exists yet
supersedes: nothing
superseded_by: nothing yet
companion: HANDOFF_TO_FRONTEND_stock_report_api_20260921.md (the twelve shipped/planned endpoints)
---

# Match preview — design intent for planning

## 0. Read this first: nothing here is built

**No code for this endpoint exists.** It is not in a plan, and the intention section that will
specify it is not yet written. This document exists because you asked to plan against it, and
publishing it early is worth more than publishing it accurate-and-late — **provided you know
which parts can move.**

This file is **never edited in place.** When the endpoint is specified and built, a new dated
handoff supersedes it and says so in its frontmatter. If you are reading this after that date,
you are reading the wrong file.

Three tiers, and they mean something different from the companion handoff's tiers:

| Tier | Meaning |
|---|---|
| **FIXED** | Already true of shipped, reviewed code. The preview reuses it, so it will not change. Build against it now. |
| **INTENDED** | The agreed design. Very likely to ship as written, but it has not survived planning or review. Do not pin pixel-level behaviour to it. |
| **OPEN** | Genuinely undecided. Do not build against it at all. |

## 1. The problem it solves — FIXED (this much is certain)

Today, to find out whether an item can go on a stock report row, you create the item, create the
task, call `POST /api/v1/stock-report/assignments`, and read the refusal. Two of the possible
refusals are unrecoverable at that point:

- **`category_mismatch`** and **`item_has_no_category`** are **hard refusals with no override.**
  By the time you see one, the item already exists and cannot be used for the thing you made it
  for.
- A **property mismatch** returns `409` and *is* overridable — but only on a second request.

The preview lets a creation form answer "can I proceed?" **before** anything is written, and lets
you send the override with the *first* create call instead of the second.

## 2. Shape — INTENDED

```http
POST /api/v1/stock-report/items/{stock_report_item_client_id}/match-preview
```

```jsonc
// request
{
  "article_number": "ABC-123",      // optional; one of article_number / sku, or neither
  "sku": null,                      // optional
  "item_category_id": "cat_...",    // the candidate's category
  "properties": { "wood_group": "teak", "upholstery": "down" },
  "assumes_new_task": true          // see §4 — changes which checks can be answered
}
```

Roles: **ADMIN, MANAGER, WORKER** — the same set as the create endpoint it previews. Read-only;
it writes nothing and reserves nothing.

The response reports **what it checked**, rather than a single verdict. A bare boolean that
silently skipped three checks is worse than no preview at all, so the shape makes the skips
visible. Exact field names are **OPEN**; the *structure* below is INTENDED.

```jsonc
{
  "can_proceed": true,
  "property_failures": [ { "key": "wood_group", "reason": "missing_on_item" } ],
  "override_required": true,        // property mismatch present but overridable
  "checks": [
    { "name": "stock_report_item_not_found", "result": "pass" },
    { "name": "item_has_no_category",        "result": "pass" },
    { "name": "category_mismatch",           "result": "pass" },
    { "name": "item_already_assigned",       "result": "pass", "advisory": true },
    { "name": "task_failed_or_cancelled",    "result": "pass_by_construction" },
    { "name": "item_not_task_primary",       "result": "pass_by_construction" },
    { "name": "already_processed_by_scanner","result": "pass_by_construction" }
  ]
}
```

## 3. The two vocabularies — FIXED

These are shipped enums. They will not change, and the preview reuses them rather than inventing
parallel ones — so **one renderer serves both the preview and the real 409.**

**Property failure reasons** (`StockCriteriaMismatchReasonEnum`) — exactly four:

| Value | Means |
|---|---|
| `missing_on_item` | the row requires this property; the item has no value for it |
| `value_not_accepted` | the item has a value, but not one this row accepts |
| `no_group_for_value` | the value exists but maps to no known group |
| `criterion_not_understood` | the row's own criterion is malformed (empty accepted list) |

A failure is `{ "key": <property name>, "reason": <one of the four> }`. **This is the same
element shape as `details[].failures[]` in the real `409`** — write one component for both.

**Refusal reasons** are the create endpoint's existing closed set. The preview reports against
the same names; it introduces none.

## 4. What it can and cannot tell you — INTENDED, and the part most worth reading

The create endpoint can refuse for **eleven** reasons. How many the preview can answer depends
entirely on whether you are creating a new task or attaching to an existing one.

**Creating a new task and item in the same form** (your main flow) — the preview is close to
complete, because several checks pass *by construction*:

- a brand-new task is `pending`, so `task_failed_or_cancelled` cannot fire;
- the item will be PRIMARY on that new task, so `item_not_task_primary` cannot fire;
- a brand-new task has no prior assignment pair, so `already_processed_by_scanner` cannot fire.

**Attaching to an existing task** — those three become unknowable and come back as
`"result": "not_evaluated"`. A preview under `assumes_new_task: true` **does not** license a
create against an existing task.

**`item_already_assigned` is advisory, always.** Between your preview and your create, another
worker can take that item. If the create then refuses, that is correct behaviour and not a bug in
either call. Every other check is stable between the two calls.

**Not finding the article number or SKU is a normal outcome, not a 404.** It means "no such item
yet" — the new-item case — and the category and property checks still run against the values you
supplied. Lookups are workspace-scoped, and at most one live item can carry a given
`article_number` or `sku` per workspace (enforced by a partial unique index), so a match is never
ambiguous.

## 5. How to use it in a creation form — INTENDED

1. User types or scans an article number / SKU.
2. Call the preview with the identifier plus the category and properties you looked up.
3. **`can_proceed: false`** → block the form and show the reason. This is the case that saves
   your user from creating an unusable item.
4. **`can_proceed: true` with `override_required: true`** → show the property failures as a
   warning the user can accept, then send `override_property_mismatch: true` on the **first**
   create call. *(That flag exists on the create request today — **FIXED** — so this saves a
   whole round trip.)*
5. **`can_proceed: true`, no failures** → proceed normally.

Do not cache a preview result across a navigation, and do not treat it as a reservation.

## 6. Still OPEN — do not build against these

- **Exact field names** in the response. The structure is agreed; the spelling is not.
- **Whether the endpoint is batch.** Specified single for now, because a creation form handles
  one item. If your form grows a multi-row mode, say so before it is planned — adding batching
  later is a new endpoint version, not a free change.
- **The reverse query** (*given this item, which rows does it match?*). Agreed as a good idea and
  will be specified, but **deliberately not built** until something calls it. If you want it,
  that is the trigger — tell us and it gets built.
- **HTTP status on a malformed body**, and whether the standard envelope wraps this response.
  Note the companion handoff's warning still applies: `403` returns `{"detail": ...}`, **not**
  the project envelope.

## 7. When this becomes real

It is scheduled as its own slice **after batch C1 is approved and before batch C2**. It depends
on phase 8's create command, because the whole point is that the preview calls the *same* check
functions the create endpoint calls rather than a second copy of them — a second implementation
of the refusal ordering would drift from the first, and the drift would show up as a preview that
disagrees with the create.

You will get a new dated handoff when it ships. Until then, treat every INTENDED item as a
sketch you can design around but not code against.
