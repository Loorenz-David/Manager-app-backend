# 11 — Infrastructure: Event Bus Contract

## What the event system does

Commands raise domain events after committing to the database. These events drive side effects: pushing real-time updates to connected clients, writing audit entries, triggering analytics snapshots, or queuing external integrations.

The event bus decouples the command from its downstream effects. A command builds events and dispatches them — it does not know which handlers will respond.

---

## Architecture

```
Command / background job
  │
  ├─ builds typed Event instances
  ├─ commits to DB (async with ctx.session.begin())
  └─ event_bus.dispatch(pending_events)
                │
          EventBus.dispatch()
          calls each registered handler
                │
        Handlers (one per side effect)
          ├─ socket_handler.py     → realtime_push → workspace / user room
          ├─ audit_handler.py      → write audit entry
          └─ webhook_handler.py    → enqueue task for durable delivery
```

Two things this diagram does not show, both load-bearing:

- **`realtime_push` picks its transport from the process.** Only the API holds websockets; every
  other process publishes through Redis for the API to forward. See "Delivery is
  process-dependent".
- **A data-carrying emitter may enter at `realtime_push` instead of at `dispatch`,** skipping the
  audit and webhook handlers. One sanctioned exception, with conditions — see "Data-carrying
  emitters".

**Two dispatch tiers:**

| Side effect | Mechanism | Reliability |
|---|---|---|
| Socket push, audit log | Event bus (synchronous, in-process) | Best-effort — fast, immediate |
| Email, webhook, external API | Task queue via execution layer | At-least-once — durable, retried |

The event bus handles immediate in-process side effects. Durable work (email, webhook) is handled by having its handler enqueue a task via `create_instant_task()` — the actual delivery happens in a task worker with retry guarantees.

---

## Event dataclasses

```python
# services/infra/events/domain_event.py
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Event:
    """Base event. All domain events inherit from this."""
    event_name: str          # "<domain>:<verb>" — e.g. "invoice:updated"
    client_id:  str          # client_id of the entity that changed
    extra:      dict = field(default_factory=dict)   # optional additional payload


@dataclass(kw_only=True)
class WorkspaceEvent(Event):
    """Broadcast to all users connected to a workspace room."""
    workspace_id: str


@dataclass(kw_only=True)
class UserEvent(Event):
    """Push to a specific user's room only."""
    user_id: str


@dataclass(kw_only=True)
class ConversationRoomEvent(Event):
    """Broadcast to all users currently viewing a specific conversation."""
    conversation_id: str
    workspace_id:    str
```

**Rules:**
- `event_name` follows `<domain>:<verb>` convention: `invoice:updated`, `message:created`, `case:state-changed`. The colon matches the frontend's `ServerToClientEvents` type exactly — no translation at the socket layer.
- `client_id` is always the identifier of the changed entity — never an alternate integer ID.
- `extra` carries optional context beyond the `client_id` (e.g. `{"new_status": "paid"}`). Keep it minimal — the frontend fetches full data via REST.
- Events are immutable after creation. Handlers must not modify them.

---

## Standard event builder

A single builder function covers the majority of domain events. Both workspace and user variants:

```python
# services/infra/events/build_event.py
from my_app.services.infra.events.domain_event import WorkspaceEvent, UserEvent


def build_workspace_event(
    entity,
    event_name: str,
    *,
    workspace_id: str | None = None,
    extra: dict | None = None,
) -> WorkspaceEvent:
    return WorkspaceEvent(
        event_name=event_name,
        client_id=entity.client_id,
        workspace_id=workspace_id or getattr(entity, "workspace_id", None),
        extra=extra or {},
    )


def build_user_event(
    user_id:    str,
    event_name: str,
    client_id:  str,
    extra: dict | None = None,
) -> UserEvent:
    return UserEvent(
        event_name=event_name,
        client_id=client_id,
        user_id=user_id,
        extra=extra or {},
    )


def build_conversation_event(
    entity,
    event_name:      str,
    *,
    conversation_id: str,
    workspace_id:    str,
    extra: dict | None = None,
) -> ConversationRoomEvent:
    return ConversationRoomEvent(
        event_name=event_name,
        client_id=entity.client_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        extra=extra or {},
    )
```

Usage in a command:

