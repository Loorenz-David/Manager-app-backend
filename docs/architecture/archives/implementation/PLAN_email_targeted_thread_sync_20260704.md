# Targeted Email Thread Sync — Implementation Plan

**Date:** 2026-07-04  
**Feature:** Add targeted IMAP header-search sync for single and batch EmailThread refresh  
**Status:** archived  
**Last updated at (UTC):** 2026-07-04T15:15:00Z

---

## 1. Architecture Findings

### 1.1 What the codebase already provides

**Provider abstraction (`base.py`, `adapter.py`, `imap_reader.py`)**
- `EmailProviderProtocol` is a `Protocol` with three methods: `test_connection`, `send_email`, `sync_inbox`. There is no method for header-targeted IMAP search.
- `SmtpImapEmailProvider` delegates every call to `ImapReader` or `SmtpSender`. It is a pure pass-through.
- `ImapReader.sync()` is synchronous (uses stdlib `imaplib`) and wraps its own `try/except` returning a `SyncResult`. It opens one IMAP session per call, fetches by UID range, parses via `MimeParser`, and returns a `SyncResult(success, new_messages, new_last_seen_uid, new_uidvalidity)`.
- `SyncResult.new_messages` is a `list[InboundMessage]`. `InboundMessage` carries `provider_uid`, `provider_folder`, RFC threading headers, and parsed body.

**Models**
- `EmailMessage` already has `UniqueConstraint("connection_id", "provider_folder", "provider_uid", name="uq_email_message_provider_uid")` — present in both ORM and migration `aa10c8c7e006`. No migration needed.
- `rfc_message_id` on `EmailMessage` has only a non-unique index (`ix_email_messages_rfc_id`). No uniqueness constraint — correct, since the same RFC Message-ID can appear across two connections (forwarded messages). No migration needed.
- `EmailThread` exposes: `entity_type`, `entity_client_id`, `major_entity_type`, `major_entity_client_id`, `connection_id`.
- `EmailSyncState` must NOT be updated by targeted sync — it only advances during full batch sync.

**Message processing in handler**
- `handle_email_inbox_sync` contains an inline loop (lines 80–132) that: checks duplicate by `(connection_id, provider_folder, provider_uid)`, calls `find_or_create_thread`, inserts `EmailMessage`, updates thread timestamps. This loop is the exact code to extract as a shared function.

**Authorization pattern**
- `assert_can_access_connection(user_id, role_name, owner_user_id)` from `domain/emails/guards.py` covers admins, managers, and connection owners. Reuse for thread-level sync — no new guard needed.

**Transaction pattern**
- Commands use `async with maybe_begin(ctx.session)`. The handler uses `async with session.begin()` directly (task context).

**IMAP implementation note**
- `ImapReader` uses stdlib `imaplib` (synchronous). The UID SEARCH HEADER command is supported: `client.uid("SEARCH", "HEADER", "In-Reply-To", "<id>")`. Follow the same calling convention as in `sync()`.

### 1.2 No migration needed

`uq_email_message_provider_uid` constraint already exists. The `rfc_message_id` non-unique index is already present and sufficient for `find_or_create_thread` lookups.

---

## 2. Refactor: Shared Message-Processing Pipeline

### 2.1 What to extract

Lines 80–132 of `handle_email_inbox_sync` are the processing loop. Extract them verbatim into a standalone async function.

### 2.2 New file and function signature

**File:** `app/beyo_manager/services/infra/email_providers/message_processor.py`

```python
@dataclass
class ProcessResult:
    saved_count: int
    skipped_count: int         # duplicates by provider_uid
    new_thread_ids: set[str]   # thread client_ids that received a new message

async def process_inbound_messages(
    session: AsyncSession,
    workspace_id: str,
    connection: EmailConnection,
    inbound_messages: list[InboundMessage],
) -> ProcessResult:
```

- Body is identical to the current handler loop.
- `now = datetime.now(timezone.utc)` computed inside the function.
- Does NOT update `EmailSyncState` — that stays in `handle_email_inbox_sync`.
- Returns `ProcessResult` instead of a bare `saved` counter.
- Keeps the existing SELECT-before-INSERT duplicate check (not replaced with ON CONFLICT) to preserve per-message logging.

### 2.3 How the existing handler calls it

Replace lines 80–132 in `handle_email_inbox_sync` with:

```python
from beyo_manager.services.infra.email_providers.message_processor import process_inbound_messages

result = await process_inbound_messages(
    session=session,
    workspace_id=workspace_id,
    connection=connection,
    inbound_messages=sync_result.new_messages,
)
saved = result.saved_count
```

