# HANDOFF_TO_FRONTEND_push_notification_deep_link_20260621

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_push_notification_deep_link_20260621`
- Created at (UTC): `2026-06-21T00:00:00Z`
- Owner agent: `Claude Sonnet 4.6`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_notification_message_enrichment_20260621.md`
- Source summary: —

## Backend delivery context

- What backend implemented: VAPID push notifications are sent for task state changes, step state changes, step assignment, case messages, and upholstery requirement state changes. Each push carries a `data` object that identifies the originating entity so the app can route to the correct page on tap.
- API or contract changes: Notification messages are being enriched (see the plan above) but the **payload shape is already stable** — this document describes the current shape and the routing contract the frontend should implement.
- Feature flags/toggles (if any): _none_

## Frontend action required

1. In the service worker `push` event handler, read `event.data.json()` and extract `data.entity_type` and `data.entity_client_id` to determine the deep-link target.
2. When the user taps the notification, call `clients.openWindow(url)` with the resolved URL, or post a message to the active client to navigate in-app.
3. After the notification is tapped (or opened from the in-app notification list), call `POST /api/v1/notifications/mark-read` with `notification_client_ids: [data.notification_client_id]` to mark it read and update the badge count.
4. For `entity_type: "task_step"` — use `data.task_client_id` as the parent task ID when building the deep link; no extra fetch is required from the push payload.
5. For the 4 bulk upholstery notification types (`entity_type: null`) — there is no single deep-link target; navigate to the upholstery requirements list view instead.

---

## Push payload shape

The JSON delivered to the service worker `push` event is:

```json
{
  "title": "<human-readable title>",
  "body":  "<human-readable body>",
  "data": {
    "notification_client_id": "ntf_...",
    "entity_type":            "<string | null>",
    "entity_client_id":       "<string | null>",
    "task_client_id":         "<string | null>"
  }
}
```

### Field reference

| Field | Type | Always present | Description |
|---|---|---|---|
| `title` | `string` | yes | Short heading shown in the OS notification |
| `body` | `string` | yes | Supporting detail line |
| `data.notification_client_id` | `string` | yes | ID of the persisted `Notification` row — use to mark read |
| `data.entity_type` | `string \| null` | yes | Routing discriminant — see table below |
| `data.entity_client_id` | `string \| null` | yes | ID of the entity to open — null for bulk events |
| `data.task_client_id` | `string \| null` | yes | Parent task ID for step notifications; null for non-task-step events |

---

## Deep-link routing table

Route on `data.entity_type`. When `entity_type` is `null` fall through to the default route.

| `entity_type` | `entity_client_id` prefix | Triggered by | Recommended route |
|---|---|---|---|
| `"task"` | `tsk_` | Task resolved / cancelled / failed | Task detail page for `entity_client_id` |
| `"task_step"` | `tss_` | Step state changed / step assigned | Step detail using `task_client_id` + `entity_client_id` |
| `"case"` | `ca_` | New case message | Case conversation page for `entity_client_id` |
| `"item_upholstery"` | `iup_` | Requirements completed / in use | Item upholstery detail for `entity_client_id` |
| `null` | — | Requirements ordered / resolved / available (bulk) | Upholstery requirements list (see note B) |

### Note A — `task_step` navigation

For step notifications, the push payload now includes both IDs needed for navigation:

```json
{
  "entity_type": "task_step",
  "entity_client_id": "tss_...",
  "task_client_id": "tsk_..."
}
```

Recommended behavior:
Use `task_client_id` to open the task detail page and `entity_client_id` to scroll to, focus, or highlight the specific step.

### Note B — bulk upholstery notifications (`entity_type: null`)

These four events affect multiple `item_upholstery` records simultaneously and cannot point to a single entity:

| `notification_type` | Trigger | Suggested fallback route |
|---|---|---|
| `upholstery_requirement_ordered` | `mark_requirements_ordered` or `create_upholstery_order` | Upholstery requirements list |
| `upholstery_requirement_resolved` | `resolve_requirements_after_stock` | Upholstery requirements list |
| `upholstery_requirement_available` | `receive_upholstery_order` | Upholstery requirements list |

---

## All notification types reference

The `notification_type` field is available both in the push `data` (indirectly, via the list API) and in `GET /api/v1/notifications`. It can be used for display icons or grouping in the in-app notification center.

