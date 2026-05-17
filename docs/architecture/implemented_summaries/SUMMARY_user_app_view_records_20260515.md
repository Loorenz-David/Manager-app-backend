# User App View Records Implementation - Summary

Plan ID: PLAN_user_app_view_records_20260515  
Status: Completed  
Completion Date: 2026-05-16  
Owner Agent: GitHub Copilot

## Overview

Implemented the HTTP transport layer for user app view record events — batch POST, self-service reads, admin/manager reads, and an admin live workspace presence snapshot — following the contract 48 two-layer architecture (Redis inline, DB via background tasks).

### Routes added

- `POST /api/v1/users/me/view-records` — batch view record event push (self-service)
- `GET /api/v1/users/me/view-records` — paginated self-service history
- `GET /api/v1/users/me/view-records/current` — current active view from Redis (self-service)
- `GET /api/v1/users/live` — admin/manager live workspace presence snapshot
- `GET /api/v1/users/{user_client_id}/view-records` — admin/manager paginated history per user

## Delivered Changes

### New files

- app/beyo_manager/services/infra/presence/user_view_key.py
- app/beyo_manager/domain/presence/serializers.py
- app/beyo_manager/services/commands/users/requests/record_view_events_request.py
- app/beyo_manager/services/commands/users/record_view_events.py
- app/beyo_manager/services/queries/users/list_self_view_records.py
- app/beyo_manager/services/queries/users/get_current_view.py
- app/beyo_manager/services/queries/users/list_user_view_records.py
- app/beyo_manager/services/queries/users/get_live_workspace_presence.py

### Updated files

- app/beyo_manager/services/tasks/presence/record_view_start.py (global auto-close + honour started_at)
- app/beyo_manager/services/tasks/presence/record_view_end.py (honour ended_at)
- app/beyo_manager/routers/api_v1/users.py (5 new routes in correct declaration order)
- backend/architecture/48_presence_local.md (documented all local overrides and decisions)

## Behaviour and Contract Compliance

- Batch POST: START items call `mark_viewing` + write `user_view` Redis key + enqueue `RECORD_VIEW_START` task. Completed items call `mark_left` + clear `user_view` key if matching + enqueue `RECORD_VIEW_START` then `RECORD_VIEW_END` tasks.
- `entity_type` validated against `EntityType` StrEnum — Pydantic coerces automatically; invalid values yield `422`.
- Batch size capped at `_MAX_BATCH_SIZE = 50`; excess yields `422`.
- `GET /me/view-records/current` reads `{prefix}:user_view:{user_id}` Redis key; returns `null` if absent.
- `GET /me/view-records` and `GET /{user_client_id}/view-records` use offset pagination (`limit+1` has_more pattern) ordered `started_at DESC`.
- `GET /{user_client_id}/view-records` verifies active workspace membership before querying, returns `404` if not found.
- `GET /live` reads all `user_view` and `user_online` keys via single Redis pipeline; missing keys treated as no-view / offline.
- `record_view_start.py`: debounce check runs first; if not debounced, bulk-closes all open records for the user before inserting new one. Uses `payload["started_at"]` if present.
- `record_view_end.py`: uses `payload["ended_at"]` if present.
- Route order: `/me/view-records` and `/me/view-records/current` declared before `PATCH /me`; `/live` declared before `GET /{user_client_id}`; `GET /{user_client_id}/view-records` at end.

## Validation Results

### Static validation

- `OK_VIEW_RECORDS` — record_view_events and get_live_workspace_presence imported cleanly.
- `OK_ROUTER` — full users router imported cleanly.

### Runtime validation and corrections

- Issue observed: asynchronous presence tasks remained pending while HTTP assertions passed.
	- Root cause: local runtime was using worker-dev (RQ queues) instead of execution presence queue consumers.
	- Correction applied: presence-worker runtime command documented and used for queue:presence task consumption.
- Issue observed: role-gated member/presence endpoints returned 403 in manual validation.
	- Root cause: token signed in with workspace scope instead of admin scope.
	- Correction applied: endpoint tests standardized on admin scope tokens for admin/manager routes.
- Issue observed: transport/runtime timing could mask disconnect completion in live checks.
	- Correction applied: integration checks now poll with a wider timeout window when asserting offline state transitions.