The `sync_state` update block below it stays unchanged in `handle_email_inbox_sync`.

---

## 3. Provider Abstraction Changes

### 3.1 New dataclass in `base.py`

Add `TargetedSyncResult` after the existing `SyncResult` dataclass:

```python
@dataclass
class TargetedSyncResult:
    success: bool
    messages: list[InboundMessage] = field(default_factory=list)
    matched_uid_count: int = 0
    error: str | None = None
```

### 3.2 New method in `EmailProviderProtocol`

Add to the Protocol body:

```python
async def search_by_header_ids(
    self,
    folder: str,
    rfc_message_ids: list[str],
) -> TargetedSyncResult: ...
```

### 3.3 New method on `ImapReader`

```python
MAX_IDS_PER_TARGETED_SYNC = 10   # module-level constant

def search_by_header_ids(
    self,
    folder: str,
    rfc_message_ids: list[str],
) -> TargetedSyncResult:
```

Implementation steps:

1. `socket.setdefaulttimeout(20)`, open one IMAP session, login, `select(folder)`. Return `TargetedSyncResult(success=False, error=...)` on failure; `logout` in `finally`.
2. Trim `rfc_message_ids` to last `MAX_IDS_PER_TARGETED_SYNC` elements.
3. For each `rfc_id`, issue TWO UID SEARCH calls:
   - `client.uid("SEARCH", "HEADER", "In-Reply-To", rfc_id)`
   - `client.uid("SEARCH", "HEADER", "References", rfc_id)`
   Parse each `search_data[0]` with the same pattern as `sync()`. Collect all UIDs into a `set[int]` (automatic dedup).
4. If no UIDs found: return `TargetedSyncResult(success=True, messages=[], matched_uid_count=0)`.
5. Fetch each UID: same `client.uid("FETCH", str(uid), "(UID BODY.PEEK[])")` pattern, same `_extract_body` helper, same `parser.parse(raw_bytes, uid, folder)` call.
6. Return `TargetedSyncResult(success=True, messages=parsed_messages, matched_uid_count=len(uid_set))`.
7. Wrap entire logic in `try/except Exception` returning `TargetedSyncResult(success=False, error=str(exc))`.

Add a fetch cap: `MAX_MESSAGES_PER_TARGETED_SYNC = 50` — take the last N UIDs if the set is larger, following the same pattern as `MAX_MESSAGES_PER_SYNC` in `sync()`.

### 3.4 Delegate in `SmtpImapEmailProvider` (`adapter.py`)

```python
async def search_by_header_ids(
    self,
    folder: str,
    rfc_message_ids: list[str],
) -> TargetedSyncResult:
    return self._imap.search_by_header_ids(folder, rfc_message_ids)
```

Import `TargetedSyncResult` from `base`.

---

## 4. New Command Files

### 4.1 Request models

**File:** `app/beyo_manager/services/commands/emails/requests/sync_thread_targeted_request.py`

```python
from pydantic import BaseModel, Field

class SyncThreadTargetedRequest(BaseModel):
    thread_client_id: str

class SyncThreadsBatchTargetedRequest(BaseModel):
    connection_client_id: str | None = None
    thread_client_ids: list[str] = Field(default_factory=list)
    entity_type: str | None = None
    entity_client_ids: list[str] = Field(default_factory=list)
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    max_threads: int = Field(default=50, ge=1, le=50)
```

### 4.2 Single targeted thread sync command

**File:** `app/beyo_manager/services/commands/emails/sync_email_thread_targeted.py`

**Function:** `async def sync_email_thread_targeted(ctx: ServiceContext) -> dict`

Logic:

1. Parse `SyncThreadTargetedRequest` from `ctx.incoming_data`.
2. `async with maybe_begin(ctx.session):`
3. Load `EmailThread` where `workspace_id == ctx.workspace_id` and `client_id == request.thread_client_id`. Raise `NotFound("Email thread not found.")` if absent.
4. Load `EmailConnection` where `client_id == thread.connection_id` and `deleted_at IS NULL`. Raise `NotFound("Email connection not found.")` if absent.
5. Call `assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)`.
6. Collect outbound `rfc_message_id` values: query `EmailMessage` where `thread_id == thread.client_id AND direction == "outbound" AND rfc_message_id IS NOT NULL`, ordered by `sent_or_received_at DESC`, limit `MAX_RFC_MESSAGE_IDS_PER_THREAD = 10`.
7. If list is empty: write audit with zero counts and return early with `sync_success=True`, all counts zero.
8. `provider = get_email_provider(connection)`. Call `await provider.search_by_header_ids(folder=connection.inbox_folder, rfc_message_ids=rfc_ids)`.
9. If `targeted_result.success is False`: write audit with `sync_success=False`, raise `DomainError(targeted_result.error)`.
10. Call `await process_inbound_messages(session, ctx.workspace_id, connection, targeted_result.messages)`.
11. Write audit event `"email.thread.sync_targeted"` (see Section 8).
12. Return response dict (see Section 6).

