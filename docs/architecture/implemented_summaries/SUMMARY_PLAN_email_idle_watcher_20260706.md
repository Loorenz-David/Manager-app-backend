# SUMMARY_PLAN_email_idle_watcher_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_email_idle_watcher_20260706`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T08:25:48Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_email_idle_watcher_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Added a new email IDLE watcher runtime under `services/infra/email_idle/` plus the `workers/email_idle_watcher.py` entrypoint and `email-idle-watcher` Procfile process.
- Added email IDLE watcher settings and explicit startup validation for sharding, reconcile cadence, renew window, debounce, and capped backoff.
- Implemented deterministic stable-hash sharding, reconcile-driven connection ownership, sleep-mode pause/resume, graceful shutdown, per-connection debounce, pending-sync suppression, auth-failure classification, and transient reconnect backoff.
- Added an `aioimaplib`-backed IDLE client wrapper that mirrors the existing IMAP security modes (`ssl`, `starttls`, `none`) and logs/returns cleanly when the provider does not advertise IDLE.
- Extended `ProcessResult` to surface exact newly-created inbound `EmailMessage` rows and wired inline arrival routing in `EMAIL_INBOX_SYNC` so only those exact new inserts enqueue `CREATE_NOTIFICATIONS` inside the same transaction.
- Added `domain/emails/notification_targets.py` as the routing seam, with conservative first-version target resolution: connection owner always, plus existing task/case notification resolvers where the thread entity already maps to one.

## Files changed

- `backend/app/beyo_manager/config.py`: added watcher settings and fail-fast validation.
- `backend/app/beyo_manager/services/infra/email_idle/idle_client.py`, `connection_watcher.py`, `supervisor.py`, `__init__.py`: added the watcher runtime, IDLE client wrapper, and sharded supervisor.
- `backend/app/beyo_manager/workers/email_idle_watcher.py`, `backend/app/Procfile`, `backend/app/requirements.txt`: registered the new process and dependency.
- `backend/app/beyo_manager/services/infra/email_providers/message_processor.py`: extended `ProcessResult` with exact created inbound messages.
- `backend/app/beyo_manager/domain/emails/notification_targets.py`: added the email arrival routing seam.
- `backend/app/beyo_manager/services/tasks/email_inbox_sync_handler.py`: enqueues `CREATE_NOTIFICATIONS` for exact newly-inserted inbound messages inside the sync transaction.

## Contract adherence

- `backend/architecture/16_background_jobs.md` and `51_worker_runtime.md`: the watcher is an explicit long-running process with its own entrypoint, signal-aware shutdown, and thin task-enqueue responsibility.
- `backend/architecture/12_infra_redis.md` and `49_observability_runtime.md`: sleep-mode sharing and runtime logging reuse the existing Redis-backed activity model and structured log conventions.
- `backend/architecture/08_domain.md`: recipient resolution lives in a dedicated domain module instead of being embedded in the watcher or router layers.
- `backend/architecture/06_commands.md` / `06_commands_local.md`: notification task creation stays inside the same transaction as the message inserts that triggered it.

## Validation evidence

- `cd app && python3 -m py_compile beyo_manager/config.py beyo_manager/services/infra/email_idle/idle_client.py beyo_manager/services/infra/email_idle/connection_watcher.py beyo_manager/services/infra/email_idle/supervisor.py beyo_manager/workers/email_idle_watcher.py beyo_manager/domain/emails/notification_targets.py beyo_manager/services/infra/email_providers/message_processor.py beyo_manager/services/tasks/email_inbox_sync_handler.py`: passed.
- `cd app && .venv/bin/ruff check beyo_manager/config.py beyo_manager/services/infra/email_idle/idle_client.py beyo_manager/services/infra/email_idle/connection_watcher.py beyo_manager/services/infra/email_idle/supervisor.py beyo_manager/workers/email_idle_watcher.py beyo_manager/domain/emails/notification_targets.py beyo_manager/services/infra/email_providers/message_processor.py beyo_manager/services/tasks/email_inbox_sync_handler.py`: passed.
- `SECRET_KEY=test JWT_SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test REDIS_URL=redis://localhost:6379/0 PYTHONPATH=app app/.venv/bin/python - <<'PY' ... PY`: passed import-level validation for `settings`, `owns_connection`, `handle_email_inbox_sync`, and `resolve_email_notification_targets`.

## Known gaps or deferred items

- I did not run a live IMAP integration test against a real or local IDLE-capable server in this turn, so the `aioimaplib` runtime path is validated statically but not exercised end to end.
- I did not add automated tests for the new watcher runtime or notification routing in this pass.
- The implementation plan references `backend/docs/architecture/under_construction/intention/INTENTION_email_idle_watcher_20260706.md`, but that intention file does not exist in the repo, so there was no linked intention-plan record to update.

## Handoff notes

- The existing manual and targeted sync endpoints remain unchanged and still serve as fallback/manual refresh paths.
- Real-time inbound delivery now depends on running the new `email-idle-watcher` process alongside the existing task worker and notification worker processes.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_email_idle_watcher_20260706.md`
