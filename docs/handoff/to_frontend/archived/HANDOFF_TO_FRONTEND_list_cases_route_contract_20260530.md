# HANDOFF_TO_FRONTEND_list_cases_route_contract_20260530

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_list_cases_route_contract_20260530`
- Created at (UTC): `2026-05-30T11:38:17Z`
- Owner agent: `copilot`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - `GET /api/v1/cases` returns the current case list-card payload used by the frontend cases surfaces.
  - The endpoint now supports an additional filter: `includes_participants`.
- API or contract changes:
  - `includes_participants` is a comma-separated query param that filters for cases containing all listed participant user ids.
  - Existing `participants` behavior remains unchanged and still matches cases containing any listed participant.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use the response envelope exactly as returned: `{ "ok": true, "data": { "cases": [...] }, "warnings": [] }`.
2. Treat `participants` and `includes_participants` as different filters:
   - `participants`: any-match filter.
   - `includes_participants`: all-match filter.
3. Treat `q` as a broad substring search across case label, case message text, and linked task item identifiers as described below.

## Interface details

- Endpoint: `GET /api/v1/cases`
- Auth: valid JWT required

### Query params

- `state: string | null`
  - Legacy single-state filter.
  - Exact enum match: `open` | `resolving` | `resolved`.
- `case_state: string | null`
  - Comma-separated multi-state filter.
  - Example: `open,resolving`.
- `q: string | null`
  - Free-text substring search.
  - Max length: `200`.
- `created_by_id: string | null`
  - Exact match on case creator user id.
- `entity_type: string | null`
  - Exact linked entity filter.
  - Allowed: `task` | `customer`.
- `entity_client_id: string | null`
  - Exact linked entity id filter.
- `participants: string | null`
  - Comma-separated user ids.
  - Matches cases where at least one listed user is a participant.
- `includes_participants: string | null`
  - Comma-separated user ids.
  - Matches only cases where all listed users are participants.
  - Duplicate ids are ignored before filtering.
- `offset: number`
  - Default: `0`.
- `limit: number`
  - Default: `50`.

### Response envelope

Success:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "cases": []
  }
}
```

Failure:

```json
{
  "ok": false,
  "error": "..."
}
```

### Case list item shape

Each entry inside `data.cases` is returned as:

```json
{
  "client_id": "ca_...",
  "created_at": "2026-05-30T11:00:00+00:00",
  "state": "open",
  "case_type_id": "cty_...",
  "case_type": {
    "name": "Repair",
    "image": "https://.../repair.webp"
  },
  "participant_count": 3,
  "messages_count": 5,
  "created_by": {
    "client_id": "usr_...",
    "username": "jane",
    "profile_picture": null
  },
  "entity_type": "task",
  "last_message_seq": 5,
  "task": {
    "client_id": "tsk_...",
    "state": "pending",
    "return_source": "pickup",
    "task_type": "repair",
    "ready_by_at": "2026-05-31T10:00:00+00:00",
    "item": {
      "client_id": "itm_...",
      "article_number": "ART-100",
      "sku": "SKU-100",
      "item_image": {
        "client_id": "img_...",
        "image_url": "https://...",
        "width_px": 1200,
        "height_px": 900
      }
    }
  }
}
```

### Field notes

- `case_type` may be `null`.
- `created_by` may be `null` if not loaded/resolved, but normally present.
- `entity_type` is derived from the chosen case link.
- `last_message_seq` is `0` when the case has no conversation.
- `task` is only included when the chosen linked entity type is `task` and the linked task still resolves.
- `participant_count` is singular in the list response. This differs from some detail payloads that use `participants_count`.

## How `q` works

`q` is a case-insensitive substring search implemented with SQL `ILIKE '%<q>%'.`

When `q` is provided, the backend expands the query with left joins and matches a case if `q` appears in any of these fields:

- `cases.type_label`
- any non-deleted `case_conversation_messages.plain_text` belonging to the case
- linked task primary item `items.article_number`
- linked task primary item `items.sku`

Important behavior notes:

- `q` is not tokenized. It is a raw substring match.
- `q` is case-insensitive because the query uses `ILIKE`.
- `q` is broad: a case can match through any historical non-deleted message, not only the latest message.
- When `q` is active, the backend applies `DISTINCT` on case id to avoid duplicate rows caused by joins.
- The route does not expose a `string_filters` selector, so `q` always searches across all four fields above.

Example:

- `GET /api/v1/cases?q=sku-100`
  - matches a case if any linked task primary item has `sku` containing `sku-100`.
- `GET /api/v1/cases?q=broken hinge`
  - matches a case if any non-deleted conversation message plain text contains `broken hinge`.

## Filter semantics summary

- `state=open`
  - exact single-state filter.
- `case_state=open,resolving`
  - multi-state filter.
- `participants=usr_1,usr_2`
  - returns cases where `usr_1` or `usr_2` is a participant.
- `includes_participants=usr_1,usr_2`
  - returns only cases where both `usr_1` and `usr_2` are participants.
- Both `participants` and `includes_participants` can be combined; both conditions must hold.

## Example request

```http
GET /api/v1/cases?case_state=open,resolving&entity_type=task&includes_participants=usr_1,usr_2&q=ART-100&offset=0&limit=20
```

## Validation notes

- Backend validation run:
  - file error checks passed for the touched backend and frontend contract files.
- Suggested frontend validation:
  - Confirm current list views handle `participant_count` and optional `task.item.item_image` safely.
  - Confirm `includes_participants` is sent as a comma-separated string.
  - Confirm `q` UX messaging reflects that search also matches case messages and task item identifiers.

## Trace links

- Parent plan: `—`
- Parent summary: `—`
- Related debug plan (optional): `—`