**Note on `inbox_folder`:** Check if `EmailConnection` stores the inbox folder name. If not, use `"INBOX"` as the default (same folder used by `EmailSyncState`). Alternatively, load the `EmailSyncState` for the connection and use `sync_state.folder` — this is the safer approach.

### 4.3 Batch targeted sync command

**File:** `app/beyo_manager/services/commands/emails/sync_email_threads_batch_targeted.py`

**Function:** `async def sync_email_threads_batch_targeted(ctx: ServiceContext) -> dict`

Logic:

1. Parse `SyncThreadsBatchTargetedRequest` from `ctx.incoming_data`.
2. `async with maybe_begin(ctx.session):`
3. Build thread-loading query with filters (all AND clauses):
   - Always: `workspace_id == ctx.workspace_id`
   - If `connection_client_id`: `connection_id == connection_client_id`
   - If `thread_client_ids` non-empty: `client_id IN thread_client_ids`
   - If `entity_type` and `entity_client_ids` non-empty: both filters applied
   - If `major_entity_type` and `major_entity_client_id`: both filters applied
   - Order by `last_message_at DESC NULLS LAST`, limit `request.max_threads`
4. If no threads: return all-zero batch summary.
5. For each unique `connection_id` among threads, load `EmailConnection` and call `assert_can_access_connection`. Any auth failure aborts the whole batch (not retryable per-thread).
6. Build map: `connection_id → (EmailConnection, list[EmailThread])`.
7. Per-connection loop:
   - For each thread: collect up to 10 outbound `rfc_message_id` values. If none, skip silently (not an error).
   - Union all `rfc_message_ids` for this connection into a single list (dedup at set level).
   - Load `EmailSyncState` for `connection.client_id` to get `folder`.
   - Call `await provider.search_by_header_ids(folder=sync_state.folder, rfc_message_ids=all_ids)`.
   - If `targeted_result.success is False`: mark all threads for this connection in `thread_errors`; continue to next connection.
   - Wrap `process_inbound_messages` in `try/except`; per-thread exceptions go to `thread_errors`, successful flushes are accumulated.
   - Accumulate totals: `total_matched_uid_count`, `total_fetched_count`, `total_created_count`, `total_existing_count`, `all_new_thread_ids`.
8. Write audit event `"email.threads.sync_targeted_batch"` (see Section 8).
9. Return batch response dict (see Section 6).

---

## 5. Router Changes

In `app/beyo_manager/routers/api_v1/email_threads.py`:

### 5.1 Single targeted sync

```
POST /api/v1/email-threads/{thread_id}/sync
```

```python
@router.post("/{thread_id}/sync")
async def sync_email_thread_targeted_route(
    thread_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(sync_email_thread_targeted, {"thread_client_id": thread_id}, claims, session)
```

### 5.2 Batch targeted sync

```
POST /api/v1/email-threads/sync-targeted
```

**CRITICAL — Route ordering:** Register `/sync-targeted` BEFORE any `/{thread_id}/...` routes. FastAPI evaluates routes in declaration order; if `/{thread_id}/sync` is declared first, the literal string `sync-targeted` would match as a `thread_id` value.

```python
class SyncTargetedBatchBody(BaseModel):
    connection_client_id: str | None = None
    thread_client_ids: list[str] = []
    entity_type: str | None = None
    entity_client_ids: list[str] = []
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    max_threads: int = 50

@router.post("/sync-targeted")
async def sync_email_threads_batch_targeted_route(
    body: SyncTargetedBatchBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(sync_email_threads_batch_targeted, body.model_dump(), claims, session)
```

Imports:
```python
from beyo_manager.services.commands.emails.sync_email_thread_targeted import sync_email_thread_targeted
from beyo_manager.services.commands.emails.sync_email_threads_batch_targeted import sync_email_threads_batch_targeted
```

---

## 6. Request/Response Schemas

