# PLAN_email_batch_send_20260704

## Metadata

- Plan ID: `PLAN_email_batch_send_20260704`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T17:00:00Z`
- Last updated at (UTC): `2026-07-04T17:45:00Z`
- Related issue/ticket: n/a
- Intention plan: n/a

---

## Goal and intent

- **Goal:** Add a batch email send endpoint that accepts up to 200 targets in a single HTTP request, sends the same content to each target (each as an independent `EmailThread`), reuses one SMTP connection per window of 50, and returns per-target success/failure results.
- **Business/user intent:** Users need to send the same message to many recipients without making N sequential API calls. Each recipient gets their own tracked thread so inbound replies are routed individually. A future content-enrichment layer will interpolate per-target variables into the body.
- **Non-goals:** Content enrichment / variable interpolation (deferred). Background task execution for very large lists (deferred). Sending to an existing thread (use the existing reply endpoint for that). Modifying the existing single-send flow.

---

## Scope

- **In scope:**
  - New `POST /api/v1/email-threads/batch-send` route
  - New `send_email_batch` command
  - New `SendEmailBatchRequest` + `BatchEmailTarget` request models
  - New `send_batch` method on `SmtpSender` (reuses one SMTP session per window)
  - New `send_email_batch` method on `SmtpImapEmailProvider` and `EmailProviderProtocol`
  - New `BatchSendResult` dataclass in `base.py`
  - Internal windowing: splits targets into windows of 50 before hitting the SMTP connection
  - Per-target success/failure reporting in the response
  - Audit event `email.batch_sent`
  - Register audit event in `domain/emails/__init__.py`

- **Out of scope:**
  - Variable/template interpolation in body content
  - Background task execution
  - Reply to an existing thread in batch mode
  - Any changes to the existing `send_email` single-send command or route

- **Assumptions:**
  - All targets in a single batch request share the same `connection_client_id`, subject, text/html body, cc, and bcc.
  - Each target creates a fresh `EmailThread` (no reply threading).
  - SMTP connection failures during a window mark all remaining unsent targets in that window as failed; already-sent targets in the same window are retained.
  - DB records (`EmailThread`, `EmailMessage`) are always created regardless of SMTP send result, for audit purposes — matching existing single-send behavior.
  - No migration is required (no new columns or tables).

---

## Clarifications required

None. Proceeding with assumptions above.

---

## Acceptance criteria

1. `POST /api/v1/email-threads/batch-send` with 3 targets returns a response containing 3 result entries each with `thread_client_id`, `message_client_id`, `send_success`, `send_error`.
2. A request with 60 targets succeeds: first 50 sent via one SMTP session, next 10 via a second SMTP session. No target is sent twice.
3. If SMTP fails for one recipient (`SMTPRecipientsRefused`), that target's result has `send_success=false` and the rest complete successfully.
4. A request with more than 200 targets is rejected with HTTP 422.
5. A user sending from another user's connection is rejected with HTTP 403.
6. All threads and messages are persisted in the database, including those whose SMTP send failed.
7. One `email.batch_sent` audit event is written per request, containing `target_count`, `sent_count`, `failed_count`, `connection_id`.

---

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: baseline layered architecture — router → command → infra
- `architecture/04_context.md`: `ServiceContext` structure and how `incoming_data` + `session` flow into commands
- `architecture/05_errors.md`: error hierarchy — `NotFound`, `PermissionDenied`, `DomainError` and when to use each
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command function shape, `maybe_begin` transaction contract, `session.add` / `flush` rules, subordinate-command event rule
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: offset-based pagination (not relevant here but loaded as part of core set)
- `architecture/09_routers.md`: router handler wiring pattern, `_run` helper usage, route ordering rules
- `architecture/21_naming_conventions.md`: file, function, and variable naming rules
- `architecture/40_identity.md`: workspace isolation enforcement
- `architecture/41_user.md`: user context and role extraction from claims
- `architecture/42_event.md`: audit event writing contract (`write_audit`, detail shape, event name format)
- `architecture/48_presence.md`: core contract (always loaded)
- `architecture/08_domain.md`: domain guard pattern — guards live in `domain/<entity>/guards.py`, raise typed errors
- `architecture/15_testing.md`: test structure, mock patterns, session fixtures
- `architecture/22_batch_write.md`: bulk insert / batch write patterns — use `session.add` in loop with periodic `flush`; do not use `insert().values([...])` unless explicitly justified

### Local extensions loaded

- `architecture/06_commands_local.md`: `maybe_begin` detail — all DB reads + writes must be inside ONE `maybe_begin` from the start; reading before `maybe_begin` triggers SQLAlchemy 2.x autobegin → subordinate mode → no commit
- `architecture/07_queries_local.md`: offset pagination overrides cursor; always apply `workspace_id` filter

### File read intent — pattern vs. relational

Permitted reads (relational — understanding what exists):
- `send_email.py` — understand existing thread/message creation pattern and RFC header generation
- `send_email_request.py` — understand existing request shape to model the batch request correctly
- `smtp_sender.py` — understand current SMTP session lifecycle to design `send_batch`
- `email_thread.py` model — field names for `EmailThread` construction
- `guards.py` — exact guard function signatures

Prohibited reads (contract already covers these):
- Other command files to understand `session.add` / `flush` shape → `06_commands.md`
- Other router files to understand handler skeleton → `09_routers.md`

### Skill selection

- Primary skill: CRUD + command
- Router trigger terms: `batch-send`, `send_email_batch`
- Excluded alternatives: background job skill — deferred per non-goals

---

## Implementation plan

### Step 1 — New `BatchSendResult` dataclass in `base.py`

File: `app/beyo_manager/services/infra/email_providers/base.py`

Add after the existing `SendResult` dataclass:

```python
@dataclass
class BatchSendResult:
    results: list[SendResult] = field(default_factory=list)
