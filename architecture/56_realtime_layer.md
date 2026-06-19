# 56 — Real-Time Layer

## What this document covers

The real-time layer of ManagerBeyo pushes entity change signals and in-app notifications to connected frontend clients without polling. This document describes how the layer is actually implemented: the Socket.IO transport, connection lifecycle, room model, event bus integration, notification pipeline, and presence system.

> **Note on doc 13 (`13_sockets.md`):** That document describes a native FastAPI WebSocket + Redis pub/sub design that was planned but not implemented. The actual implementation uses `python-socketio` as described here.

---

## Architecture overview

```
Frontend client (socket.io-client)
        │
        │  WebSocket upgrade (JWT in Socket.IO auth object)
        ▼
socketio.AsyncServer  (ASGI mode)
        │
        │  wrapped by socketio.ASGIApp — same process, same port as FastAPI
        ▼
ConnectionManager  (in-memory, per-process)
        │  manages room membership: user:{id}, workspace:{id}, conversation:{id}
        ▼
Event dispatch (after DB commit)
        │
        ├─ socket_handler.py → sio.emit() → room
        ├─ audit_handler.py  → audit log
        └─ webhook_handler.py → enqueues task

Notification pipeline (async, via task queue)
        │
        └─ notification_worker
                │  creates Notification rows
                │  emits notification:new → user room
                └─ enqueues SEND_PUSH_NOTIFICATION → VAPID web push
```

---

## Transport: python-socketio

The backend uses `python-socketio` (`AsyncServer`, ASGI mode), not native FastAPI WebSocket endpoints.

```python
# beyo_manager/sockets/__init__.py
import socketio
from beyo_manager.config import settings

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.frontend_origins,
)
socket_app = None
```

The `sio` singleton is the Socket.IO server. `socket_app` is set to a `socketio.ASGIApp(sio, other_asgi_app=fastapi_app)` in `create_app()`, making both FastAPI and Socket.IO available on the same process and port. The ASGI app is what uvicorn serves.

The frontend must use `socket.io-client` — not a raw WebSocket client. The Socket.IO protocol is not compatible with a plain `new WebSocket()`.

---

## Connection lifecycle

### Authentication

Clients authenticate by passing the JWT in the Socket.IO `auth` object:

```js
// Client-side
io(SERVER_URL, { auth: (cb) => cb({ token: getAccessToken() }) })
```

The backend also accepts the token as a query string fallback (`?token=...`), but the `auth` object is preferred because it is called fresh on every reconnect attempt, ensuring the client always sends the current token and not a stale one.

On every `connect` event, `_handle_connect` in `sockets/handlers.py`:
1. Reads the token from `auth.get("token")` or falls back to `QUERY_STRING`
2. Decodes the JWT with `PyJWT` — rejects if invalid or missing
3. Extracts `user_id`, `workspace_id`, `username` from claims
4. Creates a `ConnectionMeta` record and registers it in `ConnectionManager`
5. Calls `sio.enter_room(sid, "user:{user_id}")` and `sio.enter_room(sid, "workspace:{workspace_id}")`
6. Writes `user_online:{user_id}` to Redis (24 h TTL) — best-effort, connection proceeds even if this fails

Returning `False` from `_handle_connect` rejects the connection. The client receives `connect_error`.

### ConnectionMeta

```python
# beyo_manager/sockets/connection_meta.py
@dataclass
class ConnectionMeta:
    user_id:      str
    workspace_id: str
    username:     str
    connected_at: datetime
    entity_views: set[tuple[str, str]]  # (entity_type, entity_client_id) currently viewed
```

`entity_views` tracks every entity the user is actively viewing so the backend can clean up Redis presence on disconnect without the client sending `leave_entity`.

### Disconnect

`_handle_disconnect` in `sockets/handlers.py`:
1. Pops `ConnectionMeta` from `ConnectionManager`
2. Calls `mark_left()` in Redis for every entry in `meta.entity_views`
3. If no other connections remain for this user, deletes `user_online:{user_id}` from Redis

---

## Room model

Three room types. All room membership is managed server-side.

| Room name | Membership | Joined by |
|---|---|---|
| `user:{user_id}` | All active connections for one user | Automatically on `connect` |
| `workspace:{workspace_id}` | All active connections in one workspace | Automatically on `connect` |
| `conversation:{conversation_client_id}` | Users currently viewing a specific conversation | Server-side when `view_entity` is received with `entity_type: 'conversation'` |

The client **never** emits a room join or room leave request. Room membership is entirely driven by server logic.

---

## Client-emitted events

