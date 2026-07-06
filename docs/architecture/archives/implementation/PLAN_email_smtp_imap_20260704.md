# PLAN_email_smtp_imap_20260704

## Metadata

- Plan ID: `PLAN_email_smtp_imap_20260704`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T14:30:00Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/email_implementation.txt`

---

## Goal and intent

- **Goal:** Add a provider-agnostic SMTP/IMAP email integration to the backend. Users connect their own mailbox (per-user connections), can send outbound emails, trigger inbox syncs, and view threaded email conversations linked to Tasks, Cases, Customers, or standalone.
- **Business/user intent:** Allow workspace users to send and receive customer emails without leaving the app, with full reply-threading and per-user unread tracking.
- **Non-goals:** Gmail API adapter, Microsoft Graph adapter, IMAP IDLE / continuous background polling, email attachments (beyond metadata), rich HTML editor, shared mailbox delegation, open/click tracking, full sent-folder sync.

---

## Scope

**In scope:**
- `EmailConnection` model (per-user SMTP/IMAP credentials, encrypted at rest)
- `EmailSyncState` model (IMAP cursor per connection)
- `EmailThread` model (polymorphic link to Task/Case/Customer or standalone, with free-text `topic` field)
- `EmailThreadTopicPreset` model (global lookup table of predefined topic options for frontend suggestions)
- `EmailMessage` model (normalized inbound + outbound)
- `EmailThreadUserState` model (per-user read state)
- Field-level Fernet encryption module (`services/infra/crypto/field_encryption.py`)
- `SmtpImapEmailProvider` adapter following the `upholstery_providers` pattern
- 7 commands: create/update/delete/test connection, send email, sync connection, mark thread read
- 6 queries: list connections, get thread, list messages, list threads, get unread counts, list topic presets
- New `TaskType.EMAIL_INBOX_SYNC` + worker handler
- 2 new router files registered in `routers/api_v1/__init__.py`
- Alembic migrations for all 6 new tables
- Audit events for connection lifecycle and email send/sync-failure
- Unit tests for MimeBuilder, MimeParser, ReplyMatcher, guards, field_encryption
- Integration tests for create_connection, send_email, sync flow, mark_read, unread counts

**Out of scope:** (do not implement even if convenient)
- Gmail API / Microsoft Graph adapters
- IMAP IDLE or scheduled background polling
- Email attachments stored to file storage
- Email templates
- Shared mailboxes or team assignment
- Socket push events for email (leave for later)
- Full sent-folder sync

**Assumptions:**
- `cryptography` package is already installed (used for `pywebpush` VAPID — confirm in requirements.txt before importing Fernet)
- PostgreSQL is the database (JSONB columns are safe to use)
- The `users` table PK is `client_id` (string, prefixed ULID)
- The `workspaces` table PK is `client_id` (string, prefixed ULID)
- The `tasks` table PK is `client_id` (string, prefix `tsk`)
- The `cases` table PK is `client_id` (string, prefix `ca`)
- The `customers` table PK is `client_id` (string, prefix `cus`)

---

## Clarifications required

All clarifications resolved before plan was written. No open questions.

---

## Acceptance criteria

1. `POST /api/v1/email-connections` creates a connection with encrypted credentials; neither the request body nor the response ever contains `smtp_password` or `imap_password` in plaintext or encrypted form.
2. `POST /api/v1/email-connections/{id}/test` returns `{"reachable": true}` when SMTP + IMAP credentials are valid, without committing any DB record.
3. `POST /api/v1/email-threads/{thread_id}/send` stores an outbound `EmailMessage` with a valid RFC Message-ID and returns the thread + message `client_id`.
3a. `POST /api/v1/email-threads/send` with `topic: "Delivery coordination"` creates a new `EmailThread` where `thread.topic == "Delivery coordination"`.
3b. `GET /api/v1/email-threads/topic-presets` returns all 6 seeded presets ordered by `sort_order` ASC with no auth required beyond a valid JWT.
4. `POST /api/v1/email-connections/{id}/sync` enqueues a `TaskType.EMAIL_INBOX_SYNC` execution task (visible in `execution_tasks` table) and returns the current `EmailSyncState` snapshot — it does NOT block on IMAP.
5. After the worker processes `EMAIL_INBOX_SYNC`, new inbound messages appear in `email_messages` and their `thread_id` is set correctly (by In-Reply-To / References matching or new thread creation).
6. `GET /api/v1/email-threads/{thread_id}/messages` returns messages ordered by `sent_or_received_at ASC` with offset pagination.
7. `POST /api/v1/email-threads/{thread_id}/read` upserts `email_thread_user_states` row for `(thread_id, user_id)` and updates `last_read_at`.
8. `GET /api/v1/email-connections/{id}/threads/unread-count` returns the count of threads where `last_inbound_message_at > user_state.last_read_at` (or `user_state` does not exist).
9. Accessing another user's connection as SELLER raises `PermissionDenied`. ADMIN/MANAGER can pass `?owner_user_id=` to view another user's connections.
10. All migrations are reversible (`alembic downgrade -1` works for each).

---

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/01_architecture.md`: layer map, hard import rules
- `backend/docs/architecture/03_models.md`: ORM conventions, IdentityMixin, indexes
- `backend/docs/architecture/04_context.md`: ServiceContext structure
- `backend/docs/architecture/05_errors.md`: error hierarchy, DomainError
- `backend/docs/architecture/06_commands.md`: command structure, transaction boundary
- `backend/docs/architecture/07_queries.md`: query structure, pagination
- `backend/docs/architecture/08_domain.md`: pure domain logic rules
- `backend/docs/architecture/09_routers.md`: router handler pattern
- `backend/docs/architecture/11_infra_events.md`: event bus, dispatch timing
- `backend/docs/architecture/21_naming_conventions.md`: file/class/enum naming
- `backend/docs/architecture/30_migrations.md`: Alembic, zero-downtime patterns
- `backend/docs/architecture/40_identity.md`: IdentityMixin, prefixed ULID PKs
- `backend/docs/architecture/42_event.md`: ExecutionTask / event record pattern

### Local extensions loaded

- `backend/docs/architecture/06_commands_local.md`: `maybe_begin()` replaces `session.begin()` for all commands
- `backend/docs/architecture/07_queries_local.md`: offset-based pagination (NOT cursor) — `limit` default 50 max 200, `offset` default 0

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

**Prohibited (pattern reads — contract already covers these):**
- Reading another command to understand `session.add` / `flush` / error-raising → use `06_commands.md`
- Reading another router to understand the `_run` helper wiring → use `09_routers.md`
- Reading another serializer to understand dict output shape → use `07_queries.md`
- Reading `maybe_begin` source — it is fully documented in `06_commands_local.md`

**Permitted (relational reads — understanding what exists):**
- Reading `models/tables/tasks/task.py` to get the exact FK field name on Task
- Reading `models/tables/cases/case.py` to get the exact FK field name on Case
- Reading `models/tables/customers/customer.py` to get exact field names
- Reading `models/__init__.py` to confirm import order before appending lines
- Reading `domain/execution/enums.py` to confirm existing `TaskType` values before adding `EMAIL_INBOX_SYNC`
- Reading `workers/tasks_worker.py` (or equivalent) to find where handler map is registered
- Reading `routers/api_v1/__init__.py` to find insertion point for new router lines

---

## Implementation plan

Deliver in **10 sequential commits**. Each commit must leave the app in a runnable state. Do not skip steps or reorder phases.

---

### Commit 1 — Crypto module + config

**Files to create:**

**`app/beyo_manager/services/infra/crypto/__init__.py`** — empty file.

**`app/beyo_manager/services/infra/crypto/field_encryption.py`:**
```python
from cryptography.fernet import Fernet
from beyo_manager.config import settings


def encrypt_field(plaintext: str) -> str:
    """Encrypt a plaintext string for storage. Returns a URL-safe base64 token."""
    key = _get_key()
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a stored token back to plaintext."""
    key = _get_key()
    return Fernet(key).decrypt(ciphertext.encode()).decode()


def _get_key() -> bytes:
    if not settings.field_encryption_key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set in environment config.")
    return settings.field_encryption_key.encode()
```

