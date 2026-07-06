# SUMMARY_PLAN_email_sync_targeted_corrections_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_email_sync_targeted_corrections_20260706`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T06:22:06Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_email_sync_targeted_corrections_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Added terminal-failure socket emission to the targeted sync worker handler. The worker now emits `email.threads.synced` with `sync_success=false` and `sync_error` on the final failed attempt before re-raising into the existing retry/fail machinery.
- Switched worker-side authorization from the payload’s role snapshot to a live `WorkspaceMembership -> WorkspaceRole -> Role` lookup so revoked or changed memberships are enforced at execution time.
- Made the socket package lazy by replacing eager `AsyncRedisManager` / `AsyncServer` construction in `sockets/__init__.py` with `get_socket_manager()` and `get_sio()`. This keeps `worker_emitter` imports from initializing the web socket server objects.
- Extracted room naming into `sockets/rooms.py` and updated `ConnectionManager` plus `worker_emitter` to use those helpers without changing room names.
- Consolidated `POST /api/v1/email-threads/{thread_id}/sync` onto the same enqueue path as `POST /api/v1/email-threads/sync-targeted`, removing the old inline IMAP request-path implementation and its one-off request model.
- Reworked the success socket payload assembly so `connection_client_id` is set explicitly from the sync result instead of being silently overwritten by dict merge order.

## Files changed

- `backend/app/beyo_manager/services/tasks/emails/handle_sync_email_threads_targeted.py`: added final-attempt failure emits and explicit success payload shaping.
- `backend/app/beyo_manager/services/commands/emails/_actor_role_resolver.py`: added live role resolution from active workspace membership.
- `backend/app/beyo_manager/services/commands/emails/_sync_email_threads_targeted_core.py`: switched execution-time auth checks to the live role lookup.
- `backend/app/beyo_manager/sockets/__init__.py`, `backend/app/beyo_manager/sockets/manager.py`, `backend/app/beyo_manager/sockets/register.py`, `backend/app/beyo_manager/sockets/rooms.py`, `backend/app/beyo_manager/sockets/worker_emitter.py`, `backend/app/beyo_manager/__init__.py`: removed eager socket server initialization from import paths and centralized room helpers.
- `backend/app/beyo_manager/routers/api_v1/email_threads.py`: routed `POST /{thread_id}/sync` through `sync_email_threads_batch_targeted` with `thread_client_ids=[thread_id]`.
- `backend/app/beyo_manager/services/commands/emails/requests/sync_thread_targeted_request.py`: removed `SyncThreadTargetedRequest`, keeping only the batch request model.
- `backend/app/beyo_manager/services/commands/emails/sync_email_thread_targeted.py`: deleted the old synchronous single-thread targeted sync command.
- `backend/app/beyo_manager/domain/emails/__init__.py`: removed the unused `email.thread.sync_targeted` audit registration.

## Contract adherence

- `backend/architecture/06_commands.md` and `06_commands_local.md`: the single-thread route now uses the same command-owned enqueue path as the batch route rather than a second inline sync implementation.
- `backend/architecture/16_background_jobs.md` and `51_worker_runtime.md`: retry behavior stays in `worker_base`; the handler only adds a final-outcome user notification without changing generic worker orchestration.
- `backend/architecture/13_sockets.md`: room naming remains stable while cross-process worker emission is decoupled from web-server initialization side effects.

## Validation evidence

- `python3 -m py_compile app/beyo_manager/__init__.py app/beyo_manager/sockets/__init__.py app/beyo_manager/sockets/manager.py app/beyo_manager/sockets/register.py app/beyo_manager/sockets/worker_emitter.py app/beyo_manager/sockets/rooms.py app/beyo_manager/services/tasks/emails/handle_sync_email_threads_targeted.py app/beyo_manager/services/commands/emails/_sync_email_threads_targeted_core.py app/beyo_manager/services/commands/emails/_actor_role_resolver.py app/beyo_manager/routers/api_v1/email_threads.py app/beyo_manager/services/commands/emails/sync_email_threads_batch_targeted.py app/beyo_manager/services/commands/emails/requests/sync_thread_targeted_request.py app/beyo_manager/domain/emails/__init__.py`: passed
- `./.venv/bin/python -c 'import importlib; importlib.import_module("beyo_manager.sockets.worker_emitter"); pkg = importlib.import_module("beyo_manager.sockets"); print(...)'`: passed, reporting `sio_is_none=True socket_manager_is_none=True`
- `rg -n "sync_email_thread_targeted|SyncThreadTargetedRequest|email\\.thread\\.sync_targeted" app`: passed, with the only remaining match being the router function name `sync_email_thread_targeted_route`

## Known gaps or deferred items

- I did not run a live worker retry scenario against a connected browser client, so the final-attempt failure event behavior is validated structurally rather than with an end-to-end socket session in this turn.
- I did not add automated tests for the new live-role resolver or the final-attempt failure emit path.
- The archived plan’s metadata timestamps remain non-monotonic relative to the system clock because the source plan already contained future UTC timestamps before this implementation turn.

## Handoff notes

- `POST /api/v1/email-threads/{thread_id}/sync` now returns the same enqueue acknowledgement shape as `POST /api/v1/email-threads/sync-targeted`, not the old inline sync stats payload.
- Frontend code should treat both targeted sync endpoints as fire-and-listen flows, with `email.threads.synced` as the completion contract.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_email_sync_targeted_corrections_20260706.md`
