# HANDOFF_TO_FRONTEND_item_issues_batch_delete_contract_20260601

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_issues_batch_delete_contract_20260601`
- Created at (UTC): `2026-06-01T00:00:00Z`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Source plan: `N/A (implemented directly from chat request)`
- Source summary: `N/A`

## Backend delivery context

- What backend implemented:
  - Added batch delete support for item issues under the items router.
  - New payload-based delete route can delete multiple issue ids in a single request.
  - Service implementation performs scoped, batched validation and soft-deletion in one transaction.
- API or contract changes:
  - New endpoint: `DELETE /api/v1/items/{client_id}/issues` with JSON body payload.
  - Existing single-delete endpoint remains supported: `DELETE /api/v1/items/{client_id}/issues/{issue_id}`.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Add a batch delete API method that calls `DELETE /api/v1/items/{client_id}/issues` with `issue_ids` payload.
2. Update multi-select issue deletion UX to use batch delete endpoint instead of looping single deletes.
3. Keep single delete calls for one-off removal if desired (backward compatible path still valid).
4. Handle not-found responses when one or more ids are invalid or already deleted.

## Interface details

- Endpoint(s):
  - Batch delete: `DELETE /api/v1/items/{client_id}/issues`
  - Single delete (unchanged): `DELETE /api/v1/items/{client_id}/issues/{issue_id}`

- Auth and role access:
  - Allowed roles for delete: `ADMIN`, `MANAGER`

- Request shape (batch delete):

```json
{
  "issue_ids": ["iti_...", "iti_...", "iti_..."]
}
```

- Response shape (batch delete success):

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- Error cases:
  - `404` if any issue in the requested list is not found for the given item/workspace or already deleted.
  - `422` if payload is invalid (for example empty `issue_ids`).
  - `401/403` for auth/role failures.

- Behavioral notes:
  - Batch operation is transactional.
  - Soft-delete semantics are preserved (records are marked deleted, not physically removed).
  - All ids must be valid and active for success.

## Validation notes

- Backend validation run:
  - Unit tests: `.venv/bin/python -m pytest tests/unit/test_items_router.py -q`
  - Result: `3 passed`
  - Edited files diagnostics: no errors found
- Suggested frontend validation:
  - Delete selected issues in one request and verify list refresh.
  - Verify mixed valid/invalid id set returns error and does not partially delete.
  - Verify deleting an already deleted issue returns not-found behavior.
  - Verify manager role can perform batch delete.

## Trace links

- Parent plan:
  - `N/A`
- Parent summary:
  - `N/A`
- Related debug plan (optional):
  - `N/A`
