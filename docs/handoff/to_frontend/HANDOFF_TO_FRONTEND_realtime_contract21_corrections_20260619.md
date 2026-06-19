# HANDOFF_TO_FRONTEND_realtime_contract21_corrections_20260619

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_realtime_contract21_corrections_20260619`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source: live backend code audit (`beyo_manager/sockets/`, `beyo_manager/services/infra/events/`)

---

## Context

Frontend contract `21_realtime.md` was written as a framework document with generic invoice/payment examples. Before building the real-time layer, five concrete mismatches between the contract design and the actual backend must be corrected. The overall architecture (SocketProvider, event registry, TanStack Query invalidation strategy) is sound and does not change.

---

## Corrections required

### Correction 1 — Room joining is server-managed; remove `room:join` / `room:leave`

**What the contract says:**
The `SocketProvider` emits `room:join` to join workspace and user rooms on every connect. The `useSocketRoom` hook emits `room:join` / `room:leave` for feature-specific rooms.

**What the backend actually does:**
`room:join` and `room:leave` **are not registered Socket.IO events**. The backend never listens for them. Instead:

- The `workspace:{workspace_id}` and `user:{user_id}` rooms are joined **automatically, server-side**, in the Socket.IO `connect` handler the moment a valid JWT is received. The client never needs to request this.
- Feature-specific rooms (conversations) are joined server-side when the client emits `view_entity` with `entity_type: "conversation"`.

**Changes to make:**

Remove from `ClientToServerEvents`:
```ts
// DELETE THESE — backend does not handle them
'room:join':  (payload: { room: string }, ack: (ok: boolean) => void) => void;
'room:leave': (payload: { room: string }) => void;
```

Remove from `SocketProvider`'s `on('connect')` handler:
```ts
// DELETE THIS BLOCK — server joins these rooms automatically on connect
if (workspaceId) {
  s.emit('room:join', { room: `workspace:${workspaceId}` }, (ok) => { ... });
}
if (userId) {
  s.emit('room:leave', { room: `user:${userId}` }, () => {});
}
```

---

### Correction 2 — Replace `useSocketRoom` with `useEntityView`

The `useSocketRoom` hook emits `room:join` / `room:leave`, which the backend ignores. The actual client events for entering/leaving entity views are `view_entity` and `leave_entity`.

**Client-emitted event shapes (replace `ClientToServerEvents`):**

```ts
export type ClientToServerEvents = {
  'view_entity':  (payload: { entity_type: string; entity_client_id: string }) => void;
  'leave_entity': (payload: { entity_type: string; entity_client_id: string }) => void;
};
```

**Replace `useSocketRoom` with `useEntityView`:**

```ts
// src/hooks/use-entity-view.ts
import { useEffect } from 'react';
import { useSocket } from '@/providers/SocketProvider';

export function useEntityView(entityType: string, entityClientId: string | null) {
  const socket = useSocket();

  useEffect(() => {
    if (!socket || !entityClientId) return;

    socket.emit('view_entity', { entity_type: entityType, entity_client_id: entityClientId });

    return () => {
      socket.emit('leave_entity', { entity_type: entityType, entity_client_id: entityClientId });
    };
  }, [socket, entityType, entityClientId]);
}
```

**What this does on the backend:**
- Writes a Redis presence key (`presence:{entity_type}:{entity_client_id}` → SET of user_ids, 90 s TTL) for all entity types — used by the notification system to skip users currently viewing an entity.
- For `entity_type === "conversation"` specifically: also joins the `conversation:{entity_client_id}` Socket.IO room so the client receives `conversation:message-*` events.

**Usage in feature controllers:**
```ts
// features/cases/controllers/use-conversation-detail.controller.ts
export function useConversationDetailController(conversationId: string) {
  // Join conversation room while this surface is open
  useEntityView('conversation', conversationId);
  // ...
}

// features/cases/controllers/use-case-detail.controller.ts
export function useCaseDetailController(caseId: string) {
  // Track presence for notification suppression (does NOT join a socket room)
  useEntityView('case', caseId);
  // ...
}
```

---

### Correction 3 — All event payloads use `client_id`, not `id`

**What the contract says:**
Event payloads carry an `id` field:
```ts
'invoice:updated': (payload: { id: InvoiceId; workspace_id: WorkspaceId }) => void;
```

**What the backend sends:**
Every socket event payload is built by `socket_handler.py` as:
```python
{"client_id": event.client_id, **event.extra}
```

The field is always `client_id`. There is no `id` field. There is no `workspace_id` field in the payload either — the room routing handles targeting, not the payload.

**Update all handler signatures:**
```ts
// WRONG
'task:updated': (payload: { id: string }) => void;