```python
pending_events.append(build_workspace_event(invoice, "invoice:updated"))

# with extra context
pending_events.append(build_workspace_event(
    invoice,
    "invoice:status-changed",
    extra={"new_status": invoice.status.value},
))

# user-specific
pending_events.append(build_user_event(
    user_id=ctx.user_id,
    event_name="message:sent-receipt",
    client_id=message.client_id,
))

# conversation-scoped (all users currently viewing the conversation)
pending_events.append(build_conversation_event(
    message,
    "conversation:message-created",
    conversation_id=conversation.client_id,
    workspace_id=ctx.workspace_id,
))
```

Domain-specific builder functions are only needed when the entity does not have a standard `client_id` / `workspace_id` shape or when the event payload requires non-trivial assembly.

---

## Event bus

```python
# services/infra/events/event_bus.py
from __future__ import annotations
from my_app.services.infra.events.domain_event import Event
import logging

logger = logging.getLogger(__name__)

_handlers: list[callable] = []


def register(handler: callable) -> None:
    """Register a handler to be called on every dispatched event."""
    _handlers.append(handler)


def dispatch(events: list[Event]) -> None:
    """Call every registered handler for each event.
    Called by commands after their transaction commits.
    Handlers are fire-and-forget — a failing handler is logged and skipped,
    not re-raised, so one bad handler cannot block others.
    """
    if events and not _handlers:
        # An empty handler list is a valid loop, so dropping events here used to be
        # completely silent. It must be loud: see "Handler registration".
        logger.warning("event_bus: %d event(s) dropped — no handlers registered", len(events))
        return
    for event in events:
        for handler in _handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "event handler failed | event=%s handler=%s client_id=%s",
                    event.event_name,
                    handler.__name__,
                    event.client_id,
                )
```

**Rules:**
- `register()` is called on import of the events package — see the next section for why it is
  deliberately **not** a startup hook.
- `dispatch()` is called by every command after its transaction commits. Never inside the `begin()` block.
- Handlers are synchronous and in-process. They must be fast. Anything slow or unreliable (HTTP calls, email sends) must enqueue a task instead of executing inline.
- A failing handler does not block other handlers or raise to the command. It is logged at `ERROR` level.

---

## Handler registration — on import, in every process

The handler list is module-level state, so **every process that dispatches needs its own copy
filled.** Registration therefore happens when the events package is imported:

```python
# services/infra/events/__init__.py
from my_app.services.infra.events.event_bus import dispatch, register
from my_app.services.infra.events.bootstrap import register_default_handlers

register_default_handlers()      # idempotent; runs once per process
```

Adding a new side effect means adding one `register()` call in `bootstrap.py` and one handler
file — no command files change.

### Why not a startup hook

Because there is no single startup path. The API runs a FastAPI lifespan; of the nine worker
units, five go through `run_worker()` and four (`task_router`, both schedulers,
`email_idle_watcher`) have their own `main()`. Any hook covers some entry points and silently
misses the rest.

That is not hypothetical. Registration lived in the FastAPI lifespan alone from the first
commit, so `dispatch()` in a worker walked an empty list and discarded the events — no
exception, no log, no failing test. `notification:new` was never delivered to a connected
client for two and a half months, and the bug was found by accident.

Importing is the one thing a dispatcher cannot skip: you cannot call `dispatch` without
importing the package that defines it, and importing any submodule runs the package
`__init__` first. That makes the guarantee structural instead of remembered.

Safe at import time because it registers three functions and does nothing else — the database
imports inside `audit_handler` and `webhook_handler` are deferred into their function bodies,
and the socket module builds no server or connection until `get_sio()` is called.

`create_app()` still calls `register_default_handlers()` explicitly during lifespan. It is a
no-op by then, kept because startup wiring should be readable in one place.

---

## Delivery is process-dependent — `realtime_push` handles it

**Only the API process holds websocket connections.** A worker runs the same command code but
has no client connected to it and cannot reach one directly, no matter what it emits.

`realtime_push` is the single place that knows this:

| Process | Transport |
|---|---|
| API (`owns_socket_server()` is true) | `manager` → delivers to its own clients immediately, and publishes to Redis for other API instances |
| Everything else | `sockets/worker_emitter.py` → publishes to the Redis channel the API's socket server subscribes to, and the API forwards |

Both branches build room names from `sockets/rooms.py`, so the two paths cannot drift on
addressing. The flag is set once by `create_app()` — explicitly, not inferred from whether a
socket server object happens to exist.

**Callers never choose a transport.** A command used by both a request and a background job
emits identically from either. If you find yourself importing `worker_emitter` in a command or
a task handler, you are working around this layer rather than using it.