```

Add `send_email_batch` to `EmailProviderProtocol`:

```python
async def send_email_batch(self, messages: list[OutboundMessage]) -> BatchSendResult: ...
```

---

### Step 2 — `send_batch` method on `SmtpSender`

File: `app/beyo_manager/services/infra/email_providers/smtp_imap/smtp_sender.py`

Add constants at module level:

```python
SMTP_BATCH_WINDOW_SIZE = 50
```

Add method:

```python
def send_batch(self, messages: list[OutboundMessage]) -> list[SendResult]:
    """
    Sends all messages over one SMTP session.
    Per-message SMTPRecipientsRefused / SMTPDataError are caught individually.
    Any connection-level failure marks all remaining messages as failed.
    """
    results: list[SendResult] = []
    smtp = None
    try:
        smtp = self._connect()
        smtp.login(self._username, self._password)
        for message in messages:
            try:
                mime_message = MimeBuilder().build(message)
                recipients = message.to_addresses + message.cc_addresses + message.bcc_addresses
                smtp.sendmail(message.from_address, recipients, mime_message.as_string())
                results.append(SendResult(success=True))
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
                results.append(SendResult(success=False, error=str(exc)))
    except Exception as exc:
        remaining = len(messages) - len(results)
        results.extend([SendResult(success=False, error=str(exc))] * remaining)
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass
    return results
```

Note: `smtplib` must be imported at the top if not already (it is already imported via `smtplib.SMTP_SSL` usage).

---

### Step 3 — `send_email_batch` on `SmtpImapEmailProvider`

File: `app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py`

Add import of `BatchSendResult` from `base`.

Add method:

```python
async def send_email_batch(self, messages: list[OutboundMessage]) -> BatchSendResult:
    return BatchSendResult(results=self._smtp.send_batch(messages))
