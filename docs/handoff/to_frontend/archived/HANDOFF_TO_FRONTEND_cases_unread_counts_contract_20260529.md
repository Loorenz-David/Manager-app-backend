# HANDOFF_TO_FRONTEND_cases_unread_counts_contract_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_cases_unread_counts_contract_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Source plan: `N/A`
- Source summary: `N/A`

## Backend delivery context

- What backend implemented:
  - A user-scoped unread-count endpoint for cases: `GET /api/v1/cases/unread-counts`.
  - Counts are derived from case participant read position vs conversation last message sequence.
- API or contract changes:
  - No new endpoint added in this handoff window; this documents the current contract for frontend integration.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Use `GET /api/v1/cases/unread-counts` for case/chat unread badges.
2. Use optional `case_client_ids` when you need counts for a subset of visible cases only.
3. Keep using `GET /api/v1/notifications/unread-count` only for the global notifications badge.
4. Use `POST /api/v1/cases/messages/mark-read` to advance read position and reduce unread counts.

## Interface details

### Endpoint

- Method: `GET`
- URL: `/api/v1/cases/unread-counts`
- Auth: JWT required (`get_jwt_claims`)

### Query parameters

- `case_client_ids` (optional): comma-separated case client IDs.
  - Example: `?case_client_ids=ca_01A,ca_01B,ca_01C`

### Request examples

All cases with unread activity:

```http
GET /api/v1/cases/unread-counts
Authorization: Bearer <token>
```

Only selected cases:

```http
GET /api/v1/cases/unread-counts?case_client_ids=ca_01A,ca_01B
Authorization: Bearer <token>
```

### Success response

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case_unread_counts": {
      "ca_01A": 4,
      "ca_01B": 1
    }
  }
}
```

### Response semantics

- `case_unread_counts` is a map: `case_client_id -> unread_count`.
- Counts are user-specific and inferred from the authenticated user token.
- Without `case_client_ids`:
  - Backend returns only cases whose unread count is greater than zero.
- With `case_client_ids`:
  - Backend computes counts only for the provided cases.
  - Returned counts may include zeros for those filtered cases.

### Error response

```json
{
  "ok": false,
  "error": "..."
}
```

Common errors:

- `401`: missing/invalid JWT.
- `500`: unexpected internal error.

## Related endpoints

- Mark read progress (case participant):
  - `POST /api/v1/cases/messages/mark-read`
  - Body:

```json
{
  "case_participant_client_id": "cpa_01...",
  "up_to_message_seq": 42
}
```

- Global notifications badge (not case unread map):
  - `GET /api/v1/notifications/unread-count`

## Known limitations

- There is currently no dedicated unread-count endpoint keyed by `conversation_client_id`.
- Current unread map is keyed by `case_client_id`.

## Frontend integration notes

- Recommended polling strategy:
  - Poll `GET /api/v1/cases/unread-counts` for list/sidebar badges.
  - Poll `GET /api/v1/notifications/unread-count` for top-level notification bell badge.
- After user opens a case/chat and reaches latest messages, call mark-read and refresh unread counts.
- If UI only shows a subset of cases, pass `case_client_ids` to reduce payload and compute only relevant badges.

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/cases.py`
- Query service: `backend/app/beyo_manager/services/queries/cases/get_unread_counts.py`
- Mark-read command: `backend/app/beyo_manager/services/commands/cases/mark_read.py`
- Notifications unread count router: `backend/app/beyo_manager/routers/api_v1/notifications.py`