Two events beyond the built-in Socket.IO `connect` / `disconnect`:

### `view_entity`

```python
# Payload the client must send
{ "entity_type": str, "entity_client_id": str }
```

Handler: `_handle_view_entity` in `sockets/handlers.py`

Effects:
- Writes `presence:{entity_type}:{entity_client_id}` Redis SET — adds `user_id`, sets 90 s TTL
- Adds `(entity_type, entity_client_id)` to `meta.entity_views`
- Enqueues `RECORD_VIEW_START` analytics task
- **If `entity_type == "conversation"`**: calls `sio.enter_room(sid, "conversation:{entity_client_id}")` so the client receives `conversation:message-*` events

### `leave_entity`

```python
{ "entity_type": str, "entity_client_id": str }
```

Handler: `_handle_leave_entity`

Effects:
- Removes `user_id` from the Redis presence SET
- Removes from `meta.entity_views`
- Enqueues `RECORD_VIEW_END` analytics task
- **If `entity_type == "conversation"`**: calls `sio.leave_room(sid, "conversation:{entity_client_id}")`

---

## Server-emitted events

Events are pushed from `ConnectionManager` via `sio.emit()`:

```python
# beyo_manager/sockets/manager.py
async def send_to_user(self, user_id: str, event: str, payload: dict) -> None:
    await sio.emit(event, payload, room=f"user:{user_id}")

async def broadcast_to_room(self, room: str, event: str, payload: dict) -> None:
    await sio.emit(event, payload, room=room)
```

### Payload shape

Every server-to-client payload is built by `socket_handler.py`:

```python
{"client_id": event.client_id, **event.extra}
```

The `client_id` field is always present and is the public client-facing identifier of the changed entity. Extra context fields (`new_state`, `user_id`, etc.) are merged in when the event carries them. The payload **never** contains full entity data — it is a change signal. The client fetches updated data from the REST API.

See the frontend event catalog (`HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619`) for the complete list.

---

## Event bus integration

Commands trigger socket pushes via the event bus, not directly:

```
Command
  ├─ mutates DB inside ctx.session.begin()
  ├─ builds Event instances (WorkspaceEvent / UserEvent / ConversationRoomEvent)
  └─ await dispatch(pending_events)
              │
        event_bus calls each registered handler
              ├─ socket_handler  → routes to sio.emit()
              ├─ audit_handler   → audit log
              └─ webhook_handler → enqueues webhook task
```

### Event types and routing

```python
# beyo_manager/services/infra/events/domain_event.py
class WorkspaceEvent(Event):     # → broadcast to workspace:{workspace_id}
class UserEvent(Event):          # → send to user:{user_id}
class ConversationRoomEvent(Event):  # → broadcast to conversation:{conversation_id}
```

The socket handler routes `ConversationRoomEvent` first (most specific), then `WorkspaceEvent`, then `UserEvent`. If a `WorkspaceEvent` carries `extra["ids"]`, it is routed as a batch event (`push_workspace_batch`) which sends `{ ids: [...] }` instead of a single `client_id`.

### Builder functions

```python
# Standard workspace event (covers the majority of commands)
build_workspace_event(entity, "task:created")
build_workspace_event(entity, "task:state-changed", extra={"new_state": state.value})

# User-specific event
build_user_event(user_id=uid, event_name="notification:new", client_id=obj.client_id)

# Conversation room event
build_conversation_event(message, "conversation:message-created",
    conversation_id=conv.client_id, workspace_id=ctx.workspace_id)
```

---

## Notification pipeline

Notifications are created and delivered asynchronously by the `notification_worker`.

```
Command or scheduled job
    └─ enqueues CREATE_NOTIFICATIONS task to queue:notifications

notification_worker (separate process)
    └─ handle_create_notifications()
            │
            ├─ get_viewers() — Redis presence check for each exclude_viewing context
            │   Users currently viewing the entity are excluded (they see live updates already)
            │
            ├─ For each remaining user:
            │   ├─ INSERT Notification row (user_id, type, title, body, entity refs)
            │   ├─ build_user_event(user_id, "notification:new", client_id=notification.client_id)
            │   └─ enqueue SEND_PUSH_NOTIFICATION task (within same transaction)
            │
            ├─ session.commit()
            └─ dispatch(pending_events)  → notification:new socket event → user room
```

### Push notifications (PWA / VAPID)

`SEND_PUSH_NOTIFICATION` is picked up by `notification_worker`:
1. Loads all `PushSubscription` rows for the user
2. Calls `send_web_push(endpoint, p256dh, auth, payload)` for each subscription
3. Automatically removes subscriptions that return HTTP 410 (browser unsubscribed)

