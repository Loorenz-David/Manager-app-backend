# SUMMARY_PLAN_email_sync_targeted_via_worker_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_email_sync_targeted_via_worker_20260706`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T05:55:34Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_email_sync_targeted_via_worker_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Converted `sync_email_threads_batch_targeted` from inline IMAP execution to a thin enqueue command that creates an `EMAIL_SYNC_TARGETED` execution task and returns an immediate acknowledgement.
- Added the immutable `SyncEmailThreadsTargetedPayload` payload dataclass plus execution-system registration in `TaskType`, `QUEUE_MAP`, worker timeout config, and the general tasks worker handler map.
- Extracted the batch targeted-sync logic into a reusable core function so the worker now performs the same thread loading, RFC-ID gathering, provider header search, inbound message processing, and aggregated result building that previously happened on the request path.
- Added `handle_sync_email_threads_targeted`, which replays authorization context from the payload, executes the sync in the worker, writes the completion audit entry, and emits `email.threads.synced` to the requesting user.
- Enabled cross-process Socket.IO delivery by attaching `AsyncRedisManager(settings.redis_url)` to the web `AsyncServer` and using a worker-side write-only Redis manager for user-room emission.
- Applied the IMAP/SMTP adapter `asyncio.to_thread(...)` offload at the provider boundary so the new worker path does not keep blocking socket or worker event loops during network I/O.

## Files changed

- `backend/app/beyo_manager/services/commands/emails/sync_email_threads_batch_targeted.py`: replaced inline targeted sync with task enqueue + enqueue audit response.
- `backend/app/beyo_manager/services/commands/emails/_sync_email_threads_targeted_core.py`: added the shared targeted-sync execution core.
- `backend/app/beyo_manager/services/tasks/emails/handle_sync_email_threads_targeted.py`: added the worker handler and socket completion emit.
- `backend/app/beyo_manager/domain/execution/enums.py`, `backend/app/beyo_manager/domain/execution/payloads/sync_email_threads_targeted.py`, `backend/app/beyo_manager/services/infra/execution/task_router.py`, `backend/app/beyo_manager/services/infra/execution/worker_base.py`, `backend/app/beyo_manager/workers/tasks_worker.py`: registered the new task type, payload, queue route, timeout, and handler.
- `backend/app/beyo_manager/sockets/__init__.py`, `backend/app/beyo_manager/sockets/worker_emitter.py`: added the Redis-backed cross-process Socket.IO bridge for worker-originated user events.
- `backend/app/beyo_manager/services/commands/emails/_connection_resolver.py`: added a session-level resolver used by the worker-side auth replay.
- `backend/app/beyo_manager/domain/emails/__init__.py`: registered the enqueue audit event.
- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py`: offloaded blocking IMAP/SMTP calls with `asyncio.to_thread(...)`.

## Contract adherence

- `backend/architecture/06_commands.md` and `06_commands_local.md`: the HTTP command remains command-owned, validates its request immediately, and enqueues the task inside a single `maybe_begin` transaction.
- `backend/architecture/16_background_jobs.md` and `51_worker_runtime.md`: the targeted sync now uses an immutable payload snapshot, explicit task registration, the existing queue runtime, and a dedicated worker handler on `queue:tasks`.
- `backend/architecture/12_infra_redis.md`: the cross-process bridge reuses the configured Redis runtime rather than introducing a second transport.
- `backend/architecture/09_routers.md`: the router path and handler shape stayed unchanged; only response semantics changed from inline sync results to queued acknowledgement.

## Validation evidence

- `python3 -m py_compile app/beyo_manager/services/commands/emails/sync_email_threads_batch_targeted.py app/beyo_manager/services/commands/emails/_sync_email_threads_targeted_core.py app/beyo_manager/services/tasks/emails/handle_sync_email_threads_targeted.py app/beyo_manager/domain/execution/payloads/sync_email_threads_targeted.py app/beyo_manager/services/infra/execution/task_router.py app/beyo_manager/services/infra/execution/worker_base.py app/beyo_manager/workers/tasks_worker.py app/beyo_manager/sockets/__init__.py app/beyo_manager/sockets/worker_emitter.py app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py app/beyo_manager/services/commands/emails/_connection_resolver.py app/beyo_manager/domain/execution/enums.py app/beyo_manager/domain/emails/__init__.py`: passed
- `ruff check ...`: could not run because `ruff` is not installed in this environment

## Known gaps or deferred items

- I did not run a live end-to-end verification with separate web and worker processes plus a connected browser/socket client, so the Redis-backed Socket.IO bridge is validated statically but not exercised in this turn.
- I did not add automated tests for the new task enqueue path or worker handler.
- The implementation plan references `backend/docs/architecture/under_construction/intention/INTENTION_email_sync_targeted_via_worker_20260706.md`, but that intention file does not exist in the repo, so there was no linked intention plan to update.

## Handoff notes

- Frontend listeners should react to the user-scoped socket event `email.threads.synced`.
- The event payload includes the queued task metadata plus the aggregated sync result fields, including `thread_ids_with_new_messages`, `sync_success`, `sync_error`, and `connection_client_ids`.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_email_sync_targeted_via_worker_20260706.md`
