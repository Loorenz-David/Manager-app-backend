# HANDOFF_TO_FRONTEND_item_upholsteries_create_contract_20260601

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_upholsteries_create_contract_20260601`
- Created at (UTC): `2026-06-01T00:00:00Z`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Source plan: `N/A (implemented directly from chat request)`
- Source summary: `N/A`

## Backend delivery context

- What backend implemented:
  - Confirmed the item-upholsteries router supports creating upholstery for an existing item after item creation.
  - The router exposes a create endpoint that accepts `item_id` plus upholstery fields and dispatches to the item upholstery creation command.
  - The shared upholstery serializer now includes `image_url` in upholstery payloads returned by item-related reads.
- API or contract changes:
  - Existing create endpoint: `PUT /api/v1/item-upholsteries`
  - Existing read endpoints:
    - `GET /api/v1/item-upholsteries`
    - `GET /api/v1/item-upholsteries/{client_id}`
    - `GET /api/v1/item-upholsteries/{client_id}/requirements`
  - Upholstery read payloads now include `image_url`.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use `PUT /api/v1/item-upholsteries` when adding upholstery to an item after the item already exists.
2. Pass the item client id in `item_id` and show validation errors if the selected upholstery source requires fields that are missing.
3. Read `image_url` from upholstery read responses when showing upholstery cards or selections.
4. Use the `/requirements` sub-route when the UI needs the requirement list for a specific item upholstery record.

## Interface details

- Endpoint(s):
  - Create item upholstery: `PUT /api/v1/item-upholsteries`
  - List item upholsteries: `GET /api/v1/item-upholsteries`
  - Get item upholstery by its own client id: `GET /api/v1/item-upholsteries/{client_id}`
  - Get requirements for an item upholstery: `GET /api/v1/item-upholsteries/{client_id}/requirements`

- Auth and role access:
  - Create/update/delete: `ADMIN`, `MANAGER`
  - Read/list: `ADMIN`, `MANAGER`, `WORKER`

- Request shape for create:

```json
{
  "client_id": "iup_...",
  "item_id": "itm_...",
  "upholstery_id": "uph_...",
  "name": "Linen Beige",
  "code": "LIN-BG-01",
  "amount_meters": 3.5,
  "source": "catalog",
  "time_to_fix_in_seconds": 2400
}
```

- Request notes for create:
  - `item_id` is required.
  - `source` is required.
  - `upholstery_id` can be omitted for non-internal flows depending on backend validation.
  - The router forwards `body.model_dump()` directly to the command layer.

- Response shape for create:
  - Existing backend standard response envelope:

```json
{
  "ok": true,
  "data": {
    "client_id": "iup_..."
  },
  "warnings": []
}
```

- Response shape for read/list:
  - Upholstery records now include `image_url` alongside the existing fields.
  - Requirements responses are returned under the `item_upholsteries` / `upholstery_requirements` pagination shapes already used by the backend.

- Error cases:
  - `404` if the item is not found when creating item upholstery.
  - `422` for invalid payloads or missing required fields.
  - `401/403` for auth/role failures.

## Validation notes

- Backend validation run:
  - Unit tests for router wiring passed in the related items router work.
  - The item-upholsteries router currently follows the same command/router pattern and was inspected to confirm the create path.
- Suggested frontend validation:
  - Verify upholstery can be attached only after an item exists.
  - Verify the create form handles both catalog/internal upholstery selection and freeform inputs.
  - Verify `image_url` displays in upholstery listings and detail cards.
  - Verify the requirements view loads correctly for an upholstery record.

## Trace links

- Parent plan:
  - `N/A`
- Parent summary:
  - `N/A`
- Related debug plan (optional):
  - `N/A`
