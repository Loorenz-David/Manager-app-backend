# HANDOFF_TO_FRONTEND_issue_system_rework_contract_20260603

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_issue_system_rework_contract_20260603`
- Created at (UTC): `2026-06-03T08:37:43Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_issue_system_rework_20260603.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_issue_system_rework_20260603.md`

## Backend delivery context

- What backend implemented:
  - Reworked item issues into step-start snapshots.
  - Added batch create, batch delete, and filterable list endpoints for item issues.
  - Added read endpoints for issue types, including working-section and item-category linkage data.
- API or contract changes:
  - `GET /api/v1/issue-types`
  - `GET /api/v1/issue-types/{client_id}`
  - `POST /api/v1/items/{client_id}/issues`
  - `GET /api/v1/items/{client_id}/issues`
  - `DELETE /api/v1/items/{client_id}/issues`
- Feature flags/toggles (if any):
  - None.
- Explicitly excluded from this handoff:
  - Issue configuration write endpoints: create/update/delete issue types.

## Frontend action required

1. Add client methods for the five endpoints listed above.
2. Use `GET /api/v1/issue-types` with backend query filters for `working_section_id` and `item_category_id` whenever the screen already knows the current step and item context.
3. When creating item issues, send snapshot fields from the selected issue type and link record:
   - `issue_type_snapshot` = selected issue type `name`
   - `placement_of_issue_snapshot` = selected link `placement_of_issue`
4. Parse item issue list responses from `data.item_issues_pagination.items`.
5. Do not integrate the issue-type create/update/delete endpoints in frontend scope for this handoff.

## Interface details

- Response envelope for all success cases:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- Error envelope for all failure cases:

```json
{
  "ok": false,
  "error": "Human-readable message"
}
```

### 1. List issue types

- Endpoint:
  - `GET /api/v1/issue-types`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`
- Query params:
  - `limit: number` default `50`, max `200`
  - `offset: number` default `0`
  - `q: string | null` optional partial match on issue type name
  - `working_section_id: string | null` optional comma-separated ids, example: `wsec_01,wsec_02`
  - `item_category_id: string | null` optional comma-separated ids, example: `itc_01,itc_02`
- Success payload:

```json
{
  "ok": true,
  "data": {
    "issue_types": [
      {
        "client_id": "ist_01...",
        "name": "scratches",
        "source": "internal_inspection",
        "linked_working_section_ids": ["wsec_01...", "wsec_02..."],
        "linked_item_category_ids": [
          {
            "item_category_id": "itc_01...",
            "placement_of_issue": "front left leg"
          }
        ],
        "created_at": "2026-06-03T08:00:00+00:00",
        "created_by_id": "usr_01..."
      }
    ],
    "issue_types_pagination": {
      "has_more": false,
      "limit": 50,
      "offset": 0
    }
  },
  "warnings": []
}
```

- Filter semantics:
  - `working_section_id` matches issue types linked to any provided working section id.
  - `item_category_id` matches issue types linked to any provided item category id.
  - If both params are provided, both filters apply.
  - Returned issue type objects still include their full `linked_working_section_ids` and `linked_item_category_ids` arrays.

### 2. Get one issue type

- Endpoint:
  - `GET /api/v1/issue-types/{client_id}`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`
- Path params:
  - `client_id: string` issue type id
- Success payload:

```json
{
  "ok": true,
  "data": {
    "issue_type": {
      "client_id": "ist_01...",
      "name": "scratches",
      "source": "internal_inspection",
      "linked_working_section_ids": ["wsec_01..."],
      "linked_item_category_ids": [
        {
          "item_category_id": "itc_01...",
          "placement_of_issue": "front left leg"
        }
      ],
      "created_at": "2026-06-03T08:00:00+00:00",
      "created_by_id": "usr_01..."
    }
  },
  "warnings": []
}
```

### 3. Create item issues in batch

- Endpoint:
  - `POST /api/v1/items/{client_id}/issues`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`
- Path params:
  - `client_id: string` item id
- Request body:

```json
{
  "issues": [
    {
      "issue_type_id": "ist_01...",
      "step_id": "tsp_01...",
      "worker_id": "usr_01...",
      "working_section_id": "wsec_01...",
      "item_category_id": "itc_01...",
      "issue_type_snapshot": "scratches",
      "placement_of_issue_snapshot": "front left leg",
      "intensity": 3
    }
  ]
}
```

- Notes:
  - `issue_type_id` is nullable, but for normal configured issue selection the frontend should send it.
  - `intensity` must be an integer `>= 1`.
  - Request is transactional: all issues succeed or the whole request fails.

- Success payload:

```json
{
  "ok": true,
  "data": {
    "item_issue_ids": ["iti_01...", "iti_02..."]
  },
  "warnings": []
}
```

### 4. List item issues for one item

- Endpoint:
  - `GET /api/v1/items/{client_id}/issues`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`
- Path params:
  - `client_id: string` item id
- Query params:
  - `q: string | null` optional partial match against `issue_type_snapshot` and `placement_of_issue_snapshot`
  - `working_section_id: string | null`
  - `item_category_id: string | null`
  - `issue_type_id: string | null`
  - `limit: number` default `50`, max `200`
  - `offset: number` default `0`
- Success payload:

```json
{
  "ok": true,
  "data": {
    "item_issues_pagination": {
      "items": [
        {
          "client_id": "iti_01...",
          "workspace_id": "wrk_01...",
          "item_id": "itm_01...",
          "step_id": "tsp_01...",
          "worker_id": "usr_01...",
          "working_section_id": "wsec_01...",
          "item_category_id": "itc_01...",
          "issue_type_id": "ist_01...",
          "issue_type_snapshot": "scratches",
          "placement_of_issue_snapshot": "front left leg",
          "intensity": 3,
          "created_at": "2026-06-03T08:00:00+00:00",
          "updated_at": null
        }
      ],
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  },
  "warnings": []
}
```

- Return semantics:
  - Soft-deleted item issues are excluded.
  - Ordering is ascending by `created_at`.
  - `404` means the item itself was not found in the workspace.

### 5. Delete item issues in batch

- Endpoint:
  - `DELETE /api/v1/items/{client_id}/issues`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`
- Path params:
  - `client_id: string` item id in route
- Important backend behavior:
  - The current implementation only validates workspace ownership for the issue ids.
  - It does not currently enforce that every deleted issue belongs to the `{client_id}` item path param.
  - Frontend should therefore only send issue ids from the active item context.
- Request body:

```json
{
  "issues": [
    { "item_issue_id": "iti_01..." },
    { "item_issue_id": "iti_02..." }
  ]
}
```

- Success payload:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- Delete semantics:
  - Soft delete only.
  - Transactional: if any id is missing or already deleted, the whole request fails.

## Error cases

- `404`
  - Item not found on `GET /api/v1/items/{client_id}/issues`
  - Issue type not found on `GET /api/v1/issue-types/{client_id}`
  - One or more `item_issue_id`s not found on batch delete
  - Any referenced `step_id`, `worker_id`, `working_section_id`, `item_category_id`, or `issue_type_id` not found on batch create
- `422`
  - Invalid payload shape
  - Empty `issues` list on batch create/delete
  - `intensity < 1`
- `401/403`
  - Auth or role failure

## Suggested frontend mapping

- For step-start issue selection, call:
  - `GET /api/v1/issue-types?working_section_id=<currentWorkingSectionId>&item_category_id=<currentItemCategoryId>`
- If the screen needs a merged list across multiple sections or categories, send CSV values:
  - `working_section_id=wsec_01,wsec_02`
  - `item_category_id=itc_01,itc_02`
- When user selects one returned issue type:
  - send `issue_type_id = issueType.client_id`
  - send `issue_type_snapshot = issueType.name`
  - find matching `linked_item_category_ids` entry and send its `placement_of_issue` as `placement_of_issue_snapshot`
- Use `intensity` as the worker-entered integer value.

## Validation notes

- Backend validation run:
  - `APP_ENV=development PYTHONPATH=. .venv/bin/alembic upgrade head`
  - `APP_ENV=development PYTHONPATH=. .venv/bin/alembic downgrade -1`
  - `APP_ENV=development PYTHONPATH=. .venv/bin/alembic upgrade head`
  - `APP_ENV=development PYTHONPATH=. .venv/bin/alembic current` -> `99accdeba8b9 (head)`
  - Backend import smoke test for new commands/queries/routers -> `OK`
- Suggested frontend validation:
  - Load issue types with single-value `working_section_id` and `item_category_id` filters and confirm only matching types are returned.
  - Load issue types with CSV values and confirm union-style matching works for each filter.
  - Create 1 and multiple item issues from the same step-start flow.
  - Search/filter the item issue list with `q`, `working_section_id`, and `issue_type_id`.
  - Batch delete multiple created issues and confirm they disappear from subsequent GET results.

## Trace links

- Parent plan:
  - `backend/docs/architecture/archives/implementation/PLAN_issue_system_rework_20260603.md`
- Parent summary:
  - `backend/docs/architecture/implemented_summaries/SUMMARY_issue_system_rework_20260603.md`
- Related debug plan (optional):
  - `N/A`