**`app/beyo_manager/config.py` — add one field** inside the existing `Settings` class, after `reset_secret`:
```python
field_encryption_key: str | None = Field(default=None, alias="FIELD_ENCRYPTION_KEY")
```

**`.env.example` — add one line** (wherever other secrets are listed):
```
FIELD_ENCRYPTION_KEY=  # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Verification:** `from beyo_manager.services.infra.crypto.field_encryption import encrypt_field, decrypt_field` imports without error. `decrypt_field(encrypt_field("hello")) == "hello"` is true.

---

### Commit 2 — Domain layer (enums, guards)

**Files to create:**

**`app/beyo_manager/domain/emails/__init__.py`** — empty file.

**`app/beyo_manager/domain/emails/enums.py`:**
```python
import enum


class EmailProviderTypeEnum(str, enum.Enum):
    SMTP_IMAP = "smtp_imap"


class EmailConnectionStatusEnum(str, enum.Enum):
    ACTIVE      = "active"
    DISABLED    = "disabled"
    AUTH_FAILED = "auth_failed"
    ERROR       = "error"


class EmailSecurityEnum(str, enum.Enum):
    SSL      = "ssl"
    STARTTLS = "starttls"
    NONE     = "none"


class EmailMessageDirectionEnum(str, enum.Enum):
    INBOUND  = "inbound"
    OUTBOUND = "outbound"


class EmailThreadEntityTypeEnum(str, enum.Enum):
    TASK     = "task"
    CASE     = "case"
    CUSTOMER = "customer"
```

**`app/beyo_manager/domain/emails/guards.py`:**
```python
from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.routers.utils.roles import ADMIN, MANAGER


def assert_can_access_connection(
    ctx_user_id: str,
    ctx_role_name: str,
    connection_owner_user_id: str,
) -> None:
    """Raise PermissionDenied if the caller cannot access this connection."""
    if ctx_user_id == connection_owner_user_id:
        return
    if ctx_role_name in (ADMIN, MANAGER):
        return
    raise PermissionDenied("You do not have access to this email connection.")


def assert_can_send_from_connection(
    ctx_user_id: str,
    connection_owner_user_id: str,
) -> None:
    """Only the connection owner may send from it."""
    if ctx_user_id != connection_owner_user_id:
        raise PermissionDenied("You can only send from your own email connections.")


def is_connection_active(status: EmailConnectionStatusEnum) -> bool:
    return status == EmailConnectionStatusEnum.ACTIVE
```

---

**`app/beyo_manager/domain/emails/serializers.py`:**

Pure functions — no I/O, no ORM calls, no imports from `models/` or `services/`. Imported by queries and used as the single source of truth for response shapes.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beyo_manager.models.tables.emails.email_connection import EmailConnection
    from beyo_manager.models.tables.emails.email_message import EmailMessage
    from beyo_manager.models.tables.emails.email_thread import EmailThread
    from beyo_manager.models.tables.emails.email_thread_topic_preset import EmailThreadTopicPreset
    from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState


def serialize_email_thread(
    thread: "EmailThread",
    user_state: "EmailThreadUserState | None" = None,
) -> dict:
    """
    Fields returned (all string/ISO/bool — no ORM objects):
      client_id, workspace_id, connection_id,
      entity_type, entity_client_id,
      major_entity_type, major_entity_client_id,
      topic, subject_normalized,
      last_message_at (ISO or None),
      last_inbound_message_at (ISO or None),
      created_at (ISO), updated_at (ISO or None),
      is_unread (bool),
      user_state (dict or None — see serialize_email_thread_user_state).

    is_unread logic:
      if user_state is None:
          is_unread = thread.last_inbound_message_at is not None
      elif thread.last_inbound_message_at is None:
          is_unread = False
      elif user_state.last_read_at is None:
          is_unread = True
      else:
          is_unread = thread.last_inbound_message_at > user_state.last_read_at
    """
    is_unread: bool
    if user_state is None:
        is_unread = thread.last_inbound_message_at is not None
    elif thread.last_inbound_message_at is None:
        is_unread = False
    elif user_state.last_read_at is None:
        is_unread = True
    else:
        is_unread = thread.last_inbound_message_at > user_state.last_read_at

    return {
        "client_id":                 thread.client_id,
        "workspace_id":              thread.workspace_id,
        "connection_id":             thread.connection_id,
        "entity_type":               thread.entity_type,
        "entity_client_id":          thread.entity_client_id,
        "major_entity_type":         thread.major_entity_type,
        "major_entity_client_id":    thread.major_entity_client_id,
        "topic":                     thread.topic,
        "subject_normalized":        thread.subject_normalized,
        "last_message_at":           thread.last_message_at.isoformat() if thread.last_message_at else None,
        "last_inbound_message_at":   thread.last_inbound_message_at.isoformat() if thread.last_inbound_message_at else None,
        "created_at":                thread.created_at.isoformat(),
        "updated_at":                thread.updated_at.isoformat() if thread.updated_at else None,
        "is_unread":                 is_unread,
        "user_state":                serialize_email_thread_user_state(user_state) if user_state else None,
    }


def serialize_email_thread_user_state(state: "EmailThreadUserState") -> dict:
    return {
        "thread_id":    state.thread_id,
        "user_id":      state.user_id,
        "last_read_at": state.last_read_at.isoformat() if state.last_read_at else None,
        "muted_at":     state.muted_at.isoformat()     if state.muted_at     else None,
        "archived_at":  state.archived_at.isoformat()  if state.archived_at  else None,
    }


def serialize_email_message(message: "EmailMessage") -> dict:
    """
    Fields returned:
      client_id, workspace_id, connection_id, thread_id,
      direction ("inbound" | "outbound"),
      provider_folder (str or None), provider_uid (str or None),
      from_address, from_name (str or None),
      to_addresses_json (list or None),
      cc_addresses_json (list or None),
      bcc_addresses_json (list or None),
      subject (str or None),
      text_body (str or None),
      html_body (str or None),
      body_preview (str or None),
      rfc_message_id (str or None),
      in_reply_to (str or None),
      references_json (list or None),
      tracking_token (str or None),
      sent_or_received_at (ISO or None),
      created_by_user_id (str or None),
      created_at (ISO).

    NEVER include raw_headers_json — it is internal and may contain sensitive header data.
    """
    return {
        "client_id":           message.client_id,
        "workspace_id":        message.workspace_id,
        "connection_id":       message.connection_id,
        "thread_id":           message.thread_id,
        "direction":           message.direction,
        "provider_folder":     message.provider_folder,
        "provider_uid":        message.provider_uid,
        "from_address":        message.from_address,
        "from_name":           message.from_name,
        "to_addresses_json":   message.to_addresses_json,
        "cc_addresses_json":   message.cc_addresses_json,
        "bcc_addresses_json":  message.bcc_addresses_json,
        "subject":             message.subject,
        "text_body":           message.text_body,
        "html_body":           message.html_body,
        "body_preview":        message.body_preview,
        "rfc_message_id":      message.rfc_message_id,
        "in_reply_to":         message.in_reply_to,
        "references_json":     message.references_json,
        "tracking_token":      message.tracking_token,
        "sent_or_received_at": message.sent_or_received_at.isoformat() if message.sent_or_received_at else None,
        "created_by_user_id":  message.created_by_user_id,
        "created_at":          message.created_at.isoformat(),
        # raw_headers_json intentionally omitted
    }


def serialize_email_thread_topic_preset(preset: "EmailThreadTopicPreset") -> dict:
    return {
        "client_id":  preset.client_id,
        "label":      preset.label,
        "sort_order": preset.sort_order,
    }


def serialize_email_connection(c: "EmailConnection") -> dict:
    """
    NEVER include smtp_password_encrypted or imap_password_encrypted.
    Used by both create_email_connection command and list_email_connections query.
    """
    return {
        "client_id":      c.client_id,
        "workspace_id":   c.workspace_id,
        "owner_user_id":  c.owner_user_id,
        "email_address":  c.email_address,
        "display_name":   c.display_name,
        "provider_type":  c.provider_type,
        "status":         c.status,
        "smtp_host":      c.smtp_host,
        "smtp_port":      c.smtp_port,
        "smtp_security":  c.smtp_security,
        "smtp_username":  c.smtp_username,
        "imap_host":      c.imap_host,
        "imap_port":      c.imap_port,
        "imap_security":  c.imap_security,
        "imap_username":  c.imap_username,
        "inbox_folder":   c.inbox_folder,
        "last_error":     c.last_error,
        "created_at":     c.created_at.isoformat(),
        "updated_at":     c.updated_at.isoformat() if c.updated_at else None,
        # smtp_password_encrypted intentionally omitted
        # imap_password_encrypted intentionally omitted
    }
```

