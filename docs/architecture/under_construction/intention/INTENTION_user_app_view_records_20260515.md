# INTENTION_user_app_view_records_20260515

## Metadata

- Intention ID: `INTENTION_user_app_view_records_20260515`
- Status: `active`
- Owner: `David`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T01:00:00Z`

## Goal

Expose HTTP endpoints for the frontend to push batches of view record events, query the current active view from Redis, and retrieve paginated historical view records from the database — plus an admin/manager live-presence snapshot showing all workspace members' current views and online/offline status — following the contract 48 two-layer architecture (Redis inline, DB via background tasks).

## Why this matters

The frontend needs a reliable HTTP channel for view record events — especially for offline recovery (buffered events sent in batch after reconnect). The existing task handlers and presence service (contract 48) already handle the DB writes and Redis presence; what is missing is the HTTP transport layer and the query surface. The "current view" endpoint feeds live presence UI. The paginated history endpoint feeds user activity dashboards. The admin live-presence endpoint gives managers a single real-time view of who is doing what across the workspace, including online/offline status. Without these, all view record data sits in the DB and Redis with no way for the frontend to write or read it over HTTP.

## Success criteria

1. `POST /api/v1/users/me/view-records` accepts a batch of view record events (max batch size from config). Each item carries `entity_type`, `entity_client_id`, `started_at`, and an optional `ended_at`. Items without `ended_at` are treated as START events; items with `ended_at` as END events.
2. For each START event in the batch: calls `mark_viewing(entity_type, entity_client_id, user_id)` inline (existing presence service), writes a user-view reverse-mapping Redis key (`{prefix}:user_view:{user_id}`), and enqueues `RECORD_VIEW_START` task fire-and-forget.
3. For each END event in the batch: calls `mark_left(entity_type, entity_client_id, user_id)` inline, clears the user-view reverse-mapping key if it matches, and enqueues `RECORD_VIEW_END` task fire-and-forget.
4. `entity_type` in every batch item is validated against `EntityType` enum — invalid values are rejected with `422`.
5. `GET /api/v1/users/me/view-records/current` returns the user's current active view from the Redis reverse-mapping key (entity_type + entity_client_id). Returns an empty payload if no active view is stored.
6. `GET /api/v1/users/me/view-records` returns a paginated list of the user's view records from the DB, ordered by `started_at DESC`, with offset-based pagination (`limit`, `offset`, `has_more`) following the local query contract (07 + 07_local).
7. `record_view_start.py` task handler extended (app-specific local override): before inserting a new record, auto-close all open records for the user globally (`WHERE ended_at IS NULL`, regardless of entity). Documents in `48_presence_local.md` as a departure from the canonical "multi-tab concurrent views allowed" rule.
8. Self-service endpoints (SC 1–6) are authenticated-user-only — no role restriction, user reads and writes their own records exclusively.
9. `GET /api/v1/users/{user_client_id}/view-records` allows admin or manager to retrieve the paginated historical view records for any active workspace member. Same pagination contract as SC 6 (07 + 07_local). Route declared before `GET /{user_client_id}` is not an issue because `/{user_client_id}/view-records` is a two-segment path that does not conflict with the existing single-segment `/{user_client_id}` route.
10. `GET /api/v1/users/live` is an admin/manager-only endpoint that returns a workspace-scoped snapshot of all active members' current views and online/offline status. For each active workspace member: reads `{prefix}:user_view:{user_id}` (this plan's key) and `{prefix}:user_online:{user_id}` (a separate Redis key, owned by a future online-status plan). Reads are batched via Redis pipeline. If `user_view` key is absent, the member has no active view. If `user_online` key is absent, the member is treated as offline. The `/live` static route is declared before `GET /{user_client_id}` in the router file to prevent wildcard collision.

## Scope boundary

- In scope:
  - `POST /api/v1/users/me/view-records` — batch view record event endpoint (self-service)
  - `GET /api/v1/users/me/view-records/current` — current active view from Redis (self-service)
  - `GET /api/v1/users/me/view-records` — paginated historical records from DB (self-service)
  - `GET /api/v1/users/{user_client_id}/view-records` — admin/manager paginated historical records for any workspace member
  - `GET /api/v1/users/live` — admin/manager live workspace presence snapshot (current views + online/offline per member)
  - Redis key `{prefix}:user_view:{user_id}` — user→entity reverse-mapping key (new, owned by this plan)
  - Redis key `{prefix}:user_online:{user_id}` — online/offline status key (read by this plan; **written and owned by a separate future plan**)
  - `record_view_start.py` task handler update — auto-close all globally open records before insert
  - `48_presence_local.md` update — document the one-active-per-user global constraint override and the `user_view` key pattern

- Out of scope:
  - WebSocket `view_entity` / `leave_entity` socket handler wiring (socket infra is a separate concern)
  - Writing or owning the `{prefix}:user_online:{user_id}` key (read-only from this plan's perspective)
  - `EntityType` enum extension with new domain values (separate per-domain concern)
  - Background flush job for durability (best-effort Redis accepted)
  - Retention policy implementation (separate operational concern)

- Non-goals:
  - Multi-user presence queries ("who else is viewing entity X") — served by notification/socket layer
  - Analytics aggregation or rollups
  - Record deduplication between socket-triggered and HTTP-triggered paths (both use the same task handlers; debounce in `RECORD_VIEW_START` handles any overlap)

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_user_app_view_records_20260515` | `backend/docs/architecture/under_construction/implementation/PLAN_user_app_view_records_20260515.md` | `under_construction` | HTTP batch POST, self-service GET (current + history), admin/manager GET (per-user history + live workspace snapshot), Redis user-view key, task handler global auto-close, local presence contract update |

## Progress notes

- `2026-05-15`: Intention created. Goal-intent alignment completed with David. Key decisions:
  - Aligns with contract 48 architecture (Redis inline, DB via tasks fire-and-forget).
  - HTTP transport (not socket) is the explicit channel for this plan.
  - Task handlers (`record_view_start`, `record_view_end`), presence service (`mark_viewing`/`mark_left`), and `presence_worker` are already implemented — not re-implemented here.
  - "One active record per user globally, auto-close old" is an app-specific override to contract 48's multi-tab rule; will be documented in `48_presence_local.md` and enforced in `record_view_start.py`.
  - Live layer for current-view query: new Redis reverse-mapping key `{prefix}:user_view:{user_id}`, written inline by POST endpoint.
  - Best-effort flush durability accepted — no background safety net needed.
- `2026-05-15`: Scope expanded after alignment clarification:
  - Admin/manager can access paginated historical records for any workspace member: `GET /api/v1/users/{user_client_id}/view-records`.
  - Admin/manager live workspace presence snapshot added: `GET /api/v1/users/live`. Returns all active members with current view + online/offline status. `/live` is a static route declared before `GET /{user_client_id}` to avoid wildcard collision.
  - Online/offline status is read from a **separate** Redis key `{prefix}:user_online:{user_id}`. Writing that key is outside this plan's scope — a future online-status plan will own it. If absent, treated as offline.

## Open questions

- None — all blocking decisions resolved during alignment.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: All success criteria met and implementation plan completed and archived.
