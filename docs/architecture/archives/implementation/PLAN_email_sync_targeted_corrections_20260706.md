# PLAN_email_sync_targeted_corrections_20260706

## Metadata

- Plan ID: `PLAN_email_sync_targeted_corrections_20260706`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T07:00:00Z`
- Last updated at (UTC): `2026-07-06T06:22:06Z`
- Related issue/ticket: `Post-implementation review of PLAN_email_sync_targeted_via_worker_20260706`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_email_sync_targeted_corrections_20260706.md`

## Goal and intent

- Goal: Fix a real gap between the delivered implementation and the risk mitigations promised in `PLAN_email_sync_targeted_via_worker_20260706` (archived at `backend/docs/architecture/archives/implementation/PLAN_email_sync_targeted_via_worker_20260706.md`, summarized at `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_email_sync_targeted_via_worker_20260706.md`), plus smaller code-quality issues surfaced in that same review.
- Business/user intent: A user who triggers a targeted email sync must always eventually learn the outcome — success or failure — via the socket event. Today, if the worker hits an unhandled exception and exhausts its retries, the user gets silence forever with no indication the sync ever failed. Additionally, the single-thread sync endpoint still has the original event-loop-stall bug and should be consolidated onto the same enqueue+worker+socket path as the batch endpoint, rather than living on as a separate, divergent implementation.
- Non-goals:
  - Do NOT change the DB effects, thread-matching, or MIME parsing logic of the targeted sync core.
  - Do NOT introduce a generic "on-terminal-failure callback" mechanism into `worker_base.py` for all task types — scope the fix to this handler only, to avoid widening blast radius across every task type sharing the general worker.

## Scope

- In scope:
  1. Emit a `sync_success=False` socket event on unhandled/terminal failure in `handle_sync_email_threads_targeted.py` (the plan's own unmet mitigation).
  2. Decouple `sockets/worker_emitter.py` from the full `sio`/`AsyncRedisManager` construction in `sockets/__init__.py` by extracting room-naming helpers into a dependency-free module.
  3. Fix socket payload field precedence so the result dict's `connection_client_id` doesn't silently overwrite the originally-requested one when they differ in meaning.
  4. Decide and implement the live-role re-fetch question for worker-side authorization (see Clarifications).
  5. Consolidate `POST /{thread_id}/sync` (`services/commands/emails/sync_email_thread_targeted.py`) onto the same enqueue → `EMAIL_SYNC_TARGETED` task → worker handler → socket-event path as the batch endpoint, deleting the duplicate inline implementation instead of maintaining two sync code paths.
- Out of scope:
  - Automated test suite additions beyond what's needed to verify these specific fixes (full test coverage is a separate effort — codex's original summary already flagged "no automated tests" as a known gap).
  - The missing `INTENTION_email_sync_targeted_via_worker_20260706.md` file referenced by the original plan — not recreated retroactively; this plan gets its own intention doc going forward.
- Assumptions:
  - `worker_base.py`'s retry/backoff/timeout machinery is correct and does not need to change; the fix is additive (an except-block emit), not a restructuring of failure handling.
  - `WorkspaceMembership` → `WorkspaceRole` → `Role.name` is the authoritative live source of a user's role in a workspace, matching the resolution already done in `services/commands/auth/sign_in_user.py::build_auth_response`.
  - Confirmed by grep: `sync_email_thread_targeted.py`, `SyncThreadTargetedRequest`, and the `email.thread.sync_targeted` audit event have no callers/references outside the router and the command file itself — safe to consolidate/delete without breaking other call sites.
  - The batch core's existing thread-loading + per-connection authorization logic (`_load_threads` + the `by_connection` loop in `_sync_email_threads_targeted_core.py`) already reproduces the singular endpoint's authorization semantics when called with `thread_client_ids=[single_id]`: if no `connection_client_id` is given and the actor isn't a SELLER, the connection is derived from the thread's own `connection_id` and authorized via `assert_can_access_connection`, exactly matching `sync_email_thread_targeted.py::_resolve_thread_connection`'s non-SELLER branch.

## Clarifications required

