# SUMMARY_PLAN_email_targeted_thread_sync_20260704

## Metadata

- Summary ID: `SUMMARY_PLAN_email_targeted_thread_sync_20260704`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T15:15:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_email_targeted_thread_sync_20260704.md`
- Related debug plan (optional): none

## What was implemented

- Extracted the inbound IMAP message persistence loop into `message_processor.py` so batch inbox sync and targeted thread sync share the same duplicate detection, thread matching, message creation, and thread timestamp updates.
- Added `TargetedSyncResult` and `search_by_header_ids(...)` to the email provider abstraction, then implemented targeted IMAP `SEARCH HEADER` lookup in `ImapReader` with RFC-ID caps and fetched-message caps.
- Added single-thread targeted sync command support for `POST /api/v1/email-threads/{thread_id}/sync`.
- Added batch targeted sync command support for `POST /api/v1/email-threads/sync-targeted`, including per-connection RFC-ID unioning, per-connection IMAP search, and aggregated result reporting.
- Added audit events for both targeted sync flows and registered them with the audited event registry.
- Preserved safe router ordering so the static `/sync-targeted` path is declared before wildcard thread routes.
- Ran frontend `npm run typecheck` after the backend implementation and confirmed it completed without errors.

## Files changed

- `backend/app/beyo_manager/services/infra/email_providers/base.py`
- `backend/app/beyo_manager/services/infra/email_providers/message_processor.py`
- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/imap_reader.py`
- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py`
- `backend/app/beyo_manager/services/tasks/email_inbox_sync_handler.py`
- `backend/app/beyo_manager/services/commands/emails/requests/sync_thread_targeted_request.py`
- `backend/app/beyo_manager/services/commands/emails/sync_email_thread_targeted.py`
- `backend/app/beyo_manager/services/commands/emails/sync_email_threads_batch_targeted.py`
- `backend/app/beyo_manager/routers/api_v1/email_threads.py`
- `backend/app/beyo_manager/domain/emails/__init__.py`

## Contract adherence

- `backend/architecture/06_commands.md` and `06_commands_local.md`: new targeted sync flows remain command-owned, use `maybe_begin`, and keep database writes inside transaction boundaries.
- `backend/architecture/07_queries.md` and `07_queries_local.md`: no read-path contract regressions were introduced; router query wiring remains explicit and offset-based where applicable.
- `backend/architecture/09_routers.md`: email thread router remains thin and now keeps the static `/sync-targeted` route ahead of wildcard thread routes to avoid FastAPI path capture bugs.
- `backend/architecture/16_background_jobs.md`: full inbox worker behavior remains intact while reusing a shared message-processing path.

## Validation evidence

- `python3 -m compileall app/beyo_manager/domain/emails app/beyo_manager/services/commands/emails app/beyo_manager/services/infra/email_providers app/beyo_manager/routers/api_v1/email_threads.py app/beyo_manager/services/tasks/email_inbox_sync_handler.py`: passed
- `npm run typecheck` from `frontend/`: passed

## Known gaps or deferred items

- I did not add or run the dedicated targeted-sync backend unit tests described in the plan.
- I did not run a live mailbox QA flow for the new targeted sync endpoints in this turn.

## Handoff notes (if needed)

- Frontend can now trigger targeted sync for a single thread or a filtered batch of threads without advancing the connection-wide IMAP cursor.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
