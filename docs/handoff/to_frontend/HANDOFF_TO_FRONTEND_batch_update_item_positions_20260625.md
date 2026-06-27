# HANDOFF_TO_FRONTEND_batch_update_item_positions_20260625

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_batch_update_item_positions_20260625`
- Created at (UTC): `2026-06-25T20:40:12Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_batch_update_item_positions_20260625.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_update_item_positions_20260625.md`

## Backend delivery context

- What backend implemented: Added a bulk item-position update endpoint for warehouse relocation flows.
- API or contract changes: New `PATCH /api/v1/items/positions` endpoint that accepts `entries: [{client_id, item_position}]` and returns `updated_ids`.
- Feature flags/toggles (if any): None.

## Frontend action required

1. Add a bulk-update action in the relevant warehouse or inventory UI when users need to assign one position label to many selected items.
2. Handle atomic failure UX: if any submitted `client_id` is missing or deleted, treat the entire request as failed and keep the local selection unchanged.

## Interface details

- Endpoint(s): `PATCH /api/v1/items/positions`
- Request shape: `{"entries": [{"client_id": "itm_...", "item_position": "B-07"}, {"client_id": "itm_...", "item_position": null}]}`
- Response shape: `{"ok": true, "data": {"updated_ids": ["itm_...", "itm_..."]}}`
- Error cases:
  - `403` for roles outside `ADMIN` and `MANAGER`
  - `404` when any referenced item does not exist in the active workspace
  - `422` when `entries` is empty or contains more than 200 rows

## Validation notes

- Backend validation run: Unit tests for request parsing and router wiring passed; command integration test execution is prepared but was blocked in this sandbox by local Postgres access restrictions.
- Suggested frontend validation: Verify success for mixed `string` and `null` positions, show a single error toast on atomic `404`, and prevent sending payloads larger than 200 entries.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_batch_update_item_positions_20260625.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_batch_update_item_positions_20260625.md`
- Related debug plan (optional): none