**Single sync response dict:**
```
thread_client_id:               str
searched_rfc_message_id_count:  int
matched_uid_count:              int
fetched_message_count:          int
created_message_count:          int
existing_message_count:         int
sync_success:                   bool
sync_error:                     str | None
```

`fetched_message_count = len(targeted_result.messages)`, `created_message_count = process_result.saved_count`, `existing_message_count = process_result.skipped_count`.

**Batch sync response dict:**
```
requested_thread_count:         int
synced_thread_count:            int
searched_rfc_message_id_count:  int
matched_uid_count:              int
fetched_message_count:          int
created_message_count:          int
existing_message_count:         int
threads_with_new_messages:      list[str]
thread_errors:                  dict[str, str]
sync_success:                   bool
sync_error:                     str | None
```

---

## 7. Migration Needed

None. The `uq_email_message_provider_uid` unique constraint is already present in both ORM and migration `aa10c8c7e006`. No `rfc_message_id` uniqueness constraint is needed.

---

## 8. Audit Wiring

### 8.1 Single thread sync

```python
await write_audit(
    session=ctx.session,
    event="email.thread.sync_targeted",
    workspace_id=ctx.workspace_id,
    actor_user_id=ctx.user_id,
    resource_type="email_thread",
    resource_client_id=thread.client_id,
    detail={
        "connection_id": connection.client_id,
        "thread_client_id": thread.client_id,
        "searched_rfc_message_id_count": len(rfc_ids),
        "matched_uid_count": targeted_result.matched_uid_count,
        "fetched_message_count": len(targeted_result.messages),
        "created_message_count": process_result.saved_count,
        "existing_message_count": process_result.skipped_count,
        "sync_success": targeted_result.success,
        "sync_error": targeted_result.error,
    },
)
```

### 8.2 Batch sync

```python
await write_audit(
    session=ctx.session,
    event="email.threads.sync_targeted_batch",
    workspace_id=ctx.workspace_id,
    actor_user_id=ctx.user_id,
    resource_type="email_connection",
    resource_client_id=request.connection_client_id,
    detail={
        "requested_thread_count": len(threads),
        "synced_thread_count": synced_thread_count,
        "searched_rfc_message_id_count": total_searched_rfc_count,
        "matched_uid_count": total_matched_uid_count,
        "fetched_message_count": total_fetched_count,
        "created_message_count": total_created_count,
        "existing_message_count": total_existing_count,
        "threads_with_new_messages": list(all_new_thread_ids),
        "thread_errors": thread_errors,
        "sync_success": not bool(auth_error),
    },
)
```

Register events in `app/beyo_manager/domain/emails/__init__.py` (check existing `register_audited_events` call pattern and follow it).

---

## 9. Testing Plan

All tests are unit/service tests — no live mailbox required.

### 9.1 Unit tests for `ImapReader.search_by_header_ids`

File: `app/tests/unit/test_imap_reader_targeted_search.py`

- Single RFC ID: `In-Reply-To` returns UID 42, `References` returns UID 43 → deduped to {42, 43}; assert 2 SEARCH calls, `matched_uid_count=2`
- Same UID in both searches → deduped to 1 FETCH call, `matched_uid_count=1`
- Multiple RFC IDs: 2 IDs × 2 search types → 4 SEARCH calls, correct UID union
- `client.select()` returns `"NO"` → `TargetedSyncResult(success=False)`
- One SEARCH call returns `"NO"` → that call's UIDs silently skipped, others fetched
- One FETCH fails → that message skipped, others returned
- Empty search result (`b""`) → `TargetedSyncResult(success=True, matched_uid_count=0, messages=[])`
- Exception during login → `TargetedSyncResult(success=False, error=...)`
- `rfc_message_ids` list longer than `MAX_IDS_PER_TARGETED_SYNC` → trimmed to last 10; assert exactly 10 × 2 = 20 SEARCH calls

### 9.2 Unit tests for `process_inbound_messages`

File: `app/tests/unit/test_message_processor.py`

- New message not in DB → `saved_count=1`, `skipped_count=0`, thread created
- Duplicate message (same provider_uid) → `saved_count=0`, `skipped_count=1`
- Mix of 3 new + 2 duplicates → `saved_count=3`, `skipped_count=2`
- `new_thread_ids` contains only threads that received a new message
- `thread.last_message_at` updated only for new messages

### 9.3 Unit tests for `sync_email_thread_targeted`

File: `app/tests/unit/test_sync_email_thread_targeted.py`

