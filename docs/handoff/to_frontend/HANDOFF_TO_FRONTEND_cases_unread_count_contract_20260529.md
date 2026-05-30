# HANDOFF_TO_FRONTEND_cases_unread_count_contract_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_cases_unread_count_contract_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Source plan: `N/A`
- Source summary: `N/A`

## Backend delivery context

- What backend implemented:
  - New aggregate unread route for cases: `GET /api/v1/cases/unread-count`.
  - Returns a single user-scoped unread total across case conversations.
- API or contract changes:
  - Added a new route under cases router for lightweight global case/chat badge usage.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Use `GET /api/v1/cases/unread-count` for top-level case/chat unread badge.
2. Keep using `GET /api/v1/cases/unread-counts` only when per-case unread map is needed.
3. Keep using `POST /api/v1/cases/messages/mark-read` to advance read state after viewing chat.

## Interface details

### Endpoint

- Method: `GET`
- URL: `/api/v1/cases/unread-count`
- Auth: JWT required (`get_jwt_claims`)

### Query params

- None.

### Success response

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "unread_count": 7
  }
}
```

### Response semantics

- `unread_count` is the total unread message count for the authenticated user across all cases/conversations where the user is a participant.
- Count is computed server-side from:
  - conversation `last_message_seq`
  - participant `last_read_message_seq`
- The endpoint is user-scoped by JWT identity (no explicit `user_id` query/body required).

### Error response

```json
{
  "ok": false,
  "error": "..."
}
```

Common errors:

- `401`: missing or invalid JWT.
- `500`: unexpected internal error.

## Performance notes

- This endpoint is optimized for badge polling because it returns a single aggregated integer.
- Prefer this route over `GET /api/v1/cases/unread-counts` when the UI does not need per-case breakdown.

## Related endpoints

- Per-case unread map:
  - `GET /api/v1/cases/unread-counts`
- Mark read:
  - `POST /api/v1/cases/messages/mark-read`
- Global notification center unread count (separate domain):
  - `GET /api/v1/notifications/unread-count`

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/cases.py`
- Query service: `backend/app/beyo_manager/services/queries/cases/get_unread_count.py`
- Existing per-case unread route: `backend/app/beyo_manager/services/queries/cases/get_unread_counts.py`