```

---

### Step 4 — Request models

File: `app/beyo_manager/services/commands/emails/requests/send_email_batch_request.py`

```python
from pydantic import BaseModel, Field, field_validator


class BatchEmailTarget(BaseModel):
    to_addresses: list[str]
    entity_type: str | None = None
    entity_client_id: str | None = None
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    topic: str | None = None

    @field_validator("to_addresses")
    @classmethod
    def validate_recipients(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("to_addresses must contain at least one recipient.")
        return value


class SendEmailBatchRequest(BaseModel):
    connection_client_id: str
    targets: list[BatchEmailTarget] = Field(..., min_length=1, max_length=200)
    cc_addresses: list[str] = Field(default_factory=list)
    bcc_addresses: list[str] = Field(default_factory=list)
    subject: str
    text_body: str | None = None
    html_body: str | None = None
```

Validation rules:
- `targets`: 1–200 items (HTTP 422 outside that range via Pydantic)
- `subject`: required, non-empty string
- At least one of `text_body` / `html_body` is recommended but not enforced at request level (matches existing single-send behavior)

---

### Step 5 — `send_email_batch` command

File: `app/beyo_manager/services/commands/emails/send_email_batch.py`

```python
from datetime import datetime, timezone

from sqlalchemy import select
from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.commands.emails.requests.send_email_batch_request import (
    BatchEmailTarget,
    SendEmailBatchRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.registry import get_email_provider
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject
from beyo_manager.services.infra.email_providers.smtp_imap.smtp_sender import SMTP_BATCH_WINDOW_SIZE


async def send_email_batch(ctx: ServiceContext) -> dict:
    request = SendEmailBatchRequest.model_validate(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # Load and auth-check connection (once for the whole batch)
        connection_result = await ctx.session.execute(
            select(EmailConnection).where(
                EmailConnection.workspace_id == ctx.workspace_id,
                EmailConnection.client_id == request.connection_client_id,
                EmailConnection.deleted_at.is_(None),
            )
        )
        connection = connection_result.scalar_one_or_none()
        if connection is None:
            raise NotFound("Email connection not found.")

        assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)

        provider = get_email_provider(connection)
        now = datetime.now(timezone.utc)

        # Build OutboundMessages for all targets upfront (each gets unique rfc_message_id)
        outbound_messages: list[OutboundMessage] = []
        for target in request.targets:
            rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"
            outbound_messages.append(
                OutboundMessage(
                    from_address=connection.email_address,
                    from_name=connection.display_name,
                    to_addresses=target.to_addresses,
                    cc_addresses=request.cc_addresses,
                    bcc_addresses=request.bcc_addresses,
                    subject=request.subject,
                    text_body=request.text_body,
                    html_body=request.html_body,
                    rfc_message_id=rfc_message_id,
                    in_reply_to=None,
                    references=[],
                )
            )

        # Send in windows of SMTP_BATCH_WINDOW_SIZE (reuses one SMTP session per window)
        send_results = []
        for window_start in range(0, len(outbound_messages), SMTP_BATCH_WINDOW_SIZE):
            window = outbound_messages[window_start: window_start + SMTP_BATCH_WINDOW_SIZE]
            batch_result = await provider.send_email_batch(window)
            send_results.extend(batch_result.results)

        # Persist threads + messages for all targets (regardless of send result)
        response_results = []
        sent_count = 0
        failed_count = 0

        for target, outbound, send_result in zip(request.targets, outbound_messages, send_results):
            thread = EmailThread(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                entity_type=target.entity_type,
                entity_client_id=target.entity_client_id,
                major_entity_type=target.major_entity_type,
                major_entity_client_id=target.major_entity_client_id,
                topic=(target.topic or "")[:255] or None,
                subject_normalized=normalize_subject(request.subject),
                last_message_at=now,
            )
            ctx.session.add(thread)
            await ctx.session.flush()

            message = EmailMessage(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                thread_id=thread.client_id,
                direction=EmailMessageDirectionEnum.OUTBOUND.value,
                from_address=connection.email_address,
                from_name=connection.display_name,
                to_addresses_json=target.to_addresses,
                cc_addresses_json=request.cc_addresses,
                bcc_addresses_json=request.bcc_addresses,
                subject=request.subject,
                text_body=request.text_body,
                html_body=request.html_body,
                body_preview=(request.text_body or "")[:300] or None,
                rfc_message_id=outbound.rfc_message_id,
                in_reply_to=None,
                references_json=[],
                sent_or_received_at=now,
                created_by_user_id=ctx.user_id,
            )
            ctx.session.add(message)
            await ctx.session.flush()

            if send_result.success:
                sent_count += 1
            else:
                failed_count += 1

            response_results.append({
                "thread_client_id": thread.client_id,
                "message_client_id": message.client_id,
                "to_addresses": target.to_addresses,
                "send_success": send_result.success,
                "send_error": send_result.error,
            })

        await write_audit(
            session=ctx.session,
            event="email.batch_sent",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={
                "connection_id": connection.client_id,
                "target_count": len(request.targets),
                "sent_count": sent_count,
                "failed_count": failed_count,
            },
        )

    return {
        "requested_count": len(request.targets),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": response_results,
    }
```

**Transaction note (per `06_commands_local.md`):** All DB operations — including the connection load — are inside ONE `maybe_begin` from the start of the function. The SMTP sends happen inside this transaction, which is an acceptable trade-off for v1. The DB transaction hold time scales linearly with the number of SMTP sends; for 200 targets at ~0.5s per send, the worst case is ~100s. This is acceptable for a background-tolerant use case; a future upgrade can move SMTP to outside the transaction (Phase 1 = load+validate, Phase 2 = SMTP, Phase 3 = DB write).

---

### Step 6 — Register audit event

File: `app/beyo_manager/domain/emails/__init__.py`

Add `"email.batch_sent"` to the existing `register_audited_events` set:

```python
register_audited_events(
    {
        "email.thread.sync_targeted",
        "email.threads.sync_targeted_batch",
        "email.batch_sent",
    }
)
```

---

### Step 7 — Router

File: `app/beyo_manager/routers/api_v1/email_threads.py`

**Route ordering constraint (per `09_routers.md`):** `POST /batch-send` is a static segment. It must be declared **before** any `/{thread_id}/...` routes — otherwise FastAPI's route matching will capture `batch-send` as a thread_id value. The existing `POST /sync-targeted` is already declared before wildcard routes; add `POST /batch-send` immediately after it.

Add import:

```python
from beyo_manager.services.commands.emails.send_email_batch import send_email_batch
from beyo_manager.services.commands.emails.requests.send_email_batch_request import (
    SendEmailBatchRequest,
)
```

Add route (after `/sync-targeted`, before `GET ""`):

```python
@router.post("/batch-send")
async def batch_send_email_route(
    body: SendEmailBatchRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(send_email_batch, body.model_dump(), claims, session)
```

`SendEmailBatchRequest` is used directly as the FastAPI body model (same pattern as `SyncThreadsBatchTargetedRequest` after the review fix), so HTTP 422 validation applies at the FastAPI level.

---

## Response shape

```json
{
  "requested_count": 3,
  "sent_count": 2,
  "failed_count": 1,
  "results": [
    {
      "thread_client_id": "eth_01J...",
      "message_client_id": "ema_01J...",
      "to_addresses": ["alice@example.com"],
      "send_success": true,
      "send_error": null
    },
    {
      "thread_client_id": "eth_01J...",
      "message_client_id": "ema_01J...",
      "to_addresses": ["bob@example.com"],
      "send_success": true,
      "send_error": null
    },
    {
      "thread_client_id": "eth_01J...",
      "message_client_id": "ema_01J...",
      "to_addresses": ["bad@invalid"],
      "send_success": false,
      "send_error": "{'bad@invalid': (550, b'No such user')}"
    }
  ]
}
```

---

## Risks and mitigations

- **Risk:** DB transaction held open across all SMTP sends. For 200 targets at 0.5s/send = ~100s transaction hold. Postgres default `idle_in_transaction_session_timeout` will terminate connections exceeding the configured value.
  **Mitigation:** v1 cap is 200 targets. Note in code that SMTP should move outside the transaction in a follow-up. For very large use cases, migrate to background task pattern.

- **Risk:** SMTP connection drops mid-window. `SmtpSender.send_batch` catches the exception and marks remaining messages in that window as failed. However, the DB records for those targets are still created (this is intentional — matching existing behavior).
  **Mitigation:** Per-target `send_success=false` + `send_error` in response. Caller can retry failed targets.

- **Risk:** `smtp.quit()` not called if exception escapes before the `finally` block runs. 
  **Mitigation:** `finally` block with `try/except` around `smtp.quit()` is mandatory in `send_batch`.

- **Risk:** Route ordering — `POST /batch-send` captured by `/{thread_id}/...` if declared in wrong position.
  **Mitigation:** Explicitly position after `/sync-targeted` and before `GET ""` in the router file.

- **Risk:** `SendEmailBatchRequest` has `targets` with `max_length=200` which is validated by Pydantic at the FastAPI layer. However the internal windowing constant (`SMTP_BATCH_WINDOW_SIZE = 50`) is in `smtp_sender.py`. If those two values drift (someone raises the Pydantic limit without updating the window size), nothing breaks — windowing just runs more iterations.
  **Mitigation:** Single source of truth: document that `max_length=200` on `targets` is the HTTP cap, and `SMTP_BATCH_WINDOW_SIZE` controls how many are sent per SMTP session. Both can be tuned independently.

- **Risk:** Each target flushes the session twice (thread + message). For 200 targets this is 400 flushes. Postgres handles this efficiently, but it is redundant since we commit once at the end.
  **Mitigation:** The flush pattern is required by `06_commands_local.md` to make the PK available for the next insert that references it (thread_id on EmailMessage). This is correct and expected.

---

## Validation plan

- `python3 -m compileall app/beyo_manager/services/commands/emails/send_email_batch.py app/beyo_manager/services/infra/email_providers/smtp_imap/smtp_sender.py app/beyo_manager/services/infra/email_providers/smtp_imap/adapter.py app/beyo_manager/services/infra/email_providers/base.py app/beyo_manager/routers/api_v1/email_threads.py`: no output (clean compile)
- `POST /api/v1/email-threads/batch-send` with 1 target and valid credentials: HTTP 200 with `sent_count=1`, thread and message visible in DB
- `POST /api/v1/email-threads/batch-send` with 201 targets: HTTP 422 (Pydantic max_length enforcement)
- `POST /api/v1/email-threads/batch-send` with 0 targets: HTTP 422
- `POST /api/v1/email-threads/batch-send` from a user who does not own the connection: HTTP 403
- `POST /api/v1/email-threads/batch-send` to a non-existent connection: HTTP 404
- `POST /api/v1/email-threads/batch-send` with 60 targets (verify 2 SMTP sessions via logs)
- Idempotency: calling again with the same payload creates new threads (no dedup — each call is an independent send)

---

## Review log

- `2026-07-04`: Implemented the batch send flow with a new `send_email_batch` command, `POST /api/v1/email-threads/batch-send` route, request models, SMTP batch windowing, provider support, audit registration, and focused unit coverage for the sender and command paths.
- Validation completed with `python3 -m compileall` over the touched email modules and `PYTHONPATH=app app/.venv/bin/python -m pytest tests/emails/test_email_batch_send.py tests/emails/test_smtp_sender_batch.py tests/emails/test_email_core.py` using temporary test env values for required settings.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