- [ ] **Live role re-fetch vs. accept the stale-snapshot tradeoff.** The worker currently authorizes using `role_name` captured in the execution payload at enqueue time (a JWT-claims snapshot), not the actor's live role. If the user's role or workspace membership changes between enqueue and a retried execution (up to minutes later per `BACKOFF_SECONDS`), the worker checks against outdated permissions. Options:
  - **Option A (recommended):** Add a small helper (e.g. `services/commands/emails/_actor_role_resolver.py::resolve_live_role_name(session, user_id, workspace_id)`) that queries `WorkspaceMembership` (`user_id`, `workspace_id`, `is_active=True`) → `.workspace_role.role.name.value`, mirroring `build_auth_response`'s resolution. Call it in `execute_targeted_threads_sync` (or just before, in the handler) instead of trusting `task_payload.role_name`. Raise `PermissionDenied`/`NotFound` if membership is gone or inactive, which will surface via the new terminal-failure socket emit (item 1).
  - **Option B:** Accept the snapshot as a documented, deliberate tradeoff (matches how most background-job systems treat authorization — checked at submission time) and leave `role_name` in the payload as-is, just adding a code comment noting the tradeoff explicitly.
  - Decision needed before implementing item 4; default to Option A given this system already has a real live source of truth and the query cost is one extra indexed lookup per sync.

## Acceptance criteria