// CORRECT
'task:updated': (payload: { client_id: string }) => void;
```

All handlers that read the entity identifier must use `payload.client_id`, not `payload.id`.

---

### Correction 4 — `notification:new` delivers only a pointer; fetch content from the API

**What the contract says:**
```ts
'notification:new': (payload: { id: string; type: string; title: string; message?: string }) => void;
```
The contract's app-level registry handler calls `notify[type](title, message)` directly from the socket payload.

**What the backend sends:**
```python
build_user_event(user_id=obj.user_id, event_name="notification:new", client_id=obj.client_id)
```

The payload is `{ client_id: string }` only. No type, title, or message is included. The backend creates the `Notification` DB record first and then emits only its `client_id` as a signal.

**Correct `ServerToClientEvents` entry:**
```ts
'notification:new': (payload: { client_id: string }) => void;
```

**Correct app-level registry handler:**
```ts
'notification:new': ({ client_id }, { queryClient }) => {
  // Signal that a new notification exists — fetch the list from the API
  queryClient.invalidateQueries({
    queryKey: notificationKeys.list(),
    refetchType: 'active',
  });
  // Optionally: invalidate the unread count key if you have one
  queryClient.invalidateQueries({
    queryKey: notificationKeys.unreadCount(),
    refetchType: 'active',
  });
  // Do NOT call notify() here — you don't have the content yet.
  // The notification UI component reacts when the list query refetches.
},
```

---

### Correction 5 — Remove `auth:session-expired` from `ServerToClientEvents`

**What the contract says:**
```ts
'auth:session-expired': (payload: Record<string, never>) => void;  // server-emitted
```

**What the backend actually does:**
The backend never emits this event. When a JWT is invalid or missing at connect time, the Socket.IO handshake is rejected and the client receives a `connect_error`. The backend has no session invalidation push mechanism.

The contract's `SocketProvider` already handles this correctly via `connect_error`:
```ts
s.on('connect_error', async (err) => {
  if (err.message === 'unauthorized') {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      window.dispatchEvent(new CustomEvent('auth:session-expired'));
    }
  }
});
```

The `auth:session-expired` custom DOM event is **client-generated**, not server-pushed. Remove it from `ServerToClientEvents` entirely — it is not a Socket.IO event the server emits.

---

## Updated type definitions

Replace the type definitions in `src/lib/socket-types.ts` with these corrected signatures. Event names use the actual backend catalog (see companion handoff `HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619`):

```ts
// src/lib/socket-types.ts

// Events the server emits to the client
// — all payloads carry { client_id } as the entity identifier
// — see event catalog handoff for the full list with extra fields
export type ServerToClientEvents = {
  // populate from the event catalog handoff
};

// Events the client emits to the server
export type ClientToServerEvents = {
  'view_entity':  (payload: { entity_type: string; entity_client_id: string }) => void;
  'leave_entity': (payload: { entity_type: string; entity_client_id: string }) => void;
};

export type AppSocket = import('socket.io-client').Socket<
  ServerToClientEvents,
  ClientToServerEvents
>;
```

---

## Summary of changes to `SocketProvider`

| Section | Change |
|---|---|
| `io()` options | No change — `auth: (cb) => cb({ token: getAccessToken() })` is correct |
| `on('connect')` block | **Remove** the `room:join` emits for workspace and user rooms |
| `on('connect_error')` | No change — handles unauthorized reconnect correctly |
| `on('disconnect')` | No change |
| Event registry loop | No change in mechanism — only handler signatures change |
| `on('reconnect_failed')` | No change |

The `workspaceId` and `userId` values from `useAuthStore` can still be read in the provider (e.g. to pass as dependencies to the `useEffect`) but they must not be used to emit room join requests.

---

## What does NOT change

- The SocketProvider architecture (single connection, ref + state split, effect teardown on sign-out)
- The event registry pattern (`socketRegistry`, `SocketEventHandlers`, per-feature `socket-events.ts`)
- The TanStack Query invalidation strategy (`refetchType: 'active'`)
- The reconnect → `invalidateQueries` mitigation
- The `debouncedInvalidation` and `batchInvalidation` utilities
- The `useSocket()` / `useSocketStatus()` hooks
- The "never attach `socket.on()` inside components" rule
