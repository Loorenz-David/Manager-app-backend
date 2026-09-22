---
audience: frontend
subject: Stock Report — match failure value details
date: 2026-09-22
status: SHIPPED additive contract
extends:
  - HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md
  - HANDOFF_TO_FRONTEND_stock_report_api_20260922.md
supersedes: HANDOFF_TO_FRONTEND_stock_report_match_preview_v2_20260921.md §7 failure-element shape only
---

# Match failure value details

`property_failures[]` from match preview and `details[].failures[]` from an assignment-create
409 now use the same four-key element:

```jsonc
{
  "key": "wood_group",
  "reason": "value_not_accepted",
  "accepted_values": ["light"],
  "item_values": ["teak"]
}
```

This is additive. Existing fields, endpoints, request bodies, status codes, override behavior,
and the closed `reason` vocabulary are unchanged.

## Value semantics

- Both arrays are always present and contain the normalized lowercase comparison tokens. Format
  them for display in the client.
- `accepted_values` is the board row's accepted criterion values used by the matcher.
- `item_values` is the item-side value the matcher compared, from the stored item when
  `values_source` is `"stored"`, otherwise from the preview request.
- `missing_on_item` has `item_values: []`.
- `criterion_not_understood` has `accepted_values: []`; do not render that as "accepts nothing".
- `no_group_for_value` keeps the source value in `item_values`, because no derived group exists.

## Derived-property examples

The current Scanner-aligned groups are `dark`, `teak`, and `light`. A stored
`wood_type: "Teak"` against `wood_group: ["light"]` reports `item_values: ["teak"]`; it does
not use the previously illustrative `light teak` group name. A direct `wood_type` criterion
compares the raw normalized wood-type tokens instead.

Quantity remains a set-style equality criterion, not a range rule: a row with
`quantity: ["4"]` and an item quantity of `7` reports `accepted_values: ["4"]` and
`item_values: ["7"]`.

Only failed criteria are returned. One renderer can therefore render the preview warning and the
create endpoint's recoverable 409 identically.
