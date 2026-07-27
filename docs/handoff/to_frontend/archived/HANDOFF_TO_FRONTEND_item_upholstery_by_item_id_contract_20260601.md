# HANDOFF_TO_FRONTEND_item_upholstery_by_item_id_contract_20260601

## Metadata

- Handoff ID: HANDOFF_TO_FRONTEND_item_upholstery_by_item_id_contract_20260601
- Created at (UTC): 2026-06-01T00:00:00Z
- Owner agent: GitHub Copilot (GPT-5.3-Codex)
- Source plan: N/A (implemented from chat request)
- Source summary: N/A

## Backend delivery context

- What backend implemented:
  - Added a new items endpoint to fetch only item upholstery and requirements by item client id.
  - Added an optimized query service that validates item existence, fetches all item upholsteries with joined upholstery image_url, and fetches all requirements in one batched IN query.
  - Updated task-domain serializer serialize_upholstery to include image_url.
- API or contract changes:
  - New endpoint: GET /api/v1/items/{client_id}/upholstery
  - New response payload keys: item_upholstery, requirements
  - item_upholstery objects now include image_url
- Feature flags/toggles (if any):
  - None

## Frontend action required

1. Add a frontend API method for GET /api/v1/items/{client_id}/upholstery.
2. For screens that only need upholstery and requirements, call this endpoint instead of GET /api/v1/items/{client_id}.
3. Read data.item_upholstery and data.requirements from the response envelope.
4. Support nullable image_url in each upholstery row.

## Interface details

- Endpoint(s):
  - GET /api/v1/items/{client_id}/upholstery

- Access:
  - Allowed roles: ADMIN, MANAGER, WORKER

- Request shape:
  - Path params:
    - client_id: string (item client id)
  - Query params: none
  - Body: none

- Response shape:

```json
{
  "ok": true,
  "data": {
    "item_upholstery": [
      {
        "client_id": "iup_...",
        "item_id": "itm_...",
        "upholstery_id": "uph_...",
        "name": "Linen Beige",
        "code": "LIN-BG-01",
        "image_url": "https://.../linen-beige.webp",
        "amount_meters": 3.5,
        "source": "catalog",
        "time_to_fix_in_seconds": 2400,
        "active_requirement_id": "req_..."
      }
    ],
    "requirements": [
      {
        "client_id": "req_...",
        "item_upholstery_id": "iup_...",
        "upholstery_inventory_id": "uin_...",
        "amount_meters": 3.5,
        "value_minor": 12000,
        "currency": "EUR",
        "source": "inventory",
        "state": "pending"
      }
    ]
  }
}
```

- Return semantics:
  - If item exists and has no upholstery, returns item_upholstery as [] and requirements as [].
  - Requirements are returned across all upholsteries for the item.
  - Upholstery rows are ordered by ItemUpholstery.created_at ascending.
  - Requirement rows are ordered by ItemUpholsteryRequirement.created_at ascending.
  - image_url can be null.

- Error cases:
  - 404 when item does not exist in current workspace or is deleted.
  - 401 or 403 for auth or role failures.

## Validation notes

- Backend validation run:
  - Unit tests executed: .venv/bin/python -m pytest tests/unit/test_items_router.py -q
  - Result: 2 passed
  - LSP diagnostics on edited files: no errors found

- Suggested frontend validation:
  - Verify endpoint populates upholstery cards and requirement list for a known item.
  - Verify image rendering fallback when image_url is null.
  - Verify empty state when both arrays are empty.
  - Verify 404 handling for deleted or unknown item id.

## Trace links

- Parent plan:
  - N/A
- Parent summary:
  - N/A
- Related debug plan (optional):
  - N/A