- Thread not found → `NotFound` raised
- Connection not found → `NotFound` raised
- Permission denied → `PermissionDenied` raised
- No outbound messages → early return, all-zero counts, `sync_success=True`
- IMAP error → `DomainError` raised
- Normal flow: 2 RFC IDs → 1 new message → correct response dict
- Audit write called with `event="email.thread.sync_targeted"`

### 9.4 Unit tests for `sync_email_threads_batch_targeted`

File: `app/tests/unit/test_sync_email_threads_batch_targeted.py`

- No threads match filters → all-zero response, `sync_success=True`
- Auth error on connection → whole batch fails
- IMAP error on one connection → all threads for that connection in `thread_errors`, other connections succeed
- Threads across two connections → UIDs deduped per connection
- Thread with no outbound messages → silently skipped
- `threads_with_new_messages` contains only threads that got new messages
- `max_threads=50` honored on query limit
- Audit write called with `"email.threads.sync_targeted_batch"`

### 9.5 Router-level tests

File: `app/tests/unit/test_email_threads_router_sync.py`

- `POST /{thread_id}/sync` routes to `sync_email_thread_targeted`
- `POST /sync-targeted` does NOT match `/{thread_id}/...` pattern — literal `sync-targeted` routes correctly
- Unauthenticated → 401
- Insufficient role → 403

---

## 10. Manual QA Plan

Extend `tests/emails/test_email_live.py` with a targeted sync flow (add `--targeted` flag):

1. Sign in, create connection, send outbound email to external address; record `thread_id`.
2. Wait for manual reply.
3. `POST /api/v1/email-threads/{thread_id}/sync` → assert `sync_success=true`, `searched_rfc_message_id_count >= 1`, `matched_uid_count >= 1`, `created_message_count >= 1`.
4. `GET /api/v1/email-threads/{thread_id}/messages` → assert at least one `direction=inbound` message.
5. `POST /api/v1/email-threads/{thread_id}/sync` again (idempotency) → assert `created_message_count=0`, `existing_message_count` equals previous `created_message_count`.
6. `POST /api/v1/email-threads/sync-targeted` with `{"thread_client_ids": [thread_id]}` → assert aggregate counts match.
7. Delete connection.

---

## 11. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Route collision: `/sync-targeted` vs `/{thread_id}/...`** | Certain if ordering wrong | Register `POST /sync-targeted` before any `POST /{thread_id}/...` routes in the router file |
| **IMAP `SEARCH HEADER` case sensitivity** | Medium | Use exact RFC capitalization: `In-Reply-To` and `References`. Header name matching is case-insensitive per RFC 3501; header values are case-sensitive |
| **Message matches wrong thread** | Low | `find_or_create_thread` always validates via RFC ID matching — never forced assignment |
| **One IMAP session per batch call (not per thread)** | Correct design | Batch command unions all RFC IDs per connection and calls `search_by_header_ids` once per connection, not per thread |
| **IMAP session timeout for large batches** | Low | `MAX_MESSAGES_PER_TARGETED_SYNC = 50` cap in `search_by_header_ids`; 20-second socket timeout |
| **Handler refactor regression** | Low | Run existing email live test after extracting `process_inbound_messages` before adding new commands |
| **`rfc_message_id` angle brackets** | Low | `send_email.py` stores as `<ULID@host>`. IMAP SEARCH matches literal including brackets — correct |
| **Batch transaction partial failure** | Medium | Use `try/except` per thread in the batch loop; collect errors in `thread_errors`; `session.flush()` after each successful thread's adds. All flushes commit via `maybe_begin` at the end. SQLAlchemy does not auto-rollback partial flushes on non-flush exceptions |
| **`provider_uid` string cast** | Known — no risk | `process_inbound_messages` inherits `str(inbound.provider_uid)` cast from existing handler code |

---

## Implementation Order

1. Extract `process_inbound_messages` into `message_processor.py`; update `handle_email_inbox_sync` to call it. Run existing live test to verify no regression.
2. Add `TargetedSyncResult` to `base.py`; add `search_by_header_ids` to `EmailProviderProtocol`.
3. Implement `ImapReader.search_by_header_ids`; delegate in `SmtpImapEmailProvider`.
4. Add request models (`sync_thread_targeted_request.py`).
5. Implement `sync_email_thread_targeted` command.
6. Implement `sync_email_threads_batch_targeted` command.
7. Add router endpoints (mind ordering constraint).
8. Add unit tests.
9. Live QA with `--targeted` flag.