---

## Data-carrying emitters — the one sanctioned way to skip the bus

The default is `dispatch()`. This section exists because one pattern legitimately does not fit
the bus's payload shape, and pretending otherwise would leave the codebase contradicting this
document.

The socket handler builds every payload as `{"client_id": event.client_id, **event.extra}`, and
`extra` is meant to stay minimal — the client is expected to fetch full data over REST. A
**data-carrying** event inverts that: it ships a whole serialized object so the client can write
it straight into a cache without a round trip. That is worth doing only where the round trip is
felt — a screen someone watches while another person acts on their behalf.

Such an emitter may call `realtime_push` directly, and must obey three constraints:

1. **It is a module, not an inline call.** One named function per event set, holding the read and
   the payload shape in one place, so there is exactly one definition of what goes on the wire.
2. **It never touches `worker_emitter`.** `realtime_push` is the floor — dropping below it
   reintroduces the process bug this whole layer exists to prevent.
3. **It never raises.** It runs after the write has committed; a broadcast failure is logged and
   swallowed, never surfaced as a failed command.

**What you give up, explicitly:** the bus's other handlers. Events emitted this way are invisible
to `audit_handler` and `webhook_handler`, so adding the name to the audited allowlist does
nothing. If an event ever needs auditing, it belongs on the bus — convert it rather than teaching
the emitter to write audit rows.

**Current instances:**

| Emitter | Why it carries data |
|---|---|
| `services/infra/events/worker_shift_realtime.py` | Payload is re-read from the database so it matches `GET /worker-shifts/current` exactly; the floor app writes it straight into that cache |
| `services/tasks/emails/handle_sync_email_threads_targeted.py` | Sync outcome — counts, per-thread errors, success flag — exists only in the job that produced it |
| `services/tasks/shopify/handle_shopify_process_products.py` | Per-item success and failure lists, likewise |
| `domain/emails/arrival_notifications.py` | Per-user thread updates assembled during inbox processing |

Anything that merely notifies — "this entity changed, go refetch" — is not this pattern. Use the
bus. Note that three of the four above are *reporting the outcome of a background job*, which is
the recurring shape: there is no entity for the client to refetch, so `{client_id}` says nothing.

---

## Handlers

Each handler is a single function that receives any `Event` and acts only on the types it cares about:

### Socket handler

```python
# services/infra/events/handlers/socket_handler.py
from my_app.services.infra.events.domain_event import WorkspaceEvent, UserEvent, ConversationRoomEvent
from my_app.services.infra.events.realtime_push import (
    push_workspace_refresh,
    push_workspace_batch,
    push_to_conversation,
    push_to_user,
)


def handle(event) -> None:
    if isinstance(event, ConversationRoomEvent):
        push_to_conversation(
            event.conversation_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
    elif isinstance(event, WorkspaceEvent):
        if "ids" in event.extra:
            push_workspace_batch(event.workspace_id, event.event_name, event.extra["ids"])
        else:
            push_workspace_refresh(
                event.workspace_id,
                event.event_name,
                {"client_id": event.client_id, **event.extra},
            )
    elif isinstance(event, UserEvent):
        push_to_user(
            event.user_id,
            event.event_name,
            {"client_id": event.client_id, **event.extra},
        )
```

`ConversationRoomEvent` is checked first because a conversation event is narrower than a workspace event — checking the most specific type first prevents a subclass from being caught by a broader isinstance guard if the class hierarchy changes.

### Webhook handler (enqueues task — does not call external APIs inline)

```python
# services/infra/events/handlers/webhook_handler.py
from my_app.services.infra.events.domain_event import WorkspaceEvent
from my_app.services.infra.execution.task_factory import create_instant_task
from my_app.domain.execution.enums import TaskType

_WEBHOOK_EVENTS = {"invoice:updated", "invoice:created", "case:state-changed"}


def handle(event) -> None:
    if not isinstance(event, WorkspaceEvent):
        return
    if event.event_name not in _WEBHOOK_EVENTS:
        return
    create_instant_task(TaskType.DELIVER_WEBHOOK, {
        "event_name":   event.event_name,
        "client_id":    event.client_id,
        "workspace_id": event.workspace_id,
        "extra":        event.extra,
    })
```

The webhook handler enqueues a task and returns immediately. The actual HTTP delivery, with retries, happens in the webhook worker.

### Audit handler

