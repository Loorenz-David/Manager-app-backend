# Presence - Local Extensions
> Extends: 48_presence.md

## Overridden Behaviour

### One active view record per user globally (auto-close)

Canonical contract 48 allows multi-tab concurrent views (multiple open `UserAppViewRecord` rows for the same user + entity pair). This app overrides that rule:

**Before inserting a new `UserAppViewRecord`, the `RECORD_VIEW_START` handler bulk-closes all open records for the user globally** (`WHERE ended_at IS NULL`, regardless of entity). This enforces a single-active-view invariant per user across the entire workspace.

When `RECORD_VIEW_START` is processed:
1. All existing `UserAppViewRecord` rows for this user with `ended_at IS NULL` are bulk-closed with `ended_at = started_at` of the new record.
2. The new record is then inserted.

This is implemented in `services/tasks/presence/record_view_start.py`.

Reason: UX requirement — the live presence snapshot (`GET /api/v1/users/live`) shows one current view per user. Concurrent open records would make the current-view state ambiguous.

### Payload timestamps for offline batch records

The canonical handlers use `datetime.now(timezone.utc)` for all timestamps. This app extends both handlers to accept ISO timestamps from the task payload:

- `RECORD_VIEW_START`: uses `payload["started_at"]` (ISO string) if present; falls back to `datetime.now(timezone.utc)`.
- `RECORD_VIEW_END`: uses `payload["ended_at"]` (ISO string) if present; falls back to `datetime.now(timezone.utc)`.

Reason: the HTTP batch endpoint (`POST /api/v1/users/me/view-records`) sends buffered events after offline reconnect. These events carry the original client-side timestamps.

## Local Decisions

### Redis key: `{prefix}:user_online:{user_id}`

Owner: `services/infra/presence/user_online_key.py` (written by `PLAN_user_online_status_20260516`)
Written by: WebSocket connect/disconnect handlers (`sockets/handlers.py`)
Read by: `GET /api/v1/users/live` live presence query (via Redis pipeline)

| Event | Action |
|---|---|
| WebSocket connect | `SET {prefix}:user_online:{user_id} "1" EX 86400` |
| WebSocket disconnect (last connection) | `DEL {prefix}:user_online:{user_id}` |
| WebSocket disconnect (other connections remain) | no Redis write (key persists) |

Value: `"1"` — key existence = online; key absence = offline.
TTL: 86400s — crash-safety net. Primary offline signal is explicit deletion on disconnect.
Multi-tab rule: the in-process `ConnectionManager._connections` dict is the authority for "is this user still connected?" After `manager.disconnect(sid)` pops the disconnecting sid, `is_user_connected(user_id)` checks remaining connections. Key is deleted only when no connections remain.

### Redis key: `{prefix}:user_view:{user_id}`

Key pattern: `{prefix}:user_view:{user_id}`
Value: JSON `{"entity_type": "...", "entity_client_id": "..."}`
TTL: `_USER_VIEW_TTL_SECONDS` (module constant, 86400 s — 24 h)
Owner: `services/infra/presence/user_view_key.py` (written by `PLAN_user_app_view_records_20260515`)

Written inline by `POST /api/v1/users/me/view-records` on START events.
Cleared on END events if the stored entity matches.
Read by `GET /api/v1/users/me/view-records/current` and `GET /api/v1/users/live`.

Stores the user's most recent active view as a JSON object `{"entity_type": "...", "entity_client_id": "..."}`. TTL 86400s.
