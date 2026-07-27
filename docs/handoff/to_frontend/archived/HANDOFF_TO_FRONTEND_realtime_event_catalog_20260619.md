# HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source: live backend code audit (`beyo_manager/services/commands/`, `beyo_manager/services/tasks/`)

---

## Context

This is the authoritative Socket.IO event catalog for ManagerBeyo. Every event the backend can emit and every event the client must emit is listed here. Use this to populate `ServerToClientEvents` and `ClientToServerEvents` in `src/lib/socket-types.ts` and to write the per-feature `socket-events.ts` handler files.

Read this alongside the contract corrections handoff (`HANDOFF_TO_FRONTEND_realtime_contract21_corrections_20260619`).

---

## Payload shape rules

These rules apply to every event in this catalog without exception:

1. **`client_id`** — every payload carries `client_id` as the entity identifier. Never `id`.
2. **Extra fields** — some events carry additional context fields alongside `client_id` (e.g. `new_state`). The frontend must use `.get()`-style defensive access (TypeScript optional chaining) because the extra field list may grow.
3. **No full entity data** — payloads never contain the full entity. They are change signals. The frontend fetches updated data from the REST API in response.
4. **Routing is via rooms, not payload** — workspace-scoped events are already delivered only to the right workspace. The payload does not include `workspace_id`.

---

## Client → Server events

The client emits exactly two events beyond the built-in Socket.IO `connect` / `disconnect`.

```ts
export type ClientToServerEvents = {
  /**
   * Tell the backend the user is viewing an entity.
   * Effects:
   *   - Writes Redis presence for ALL entity types (used to suppress notifications)
   *   - For entity_type === 'conversation': also joins the conversation Socket.IO room
   *     so the client receives conversation:message-* events
   *
   * Emit when a detail surface mounts. Re-emit is idempotent.
   */
  'view_entity': (payload: {
    entity_type:      string;  // 'case' | 'conversation' | 'task' | etc.
    entity_client_id: string;
  }) => void;

  /**
   * Tell the backend the user stopped viewing an entity.
   * Effects:
   *   - Removes Redis presence key
   *   - For entity_type === 'conversation': leaves the Socket.IO room
   *
   * Emit when a detail surface unmounts. Emitted automatically on disconnect cleanup.
   */
  'leave_entity': (payload: {
    entity_type:      string;
    entity_client_id: string;
  }) => void;
};
```

**Notes:**
- The backend silently ignores unknown `entity_type` values — no error is returned.
- If the client disconnects without emitting `leave_entity`, the backend cleans up presence on the `disconnect` event.
- No acknowledgment callback is needed — these are fire-and-forget.

---

## Server → Client events

### Scope legend

| Scope | Who receives it | How rooms work |
|---|---|---|
| **workspace** | All connected users in the same workspace | Joined automatically on connect |
| **user** | Only the specific user targeted | Joined automatically on connect |
| **conversation** | Only users who have emitted `view_entity` with `entity_type: 'conversation'` for this conversation | Joined when `view_entity` is received |

---

### Tasks

All task events are workspace-scoped.

```ts
// Task entity created
'task:created': (payload: { client_id: string; working_section_ids: string[] }) => void;

// Task metadata changed (title, assignee, dates, etc.)
'task:updated': (payload: { client_id: string }) => void;

// Task deleted
'task:deleted': (payload: { client_id: string }) => void;

// Task transitioned to a new state (open → in_progress → resolved → etc.)
'task:state-changed': (payload: {
  client_id: string;
  new_state:  string;  // TaskStateEnum value
}) => void;
```

### Task steps

All task step events are workspace-scoped. `client_id` refers to the **step**, not the parent task.

