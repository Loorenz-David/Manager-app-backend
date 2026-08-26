# Pending-review items NOT emitted — anchors go on the review decision

`archgraph_repair_anchors` refuses items whose origin is `ai_inferred` and that are still pending.
When reviewing each one, add `anchors` to the `promote`/`edit` decision with path + symbol and no range.

- `node:source-symbol-working-section-typical-times-statement-narrowing` — 2 span-bearing entries (index 0, 1); pass `anchors` (path + symbol, no range) on the `promote` or `edit` decision when this item is reviewed