```python
# services/infra/events/handlers/audit_handler.py
from datetime import datetime, timezone
from my_app.services.infra.events.domain_event import Event

_AUDITED_EVENTS = {"invoice:updated", "invoice:deleted", "case:state-changed"}


def handle(event: Event) -> None:
    if event.event_name not in _AUDITED_EVENTS:
        return
    # write audit row synchronously — it's a fast DB insert
    from my_app.services.infra.audit import write_audit_entry
    write_audit_entry(
        event_name=event.event_name,
        client_id=event.client_id,
        extra=event.extra,
        occurred_at=datetime.now(timezone.utc),
    )
```

---

## Batch events

When a command changes multiple entities, it emits one batch event — not N individual events. The frontend's `batchInvalidation()` handles per-ID cache decisions from a single event.

The standard builder does not handle batch natively — the command builds the batch event explicitly:

```python
# For 2–200 entities
pending_events.append(WorkspaceEvent(
    event_name="invoice:batch-updated",
    client_id="",                       # empty — batch has no single client_id
    workspace_id=ctx.workspace_id,
    extra={"ids": [i.client_id for i in invoices]},
))

# For 200+ entities (broad signal — no ID enumeration)
pending_events.append(WorkspaceEvent(
    event_name="invoice:invalidate-all",
    client_id="",
    workspace_id=ctx.workspace_id,
))
```

The socket handler routes batch events via `push_workspace_batch` when `extra["ids"]` is present:

```python
def handle(event) -> None:
    if isinstance(event, WorkspaceEvent):
        if "ids" in event.extra:
            push_workspace_batch(event.workspace_id, event.event_name, event.extra["ids"])
        else:
            push_workspace_refresh(
                event.workspace_id,
                event.event_name,
                {"client_id": event.client_id, **event.extra},
            )
```

### Single vs batch vs signal — decision rule

| Command type | Entities changed | Event |
|---|---|---|
| Single-entity create/update/delete | 1 | `entity:created` / `entity:updated` / `entity:deleted` |
| Bulk command | 2–200 | `entity:batch-updated` with `extra={"ids": [...]}` |
| Mass operation (import, reconcile) | 200+ | `entity:invalidate-all` (no IDs) |

---

## File structure

```
services/infra/events/
├── domain_event.py        # Event, WorkspaceEvent, UserEvent, ConversationRoomEvent dataclasses
├── build_event.py         # build_workspace_event(), build_user_event(), build_conversation_event()
├── event_bus.py           # register(), dispatch()
├── bootstrap.py           # register_default_handlers() — called on package import
├── realtime_push.py       # transport selection — push_workspace_*, push_to_conversation, push_to_user
├── worker_shift_realtime.py  # data-carrying emitter — sockets only, no audit, no webhooks
└── handlers/
    ├── socket_handler.py  # conversation + workspace + user socket delivery
    ├── audit_handler.py   # audit log writes
    └── webhook_handler.py # enqueues webhook delivery task
```

---

## Schema versioning

Event payloads evolve as domains add fields. `extra` is a free-form dict — handlers must use `.get()` with defaults for any key that may not exist in older events:

```python
# safe — works whether "new_status" is present or not
new_status = event.extra.get("new_status")
```

Adding a new key to `extra` is non-breaking. Renaming or removing a key is breaking and requires coordinating handler updates before the builder change is deployed.

---

## Rules

- **Commands never import handlers directly.** Commands call `event_bus.dispatch()`, or a
  data-carrying emitter that calls `realtime_push` — never a handler, and never `worker_emitter`.
- **`dispatch()` works from any process.** Background jobs use it exactly as commands do — never
  reach past it to `worker_emitter`, and never add a per-process registration hook.
- **Skipping the bus costs you audit and webhooks.** A data-carrying emitter reaches sockets only.
  If the event needs auditing, put it on the bus instead of extending the emitter.
- **Handlers never query the database for event context.** Events must carry enough information for handlers to act. If a handler needs more data, the builder should include it in `extra`.
- **Dispatch is always after commit.** `event_bus.dispatch(pending_events)` is always the line after `async with ctx.session.begin()` exits, never inside it.
- **One handler = one side effect.** Do not combine socket push and email send in one handler.
- **Slow or unreliable work belongs in a task worker.** Handlers must return in milliseconds. Enqueue a task for anything that makes network calls.
- **`client_id` is always the entity identifier.** Never put alternate integer IDs in events.
