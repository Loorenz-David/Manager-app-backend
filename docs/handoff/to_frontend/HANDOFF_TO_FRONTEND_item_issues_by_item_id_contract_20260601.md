# HANDOFF_TO_FRONTEND_item_issues_by_item_id_contract_20260601

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_issues_by_item_id_contract_20260601`
- Created at (UTC): `2026-06-01T00:00:00Z`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Source plan: `N/A (implemented directly from chat request)`
- Source summary: `N/A (no summary artifact created)`

## Backend delivery context

- What backend implemented:
  - Added a new read endpoint to fetch all non-deleted item issues for a single item by item `client_id`.
  - Added a query service that validates item existence in workspace scope, then returns the item issues.
  - Reused existing serializer `serialize_item_issue` from task serializers as requested.
- API or contract changes:
  - New endpoint: `GET /api/v1/items/{client_id}/issues`
  - New response payload key inside `data`: `item_issues`
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Add a frontend API client method for `GET /api/v1/items/{client_id}/issues`.
2. Use the endpoint when only issue data is needed, instead of loading full item detail.
3. Parse `response.data.item_issues` from the backend envelope.
4. Handle `404` as item-not-found and show an empty/error state based on UX rules.

## Interface details

- Endpoint(s):
  - `GET /api/v1/items/{client_id}/issues`
- Auth and role access:
  - Allowed roles: `ADMIN`, `MANAGER`, `WORKER`
- Request shape:
  - Path param:
    - `client_id: string` (item client id)
  - Query/body:
    - None

- Response shape:
  - HTTP success envelope (existing backend standard):

```json
{
  "ok": true,
  "data": {
    "item_issues": [
      {
        "client_id": "iss_...",
        "item_id": "itm_...",
        "issue_type_id": "ity_...",
        "issue_severity_id": "ise_...",
        "state": "open",
        "base_time_seconds": 1800,
        "time_multiplier": 1.25,
        "issue_name_snapshot": "Loose stitching",
        "severity_name_snapshot": "Medium",
        "created_by_id": "usr_...",
        "created_at": "2026-06-01T10:00:00+00:00",
        "started_at": null,
        "resolved_at": null,
        "updated_at": "2026-06-01T10:00:00+00:00"
      }
    ]
  }
}
```

- Return semantics:
  - If item exists and has issues: returns list in `data.item_issues`.
  - If item exists and has no issues: returns `data.item_issues: []`.
  - Soft-deleted issues are excluded.
  - Ordering is ascending by issue `created_at`.

- Error cases:
  - `404` when item does not exist in current workspace (or is deleted).
  - `401/403` for auth/role failures (standard auth middleware behavior).

## Validation notes

- Backend validation run:
  - Unit test added for route wiring and context forwarding.
  - Test command executed: `.venv/bin/python -m pytest tests/unit/test_items_router.py -q`
  - Result: `1 passed`.
- Suggested frontend validation:
  - Verify issues render with real item id.
  - Verify empty state for item with no issues.
  - Verify non-existing item path handles `404` gracefully.
  - Verify worker session can read this endpoint.

## Trace links

- Parent plan:
  - `N/A`
- Parent summary:
  - `N/A`
- Related debug plan (optional):
  - `N/A`