```ts
// A step was created on an existing task
'task:step-created': (payload: {
  client_id:          string;  // step client_id
  working_section_id: string;
}) => void;

// A step was removed from a task
'task:step-deleted': (payload: {
  client_id:          string;  // step client_id
  working_section_id: string;
}) => void;

// A worker was assigned to a step
'task:step-assigned': (payload: {
  client_id: string;  // step client_id
  user_id:   string;  // the user assigned
}) => void;

// Step transitioned to a new state
'task:step-state-changed': (payload: {
  client_id: string;  // step client_id
  new_state:  string;  // TaskStepStateEnum value — 'pending' | 'working' | 'paused' | 'completed' | etc.
}) => void;
```

**Note on auto-pause:** When a step is started (`working`) and the worker is already in `working` state on another step, the backend auto-pauses the previous step. This emits a second `task:step-state-changed` event for the auto-paused step in the same operation.

---

### Cases

Most case events are workspace-scoped. `client_id` refers to the case. Exception: `case:participant-added` is a `UserEvent` emitted only to each participant's own `user:{id}` room, not broadcast to the workspace.

```ts
// Case created
'case:created': (payload: { client_id: string }) => void;

// Case metadata updated
'case:updated': (payload: { client_id: string }) => void;

// Case moved to a new state
'case:state-changed': (payload: {
  client_id: string;
  new_state:  string;  // CaseStateEnum value
}) => void;

// Sent to each newly added participant on their user:{id} room only (UserEvent, not workspace-scoped).
// unread_count is the total messages in the case they have not yet read when they are added.
'case:participant-added': (payload: { client_id: string; unread_count: number }) => void;

// A user was removed from the case's participant list
'case:participant-removed': (payload: { client_id: string }) => void;

// A conversation was created inside a case
'case:conversation-created': (payload: { client_id: string }) => void;
```

---

### Conversation messages

Conversation message events are **conversation-scoped** — only users who emitted `view_entity` with `entity_type: 'conversation'` for this conversation receive them. `client_id` refers to the **message**, not the conversation.

```ts
// A new message was sent in the conversation
'conversation:message-created': (payload: { client_id: string }) => void;

// An existing message was edited
'conversation:message-edited': (payload: { client_id: string }) => void;

// A message was soft-deleted
'conversation:message-deleted': (payload: { client_id: string }) => void;
```

---

### Items

All item events are workspace-scoped.

```ts
'item:created': (payload: { client_id: string }) => void;
'item:updated': (payload: { client_id: string }) => void;
'item:deleted': (payload: { client_id: string }) => void;
```

---

### Item upholsteries

All item upholstery events are workspace-scoped. `client_id` refers to the **ItemUpholstery** entity, not the parent item.

```ts
// An upholstery selection was added to an item
'item:upholstery-created': (payload: { client_id: string }) => void;

// Upholstery selection or quantity changed (includes upholstery swap)
'item:upholstery-updated': (payload: { client_id: string }) => void;

// Item upholstery was soft-deleted
'item:upholstery-deleted': (payload: { client_id: string }) => void;

// Requirement state changed (MISSING_QUANTITY → AVAILABLE/NEEDS_ORDERING,
// AVAILABLE/NEEDS_ORDERING → ORDERED, ORDERED/NEEDS_ORDERING → AVAILABLE, etc.)
// client_id is the ItemUpholstery's client_id, not the requirement row's own id.
'item:upholstery-requirement-state-changed': (payload: {
  client_id: string;
  new_state:  string;  // ItemUpholsteryRequirementStateEnum value
}) => void;
```

---

### Working sections

All working section events are workspace-scoped.

```ts
'working_section:created': (payload: { client_id: string }) => void;
'working_section:updated': (payload: { client_id: string }) => void;
'working_section:deleted': (payload: { client_id: string }) => void;
```

---

### Upholstery entities

All upholstery entity events are workspace-scoped. `client_id` refers to the **Upholstery** entity or the **UpholsteryInventory** entity as noted per event.

