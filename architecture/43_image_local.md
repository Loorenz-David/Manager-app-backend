# Image - Local Extensions
> Extends: 43_image.md

<!-- Scope: image storage, variants, CDN policy -->
<!-- Add app-specific fields, overrides, and decisions below. -->
<!-- Do NOT modify the canonical 43_image.md directly. -->

## Added Fields

<!-- Example:
- `field_name: Type` - purpose and nullability
-->

## Overridden Behaviour

<!-- Document any behaviour that differs from the canonical contract. -->

- DELETE image supports a query selector `hard_delete=true` in addition to default soft delete behavior.
- Soft delete remains the default when the query flag is omitted or false.
- CONFIRM upload accepts optional optimistic image creation fields (`image_client_id`, `width_px`, `height_px`) and optional inline `image_annotations`.
- CONFIRM upload accepts both single object payloads and batch payloads via `items`, processing all items atomically in one request.

## Local Decisions

<!-- Document app-specific design choices and the reasoning behind them. -->

- Hard delete performs best-effort storage deletion first via the storage client and then removes the image graph rows (`image_links`, `image_annotations`, `image_events`, `images`) in one DB transaction.
- Missing storage objects do not fail hard delete. Unexpected storage provider failures are logged and DB deletion continues.
