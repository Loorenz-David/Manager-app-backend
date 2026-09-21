---
audience: frontend
subject: Stock Report — assignment match preview, v3 ADDENDUM (one request field relaxed)
date: 2026-09-21
status: DRAFT — awaiting owner ratification. Do not send.
extends: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md (v2, RATIFIED)
supersedes: nothing
companion: HANDOFF_TO_FRONTEND_stock_report_api_20260921.md (the twelve board endpoints)
---

# Match preview — v3 addendum

**This is an addendum, not a replacement. v2 stays valid in full — keep reading it.** Exactly one
thing in it changes, and the change is additive: nothing you have already built against v2 breaks.

## The one change: `item_category_id` is now nullable

v2's request block showed:

```jsonc
"item_category_id": "cat_...",
```

and marked `task_id` and `sku` as nullable while leaving this one unmarked, so it read as
**required**. It is now:

```jsonc
"item_category_id": "cat_..." | null,   // null = "this item has no category yet"
```

**Nothing you built against v2 breaks.** If you always send a category, the endpoint behaves
exactly as v2 describes. This only *widens* what it accepts.

## Why

Item creation in this system already allows an item with no category — the create-item request
carries `item_category_id` as optional, and the column is nullable. The preview requiring a
category while create does not would have made **the preview stricter than the thing it
previews**, which is the exact preview/create divergence this endpoint exists to eliminate.

So a form that has not picked a category yet can now ask the question, and get a useful answer
instead of a 422.

## What you get back when you send `null`

The `item_has_no_category` check reports **`fail`**, and — because it is one of the two refusals
with **no override** — the response is:

```jsonc
{
  "can_proceed": false,
  "refusal_reason": "item_has_no_category",
  "override_required": false
}
```

`item_has_no_category` was already documented in v2 §1 as an unoverridable refusal, and your
handling of it does not change. The only new thing is that you can now *reach* it by sending
`null`, rather than only when a resolved item happened to have no category.

## What does NOT change

- **v2 §3 still holds exactly as written.** If `article_number` or `sku` resolves to a live item,
  the preview evaluates that item's **stored** category, properties and quantity and ignores what
  you sent — including this field. `values_source` still reports `"stored"` in that case.
- The response shape is unchanged. Same seven keys, same check names, same ordering.
- `quantity` is still required. That has not moved.
- Sending both `article_number` and `sku` is still a 422.

## Status of this addendum

The code is implemented and verified (phase 8A round 2, checkpoint `efaf9f6`): three new criterion
cases pin the supplied category reaching a decision — its own category passes, a different one
fails with `category_mismatch`, and `null` fails with `item_has_no_category`.

**This file is a DRAFT pending owner ratification and has not been sent.** When ratified, remove
the `DRAFT` marker and this section; do not edit v2 in place.