```ts
// Upholstery properties changed (name, code, image, favorite)
'upholstery:updated': (payload: { client_id: string }) => void;  // client_id = upholstery

// Upholstery and its inventory were soft-deleted together
'upholstery:deleted': (payload: { client_id: string }) => void;  // client_id = upholstery

// Inventory settings changed (thresholds, planning position, projected value, etc.)
'upholstery:inventory-updated': (payload: { client_id: string }) => void;  // client_id = inventory

// Inventory (and parent upholstery) was soft-deleted
'upholstery:inventory-deleted': (payload: { client_id: string }) => void;  // client_id = inventory
```

---

### Notifications

Notification events are **user-scoped** — only the target user receives them.

```ts
/**
 * A new in-app notification was created for this user.
 * Payload carries only the pointer (client_id). The title, body, and entity
 * context live in the database — fetch them via the REST API.
 */
'notification:new': (payload: { client_id: string }) => void;
```

#### Dual delivery model

Notifications are delivered through two independent paths depending on whether the app is open. Both are triggered by the same backend `CREATE_NOTIFICATIONS` task — they are not mutually exclusive.

**Path 1 — In-app (app open, socket connected)**

The socket event `notification:new { client_id }` is a signal, not the message. On receiving it, invalidate the notification list query. TanStack Query refetches from the REST API, which returns the full content.

```
GET /api/v1/notifications?unread_only=true&limit=30

Response:
{
  "notifications": [
    {
      "client_id":         "...",
      "notification_type": "...",
      "title":             "...",    ← full text
      "body":              "...",    ← full text
      "entity_type":       "...",
      "entity_client_id":  "...",
      "read_at":           null,
      "created_at":        "..."
    }
  ],
  "has_more":     false,
  "unread_count": 3    ← badge value, always included
}
```

The `unread_count` is included in every list response — no separate request needed for the badge.

Correct handler:
```ts
'notification:new': ({ client_id }, { queryClient }) => {
  queryClient.invalidateQueries({
    queryKey:    notificationKeys.list(),
    refetchType: 'active',
  });
  // unread count is returned inside the list response — no separate invalidation needed
  // Do NOT call notify() here — you don't have the content yet
},
```

**Path 2 — Background push (app closed, no socket connection)**

When the app is closed the socket is not connected, so `notification:new` is never received. The backend enqueues a `SEND_PUSH_NOTIFICATION` task in the same DB transaction that created the notification row. That task calls the VAPID API and delivers a push payload that contains the full title and body:

```json
{
  "title": "...",
  "body":  "...",
  "data": {
    "notification_client_id": "...",
    "entity_type":            "...",
    "entity_client_id":       "..."
  }
}
```

The browser push service delivers this to the service worker even when the app is completely closed. The service worker has everything it needs to display the system notification — no HTTP fetch required:

```js
// service-worker.js
self.addEventListener('push', (event) => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      data: data.data,   // used on click to navigate to the entity
    })
  );
});
```

**Summary**

| State | Delivery path | Content source |
|---|---|---|
| App open, socket connected | `notification:new` → `GET /notifications` | REST API |
| App closed / socket disconnected | VAPID push → service worker | Push payload (no fetch) |
| App was closed, user reopens | Socket reconnect → `invalidateQueries` | REST API on mount |

#### Push subscription endpoints

The frontend is responsible for registering the browser's `PushSubscription` with the backend after the user grants push permission.

```
GET  /api/v1/notifications/vapid-public-key   — public, no auth — fetch before subscribing
POST /api/v1/notifications/push-subscription  — register a new device subscription
DELETE /api/v1/notifications/push-subscription — remove on permission revoke or sign-out
```

The backend auto-removes stale subscriptions when the browser push service returns HTTP 410 (user revoked permission in the browser). No manual cleanup is needed for that case.

---

### User membership

User membership events are **user-scoped** — only the affected user receives them. This allows the UI to reactively update without a page reload when the user's working section assignments change.

```ts
/**
 * The user's working section memberships changed (assigned or unassigned).
 * extra.working_section_ids contains the IDs involved in the change,
 * but it is safer to invalidate the full working section membership query
 * rather than trying to merge partials.
 */
'user:working_sections_updated': (payload: {
  client_id:            string;   // equals user_id in this event
  working_section_ids:  string[];
}) => void;
```