The push payload sent to the browser service worker:
```python
{
    "title": title,
    "body":  body,
    "data": {
        "notification_client_id": notification.client_id,
        "entity_type":            entity_type,
        "entity_client_id":       entity_client_id,
    },
}
```

---

## Presence system

Redis-backed, cross-process. Two independent subsystems:

### Entity presence (viewing)

Purpose: track which users are currently viewing a given entity, used to suppress notifications for users who are already seeing live updates.

```
Key:   presence:{entity_type}:{entity_client_id}
Type:  Redis SET of user_id strings
TTL:   90 seconds (refreshed on every view_entity)
```

`mark_viewing(entity_type, entity_client_id, user_id)` — SADD + EXPIRE  
`mark_left(entity_type, entity_client_id, user_id)` — SREM  
`get_viewers(entity_type, entity_client_id)` — SMEMBERS → `set[str]`

Called by: socket `view_entity` / `leave_entity` handlers and `_cleanup_presence` on disconnect.

Used by: `handle_create_notifications` to compute the exclusion set before inserting notification rows.

### User online status

Purpose: a coarse online/offline signal (not yet fully used in the product, available for future features).

```
Key:   user_online:{user_id}
Type:  Redis string ("1")
TTL:   24 hours
```

Set on `connect`, deleted on `disconnect` when no other connections remain for the user.

---

## Worker processes

The real-time layer spans multiple worker processes beyond the API server:

| Worker | Queue | Handles |
|---|---|---|
| `notification_worker` | `queue:notifications` | `CREATE_NOTIFICATIONS`, `SEND_PUSH_NOTIFICATION`, `NOTIFICATION`, `DELAYED_*`, `RECURRING_*` |
| `presence_worker` | `queue:presence` | `RECORD_VIEW_START`, `RECORD_VIEW_END` (analytics) |
| `tasks_worker` | `queue:tasks` | `DELAYED_STEP_COMPLETION` |
| `task_router_process` | — | Routes tasks to the correct queue |

Workers use `rq` (Redis Queue) and are started as separate processes. They do not hold WebSocket connections. Socket pushes from the notification pipeline go through the `dispatch()` event bus, which calls `socket_handler` synchronously in the notification worker's async loop — the `sio` singleton is imported from the same package and works because the ASGI app and workers share the same codebase (single-process model; workers import the app package).

---

## File map

```
beyo_manager/
├── sockets/
│   ├── __init__.py          — sio singleton, socket_app reference
│   ├── connection_meta.py   — ConnectionMeta dataclass
│   ├── manager.py           — ConnectionManager (room joins, sio.emit wrappers)
│   ├── handlers.py          — connect, disconnect, view_entity, leave_entity handlers
│   └── register.py          — sio.on() registrations called from create_app()
│
├── services/infra/events/
│   ├── domain_event.py      — Event, WorkspaceEvent, UserEvent, ConversationRoomEvent
│   ├── build_event.py       — build_workspace_event(), build_user_event(), build_conversation_event()
│   ├── event_bus.py         — register(), dispatch()
│   ├── realtime_push.py     — push_workspace_refresh/batch, push_to_conversation, push_to_user
│   └── handlers/
│       ├── socket_handler.py   — routes domain events to ConnectionManager
│       ├── audit_handler.py    — audit log writes
│       └── webhook_handler.py  — enqueues webhook delivery task
│
├── services/infra/presence/
│   ├── presence.py          — mark_viewing(), mark_left(), get_viewers() (Redis SET)
│   └── user_online_key.py   — set_user_online(), delete_user_online() (Redis string)
│
├── services/infra/push/
│   └── vapid.py             — send_web_push() (pywebpush)
│
└── workers/
    ├── notification_worker.py     — queue:notifications process entry point
    ├── presence_worker.py         — queue:presence process entry point
    ├── tasks_worker.py            — queue:tasks process entry point
    └── task_router_process.py     — task routing entry point
```

---

## Rules

- Commands never call `sio.emit()` directly. Socket pushes always go through `dispatch()` → `socket_handler`.
- Room membership is never driven by client requests. The client emits `view_entity` / `leave_entity` for entity semantics; room joins are a server-side consequence.
- All payload identifiers use `client_id`. Never integer PKs.
- `_handle_connect` returning `False` rejects the connection — no exception needed.
- The `entity_views` set in `ConnectionMeta` is the source of truth for disconnect cleanup. The Redis TTL (90 s) is the last-resort fallback for process crashes.
- Socket pushes after DB commit are best-effort. A failed socket push does not roll back the transaction.
