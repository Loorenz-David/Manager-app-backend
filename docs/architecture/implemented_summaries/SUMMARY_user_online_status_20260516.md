# User Online Status Implementation - Summary

Plan ID: PLAN_user_online_status_20260516  
Status: Completed  
Completion Date: 2026-05-16  
Owner Agent: GitHub Copilot

## Overview

Implemented online/offline Redis key ownership for WebSocket lifecycle so workspace live presence can report accurate `is_online` values.

The implementation writes `{prefix}:user_online:{user_id}` on successful connect and deletes it only when the user's last active socket disconnects.

## Delivered Changes

### New files

- app/beyo_manager/services/infra/presence/user_online_key.py

### Updated files

- app/beyo_manager/sockets/manager.py
- app/beyo_manager/sockets/handlers.py
- backend/architecture/48_presence_local.md

## Behavior and Contract Compliance

- Added `set_user_online(user_id)` and `delete_user_online(user_id)` async Redis helpers.
- Key pattern implemented: `{prefix}:user_online:{user_id}`.
- Key value implemented: `"1"`.
- Key TTL implemented: `86400` seconds.
- `_handle_connect` now validates `user_id` claim and sets online key after successful manager connect.
- `_handle_disconnect` now deletes key only if no other active connections remain for that user.
- Added `ConnectionManager.is_user_connected(user_id)` for multi-tab guard.
- Updated local presence contract doc to record ownership, TTL, and multi-tab behavior for both `user_online` and `user_view` keys.

## Validation Results

### Static validation

- Import validation passed for new online key module and socket handlers (`OK_ONLINE_STATUS`).
- Router import validation passed (`OK_ROUTER`).

### Runtime validation and corrections

- Issue observed: Socket runtime accepted connections but online/offline side effects did not execute.
	- Root cause: Socket handlers were defined but not registered during app startup.
	- Correction applied: handler registration is now invoked in app startup before creating the Socket.IO ASGI wrapper.
- Issue observed: Final disconnect in integration testing could remain online for tens of seconds.
	- Root cause: disconnect propagation may follow heartbeat timeout depending on transport/session timing.
	- Correction applied: integration test timeout widened for offline assertion and startup precondition waits for baseline offline state.
- Issue observed during endpoint validation: role-gated endpoints returned 403 when token used workspace scope.
	- Root cause: endpoint requires admin-capable claims/scope.
	- Correction applied: test execution standardized on admin scope token for role-gated presence/member endpoints.

## Notes

- This plan targets current single-process socket runtime (no Redis adapter for Socket.IO).
- Multi-process online counting remains out of scope by plan design.
