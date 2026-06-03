# HANDOFF_TO_FRONTEND_issue_mode_response_shapes_20260603

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_issue_mode_response_shapes_20260603`
- Created at (UTC): `2026-06-03T12:42:24Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_issue_mode_20260603.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_issue_mode_20260603.md`

## Backend delivery context

- What backend implemented:
  - `IssueType` now exposes `issue_mode` (`graded` or `switch`) in read responses.
  - `ItemIssue` now exposes `issue_mode_snapshot` in read responses.
  - Snapshot is set during item-issue creation using the current mode of the linked issue type.
- API or contract changes:
  - `GET /api/v1/issue-types`
  - `GET /api/v1/issue-types/{client_id}`
  - `GET /api/v1/items/{client_id}/issues`
  - `POST /api/v1/items/{client_id}/issues` — request body accepts optional `client_id` per issue entry
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Update issue type DTOs/models to include required `issue_mode: "graded" | "switch"`.
2. Update item issue DTOs/models to include optional `issue_mode_snapshot: "graded" | "switch" | null`.
3. For issue-type driven UI:
   - Use `issue_mode` to determine input widget behavior.
   - `graded`: show grade/intensity selector.
   - `switch`: use binary toggle and submit `intensity = 1` (frontend rule).
4. For item issue lists/details:
   - Prefer `issue_mode_snapshot` for rendering historical entries.
   - Handle `null` snapshot gracefully (legacy/custom issue records).
5. Add type-safe fallback in UI for unexpected enum values to avoid runtime crashes.
6. When creating item issues (`POST /api/v1/items/{client_id}/issues`), the frontend may optionally provide `client_id` for each issue entry. Use this to pre-assign a stable ID client-side (optimistic UI, deduplication). If omitted the backend generates the ID.

## Interface details

- Endpoint(s):
  - `GET /api/v1/issue-types`
  - `GET /api/v1/issue-types/{client_id}`
  - `GET /api/v1/items/{client_id}/issues`
  - `POST /api/v1/items/{client_id}/issues`

- Request shape:
  - No request body changes for GET routes.
  - Existing query params remain unchanged.

- Response shape:

### 1) `GET /api/v1/issue-types` and `GET /api/v1/issue-types/{client_id}`

Returned issue type objects now include:

```json
{
  "client_id": "ist_xxx",
  "name": "Scratches",
  "source": "manual",
  "issue_mode": "graded",
  "linked_working_section_ids": ["wsc_xxx"],
  "linked_item_category_ids": [
    {
      "item_category_id": "itc_xxx",
      "placement_of_issue": "Frame"
    }
  ],
  "created_at": "2026-06-03T12:00:00+00:00",
  "created_by_id": "usr_xxx"
}
```

Notes:
- `issue_mode` is always present on issue type read responses.
- Allowed values: `graded`, `switch`.

### 2) `GET /api/v1/items/{client_id}/issues`

Returned item issue objects now include:

```json
{
  "client_id": "iti_xxx",
  "workspace_id": "wsp_xxx",
  "item_id": "itm_xxx",
  "step_id": "stp_xxx",
  "worker_id": "usr_xxx",
  "working_section_id": "wsc_xxx",
  "item_category_id": "itc_xxx",
  "issue_type_id": "ist_xxx",
  "issue_type_snapshot": "Scratches",
  "issue_mode_snapshot": "graded",
  "placement_of_issue_snapshot": "Frame",
  "intensity": 3,
  "created_at": "2026-06-03T12:00:00+00:00",
  "updated_at": null
}
```

Notes:
- `issue_mode_snapshot` can be `graded`, `switch`, or `null`.
- `null` is expected for legacy rows or rows without an `issue_type_id`.

### 3) `POST /api/v1/items/{client_id}/issues`

Each entry in the `issues` array now accepts an optional `client_id`:

```json
[
  {
    "client_id": "iti_01KT6PM160NTJRPQZ14JPAH65N",
    "issue_type_id": "ist_01KT6PKAF4HP59XY6NW5PEJC17",
    "step_id": "tsp_01KT6PMH746QDQ1RFQAM8VQZP0",
    "worker_id": "usr_01KT6PKBCHK5ED6SBHJZA09N8H",
    "working_section_id": "wsec_01KT6PKAFENYGJWZSSX2H1A66W",
    "item_category_id": "itc_01KT6PKAEAPKR3ZVD7A77CAZ4D",
    "issue_type_snapshot": "Padding Damage",
    "placement_of_issue_snapshot": "Seat",
    "intensity": 1
  }
]
```

Response (unchanged shape):

```json
{
  "data": {
    "item_issue_ids": ["iti_01KT6PM160NTJRPQZ14JPAH65N"]
  },
  "ok": true,
  "warnings": []
}
```

Notes:
- `client_id` per issue entry is **optional**. When provided it must follow the format `iti_<26-char Crockford Base32 ULID>`. Any other format returns HTTP 422.
- When provided, the returned `item_issue_ids` entry for that position will match the supplied `client_id`.
- When omitted, the backend generates and returns the ID as usual.
- Mixed batches (some entries with `client_id`, some without) are supported.
- Use cases: optimistic UI updates, idempotency / deduplication on retry.

- Error cases:
  - Route-level error behavior is unchanged.
  - No new error envelope fields were introduced.

## Validation notes

- Backend validation run:
  - Migration cycle passed (`upgrade head`, `downgrade -1`, `upgrade head`).
  - Response fields are emitted by serializers used by the listed GET endpoints.
- Suggested frontend validation:
  - Confirm issue type list/detail parsing includes `issue_mode`.
  - Confirm item issues list parsing includes nullable `issue_mode_snapshot`.
  - Confirm UI renders switch-mode issues without grade selector.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_issue_mode_20260603.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_issue_mode_20260603.md`
- Related debug plan (optional): `—`