---

### Commit 3 — Models

Create directory `app/beyo_manager/models/tables/emails/` with the files below.

**`app/beyo_manager/models/tables/emails/__init__.py`** — empty file.

---

**`app/beyo_manager/models/tables/emails/email_connection.py`:**
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailConnection(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ecn"
    __tablename__ = "email_connections"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )
    owner_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False, index=True
    )

    email_address:  Mapped[str]       = mapped_column(String(255), nullable=False)
    display_name:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type:  Mapped[str]       = mapped_column(String(32),  nullable=False)
    status:         Mapped[str]       = mapped_column(String(32),  nullable=False, index=True)

    smtp_host:               Mapped[str]       = mapped_column(String(255), nullable=False)
    smtp_port:               Mapped[int]       = mapped_column(Integer,     nullable=False)
    smtp_security:           Mapped[str]       = mapped_column(String(16),  nullable=False)
    smtp_username:           Mapped[str]       = mapped_column(String(255), nullable=False)
    smtp_password_encrypted: Mapped[str]       = mapped_column(String(512), nullable=False)

    imap_host:               Mapped[str]       = mapped_column(String(255), nullable=False)
    imap_port:               Mapped[int]       = mapped_column(Integer,     nullable=False)
    imap_security:           Mapped[str]       = mapped_column(String(16),  nullable=False)
    imap_username:           Mapped[str]       = mapped_column(String(255), nullable=False)
    imap_password_encrypted: Mapped[str]       = mapped_column(String(512), nullable=False)

    inbox_folder: Mapped[str]       = mapped_column(String(128), nullable=False, default="INBOX", server_default="INBOX")
    last_error:   Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    deleted_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sync_state: Mapped["EmailSyncState"] = relationship("EmailSyncState", back_populates="connection", uselist=False, lazy="raise")
```

---

**`app/beyo_manager/models/tables/emails/email_sync_state.py`:**
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailSyncState(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "esyn"
    __tablename__ = "email_sync_states"

    connection_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("email_connections.client_id"), nullable=False, unique=True, index=True
    )

    folder:       Mapped[str]       = mapped_column(String(128), nullable=False, default="INBOX", server_default="INBOX")
    uidvalidity:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_uid: Mapped[int]      = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error:   Mapped[str | None] = mapped_column(String(512), nullable=True)

    last_sync_at:            Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    connection: Mapped["EmailConnection"] = relationship("EmailConnection", back_populates="sync_state", lazy="raise")
```

---

**`app/beyo_manager/models/tables/emails/email_thread.py`:**
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailThread(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "eth"
    __tablename__ = "email_threads"
    __table_args__ = (
        Index("ix_email_threads_entity", "entity_type", "entity_client_id"),
        Index("ix_email_threads_major_entity", "major_entity_type", "major_entity_client_id"),
    )

    workspace_id:  Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(64), ForeignKey("email_connections.client_id"), nullable=False, index=True)

    # Polymorphic entity link (mirrors NotificationPin pattern exactly)
    entity_type:       Mapped[str | None] = mapped_column(String(64),  nullable=True, index=True)
    entity_client_id:  Mapped[str | None] = mapped_column(String(128), nullable=True)
    major_entity_type:       Mapped[str | None] = mapped_column(String(64),  nullable=True)
    major_entity_client_id:  Mapped[str | None] = mapped_column(String(128), nullable=True)

    subject_normalized: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Free-text topic set by the sender at thread creation time.
    # e.g. "Delivery coordination", "Repair status update".
    # Frontend shows preset suggestions from email_thread_topic_presets but any string is valid.
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_message_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_inbound_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    messages:    Mapped[list["EmailMessage"]]         = relationship("EmailMessage",         back_populates="thread", lazy="raise")
    user_states: Mapped[list["EmailThreadUserState"]] = relationship("EmailThreadUserState", back_populates="thread", lazy="raise")
```

---

**`app/beyo_manager/models/tables/emails/email_message.py`:**
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailMessage(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "emsg"
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint("connection_id", "provider_folder", "provider_uid", name="uq_email_message_provider_uid"),
        Index("ix_email_messages_rfc_id", "rfc_message_id"),
        Index("ix_email_messages_thread_time", "thread_id", "sent_or_received_at"),
    )

    workspace_id:  Mapped[str] = mapped_column(String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(64), ForeignKey("email_connections.client_id"), nullable=False, index=True)
    thread_id:     Mapped[str] = mapped_column(String(64), ForeignKey("email_threads.client_id"), nullable=False, index=True)

    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # "inbound" | "outbound"

    provider_folder: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_uid:    Mapped[int | None] = mapped_column(String(32),  nullable=True)  # IMAP UID as string

    from_address: Mapped[str]       = mapped_column(String(255), nullable=False)
    from_name:    Mapped[str | None] = mapped_column(String(255), nullable=True)

    to_addresses_json:  Mapped[list | None] = mapped_column(JSONB, nullable=True)
    cc_addresses_json:  Mapped[list | None] = mapped_column(JSONB, nullable=True)
    bcc_addresses_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    subject:      Mapped[str | None] = mapped_column(String(512), nullable=True)
    text_body:    Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body:    Mapped[str | None] = mapped_column(Text, nullable=True)
    body_preview: Mapped[str | None] = mapped_column(String(300), nullable=True)

    rfc_message_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    in_reply_to:    Mapped[str | None] = mapped_column(String(512), nullable=True)
    references_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tracking_token: Mapped[str | None] = mapped_column(String(128), nullable=True)

    raw_headers_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    sent_or_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id:  Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="messages", lazy="raise")
```

---

**`app/beyo_manager/models/tables/emails/email_thread_user_state.py`:**
```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailThreadUserState(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "etus"
    __tablename__ = "email_thread_user_states"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_email_thread_user_state"),
    )

    thread_id: Mapped[str] = mapped_column(String(64), ForeignKey("email_threads.client_id"), nullable=False, index=True)
    user_id:   Mapped[str] = mapped_column(String(64), ForeignKey("users.client_id"),        nullable=False, index=True)

    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    muted_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="user_states", lazy="raise")
```

---

**`app/beyo_manager/models/tables/emails/email_thread_topic_preset.py`:**