---

## Complete `ServerToClientEvents` type

```ts
// src/lib/socket-types.ts

export type ServerToClientEvents = {
  // --- Tasks ---
  'task:created':            (payload: { client_id: string; working_section_ids: string[] }) => void;
  'task:updated':            (payload: { client_id: string }) => void;
  'task:deleted':            (payload: { client_id: string }) => void;
  'task:state-changed':      (payload: { client_id: string; new_state: string }) => void;

  // --- Task steps ---
  'task:step-created':       (payload: { client_id: string; working_section_id: string }) => void;
  'task:step-deleted':       (payload: { client_id: string; working_section_id: string }) => void;
  'task:step-assigned':      (payload: { client_id: string; user_id: string }) => void;
  'task:step-state-changed': (payload: { client_id: string; new_state: string }) => void;

  // --- Cases ---
  'case:created':              (payload: { client_id: string }) => void;
  'case:updated':              (payload: { client_id: string }) => void;
  'case:state-changed':        (payload: { client_id: string; new_state: string }) => void;
  'case:participant-added':    (payload: { client_id: string; unread_count: number }) => void;
  'case:participant-removed':  (payload: { client_id: string }) => void;
  'case:conversation-created': (payload: { client_id: string }) => void;

  // --- Conversation messages (conversation-scoped) ---
  'conversation:message-created': (payload: { client_id: string }) => void;
  'conversation:message-edited':  (payload: { client_id: string }) => void;
  'conversation:message-deleted': (payload: { client_id: string }) => void;

  // --- Items ---
  'item:created': (payload: { client_id: string }) => void;
  'item:updated': (payload: { client_id: string }) => void;
  'item:deleted': (payload: { client_id: string }) => void;

  // --- Working sections ---
  'working_section:created': (payload: { client_id: string }) => void;
  'working_section:updated': (payload: { client_id: string }) => void;
  'working_section:deleted': (payload: { client_id: string }) => void;

  // --- Item upholsteries ---
  'item:upholstery-created': (payload: { client_id: string }) => void;
  'item:upholstery-updated': (payload: { client_id: string }) => void;
  'item:upholstery-deleted':                   (payload: { client_id: string }) => void;
  'item:upholstery-requirement-state-changed': (payload: { client_id: string; new_state: string }) => void;

  // --- Upholstery entities ---
  'upholstery:updated':           (payload: { client_id: string }) => void;
  'upholstery:deleted':           (payload: { client_id: string }) => void;
  'upholstery:inventory-updated': (payload: { client_id: string }) => void;
  'upholstery:inventory-deleted': (payload: { client_id: string }) => void;

  // --- Notifications (user-scoped) ---
  'notification:new': (payload: { client_id: string }) => void;

  // --- User membership (user-scoped) ---
  'user:working_sections_updated': (payload: {
    client_id:           string;
    working_section_ids: string[];
  }) => void;
};
```

---

## Handler responsibility matrix

Which feature owns which events and what it should do:

| Event | Feature file | Action |
|---|---|---|
| `task:created` | `features/tasks/socket-events.ts` | Invalidate task list; use `working_section_ids` for section-scoped list filtering if needed |
| `task:updated` | `features/tasks/socket-events.ts` | Invalidate task detail + list |
| `task:deleted` | `features/tasks/socket-events.ts` | Remove task detail from cache, invalidate list |
| `task:state-changed` | `features/tasks/socket-events.ts` | Invalidate task detail + list |
| `task:step-created` | `features/tasks/socket-events.ts` | Invalidate task detail (step list); filter by `working_section_id` for section-specific views |
| `task:step-deleted` | `features/tasks/socket-events.ts` | Remove step detail from cache, invalidate task detail; filter by `working_section_id` for section-specific views |
| `task:step-assigned` | `features/tasks/socket-events.ts` | Invalidate step detail + task detail |
| `task:step-state-changed` | `features/tasks/socket-events.ts` | Invalidate step detail + task detail |
| `case:created` | `features/cases/socket-events.ts` | Invalidate case list |
| `case:updated` | `features/cases/socket-events.ts` | Invalidate case detail + list |
| `case:state-changed` | `features/cases/socket-events.ts` | Invalidate case detail + list |
| `case:participant-added` | `features/cases/socket-events.ts` | Add case to "my cases" list; set unread badge for this case to `payload.unread_count` |
| `case:participant-removed` | `features/cases/socket-events.ts` | Invalidate case detail |
| `case:conversation-created` | `features/cases/socket-events.ts` | Invalidate case detail (conversation list embedded) |
| `conversation:message-created` | `features/cases/socket-events.ts` | Invalidate message list for that conversation |
| `conversation:message-edited` | `features/cases/socket-events.ts` | Invalidate message detail + list |
| `conversation:message-deleted` | `features/cases/socket-events.ts` | Invalidate message list |
| `item:created` | `features/items/socket-events.ts` | Invalidate item list |
| `item:updated` | `features/items/socket-events.ts` | Invalidate item detail + list |
| `item:deleted` | `features/items/socket-events.ts` | Remove item detail, invalidate list |
| `working_section:created` | `features/working-sections/socket-events.ts` | Invalidate section list |
| `working_section:updated` | `features/working-sections/socket-events.ts` | Invalidate section detail + list |
| `working_section:deleted` | `features/working-sections/socket-events.ts` | Remove section detail, invalidate list |
| `item:upholstery-created` | `features/items/socket-events.ts` | Invalidate item upholstery list for the parent item |
| `item:upholstery-updated` | `features/items/socket-events.ts` | Invalidate item upholstery detail + parent item detail |
| `item:upholstery-deleted` | `features/items/socket-events.ts` | Remove item upholstery detail from cache, invalidate parent item detail |
| `item:upholstery-requirement-state-changed` | `features/items/socket-events.ts` | Invalidate item upholstery detail (requirement state drives availability badge) |
| `upholstery:updated` | `features/upholstery/socket-events.ts` | Invalidate upholstery detail + list |
| `upholstery:deleted` | `features/upholstery/socket-events.ts` | Remove upholstery detail, invalidate list |
| `upholstery:inventory-updated` | `features/upholstery/socket-events.ts` | Invalidate upholstery inventory detail |
| `upholstery:inventory-deleted` | `features/upholstery/socket-events.ts` | Remove inventory detail, invalidate upholstery list |
| `notification:new` | `src/app/socket-registry.ts` (app-level) | Invalidate notification list + unread count |
| `user:working_sections_updated` | `src/app/socket-registry.ts` or `features/working-sections/` | Invalidate current user's section membership query |

---

## Conversation message event note

`conversation:message-*` events are only delivered while the client is in the conversation room. The client joins the conversation room by emitting `view_entity` with `entity_type: 'conversation'`.

The handler for these events needs the conversation `client_id` to build the right query key, but the payload only carries the message `client_id`. The handler should invalidate the message list for the conversation the user is currently viewing:

```ts
// features/cases/socket-events.ts
'conversation:message-created': ({ client_id }, { queryClient }) => {
  // The message client_id is a pointer — invalidate the whole message list
  // for any conversation the user is currently viewing.
  // The queryKey for message lists should be scoped to conversationId.
  queryClient.invalidateQueries({
    queryKey: conversationKeys.messages(),  // or a predicate filter by entity type
    refetchType: 'active',
  });
},
```

If your query keys for conversation messages are scoped by conversation ID (recommended), consider using a `queryClient.invalidateQueries` predicate to match only the active conversation surface rather than invalidating all message queries.

---

## What is NOT in the catalog (future extensions)

The batch event infrastructure exists in the backend (`push_workspace_batch`) but no command currently emits batch events. If a bulk operation is added, expect events named `entity:batch-updated` with payload `{ ids: string[] }` rather than a per-entity `client_id`. The `batchInvalidation` utility in the contract is the correct handler for those.