1. When `execute_targeted_threads_sync` (or anything else in the handler) raises, the handler emits `email.threads.synced` to the requesting user with `sync_success=False` and a populated `sync_error` before the exception propagates to `worker_base` for retry/failure handling — on every attempt that ultimately exhausts retries, the user receives exactly one such terminal event.
2. Retries that eventually succeed do NOT also emit a spurious failure event from an earlier failed attempt — only the final outcome (success or exhausted-retries failure) reaches the user.
3. `sockets/worker_emitter.py` no longer transitively imports or constructs `sio`/`socket_manager` (the full `AsyncServer` + non-write-only `AsyncRedisManager`) as a side effect of resolving a room name.
4. `sockets/manager.py`'s `ConnectionManager.user_room`/`workspace_room`/`conversation_room` continue to work unchanged for the web process (no behavior change there, only where the helper functions live).
5. The socket event payload's `connection_client_id` field reflects the sync result's actual connection scope, not a stale pre-overwrite value from the request payload; frontend-visible field semantics are unambiguous (single connection id when scoped to one, `None`/omitted when the batch spanned multiple).
6. Per the Clarification decision: either (Option A) the worker re-authorizes against a freshly queried live role and a revoked/changed membership now correctly produces a `PermissionDenied`-driven terminal failure event instead of proceeding with stale permissions, or (Option B) the tradeoff is explicitly documented in code.
7. `POST /{thread_id}/sync` returns an immediate enqueue acknowledgement (no IMAP call on the request path) after creating an `EMAIL_SYNC_TARGETED` execution task with `thread_client_ids=[thread_id]`, and a concurrent pure-DB request during that sync is unaffected — closing the same event-loop-stall class of bug the batch endpoint was originally fixed for.
8. The worker processes single-thread and batch-triggered tasks through the identical handler and core function, producing the same DB effects and the same `email.threads.synced` socket event (success or terminal-failure) the batch path already produces — no separate code path remains for the single-thread case.
9. `services/commands/emails/sync_email_thread_targeted.py` and `services/commands/emails/requests/sync_thread_targeted_request.py::SyncThreadTargetedRequest` are removed, with no remaining references anywhere in the codebase.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/.../16_background_jobs.md` / `51_worker_runtime.md`: reason — confirm the correct way to signal terminal failure outcomes from a handler without altering `worker_base`'s generic retry contract.
- `backend/docs/architecture/.../sockets/*.md` (if present): reason — confirm event-emission conventions for failure vs. success payloads.
- `backend/docs/architecture/.../06_commands.md` / local extension: reason — confirm authorization-check conventions if adding a live-role resolver (Option A).

### Local extensions loaded

- None expected.

### File read intent — pattern vs. relational

Relational reads already performed and sufficient — do not re-read broadly:
- `services/tasks/emails/handle_sync_email_threads_targeted.py` — the file being corrected (item 1, 3, 5).
- `services/commands/emails/_sync_email_threads_targeted_core.py` — where `execute_targeted_threads_sync` raises `DomainError`/other exceptions that need to reach the handler's new except block.
- `sockets/worker_emitter.py`, `sockets/manager.py`, `sockets/__init__.py` — the coupling being removed (item 2).
- `services/commands/auth/sign_in_user.py::build_auth_response` — the reference role-resolution logic to mirror if Option A is chosen.
- `models/tables/workspaces/workspace_membership.py`, `models/tables/roles/workspace_role.py`, `models/tables/roles/role.py` — exact fields for the live-role query (Option A).
- `routers/api_v1/email_threads.py` — the `/{thread_id}/sync` and `/sync-targeted` route definitions being consolidated (item 5).
- `services/commands/emails/sync_email_thread_targeted.py`, `services/commands/emails/requests/sync_thread_targeted_request.py` — the duplicate implementation being removed (item 5).
- `services/commands/emails/sync_email_threads_batch_targeted.py`, `services/commands/emails/requests/sync_thread_targeted_request.py::SyncThreadsBatchTargetedRequest` — the existing thin-enqueue command and request shape the single-thread route will delegate to.

### Skill selection

- Primary skill: n/a (targeted corrective edits to existing files from the prior plan).
- Router trigger terms: `socket emit failure, terminal failure event, room helper decoupling, live role resolution`.
- Excluded alternatives: generic worker-wide failure-hook framework — excluded per Non-goals (keep blast radius to this handler).

## Implementation plan

1. **Terminal failure emit (item 1, 2).** In `handle_sync_email_threads_targeted.py`, wrap the `async with session.begin(): result = await execute_targeted_threads_sync(...); await write_audit(...)` block in `try/except Exception as exc`. On exception: emit `email.threads.synced` to `task_payload.requested_by_user_id` with `{"task_client_id": task_client_id, **asdict(task_payload), "sync_success": False, "sync_error": str(exc)}` (no `result` dict available since the core never returned), then `raise` to preserve existing `worker_base` retry/backoff/timeout behavior. Ensure this emit happens only after the exception is caught at the **outermost** attempt — i.e., do NOT emit on every retry attempt, only let it fire per actual invocation (each worker attempt is a fresh handler call, so this naturally means each failed attempt emits once; acceptable per Acceptance Criterion 2 as long as retried-then-succeeded runs never also fire the earlier attempt's failure event, which is inherently true since failed attempts don't get to emit anything else afterward — confirm no queuing/dedup issue exists before considering this criterion met).
2. **Decouple room helpers (item 3, 4).** Create `sockets/rooms.py` with no `sio`/`AsyncRedisManager` imports, containing the three static room-naming functions (`user_room`, `workspace_room`, `conversation_room`) currently on `ConnectionManager`. Update `ConnectionManager` in `sockets/manager.py` to delegate to (or re-export) these functions so its public behavior is unchanged. Update `sockets/worker_emitter.py` to import `user_room` from `sockets/rooms.py` instead of `ConnectionManager` from `sockets/manager.py`, removing the transitive import of `sockets/__init__.py` from the worker process.
3. **Fix payload precedence (item 5).** In the socket emit call, spread `**result` before `**asdict(task_payload)` for fields where the payload's originally-requested value should win, OR — simpler and clearer — explicitly construct the emitted dict field-by-field instead of relying on dict-spread ordering, so `connection_client_id`'s source is unambiguous at the call site rather than implicit in spread order.
4. **Live role resolution (item 4, per Clarification decision).** If Option A: add `resolve_live_role_name(session, user_id, workspace_id)` querying `WorkspaceMembership` joined to `WorkspaceRole`/`Role`, filtered by `is_active=True`; call it at the top of `execute_targeted_threads_sync` (or in the handler before calling it) and use the returned role instead of `role_name` passed through the payload/request. Raise a clear domain error (caught by item 1's new except block) if no active membership is found. If Option B: add a one-line code comment on `SyncEmailThreadsTargetedPayload.role_name` documenting that authorization uses an enqueue-time snapshot by design.
5. **Consolidate the single-thread route (item 5).** In `routers/api_v1/email_threads.py`, change `sync_email_thread_targeted_route` (`POST /{thread_id}/sync`) to call `sync_email_threads_batch_targeted` instead of `sync_email_thread_targeted`, passing `{"thread_client_ids": [thread_id]}` as the incoming data (mirroring how `sync_email_threads_batch_targeted_route` already calls it with the request body). Delete `services/commands/emails/sync_email_thread_targeted.py` and `SyncThreadTargetedRequest` from `services/commands/emails/requests/sync_thread_targeted_request.py`, keeping only `SyncThreadsBatchTargetedRequest` in that module. Remove the now-unused `email.thread.sync_targeted` entry from `domain/emails/__init__.py`'s registered audit events (confirmed no other writer uses it). Note for whoever reviews this: the response shape for `POST /{thread_id}/sync` changes from thread-scoped sync stats (`thread_client_id`, `searched_rfc_message_id_count`, ...) to the enqueue acknowledgement (`enqueued`, `task_client_id`, `connection_client_id`) — this is a frontend-facing contract change on this route, same as the batch endpoint's original conversion, and must be coordinated with the frontend alongside the `email.threads.synced` socket event it now also relies on.

## Risks and mitigations

- Risk: Adding a `try/except Exception` around the sync core could accidentally swallow `asyncio.CancelledError` (e.g. from `asyncio.wait_for` timeout in `worker_base`) if not careful, breaking cooperative cancellation.
  Mitigation: Catch `Exception` only (not `BaseException`), and re-raise unconditionally after emitting — `CancelledError` in modern Python does not subclass `Exception`, so it will propagate untouched regardless; verify this explicitly in review.
- Risk: The new live-role query (Option A) adds a DB round-trip and a new failure mode (membership revoked mid-flight) to every targeted sync execution.
  Mitigation: Single indexed lookup (`user_id` + `workspace_id` are both indexed FKs on `WorkspaceMembership`); the new failure mode is exactly the gap being fixed, and now correctly surfaces as a terminal failure event instead of silently proceeding with stale trust.
- Risk: Extracting room helpers into `sockets/rooms.py` could break an import path some other file relies on (`ConnectionManager.user_room` used as a static method elsewhere).
  Mitigation: Keep `ConnectionManager.user_room` etc. as thin delegating wrappers (not removed), so no existing call site breaks; only `worker_emitter.py`'s import path changes.
- Risk: Consolidating `/{thread_id}/sync` onto the enqueue path is a breaking response-contract change for any frontend code still reading synchronous sync-result fields (`thread_client_id`, `searched_rfc_message_id_count`, etc.) from that endpoint's HTTP response.
  Mitigation: This mirrors the change already made and presumably coordinated for the batch endpoint; call it out explicitly to the user/frontend owner before merging (see implementation step 5's note). Do not merge silently.
- Risk: The single-thread route's authorization semantics could subtly differ from the batch core's derived-connection-from-thread logic in an edge case not covered by the Assumptions section (e.g. a thread whose `connection_id` no longer matches any live connection).
  Mitigation: Both paths already raise `DomainError`/`NotFound` in that case (confirmed by reading both implementations); validate explicitly with a thread pointing at a soft-deleted connection before considering item 5 done.

## Validation plan

- Static: `ruff check` (if available) + type check on all touched files.
- Unit/manual: force `execute_targeted_threads_sync` to raise (e.g. temporarily point a connection at a nonexistent id) and confirm exactly one `sync_success=False` socket event reaches a connected test client, and that the `ExecutionTask` still goes through its normal retry/backoff/FAIL lifecycle unaffected.
- Import isolation check: in a fresh Python process, `import beyo_manager.sockets.worker_emitter` and assert `beyo_manager.sockets` (the `__init__.py` module) has NOT been imported as a side effect (e.g. via `sys.modules` inspection) — proving the decoupling in item 2 worked.
- Live-role check (if Option A): deactivate a test user's `WorkspaceMembership` between enqueue and worker execution (or mock the timing) and confirm the worker now rejects with a terminal failure event rather than proceeding.
- Regression: re-run the original plan's validation steps (enqueue returns immediately, worker performs the same DB effects, concurrent DB request unaffected) to confirm no behavior regressed.
- Single-thread consolidation: call `POST /{thread_id}/sync`; assert an immediate enqueue-ack response and exactly one `EMAIL_SYNC_TARGETED` task created with `thread_client_ids=[thread_id]`; assert a concurrent pure-DB request during the sync returns immediately (same concurrency check as the batch endpoint originally required).
- Dead-code check: after deleting `sync_email_thread_targeted.py` and `SyncThreadTargetedRequest`, grep the codebase to confirm zero remaining references, and confirm the app still starts and the route table registers correctly.

## Review log

- `2026-07-06` `claude`: Drafted from a post-implementation review of `PLAN_email_sync_targeted_via_worker_20260706` — identified that the plan's own "emit on terminal failure" mitigation was not implemented, plus three smaller issues (socket-server coupling in the worker process, payload field precedence, stale-role authorization snapshot).
- `2026-07-06` `david`: Requested folding the sibling `POST /{thread_id}/sync` endpoint consolidation into this plan rather than tracking it separately; scope, acceptance criteria, implementation steps, risks, and validation updated accordingly. Confirmed via grep that the singular command/request/audit-event have no external callers, making a clean delete-and-delegate consolidation safe.
- `2026-07-06` `codex`: Implemented final-attempt failure emits, live role re-authorization, lazy socket server initialization, and single-thread route consolidation onto the existing `EMAIL_SYNC_TARGETED` worker path.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
