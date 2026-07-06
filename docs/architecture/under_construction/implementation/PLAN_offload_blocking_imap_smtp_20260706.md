# PLAN_offload_blocking_imap_smtp_20260706

## Metadata

- Plan ID: `PLAN_offload_blocking_imap_smtp_20260706`
- Status: `under_construction`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T05:30:00Z`
- Last updated at (UTC): `2026-07-06T05:30:00Z`
- Related issue/ticket: `n/a — reported via prod log analysis (sync-targeted stalls all requests)`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_offload_blocking_imap_smtp_20260706.md`

## Goal and intent

- Goal: Stop blocking IMAP/SMTP network I/O from freezing the single asyncio event loop, so that email sync/send requests no longer stall unrelated concurrent requests.
- Business/user intent: When a user triggers `POST /api/v1/email-threads/sync-targeted` (or any email sync/send), other in-flight requests from the same or other sessions (e.g. `GET /api/v1/tasks/customer-coordination/threads`) must keep responding instead of hanging until the IMAP round-trip completes.
- Non-goals:
  - Do NOT change email business logic, thread-matching, MIME parsing, or DB access patterns.
  - Do NOT introduce a background job queue / worker process (a thread offload is sufficient for I/O-bound waits).
  - Do NOT change any router, command, serializer, or public contract.

## Scope

- In scope:
  - `app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py` — the `SmtpImapEmailProvider` class methods that currently `await` nothing while calling blocking `imaplib` / `smtplib` code.
- Out of scope:
  - `imap_reader.py`, `smtp_sender.py` internals — they stay synchronous by design; only the async adapter boundary changes.
  - Command/router/serializer layers — no changes.
  - Other providers (none exist today besides `SmtpImapEmailProvider`).
- Assumptions:
  - The blocking work is I/O-bound (network waits on IMAP/SMTP sockets), not CPU-bound, so a threadpool offload (`asyncio.to_thread`) fully resolves event-loop starvation despite the GIL.
  - No `AsyncSession` / SQLAlchemy object is touched inside the synchronous `ImapReader` / `SmtpSender` calls — they operate purely on network sockets and plain result objects. (Verified: `sync`, `search_by_header_ids`, `send`, `send_batch`, `test` take primitives / `OutboundMessage` and return dataclass results; DB work happens in the command layer around them.)
  - Default asyncio threadpool capacity (~40 threads, `min(32, cpu+4)`) is adequate for current email concurrency.

## Clarifications required

- [ ] None — the change is a mechanical, behavior-preserving offload. Proceed without blocking questions.

## Acceptance criteria

1. Every method on `SmtpImapEmailProvider` that invokes blocking `ImapReader` / `SmtpSender` code executes that call via `asyncio.to_thread(...)` (or equivalent executor offload) rather than calling it inline on the event loop.
2. Method signatures, return types, and return values are unchanged — callers in the command layer require no edits.
3. While a `sync-targeted` / `sync_inbox` / send call is waiting on the network, a concurrent pure-DB request (`GET /api/v1/tasks/customer-coordination/threads`) returns without waiting for the email call to finish (observable: the DB request's `200 OK` log line no longer trails the email endpoint's completion).
4. No new blocking call is introduced and no existing DB/session access is moved into a worker thread.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/.../infra/email_providers.md` (if present): reason — confirm the provider adapter is the designated async boundary and that internals are intentionally synchronous.

### Local extensions loaded

- None expected.

### File read intent — pattern vs. relational

- Relational reads permitted: `adapter.py` (the file being edited), and — only to confirm no session/DB object crosses the thread boundary — the signatures of `ImapReader.sync`, `ImapReader.search_by_header_ids`, `ImapReader.test`, `SmtpSender.send`, `SmtpSender.send_batch`, `SmtpSender.test`. Do not read command/router/serializer files; they are out of scope and unchanged.

### Skill selection

- Primary skill: n/a (targeted mechanical edit).
- Router trigger terms: `asyncio.to_thread, event loop, blocking I/O, imaplib, smtplib`.
- Excluded alternatives: background-worker/queue skill — excluded because the work is I/O-bound waiting, not CPU-bound, so a thread offload is the correct minimal fix.

## Implementation plan

1. In `adapter.py`, add `import asyncio` at the top of the module.
2. Wrap each blocking call in `asyncio.to_thread`, preserving signatures and return shapes:
   - `send_email` → `return await asyncio.to_thread(self._smtp.send, message)`
   - `send_email_batch` → `results = await asyncio.to_thread(self._smtp.send_batch, messages); return BatchSendResult(results=results)`
   - `sync_inbox` → `return await asyncio.to_thread(self._imap.sync, folder, uidvalidity, last_seen_uid)`
   - `search_by_header_ids` → `return await asyncio.to_thread(self._imap.search_by_header_ids, folder, rfc_message_ids)`
   - `test_connection` → offload both blocking calls: `smtp_ok, smtp_error = await asyncio.to_thread(self._smtp.test)` and `imap_ok, imap_error = await asyncio.to_thread(self._imap.test)` (they run sequentially, which is fine; optionally `asyncio.gather` two `to_thread` calls if parallelism is desired — not required).
3. Leave `ImapReader` and `SmtpSender` untouched (they remain synchronous, which is correct — they are always called through the offloading adapter).
4. Confirm no other call site invokes `self._smtp` / `self._imap` blocking methods directly on the event loop (grep for `._smtp.` / `._imap.` usage across the codebase; expected only inside `adapter.py`).

## Risks and mitigations

- Risk: A blocking call inadvertently touches the async DB session inside the worker thread (SQLAlchemy async sessions are not thread-safe).
  Mitigation: Verify by signature/inspection that `ImapReader` / `SmtpSender` methods receive only primitives and `OutboundMessage` and return plain dataclasses; DB reads/writes stay in the command layer around the adapter call. Do not pass `ctx` or `session` into `to_thread`.
- Risk: Threadpool exhaustion under high concurrent email load (default ~40 threads).
  Mitigation: Acceptable for current scale; if email concurrency grows, introduce a dedicated bounded executor for email I/O in a follow-up. Note this in the intention doc; do not implement now.
- Risk: Exceptions raised inside the sync call surface differently.
  Mitigation: `asyncio.to_thread` re-raises the worker exception in the awaiting coroutine unchanged, so existing try/except handling in the command layer is preserved. No change needed.

## Validation plan

- Static: `ruff check app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py` and the project's type check — expected clean.
- Grep: `grep -rn "self\._smtp\.\|self\._imap\." app/beyo_manager` — expected all matches inside `adapter.py` and each wrapped in `asyncio.to_thread`.
- Behavioral (manual, mirrors the reported repro):
  1. Start the server. Ensure an active email connection with a reachable but slow-to-respond IMAP account (or temporarily add a `time.sleep(15)` shim in `ImapReader.search_by_header_ids` to simulate latency — remove after).
  2. Fire `POST /api/v1/email-threads/sync-targeted` and, immediately in parallel, `GET /api/v1/tasks/customer-coordination/threads`.
  3. Expected: the GET returns in well under a second (its own DB time), NOT after the sync completes. Before the fix, the GET's `200 OK` trails the POST by the full IMAP wait.
- Regression: run the existing email provider / sync test suite — expected pass with no signature changes.

## Review log

- `2026-07-06` `claude`: Initial plan drafted from prod log analysis; root cause = blocking `imaplib`/`smtplib` calls awaited inline on the single event loop in `SmtpImapEmailProvider`.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
