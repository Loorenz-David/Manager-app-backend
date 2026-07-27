# HANDOFF_TO_FRONTEND_item_zone_batch_position_update_and_location_search_20260707

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_zone_batch_position_update_and_location_search_20260707`
- Created at (UTC): `2026-07-07T00:00:00Z`
- Owner agent: `claude`
- Source plan: none (direct request)
- Source summary: none (direct request)

## Backend delivery context

- What backend implemented:
  1. `PATCH /api/v1/items/positions` now accepts an optional `item_zone` per entry. When an entry sets `item_zone`, the backend updates the item's zone **and** enqueues the same external location-tracker push that `PATCH /api/v1/items/{client_id}` already triggers when `item_zone` changes.
  2. Documenting the existing (previously undocumented) `GET /api/v1/location-tracker/items/location` endpoint, which is how the frontend reads back the zone/position data that these pushes populate in the external location tracker.
- API or contract changes:
  - `_ItemPositionEntry` gained `item_zone: str | null` (optional, omit to leave the item's zone untouched).
  - No changes to `GET /api/v1/location-tracker/items/location` — it already existed; this handoff just documents its contract.
- Feature flags/toggles (if any): None.

## Frontend action required

1. If the positions-board / zone-drag UI wants to let users reassign an item's zone in the same bulk action as reordering, add `item_zone` to the entries sent to `PATCH /api/v1/items/positions`. **Omit the key entirely** for any entry that should only reposition (do not send `item_zone: null` unless you intend to clear the zone) — the backend only touches zone data for entries where the key is present in the JSON body.
2. Only entries that include `item_zone` will trigger the external location-tracker push and get an `item:updated` history entry mentioning `item_zone`; pure reorders behave exactly as before.
3. If you build a "where is this item" search/lookup UI, wire it to `GET /api/v1/location-tracker/items/location` (see contract below). This reads live data from the external location tracker service, not from the local `items` table, so results reflect whatever was last successfully pushed (including via the zone updates above).

## Interface details

### `PATCH /api/v1/items/positions` (updated)

- Roles allowed: `ADMIN`, `MANAGER`, `WORKER`
- Request shape:
  ```json
  {
    "entries": [
      { "client_id": "itm_a", "item_position": "B-07" },
      { "client_id": "itm_b", "item_position": "B-08", "item_zone": "WAREHOUSE_2" },
      { "client_id": "itm_c", "item_position": null, "item_zone": null }
    ]
  }
  ```
  - `item_position`: as before, always applied per the JSON value sent (send it explicitly for every entry).
  - `item_zone` (new, optional): only applied when the key is present in the entry. `null` clears the zone; omitting the key leaves the current zone untouched.
- Response shape: unchanged — `{"ok": true, "data": {"updated_ids": ["itm_a", "itm_b", "itm_c"]}}`
- Error cases (unchanged):
  - `403` for roles outside `ADMIN`, `MANAGER`, `WORKER`
  - `404` when any referenced item does not exist in the active workspace (atomic failure — nothing is applied)
  - `422` when `entries` is empty or contains more than 200 rows
- Side effect (new): for each entry where `item_zone` is set and non-empty after trimming, and the item has an `article_number` or `sku` to identify it, the backend enqueues an async task (`LOCATION_TRACKER_PUSH_LOCATIONS`, up to 3 retries) that pushes `{position: <zone>, item_targets: [{article_number, sku}], username}` to the external location tracker. This is fire-and-forget relative to the HTTP response — a `200` does not guarantee the external push has completed yet.

### `GET /api/v1/location-tracker/items/location` (documented, no code changes)

- Roles allowed: `ADMIN`, `MANAGER`, `SELLER`, `WORKER`
- Query params:
  - `q` (required, string, max 200 chars, non-empty after trim) — free-text search term forwarded to the external location tracker.
  - `item_identity` (optional) — restricts which identity fields are searched. Accepts a comma-separated string, e.g. `item_identity=article_number,sku`. Valid values: `article_number`, `sku`. Invalid values return `422`. Omit to search both (default).
- Response shape:
  ```json
  {
    "ok": true,
    "data": [
      { "item_article_number": "ABC-123", "sku": "SKU-1", "item_position": "WAREHOUSE_2" }
    ],
    "warnings": []
  }
  ```
  Any of the three fields on an item may be `null` if the external service didn't return them.
- Error cases:
  - `403` for roles outside `ADMIN`, `MANAGER`, `SELLER`, `WORKER`
  - `422` when `q` is missing/empty or `item_identity` contains a value outside `article_number`/`sku`
- Notes:
  - This is a read-through to the external location tracker client (`get_location_tracker_client().get_item_locations(...)`), not a query against local Postgres — there is no pagination or local filtering beyond what the external service does.
  - `item_position` in the response is the external tracker's freeform position/zone label — it corresponds to whatever string was last pushed (e.g. via the `item_zone` push described above), not necessarily the local `items.item_position` column.

## Validation notes

- Backend validation run: `python -m py_compile` on the changed router/service/request files; no test suite run was requested.
- Suggested frontend validation:
  - Confirm bulk zone reassignment only affects entries that explicitly include `item_zone`.
  - Confirm a mixed batch (some entries with `item_zone`, some without) only pushes/records history for the ones that set it.
  - Exercise the search endpoint with `q` only, and with `item_identity` restricted to a single value, to confirm both request shapes work.

## Trace links

- Parent plan: none
- Parent summary: none
- Related debug plan (optional): none