Global lookup table of predefined topic options. No `workspace_id` — presets are shared across all workspaces.
Frontend calls `GET /api/v1/email-threads/topic-presets` to populate suggestion UI.

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailThreadTopicPreset(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "ettp"
    __tablename__ = "email_thread_topic_presets"

    label:      Mapped[str]  = mapped_column(String(255), nullable=False, unique=True)
    sort_order: Mapped[int]  = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

**Seed data** — insert these rows in the migration's `data_upgrades` function (inline `op.execute` with INSERT after table creation). Do NOT use a separate migration; include them at the end of `add_email_thread_topic_preset_table` migration's `upgrade()`:

```python
# In the migration upgrade() function, after op.create_table(...):
from ulid import ULID

presets = [
    ("Delivery coordination",    10),
    ("Pickup coordination",       20),
    ("Repair completion update",  30),
    ("Parts availability update", 40),
    ("Quote discussion",          50),
    ("General follow-up",         60),
]
for label, sort_order in presets:
    op.execute(
        f"INSERT INTO email_thread_topic_presets (client_id, label, sort_order, is_active, created_at) "
        f"VALUES ('ettp_{ULID()}', '{label}', {sort_order}, true, now())"
    )
```

**downgrade()** only needs `op.drop_table("email_thread_topic_presets")` — data is dropped automatically.

---

**`app/beyo_manager/models/__init__.py` — append these lines** after the last existing import (after `working_section_daily_work_stats`):
```python
# --- Emails ---
from beyo_manager.models.tables.emails import email_connection             # noqa: F401
from beyo_manager.models.tables.emails import email_sync_state            # noqa: F401
from beyo_manager.models.tables.emails import email_thread_topic_preset   # noqa: F401
from beyo_manager.models.tables.emails import email_thread                # noqa: F401
from beyo_manager.models.tables.emails import email_message               # noqa: F401
from beyo_manager.models.tables.emails import email_thread_user_state     # noqa: F401
```

**Import order rationale:**
1. `email_connection` — no internal FKs to other email tables
2. `email_sync_state` — FK to `email_connections`
3. `email_thread_topic_preset` — no FKs (global table)
4. `email_thread` — FK to `email_connections` (no FK to preset — topic is free text)
5. `email_message` — FK to `email_connections` + `email_threads`
6. `email_thread_user_state` — FK to `email_threads` + `users`

---

### Commit 4 — Migrations

Run `alembic revision --autogenerate -m "<slug>"` for **each table separately**, in the order below. Review the generated file before applying. Do NOT combine all 6 tables into one migration — keep them independent for rollback safety.

**Migration 1:** `add_email_connection_table`
**Migration 2:** `add_email_sync_state_table`
**Migration 3:** `add_email_thread_topic_preset_table` ← includes seed INSERT statements (see model section above)
**Migration 4:** `add_email_thread_table`
**Migration 5:** `add_email_message_table`
**Migration 6:** `add_email_thread_user_state_table`

**Apply:** `alembic upgrade head` after all 6 are generated.
**Rollback check:** `alembic downgrade -1` must succeed for each migration in reverse order.

---

### Commit 5 — Infra adapter

Create directory `app/beyo_manager/services/infra/email_providers/` and `app/beyo_manager/services/infra/email_providers/smtp_imap/`.

**`services/infra/email_providers/__init__.py`** — empty.

**`services/infra/email_providers/base.py`:**
```python
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OutboundMessage:
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    bcc_addresses: list[str]
    subject: str
    text_body: str | None
    html_body: str | None
    rfc_message_id: str         # pre-generated by caller: "<ulid>@<smtp_host>"
    in_reply_to: str | None     # RFC Message-ID of the parent message
    references: list[str]       # RFC message IDs of the thread chain


@dataclass
class SendResult:
    success: bool
    error: str | None = None


@dataclass
class InboundMessage:
    provider_uid: int
    provider_folder: str
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str]
    subject: str | None
    text_body: str | None
    html_body: str | None
    body_preview: str | None
    rfc_message_id: str | None
    in_reply_to: str | None
    references: list[str]
    raw_headers: dict
    received_at: object  # datetime


@dataclass
class SyncResult:
    success: bool
    new_messages: list[InboundMessage] = field(default_factory=list)
    new_last_seen_uid: int = 0
    new_uidvalidity: int | None = None
    error: str | None = None


@dataclass
class ConnectionTestResult:
    smtp_ok: bool
    imap_ok: bool
    smtp_error: str | None = None
    imap_error: str | None = None

    @property
    def reachable(self) -> bool:
        return self.smtp_ok and self.imap_ok


class EmailProviderProtocol(Protocol):
    async def test_connection(self) -> ConnectionTestResult: ...
    async def send_email(self, message: OutboundMessage) -> SendResult: ...
    async def sync_inbox(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult: ...
```

---

**`services/infra/email_providers/registry.py`:**
```python
from beyo_manager.domain.emails.enums import EmailProviderTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.infra.crypto.field_encryption import decrypt_field
from beyo_manager.services.infra.email_providers.base import EmailProviderProtocol
from beyo_manager.services.infra.email_providers.smtp_imap.adapter import SmtpImapEmailProvider


def get_email_provider(connection: EmailConnection) -> EmailProviderProtocol:
    """Return the concrete provider for the given connection. Decrypts credentials here."""
    if connection.provider_type == EmailProviderTypeEnum.SMTP_IMAP:
        return SmtpImapEmailProvider(
            smtp_host=connection.smtp_host,
            smtp_port=connection.smtp_port,
            smtp_security=connection.smtp_security,
            smtp_username=connection.smtp_username,
            smtp_password=decrypt_field(connection.smtp_password_encrypted),
            imap_host=connection.imap_host,
            imap_port=connection.imap_port,
            imap_security=connection.imap_security,
            imap_username=connection.imap_username,
            imap_password=decrypt_field(connection.imap_password_encrypted),
        )
    allowed = ", ".join(e.value for e in EmailProviderTypeEnum)
    raise ValidationError(f"Unsupported email provider type '{connection.provider_type}'. Allowed: {allowed}")
```

---

**`services/infra/email_providers/smtp_imap/__init__.py`** — empty.

**`services/infra/email_providers/smtp_imap/mime_builder.py`:**

Build a `MimeBuilder` class with a single method:
```python
class MimeBuilder:
    def build(self, message: OutboundMessage) -> email.message.Message:
        """
        Returns a stdlib email.message.Message ready to pass to smtplib.
        Sets: From, To, Cc, Subject, Message-ID, In-Reply-To, References headers.
        Adds text/plain part. If html_body is present, makes it multipart/alternative.
        MUST NOT log or expose smtp_password.
        """
```

**`services/infra/email_providers/smtp_imap/mime_parser.py`:**

Build a `MimeParser` class:
```python
class MimeParser:
    def parse(self, raw_bytes: bytes, uid: int, folder: str) -> InboundMessage:
        """
        Parses a raw RFC 2822 email bytes into InboundMessage.
        Extracts: from, to, cc, subject, text/plain body, text/html body,
        Message-ID, In-Reply-To, References (split by whitespace), received_at.
        Sets body_preview to first 300 chars of text_body.
        raw_headers: dict of {header_name: header_value} for all headers.
        MUST NOT raise on malformed messages — return None fields instead.
        """
```

**`services/infra/email_providers/smtp_imap/reply_matcher.py`:**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.infra.email_providers.base import InboundMessage


async def find_or_create_thread(
    session: AsyncSession,
    workspace_id: str,
    connection_id: str,
    inbound: InboundMessage,
) -> EmailThread:
    """
    Matching priority:
    1. in_reply_to → lookup email_messages.rfc_message_id
    2. references (each ID in order) → lookup email_messages.rfc_message_id
    3. No match → create new EmailThread (entity_type=None, entity_client_id=None)

    If a match is found, return the matched message's thread.
    If no match: create EmailThread with subject_normalized=normalize_subject(inbound.subject).
    subject normalization: strip leading "Re:", "Fwd:", "FW:", "RE:", "FWD:" (case-insensitive, repeated).
    """
```

**`services/infra/email_providers/smtp_imap/smtp_sender.py`:**

```python
import smtplib
import ssl

from beyo_manager.domain.emails.enums import EmailSecurityEnum
from beyo_manager.services.infra.email_providers.base import OutboundMessage, SendResult
from beyo_manager.services.infra.email_providers.smtp_imap.mime_builder import MimeBuilder


class SmtpSender:
    def __init__(self, host: str, port: int, security: str, username: str, password: str):
        self._host = host
        self._port = port
        self._security = security
        self._username = username
        self._password = password  # already decrypted by registry.py

    def send(self, message: OutboundMessage) -> SendResult:
        """
        Connects via smtplib. Security behavior:
        - EmailSecurityEnum.SSL: smtplib.SMTP_SSL(host, port)
        - EmailSecurityEnum.STARTTLS: smtplib.SMTP(host, port) then .starttls()
        - EmailSecurityEnum.NONE: smtplib.SMTP(host, port) with no TLS
        Timeout: 15 seconds.
        On success: return SendResult(success=True).
        On exception: return SendResult(success=False, error=str(exc)) — NEVER re-raise.
        MUST NOT log self._password.
        """
```

**`services/infra/email_providers/smtp_imap/imap_reader.py`:**

```python
import imaplib

from beyo_manager.domain.emails.enums import EmailSecurityEnum
from beyo_manager.services.infra.email_providers.base import InboundMessage, SyncResult
from beyo_manager.services.infra.email_providers.smtp_imap.mime_parser import MimeParser


class ImapReader:
    def __init__(self, host: str, port: int, security: str, username: str, password: str):
        ...  # store params, do NOT connect in __init__

    def sync(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult:
        """
        1. Connect to IMAP. Security:
           - EmailSecurityEnum.SSL: imaplib.IMAP4_SSL(host, port)
           - EmailSecurityEnum.STARTTLS: imaplib.IMAP4(host, port) then .starttls()
           - EmailSecurityEnum.NONE: imaplib.IMAP4(host, port)
        2. Login with username + password.
        3. SELECT folder (e.g. "INBOX").
        4. Read UIDVALIDITY from SELECT response.
        5. If uidvalidity differs from stored value: reset last_seen_uid to 0, treat as full re-sync.
        6. SEARCH UID uid_set "UID last_seen_uid+1:*" — fetch only new messages.
        7. For each UID: FETCH UID BODY[] to get raw bytes.
        8. Parse via MimeParser.parse(raw_bytes, uid, folder).
        9. Collect InboundMessage list.
        10. Close connection.
        11. Return SyncResult(
                success=True,
                new_messages=messages,
                new_last_seen_uid=max_uid_seen,
                new_uidvalidity=current_uidvalidity,
            )
        On any exception: return SyncResult(success=False, error=str(exc)).
        MUST NOT log self._password.
        Timeout: set socket.setdefaulttimeout(20) before connecting, reset after.
        """

    def test(self) -> tuple[bool, str | None]:
        """Attempt LOGIN only. Return (True, None) on success or (False, error_message)."""
```

**`services/infra/email_providers/smtp_imap/adapter.py`:**

```python
from beyo_manager.services.infra.email_providers.base import (
    ConnectionTestResult, EmailProviderProtocol, OutboundMessage, SendResult, SyncResult,
)
from beyo_manager.services.infra.email_providers.smtp_imap.imap_reader import ImapReader
from beyo_manager.services.infra.email_providers.smtp_imap.smtp_sender import SmtpSender


class SmtpImapEmailProvider:
    """Implements EmailProviderProtocol using stdlib smtplib + imaplib."""

    def __init__(
        self,
        smtp_host: str, smtp_port: int, smtp_security: str,
        smtp_username: str, smtp_password: str,
        imap_host: str, imap_port: int, imap_security: str,
        imap_username: str, imap_password: str,
    ):
        self._smtp = SmtpSender(smtp_host, smtp_port, smtp_security, smtp_username, smtp_password)
        self._imap = ImapReader(imap_host, imap_port, imap_security, imap_username, imap_password)

    async def test_connection(self) -> ConnectionTestResult:
        smtp_ok, smtp_err = self._smtp.test() if hasattr(self._smtp, "test") else (True, None)
        imap_ok, imap_err = self._imap.test()
        return ConnectionTestResult(smtp_ok=smtp_ok, imap_ok=imap_ok, smtp_error=smtp_err, imap_error=imap_err)

    async def send_email(self, message: OutboundMessage) -> SendResult:
        return self._smtp.send(message)

    async def sync_inbox(self, folder: str, uidvalidity: int | None, last_seen_uid: int) -> SyncResult:
        return self._imap.sync(folder, uidvalidity, last_seen_uid)
```

Note: `SmtpSender` and `ImapReader` use stdlib blocking I/O. The `async` wrappers in the adapter are acceptable for MVP because sync is enqueued to a background worker (not running in the async event loop). If later moved to in-process async, wrap calls with `asyncio.run_in_executor`.

---

### Commit 6 — TaskType enum update

**`app/beyo_manager/domain/execution/enums.py` — add one value** to `TaskType`:
```python
    # Email
    EMAIL_INBOX_SYNC = "email_inbox_sync"
```
Add it after the last existing value (`PROCESS_STEP_TRANSITION`). Do not modify any other enum member.

---

### Commit 7 — Commands

Create directory `app/beyo_manager/services/commands/emails/` and `app/beyo_manager/services/commands/emails/requests/`.

All commands follow this signature exactly:
```python
async def <command_name>(ctx: ServiceContext) -> dict:
```

All commands use `maybe_begin` from `beyo_manager.services.commands.utils.transaction`.
All commands import from `beyo_manager.services.infra.audit.write_audit` for audit writes.
All commands return plain `dict` — no ORM objects in the return value.

---

**`services/commands/emails/requests/__init__.py`** — empty.

**`services/commands/emails/requests/create_email_connection_request.py`:**
```python
from pydantic import BaseModel, field_validator
from beyo_manager.domain.emails.enums import EmailProviderTypeEnum, EmailSecurityEnum


class CreateEmailConnectionRequest(BaseModel):
    email_address: str
    display_name: str | None = None
    provider_type: EmailProviderTypeEnum = EmailProviderTypeEnum.SMTP_IMAP

    smtp_host: str
    smtp_port: int
    smtp_security: EmailSecurityEnum
    smtp_username: str
    smtp_password: str  # plaintext — encrypted before DB write, NEVER logged

    imap_host: str
    imap_port: int
    imap_security: EmailSecurityEnum
    imap_username: str
    imap_password: str  # plaintext — encrypted before DB write, NEVER logged

    inbox_folder: str = "INBOX"

    @field_validator("smtp_port", "imap_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535.")
        return v

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("email_address must be a valid email.")
        return v.strip().lower()
```

**`services/commands/emails/requests/update_email_connection_request.py`:**
```python
from pydantic import BaseModel, field_validator
from beyo_manager.domain.emails.enums import EmailSecurityEnum


class UpdateEmailConnectionRequest(BaseModel):
    connection_client_id: str
    display_name: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: EmailSecurityEnum | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None  # only re-encrypted if provided
    imap_host: str | None = None
    imap_port: int | None = None
    imap_security: EmailSecurityEnum | None = None
    imap_username: str | None = None
    imap_password: str | None = None  # only re-encrypted if provided
    inbox_folder: str | None = None
```

**`services/commands/emails/requests/send_email_request.py`:**
```python
from pydantic import BaseModel, field_validator


class SendEmailRequest(BaseModel):
    connection_client_id: str
    thread_client_id: str | None = None  # provide to reply in existing thread
    to_addresses: list[str]
    cc_addresses: list[str] = []
    bcc_addresses: list[str] = []
    subject: str
    text_body: str | None = None
    html_body: str | None = None

    # Entity to link a NEW thread to (ignored if thread_client_id is provided)
    entity_type: str | None = None
    entity_client_id: str | None = None
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None

    # Optional free-text topic for the thread.
    # Ignored if thread_client_id is provided (topic is set on thread creation only).
    # Frontend populates suggestions from GET /api/v1/email-threads/topic-presets.
    topic: str | None = None

    @field_validator("to_addresses")
    @classmethod
    def validate_recipients(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("to_addresses must contain at least one recipient.")
        return v
```

---

**`services/commands/emails/create_email_connection.py`:**

```python
from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum, EmailProviderTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.services.commands.emails.requests.create_email_connection_request import CreateEmailConnectionRequest
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.crypto.field_encryption import encrypt_field


async def create_email_connection(ctx: ServiceContext) -> dict:
    request = CreateEmailConnectionRequest.model_validate(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        connection = EmailConnection(
            workspace_id=ctx.workspace_id,
            owner_user_id=ctx.user_id,
            email_address=request.email_address,
            display_name=request.display_name,
            provider_type=request.provider_type.value,
            status=EmailConnectionStatusEnum.ACTIVE.value,
            smtp_host=request.smtp_host,
            smtp_port=request.smtp_port,
            smtp_security=request.smtp_security.value,
            smtp_username=request.smtp_username,
            smtp_password_encrypted=encrypt_field(request.smtp_password),
            imap_host=request.imap_host,
            imap_port=request.imap_port,
            imap_security=request.imap_security.value,
            imap_username=request.imap_username,
            imap_password_encrypted=encrypt_field(request.imap_password),
            inbox_folder=request.inbox_folder,
        )
        ctx.session.add(connection)
        await ctx.session.flush()  # assign connection.client_id

        sync_state = EmailSyncState(
            connection_id=connection.client_id,
            folder=request.inbox_folder,
            last_seen_uid=0,
        )
        ctx.session.add(sync_state)

        await write_audit(
            session=ctx.session,
            event="email_connection.created",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={"email_address": connection.email_address, "provider_type": connection.provider_type},
        )

    return {
        "email_connection": _serialize_connection(connection),
    }
```

Add this import at the top of `create_email_connection.py`:
```python
from beyo_manager.domain.emails.serializers import serialize_email_connection
```
Use `serialize_email_connection(connection)` in the return value. Do NOT define a private `_serialize_connection` in the command file — the canonical serializer lives in `domain/emails/serializers.py` and is shared with the query layer.

---

**`services/commands/emails/update_email_connection.py`:**

Logic:
1. Parse `UpdateEmailConnectionRequest` from `ctx.incoming_data`.
2. Load connection by `client_id` where `workspace_id == ctx.workspace_id` and `deleted_at IS NULL`.
3. Call `assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)`.
4. For each non-None field in the request: update the column. If `smtp_password` provided: re-encrypt.
5. Write audit event `email_connection.updated`.
6. Return `{"email_connection": _serialize_connection(connection)}`.

---

**`services/commands/emails/delete_email_connection.py`:**

Logic:
1. `ctx.incoming_data["connection_client_id"]` — required string.
2. Load connection (same filter as above).
3. `assert_can_access_connection(...)`.
4. Set `connection.deleted_at = datetime.now(timezone.utc)` and `connection.status = EmailConnectionStatusEnum.DISABLED.value`.
5. Write audit event `email_connection.deleted`.
6. Return `{"deleted": True}`.

---

**`services/commands/emails/test_email_connection.py`:**

Logic (does NOT open a DB transaction — read-only + external I/O only):
1. Load connection by `client_id` where `workspace_id == ctx.workspace_id` and `deleted_at IS NULL`.
2. `assert_can_access_connection(...)`.
3. `provider = get_email_provider(connection)`.
4. `result = await provider.test_connection()`.
5. Return `{"reachable": result.reachable, "smtp_ok": result.smtp_ok, "imap_ok": result.imap_ok, "smtp_error": result.smtp_error, "imap_error": result.imap_error}`.
6. Do NOT write to DB. Do NOT write audit here.

---

**`services/commands/emails/send_email.py`:**

```python
from datetime import datetime, timezone
from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.commands.emails.requests.send_email_request import SendEmailRequest
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.registry import get_email_provider
```

Logic:
1. Parse `SendEmailRequest` from `ctx.incoming_data`.
2. Load connection. Raise `NotFound` if not found or `deleted_at IS NOT NULL`.
3. `assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)`.
4. Generate `rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"`.
5. Determine `in_reply_to` and `references`:
   - If `request.thread_client_id` provided: load the most recent outbound message of that thread, use its `rfc_message_id` as `in_reply_to` and build `references` list.
   - Otherwise: `in_reply_to = None`, `references = []`.
6. Build `OutboundMessage(...)`.
7. `provider = get_email_provider(connection)`.
8. `send_result = await provider.send_email(outbound_message)`.
9. Open `maybe_begin(ctx.session)`:
   a. If send_result.success is False: set a `send_error` var, do NOT raise — still persist the message with direction=OUTBOUND so the user can see the failure.
   b. Find or create `EmailThread`: if `request.thread_client_id` provided, load it (workspace check); otherwise create new thread with `entity_type`, `entity_client_id`, `major_entity_type`, `major_entity_client_id`, `topic` from request, `subject_normalized=_normalize_subject(request.subject)`. `topic` max length 255 — truncate silently if longer.
   c. Flush if thread was just created (to get `thread.client_id`).
   d. Create `EmailMessage(direction=OUTBOUND, rfc_message_id=rfc_message_id, ...)`.
   e. Update `thread.last_message_at = datetime.now(timezone.utc)`.
   f. Write audit `email.sent` (include `thread_client_id`, `to_addresses`, **not** body content).
10. Return `{"thread_client_id": thread.client_id, "message_client_id": message.client_id, "send_success": send_result.success, "send_error": send_result.error}`.

Private helper:
```python
def _normalize_subject(subject: str | None) -> str | None:
    """Strip Re:, Fwd:, RE:, FW:, FWD: prefixes repeatedly."""
    if not subject:
        return None
    import re
    return re.sub(r"^(re|fwd?|fw):\s*", "", subject, flags=re.IGNORECASE).strip() or subject
```

---

**`services/commands/emails/sync_email_connection.py`:**

Logic:
1. `connection_client_id = ctx.incoming_data["connection_client_id"]` — required.
2. Load connection (workspace check, deleted_at IS NULL).
3. `assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id)`.
4. Load `EmailSyncState` where `connection_id == connection.client_id`.
5. Inside `maybe_begin`:
   a. `await create_instant_task(session=ctx.session, task_type=TaskType.EMAIL_INBOX_SYNC, payload={"connection_client_id": connection.client_id, "workspace_id": ctx.workspace_id, "requested_by_user_id": ctx.user_id}, max_try=3)`.
6. Return current sync_state snapshot: `{"sync_state": _serialize_sync_state(sync_state)}`.

```python
def _serialize_sync_state(s: EmailSyncState) -> dict:
    return {
        "client_id": s.client_id,
        "connection_id": s.connection_id,
        "folder": s.folder,
        "uidvalidity": s.uidvalidity,
        "last_seen_uid": s.last_seen_uid,
        "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
        "last_successful_sync_at": s.last_successful_sync_at.isoformat() if s.last_successful_sync_at else None,
        "last_error": s.last_error,
    }
```

---

**`services/commands/emails/mark_email_thread_read.py`:**

Logic:
1. `thread_client_id = ctx.incoming_data["thread_client_id"]`.
2. Load `EmailThread` where `client_id == thread_client_id` and `workspace_id == ctx.workspace_id`.
3. `assert_can_access_connection(...)` — load the thread's connection to check ownership.
4. Inside `maybe_begin`: upsert `EmailThreadUserState`:
   - `SELECT ... WHERE thread_id == thread.client_id AND user_id == ctx.user_id` with `with_for_update()`.
   - If exists: `state.last_read_at = datetime.now(timezone.utc)`.
   - If not: `ctx.session.add(EmailThreadUserState(thread_id=..., user_id=ctx.user_id, last_read_at=now))`.
5. Return `{"marked_read": True}`.

---

### Commit 8 — Worker handler for EMAIL_INBOX_SYNC

**Read first:** `workers/tasks_worker.py` (or equivalent file that holds the handler map) to find where `TaskType` values are mapped to handler functions. Replicate that exact registration pattern.

**Create `app/beyo_manager/services/tasks/email_inbox_sync_handler.py`:**

```python
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_sync_state import EmailSyncState
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.services.infra.email_providers.registry import get_email_provider
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import find_or_create_thread

logger = logging.getLogger(__name__)


async def handle_email_inbox_sync(payload: dict, session: AsyncSession) -> None:
    """
    payload keys: connection_client_id, workspace_id, requested_by_user_id
    Steps:
    1. Load EmailConnection + EmailSyncState (selectinload or separate query).
    2. get_email_provider(connection) — decrypts inside registry.
    3. Call provider.sync_inbox(folder, uidvalidity, last_seen_uid).
    4. If sync_result.success is False:
       - Update sync_state.last_error = sync_result.error, sync_state.last_sync_at = now
       - If error looks like auth failure: set connection.status = "auth_failed"
       - Commit and return (log warning).
    5. For each inbound_message in sync_result.new_messages:
       a. Check for duplicate: SELECT 1 FROM email_messages WHERE connection_id=? AND provider_folder=? AND provider_uid=?
          If exists: skip.
       b. thread = await find_or_create_thread(session, workspace_id, connection.client_id, inbound_message)
       c. Create EmailMessage(direction="inbound", provider_uid=str(inbound.provider_uid), ...)
       d. Update thread.last_message_at and thread.last_inbound_message_at = inbound.received_at
    6. Update sync_state:
       - last_seen_uid = sync_result.new_last_seen_uid
       - uidvalidity = sync_result.new_uidvalidity
       - last_sync_at = now
       - last_successful_sync_at = now
       - last_error = None
    7. Commit (session.commit() — worker owns the session lifecycle).
    """
```

**Register the handler** in the handler map file (read it first to find exact pattern). Add:
```python
TaskType.EMAIL_INBOX_SYNC: handle_email_inbox_sync,
```

---

### Commit 9 — Queries

All queries follow this pattern:
- Import `select` from `sqlalchemy`
- Filter `workspace_id == ctx.workspace_id` as the first WHERE clause always
- Use offset pagination: read `limit = min(int(ctx.query_params.get("limit", 50)), 200)` and `offset = int(ctx.query_params.get("offset", 0))`
- Return `{"<entity_plural>": [...], "<entity_plural>_pagination": {"limit": limit, "offset": offset, "has_more": bool}}`

---

**`services/queries/emails/list_email_connections.py`:**

```python
from beyo_manager.domain.emails.serializers import serialize_email_connection


async def list_email_connections(ctx: ServiceContext) -> dict:
    """
    Query params (from ctx.query_params):
    - owner_user_id (str, optional): ADMIN/MANAGER only. Defaults to ctx.user_id.
    - limit (int, default 50, max 200)
    - offset (int, default 0)

    1. Resolve target_user_id:
       - If owner_user_id param absent: target_user_id = ctx.user_id
       - If owner_user_id param present AND ctx.role_name not in (ADMIN, MANAGER): raise PermissionDenied
       - Else: target_user_id = owner_user_id param value

    2. Query:
       SELECT * FROM email_connections
       WHERE workspace_id = :workspace_id
         AND owner_user_id = :target_user_id
         AND deleted_at IS NULL
       ORDER BY created_at DESC
       LIMIT :limit OFFSET :offset

    3. Return:
    {
        "email_connections": [serialize_email_connection(c) for c in connections],
        "email_connections_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }

    serialize_email_connection returns the same fields as _serialize_connection() in
    create_email_connection.py. NEVER include smtp_password_encrypted or imap_password_encrypted.
    Import from: beyo_manager.domain.emails.serializers
    """
```

---

**`services/queries/emails/get_email_thread.py`:**

```python
from beyo_manager.domain.emails.serializers import serialize_email_thread
from beyo_manager.domain.emails.guards import assert_can_access_connection


async def get_email_thread(ctx: ServiceContext) -> dict:
    """
    ctx.incoming_data["thread_client_id"] required.
    1. Load EmailThread where client_id=? AND workspace_id=?. Raise NotFound if missing.
    2. Load connection by thread.connection_id (no relationship traversal — separate query).
    3. assert_can_access_connection(ctx.user_id, ctx.role_name, connection.owner_user_id).
    4. Load EmailThreadUserState where thread_id=thread.client_id AND user_id=ctx.user_id.
       Use: result = await session.execute(select(EmailThreadUserState).where(...))
            user_state = result.scalar_one_or_none()
    5. Return:
       {"email_thread": serialize_email_thread(thread, user_state)}

    serialize_email_thread() handles is_unread computation and user_state nesting.
    Import from: beyo_manager.domain.emails.serializers
    """
```

---

**`services/queries/emails/list_email_messages.py`:**

```python
from beyo_manager.domain.emails.serializers import serialize_email_message
from beyo_manager.domain.emails.guards import assert_can_access_connection


async def list_email_messages(ctx: ServiceContext) -> dict:
    """
    ctx.incoming_data["thread_client_id"] required.
    1. Load EmailThread where client_id=? AND workspace_id=?. Raise NotFound if missing.
    2. Load connection by thread.connection_id. assert_can_access_connection(...).
    3. limit = min(int(ctx.query_params.get("limit", 50)), 200)
       offset = int(ctx.query_params.get("offset", 0))
    4. Query:
       SELECT * FROM email_messages
       WHERE thread_id = :thread_id
       ORDER BY sent_or_received_at ASC NULLS LAST, created_at ASC
       LIMIT :limit OFFSET :offset
    5. Fetch limit+1 rows to determine has_more; slice to limit before serializing.
    6. Return:
       {
           "email_messages": [serialize_email_message(m) for m in messages],
           "email_messages_pagination": {
               "limit": limit,
               "offset": offset,
               "has_more": len(rows) > limit,
           },
       }

    serialize_email_message() excludes raw_headers_json.
    Import from: beyo_manager.domain.emails.serializers
    """
```

---

**`services/queries/emails/list_email_threads.py`:**

```python
from beyo_manager.domain.emails.serializers import serialize_email_thread


async def list_email_threads(ctx: ServiceContext) -> dict:
    """
    Query params (all from ctx.query_params):
    - connection_client_id (str, optional): filter by connection
    - entity_type (str, optional) + entity_client_id (str, optional): filter by linked entity.
      Both must be provided together or neither.
    - unread_only ("true"/"false", optional, default false)
    - limit (int, default 50, max 200)
    - offset (int, default 0)

    Base query:
      SELECT t.*, s.*
      FROM email_threads t
      LEFT JOIN email_thread_user_states s
             ON s.thread_id = t.client_id AND s.user_id = :user_id
      WHERE t.workspace_id = :workspace_id
      [AND t.connection_id = :connection_client_id]           -- if provided
      [AND t.entity_type = :entity_type
         AND t.entity_client_id = :entity_client_id]          -- if both provided
      [AND (t.last_inbound_message_at IS NOT NULL
         AND (s.last_read_at IS NULL
              OR t.last_inbound_message_at > s.last_read_at))] -- if unread_only=true
      ORDER BY t.last_message_at DESC NULLS LAST
      LIMIT :limit OFFSET :offset

    Fetch limit+1 to determine has_more.

    Serialization:
      For each (thread, user_state) row pair:
        serialize_email_thread(thread, user_state)
      user_state may be None (LEFT JOIN) — pass as None to serializer.

    Return:
    {
        "email_threads": [serialize_email_thread(t, s) for t, s in pairs],
        "email_threads_pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(rows) > limit,
        },
    }

    Import serialize_email_thread from: beyo_manager.domain.emails.serializers
    """
```

---

**`services/queries/emails/list_email_thread_topic_presets.py`:**

```python
from beyo_manager.domain.emails.serializers import serialize_email_thread_topic_preset


async def list_email_thread_topic_presets(ctx: ServiceContext) -> dict:
    """
    Returns all active topic presets ordered by sort_order ASC.
    No workspace filter — presets are global.
    No pagination — list is small and static; always return all active rows.

    Query:
    SELECT * FROM email_thread_topic_presets
    WHERE is_active = true
    ORDER BY sort_order ASC

    Return:
    {
        "email_thread_topic_presets": [
            serialize_email_thread_topic_preset(p) for p in presets
        ]
    }

    serialize_email_thread_topic_preset returns: {"client_id", "label", "sort_order"}.
    Import from: beyo_manager.domain.emails.serializers
    """
```

This endpoint requires no auth beyond a valid JWT (any role). It is read-only and returns no sensitive data.

---

**`services/queries/emails/get_email_unread_counts.py`:**

```python
async def get_email_unread_counts(ctx: ServiceContext) -> dict:
    """
    Returns unread thread count for ctx.user_id within ctx.workspace_id.
    Optional query param: connection_client_id to scope to one mailbox.

    Query:
    SELECT COUNT(*)
    FROM email_threads t
    LEFT JOIN email_thread_user_states s ON s.thread_id = t.client_id AND s.user_id = :user_id
    WHERE t.workspace_id = :workspace_id
      AND t.last_inbound_message_at IS NOT NULL
      AND (s.last_read_at IS NULL OR t.last_inbound_message_at > s.last_read_at)

    Return: {"unread_count": int}
    """
```

---

### Commit 10 — Routers

**`app/beyo_manager/routers/api_v1/email_connections.py`:**

Pattern: copy the exact `_run` helper from `notifications.py` (lines 59–64). Imports from the same locations.

```
Endpoints:
POST   /                    → create_email_connection    ADMIN, MANAGER, SELLER
GET    /                    → list_email_connections     ADMIN, MANAGER, SELLER
GET    /{connection_id}     → (inline: load + serialize) ADMIN, MANAGER, SELLER
PUT    /{connection_id}     → update_email_connection    ADMIN, MANAGER, SELLER
DELETE /{connection_id}     → delete_email_connection    ADMIN, MANAGER
POST   /{connection_id}/test    → test_email_connection  ADMIN, MANAGER, SELLER
POST   /{connection_id}/sync    → sync_email_connection  ADMIN, MANAGER, SELLER
```

Path params are merged into `incoming_data` before calling `_run`:
```python
@router.post("/{connection_id}/sync")
async def sync_connection(
    connection_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        sync_email_connection,
        {"connection_client_id": connection_id},
        claims, session,
    )
```

---

**`app/beyo_manager/routers/api_v1/email_threads.py`:**

```
Endpoints (declare in this exact order — static routes must come before /{thread_id}):
GET    /topic-presets               → list_email_thread_topic_presets  ADMIN, MANAGER, SELLER, WORKER
GET    /unread-count                → get_email_unread_counts          ADMIN, MANAGER, SELLER
GET    /send                        → (not valid — skip)
POST   /send                        → send_email (new thread)          ADMIN, MANAGER, SELLER
GET    /                            → list_email_threads               ADMIN, MANAGER, SELLER
GET    /{thread_id}                 → get_email_thread                 ADMIN, MANAGER, SELLER
GET    /{thread_id}/messages        → list_email_messages              ADMIN, MANAGER, SELLER
POST   /{thread_id}/send            → send_email (reply)               ADMIN, MANAGER, SELLER
POST   /{thread_id}/read            → mark_email_thread_read           ADMIN, MANAGER, SELLER
```

**CRITICAL — static routes before path params.** FastAPI matches in declaration order. All fixed-string routes (`/topic-presets`, `/unread-count`, `/send`) MUST be declared **before** `GET /{thread_id}` in the file. If any static route appears after `/{thread_id}`, FastAPI will interpret the static segment as a `thread_id` value — silently wrong at runtime, not a startup error.

Query params (`limit`, `offset`, `connection_client_id`, `entity_type`, `entity_client_id`, `unread_only`) are injected into `ctx.query_params`, not `ctx.incoming_data`. Match how existing query-heavy routes pass params.

---

**`app/beyo_manager/routers/api_v1/__init__.py` — two changes:**

1. Add imports at the top (alphabetical order with existing imports):
```python
from beyo_manager.routers.api_v1 import (
    ...existing...,
    email_connections,
    email_threads,
)
```

2. Add to `register_v1_routers()` before the trailing comment:
```python
    app.include_router(email_connections.router, prefix="/api/v1/email-connections", tags=["email-connections"])
    app.include_router(email_threads.router,     prefix="/api/v1/email-threads",     tags=["email-threads"])
```

---

## Risks and mitigations

- **Risk:** SMTP/IMAP blocking I/O in async context.
  **Mitigation:** Sync is enqueued to the worker (blocking I/O stays off the event loop). `send_email` calls `provider.send_email()` which uses stdlib smtplib — this runs synchronously in the async command. For MVP this is acceptable; flag it with a `# TODO: wrap in run_in_executor for high-traffic` comment.

- **Risk:** UIDVALIDITY mismatch causes re-downloading entire inbox.
  **Mitigation:** `ImapReader.sync` resets `last_seen_uid` to 0 on UIDVALIDITY change. The duplicate-check in the worker handler prevents inserting messages twice.

- **Risk:** `FIELD_ENCRYPTION_KEY` not set in production.
  **Mitigation:** `_get_key()` raises `RuntimeError` with clear message. Startup health check or test should exercise this path.

- **Risk:** Reply threading fails if customer strips email headers.
  **Mitigation:** `find_or_create_thread` falls back to creating a new thread (never crashes). Body tracking token can be added later.

- **Risk:** `smtp_password` / `imap_password` accidentally logged.
  **Mitigation:** Passwords are encrypted in `create_email_connection` before any DB flush. Request objects hold plaintext only transiently. Serializer `_serialize_connection` explicitly omits `*_encrypted` fields. `SmtpSender` and `ImapReader` docstrings say "MUST NOT log self._password".

---

## Validation plan

After all 10 commits are applied:

- `alembic upgrade head` — no errors; 5 new tables visible in DB.
- `alembic downgrade -1` (×5) — each migration reverses cleanly.
- `python -c "from beyo_manager.services.infra.email_providers.smtp_imap.adapter import SmtpImapEmailProvider"` — imports without error.
- `python -c "from beyo_manager.routers.api_v1 import email_connections, email_threads"` — imports without error.
- Unit test: `encrypt_field`/`decrypt_field` round-trip.
- Unit test: `MimeBuilder.build()` sets correct `Message-ID` and `In-Reply-To` headers.
- Unit test: `MimeParser.parse()` extracts `rfc_message_id`, `in_reply_to`, `references` from a sample raw email bytes fixture.
- Unit test: `find_or_create_thread` returns existing thread on `In-Reply-To` match; creates new thread when no match.
- Unit test: `_normalize_subject("Re: Re: Fwd: Hello")` returns `"Hello"`.
- Unit test: `assert_can_access_connection` raises `PermissionDenied` for SELLER accessing another user's connection.
- Integration test: after migration, `SELECT COUNT(*) FROM email_thread_topic_presets WHERE is_active = true` returns 6.
- Integration test: `list_email_thread_topic_presets` returns presets ordered by `sort_order` ASC; `label` values include `"Delivery coordination"`.
- Integration test: `send_email` with `topic="Delivery coordination"` and no `thread_client_id` creates a new thread with `topic == "Delivery coordination"`.
- Integration test: `send_email` reply (with existing `thread_client_id`) ignores any `topic` in the request — the existing thread's topic is unchanged.
- Integration test: `create_email_connection` persists connection + sync_state, never exposes encrypted fields in return.
- Integration test: `send_email` with a fake provider stores outbound `EmailMessage` and `EmailThread`.
- Integration test: `mark_email_thread_read` upserts `EmailThreadUserState`; calling twice does not create a second row.
- Integration test: `get_email_unread_counts` returns 1 after inbound message arrives, 0 after `mark_email_thread_read`.

---

## Review log

- `2026-07-04` David (owner): Plan created after architecture survey and Q&A alignment.
- `2026-07-04` David (owner): Added `EmailThread.topic` (free-text), `EmailThreadTopicPreset` global lookup table, seed data (6 presets), `list_email_thread_topic_presets` query, and `/topic-presets` route. Topic is set only on new thread creation, not on replies.
- `2026-07-04` David (owner): Added explicit `domain/emails/serializers.py` with field-by-field definitions for `serialize_email_thread`, `serialize_email_message`, `serialize_email_thread_user_state`, `serialize_email_thread_topic_preset`, `serialize_email_connection`. All queries and commands now import from this single source. `raw_headers_json` and credential fields explicitly marked as omitted.

---

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: David (owner)