| `notification_type` | Human event | `entity_type` |
|---|---|---|
| `task_state_changed` | Task resolved / cancelled / failed | `"task"` |
| `task_step_state_changed` | Step state transition | `"task_step"` |
| `task_step_assigned` | Step assigned to user | `"task_step"` |
| `case:message` | New message in a case conversation | `"case"` |
| `upholstery_requirement_completed` | Requirements marked completed | `"item_upholstery"` |
| `upholstery_requirement_in_use` | Requirements marked in use | `"item_upholstery"` |
| `upholstery_requirement_ordered` | Requirements ordered (bulk) | `null` |
| `upholstery_requirement_resolved` | Requirements resolved from stock (bulk) | `null` |
| `upholstery_requirement_available` | Requirements available after order received (bulk) | `null` |

---

## Notification REST API

Base path: `GET /api/v1/notifications`
Auth: all roles (ADMIN, MANAGER, SELLER, WORKER)

### `GET /api/v1/notifications`

Paginated notification list for the authenticated user. Use this to populate the in-app notification center.

Query params:

| Param | Type | Default | Description |
|---|---|---|---|
| `unread_only` | `bool` | `false` | Return only unread notifications |
| `limit` | `int` | `30` (max `100`) | Page size |
| `before_client_id` | `string` | — | Keyset cursor: return items older than this notification |

Response shape:

```json
{
  "ok": true,
  "data": {
    "notifications": [
      {
        "client_id":         "ntf_...",
        "notification_type": "task_state_changed",
        "title":             "Task #42 resolved",
        "body":              "#42 · A-1234 · by john",
        "entity_type":       "task",
        "entity_client_id":  "tsk_...",
        "read_at":           null,
        "created_at":        "2026-06-21T10:00:00+00:00"
      }
    ],
    "has_more":     true,
    "unread_count": 3
  }
}
```

### `GET /api/v1/notifications/unread-count`

Lightweight badge count. Call on app foreground or after receiving a `notification:new` realtime event.

Response shape:

```json
{
  "ok": true,
  "data": { "unread_count": 3 }
}
```

### `POST /api/v1/notifications/mark-read`

Mark one or more notifications as read. Call after the user taps a push notification or views the notification center.

Request body:

```json
{
  "notification_client_ids": ["ntf_...", "ntf_..."],
  "mark_all_read": false
}
```

- `notification_client_ids` — list of IDs to mark read. Required unless `mark_all_read` is `true`.
- `mark_all_read` — if `true`, marks all of the user's notifications read. Ignores `notification_client_ids`.

Response shape:

```json
{
  "ok": true,
  "data": {}
}
```

---

## Realtime — `notification:new` event

The backend also emits a realtime socket event when a new notification is created. The frontend should listen for this and refresh the unread count badge without a full poll.

Event name: `notification:new`
Payload: `{ "client_id": "ntf_..." }`

On receipt: call `GET /api/v1/notifications/unread-count` to refresh the badge, or prepend the new notification to the in-app list.

---

## Recommended service worker implementation sketch

```js
self.addEventListener('push', event => {
  const payload = event.data.json();
  const { title, body, data } = payload;

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      data,   // passed through to notificationclick
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const { entity_type, entity_client_id, task_client_id, notification_client_id } = event.notification.data;

  const url = resolveDeepLink(entity_type, entity_client_id, task_client_id); // see routing table above

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(windowClients => {
      // Focus existing window and navigate, or open a new one
      const existing = windowClients.find(c => c.url.startsWith(self.location.origin));
      if (existing) {
        existing.focus();
        existing.postMessage({ type: 'NAVIGATE', url, notification_client_id });
      } else {
        clients.openWindow(url);
      }
    })
  );
});
```

The app client should listen for `NAVIGATE` messages from the service worker and:
1. Navigate to `url`
2. Call `POST /api/v1/notifications/mark-read` with `{ notification_client_ids: [notification_client_id] }`

---

## Validation notes

- Backend validation run: push delivery confirmed working end-to-end before this document was written.
- Suggested frontend validation:
  - Trigger each notification type (resolve a task, transition a step, send a case message, mark upholstery requirements) and confirm the service worker receives the correct `entity_type` and `entity_client_id`.
  - Tap the notification and confirm the app opens the correct page.
  - Confirm `notification_client_id` can be used to mark the notification read via `POST /mark-read`.
  - Confirm `unread_count` decrements correctly after marking read.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_notification_message_enrichment_20260621.md`
- Parent summary: —
- Related handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pin_notification_batch_20260620.md`
