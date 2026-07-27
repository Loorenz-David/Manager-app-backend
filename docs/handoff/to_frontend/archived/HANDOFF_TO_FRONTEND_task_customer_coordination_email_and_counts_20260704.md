# HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704`
- Created at (UTC): `2026-07-04T20:00:00Z`
- Owner agent: `claude`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_customer_coordination_email_batch_20260704.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_customer_coordination_email_batch_20260704.md`

---

## Backend delivery context

- What backend implemented:
  - A new batch email endpoint that sends personalised emails to customers of multiple tasks at once, using content placeholders (`{{var}}`) that are resolved per task at send time.
  - A new endpoint to count customer coordination records by state.
  - An extension to the task list endpoint: tasks can now be filtered by customer coordination state, and the response optionally includes the coordination records inline.
  - Thread message list, mark-as-read, reply, and targeted IMAP sync endpoints for email threads (`/api/v1/email-threads/...`).

- API or contract changes:
  - **New** `POST /api/v1/tasks/customer-coordination/email-batch`
  - **New** `GET /api/v1/tasks/customer-coordination/counts`
  - **New** `POST /api/v1/tasks/{task_id}/customer-coordination/complete`
  - **New** `POST /api/v1/tasks/{task_id}/customer-coordination/fail`
  - **Extended** `GET /api/v1/tasks` — new optional query param `customer_coordination_states` and new optional key `customer_coordination` in each task object
  - **Extended** `GET /api/v1/tasks/customer-coordination/threads` — each element now includes `primary_item`, `item_images`, `message_count`, `last_message`, and `last_messages` (up to the 2 newest messages)
  - **New** `GET /api/v1/email-threads/{thread_id}/messages`
  - **New** `POST /api/v1/email-threads/{thread_id}/read`
  - **New** `POST /api/v1/email-threads/{thread_id}/send` (reply within thread)
  - **New** `POST /api/v1/email-threads/{thread_id}/sync` (single-thread targeted IMAP sync)
  - **New** `POST /api/v1/email-threads/sync-targeted` (batch targeted IMAP sync)

- Feature flags/toggles: none

---

## Frontend action required

1. Build the coordination email batch UI: a form that collects `task_ids`, email content, and an optional `connection_client_id`, then calls `POST /tasks/customer-coordination/email-batch`.
2. Display the per-task send result from the response — show `skipped` tasks and their reasons.
3. Optionally use `GET /tasks/customer-coordination/counts` to show a badge or filter count on the coordination queue view.
4. When the task list is displayed in a coordination-focused context, pass `customer_coordination_states` to filter, and read `task.customer_coordination` to show inline coordination status — but only when the param is passed (see serialization rules below).

---

## Interface details

---

### 1. `POST /api/v1/tasks/customer-coordination/email-batch`

Sends a personalised email to the customer of each task. Content is the same for all targets but placeholder variables are resolved per task/customer/item.

#### Request body

```json
{
  "connection_client_id": "ecn_abc123",
  "task_ids": ["tsk_1", "tsk_2", "tsk_3"],
  "subject": "Din {{task_type}} är klar — {{customer_name}}",
  "text_body": "Hej {{customer_name}},\n\nDin order är {{task_state}}.\nUpphämtning: {{task_scheduled_time}}\n\nArtikelnummer: {{item_article_number}}",
  "html_body": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `connection_client_id` | `string \| null` | No | If omitted, the current user's single active connection is used automatically. Required if the user has more than one active connection. |
| `task_ids` | `string[]` | Yes | 1–50 task client IDs |
| `subject` | `string` | Yes | 1–255 chars. Supports `{{vars}}`. |
| `text_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` must be present. |
| `html_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` must be present. |

#### Available `{{vars}}` in subject and body

| Placeholder | Resolves to | Fallback |
|---|---|---|
| `{{customer_name}}` | Customer display name | `""` |
| `{{customer_email}}` | Customer primary email | `""` |
| `{{customer_phone}}` | Customer primary phone number | `""` |
| `{{customer_address}}` | Street, city, postal code, country joined | `""` |
| `{{task_type}}` | e.g. `"Pre Order"`, `"Return"`, `"Internal"` | `""` |
| `{{task_state}}` | e.g. `"Ready"`, `"Working"`, `"Pending"` | `""` |
| `{{task_fulfillment_method}}` | e.g. `"Pickup At Store"`, `"Delivery"` | `""` |
| `{{task_scheduled_time}}` | Swedish-formatted schedule, e.g. `"Juli, Lördag 4 → Juli, Söndag 5"`. Year is included only when it differs from the current year. | `"—"` when task exists but no dates are set |
| `{{item_article_number}}` | Primary item article number | `""` |
| `{{item_sku}}` | Primary item SKU | `""` |
| `{{item_category}}` | Primary item category name | `""` |

Unknown placeholders (e.g. `{{some_unknown_var}}`) are left unchanged in the content — they are not removed or errored.

#### Success response `200`

```json
{
  "job_id": "task_abc123",
  "status": "queued",
  "queued_count": 2,
  "skipped_count": 1,
  "skipped": [
    {
      "task_client_id": "tsk_3",
      "reason": "no_customer_email"
    }
  ]
}
```

| Field | Notes |
|---|---|
| `job_id` | `client_id` of the created `ExecutionTask`. `null` when all tasks were skipped. |
| `status` | `"queued"` when at least one email was enqueued. `"nothing_to_send"` when all tasks were skipped. |
| `queued_count` | Number of emails enqueued for background delivery (excludes skipped) |
| `skipped_count` | Number of tasks that were excluded before enqueue |
| `skipped[].reason` | One of: `task_not_found`, `no_coordination_record`, `no_customer_email` |

Delivery results are not returned by the POST response anymore. To check per-message delivery status after the worker runs, call `GET /api/v1/email-threads/{thread_id}/messages` and read `send_attempted_at` plus `send_error` on each message. `send_attempted_at` stays `null` while the background job has not yet attempted that message.

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | Pydantic validation error — e.g. `task_ids` is empty, no body provided |
| `404` | `connection_client_id` not found — **or** — `connection_client_id` was omitted and the current user has no active email connection |
| `403` | The specified connection is owned by a different user |
| `422` | `connection_client_id` was omitted and the current user has **multiple** active email connections — must specify `connection_client_id` explicitly |

---

### 2. `GET /api/v1/tasks/customer-coordination/counts`

Returns the count of customer coordination records grouped by state. Useful for displaying a badge count on the coordination queue or building a filtered navigation.

#### Query parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `customer_coordination_states` | `string` (CSV) | No | Comma-separated list of states to include. If omitted, all states are returned. |

**Valid state values:** `pending`, `coordinating`, `completed`, `failed`

#### Examples

```
GET /api/v1/tasks/customer-coordination/counts
→ returns all states

GET /api/v1/tasks/customer-coordination/counts?customer_coordination_states=pending,coordinating
→ returns only pending and coordinating counts
```

#### Success response `200`

Without filter (all states returned):
```json
{
  "pending": 12,
  "coordinating": 5,
  "completed": 43,
  "failed": 2
}
```

With `customer_coordination_states=pending,coordinating`:
```json
{
  "pending": 12,
  "coordinating": 5
}
```

States with zero records are included with value `0`. States not included in the filter are absent from the response.

---

### 3. `GET /api/v1/tasks` — `customer_coordination_states` extension

The task list endpoint gained one new optional query parameter and one new conditional key in each task object.

#### New query parameter

| Param | Type | Required | Notes |
|---|---|---|---|
| `customer_coordination_states` | `string` (CSV) | No | Comma-separated list of coordination states. When provided, **only tasks that have at least one coordination record in one of those states** are returned. |

**Valid state values:** `pending`, `coordinating`, `completed`, `failed`

```
GET /api/v1/tasks?customer_coordination_states=pending,coordinating
```

This parameter stacks with all existing filters (`task_states`, `task_types`, `scheduled_from_date`, etc.).

#### Serialization rule for `customer_coordination` key

The `customer_coordination` key in each task object behaves differently depending on whether the filter was used:

| `customer_coordination_states` param | `task.customer_coordination` value |
|---|---|
| **Not passed** | `null` — key is present but always `null` |
| **Passed** | Array of coordination records for that task (may be empty `[]` if none matched the filter but the task passed other filters) |

```json
// Without customer_coordination_states param:
{
  "task": {
    "client_id": "tsk_1",
    "state": "ready",
    ...
    "customer_coordination": null
  }
}

// With customer_coordination_states=pending:
{
  "task": {
    "client_id": "tsk_1",
    "state": "ready",
    ...
    "customer_coordination": [
      {
        "client_id": "tcc_abc",
        "task_id": "tsk_1",
        "state": "pending",
        "created_at": "2026-07-01T10:00:00+00:00",
        "updated_at": null
      }
    ]
  }
}
```

#### Coordination record shape (when included)

```json
{
  "client_id": "tcc_abc123",
  "task_id": "tsk_1",
  "state": "pending",
  "created_at": "2026-07-01T10:00:00+00:00",
  "updated_at": "2026-07-03T14:22:00+00:00"
}
```

| Field | Values |
|---|---|
| `state` | `"pending"` \| `"coordinating"` \| `"completed"` \| `"failed"` |
| `updated_at` | ISO-8601 or `null` if never updated |

Multiple records per task are returned in ascending `created_at` order (oldest first).

---

### 4. `GET /api/v1/email-threads/unread-count`

Returns the count of unread email threads for the current user. Supports optional filters by connection, entity type, and entity instance. All parameters are independent — they can be combined freely.

A thread is considered **unread** when it has at least one inbound message and either:
- the user has never read it (`last_read_at` is null), or
- the last inbound message arrived after the user's last read timestamp.

#### Query parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `connection_client_id` | `string` | No | Limit to threads on a specific email connection |
| `entity_type` | `string` | No | Limit to threads linked to a specific entity type |
| `entity_client_id` | `string` | No | Limit to threads linked to a specific entity instance. Useful combined with `entity_type`. |

**Valid `entity_type` values:** `task_customer_coordination`, `task`, `case`, `customer`

#### Usage examples

```
// All unread across the workspace
GET /api/v1/email-threads/unread-count

// All unread on a specific connection
GET /api/v1/email-threads/unread-count?connection_client_id=ecn_1

// All unread threads linked to ANY customer coordination record
GET /api/v1/email-threads/unread-count?entity_type=task_customer_coordination

// Unread threads for a specific coordination instance
GET /api/v1/email-threads/unread-count?entity_type=task_customer_coordination&entity_client_id=tcc_abc

// Unread coordination threads on a specific connection
GET /api/v1/email-threads/unread-count?entity_type=task_customer_coordination&connection_client_id=ecn_1
```

#### Success response `200`

```json
{ "unread_count": 7 }
```

`unread_count` is always an integer, `0` when there are no matching unread threads.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Role not allowed (`WORKER` is excluded — only `ADMIN`, `MANAGER`, `SELLER`) |

No `404` is returned for unknown `entity_type` or `entity_client_id` values — the filter simply matches zero threads and returns `{ "unread_count": 0 }`.

---

### 5. `GET /api/v1/tasks/customer-coordination/threads`

Returns a paginated inbox-style list of email threads linked to task customer coordination records. Each list item includes the email thread plus the linked task with the matching coordination record inlined under `task.customer_coordination`.

Unread threads are always returned before read threads. Inside each group, ordering is newest `last_message_at` first.

#### Query parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `coordination_states` | `string` (CSV) | No | Filter by coordination state |
| `task_states` | `string` (CSV) | No | Filter by task state |
| `task_types` | `string` (CSV) | No | Filter by task type |
| `limit` | `int` | No | Default `50`, max `200` |
| `offset` | `int` | No | Default `0` |

**Valid `coordination_states` values:** `pending`, `coordinating`, `completed`, `failed`

`task_states` and `task_types` use the same enum values already used by `GET /api/v1/tasks`.

#### Usage examples

```
GET /api/v1/tasks/customer-coordination/threads

GET /api/v1/tasks/customer-coordination/threads?coordination_states=pending,coordinating

GET /api/v1/tasks/customer-coordination/threads?task_states=ready&task_types=return&limit=20&offset=0
```

#### Success response `200`

```json
{
  "coordination_threads": [
    {
      "thread": {
        "client_id": "eth_123",
        "workspace_id": "wrk_1",
        "connection_id": "ecn_1",
        "entity_type": "task_customer_coordination",
        "entity_client_id": "tcc_123",
        "major_entity_type": "task",
        "major_entity_client_id": "tsk_1",
        "topic": "pickup_ready",
        "subject_normalized": "din order ar klar",
        "last_message_at": "2026-07-04T12:00:00+00:00",
        "last_inbound_message_at": "2026-07-04T12:00:00+00:00",
        "created_at": "2026-07-03T08:00:00+00:00",
        "updated_at": null,
        "is_unread": true,
        "user_state": {
          "thread_id": "eth_123",
          "user_id": "usr_1",
          "last_read_at": "2026-07-03T09:00:00+00:00",
          "muted_at": null,
          "archived_at": null
        }
      },
      "task": {
        "client_id": "tsk_1",
        "task_scalar_id": 101,
        "task_type": "return",
        "priority": "normal",
        "state": "ready",
        "title": "Pickup order",
        "summary": null,
        "return_source": null,
        "item_location": null,
        "return_method": null,
        "fulfillment_method": null,
        "assortment": null,
        "additional_details": null,
        "ready_by_at": null,
        "scheduled_start_at": null,
        "scheduled_end_at": null,
        "customer_id": "cus_1",
        "primary_phone_number": null,
        "secondary_phone_number": null,
        "primary_email": "customer@example.com",
        "secondary_email": null,
        "address": null,
        "created_at": "2026-07-01T10:00:00+00:00",
        "updated_at": null,
        "closed_at": null,
        "is_deleted": false,
        "deleted_at": null,
        "post_handling": null,
        "customer_coordination": [
          {
            "client_id": "tcc_123",
            "task_id": "tsk_1",
            "state": "coordinating",
            "created_at": "2026-07-02T09:00:00+00:00",
            "updated_at": null
          }
        ]
      },
      "primary_item": {
        "client_id": "itm_abc",
        "article_number": "ABC-123",
        "sku": "SKU-XYZ",
        "state": "active",
        "item_category_id": "icat_1",
        "quantity": 1,
        "designer": "Cassina",
        "height_in_cm": 85,
        "width_in_cm": 210,
        "depth_in_cm": 95,
        "item_value_minor": 120000,
        "item_cost_minor": null,
        "item_currency": "sek",
        "item_position": "Living room",
        "external_id": null,
        "external_url": null,
        "external_source": null,
        "external_order_id": null,
        "item_category_snapshot": "Sofa",
        "item_major_category_snapshot": "Upholstery"
      },
      "item_images": [
        {
          "client_id": "img_1",
          "image_url": "https://cdn.example.com/items/img_1.jpg",
          "storage_provider": "s3",
          "source_type": "uploaded",
          "source_reference": "s3_image_url",
          "width_px": 1600,
          "height_px": 1200,
          "file_size_bytes": 245000,
          "created_at": "2026-07-01T09:00:00+00:00",
          "last_event": null,
          "events": [],
          "image_annotation": null
        }
      ],
      "message_count": 4,
      "last_messages": [
        {
          "client_id": "emsg_1",
          "workspace_id": "wrk_1",
          "connection_id": "ecn_1",
          "thread_id": "eth_123",
          "direction": "inbound",
          "provider_folder": "INBOX",
          "provider_uid": "1001",
          "from_address": "customer@example.com",
          "from_name": "Customer Name",
          "to_addresses_json": ["store@example.com"],
          "cc_addresses_json": [],
          "bcc_addresses_json": [],
          "subject": "Re: din order",
          "text_body": "Hej, jag vill hämta fredag...",
          "html_body": null,
          "body_preview": "Hej, jag vill hämta fredag...",
          "rfc_message_id": "<abc@mail.example.com>",
          "in_reply_to": "<prev@mail.example.com>",
          "references_json": ["<prev@mail.example.com>"],
          "tracking_token": null,
          "sent_or_received_at": "2026-07-04T12:00:00+00:00",
          "created_by_user_id": null,
          "send_attempted_at": null,
          "send_error": null,
          "created_at": "2026-07-04T12:01:00+00:00"
        },
        {
          "client_id": "emsg_0",
          "workspace_id": "wrk_1",
          "connection_id": "ecn_1",
          "thread_id": "eth_123",
          "direction": "outbound",
          "provider_folder": "Sent",
          "provider_uid": "1000",
          "from_address": "store@example.com",
          "from_name": "Store Name",
          "to_addresses_json": ["customer@example.com"],
          "cc_addresses_json": [],
          "bcc_addresses_json": [],
          "subject": "Re: din order",
          "text_body": "Hej, fredagen fungerar bra.",
          "html_body": null,
          "body_preview": "Hej, fredagen fungerar bra.",
          "rfc_message_id": "<prev@mail.example.com>",
          "in_reply_to": null,
          "references_json": [],
          "tracking_token": null,
          "sent_or_received_at": "2026-07-04T10:00:00+00:00",
          "created_by_user_id": "usr_1",
          "send_attempted_at": "2026-07-04T10:00:02+00:00",
          "send_error": null,
          "created_at": "2026-07-04T10:00:01+00:00"
        }
      ],
      "last_message": {
        "client_id": "emsg_1",
        "workspace_id": "wrk_1",
        "connection_id": "ecn_1",
        "thread_id": "eth_123",
        "direction": "inbound",
        "provider_folder": "INBOX",
        "provider_uid": "1001",
        "from_address": "customer@example.com",
        "from_name": "Customer Name",
        "to_addresses_json": ["store@example.com"],
        "cc_addresses_json": [],
        "bcc_addresses_json": [],
        "subject": "Re: din order",
        "text_body": "Hej, jag vill hämta fredag...",
        "html_body": null,
        "body_preview": "Hej, jag vill hämta fredag...",
        "rfc_message_id": "<abc@mail.example.com>",
        "in_reply_to": "<prev@mail.example.com>",
        "references_json": ["<prev@mail.example.com>"],
        "tracking_token": null,
        "sent_or_received_at": "2026-07-04T12:00:00+00:00",
        "created_by_user_id": null,
        "send_attempted_at": null,
        "send_error": null,
        "created_at": "2026-07-04T12:01:00+00:00"
      }
    }
  ],
  "coordination_threads_pagination": {
    "has_more": true,
    "limit": 50,
    "offset": 0
  }
}
```

#### Response notes

| Field | Notes |
|---|---|
| `coordination_threads[].thread` | Same thread shape as the email domain serializer, including `is_unread` for the current user |
| `coordination_threads[].thread.major_entity_type` | Always `"task"` for threads created by the batch send endpoint — can be used to navigate directly to the linked task |
| `coordination_threads[].thread.major_entity_client_id` | The `client_id` of the linked task — same value as `task.client_id` in the same list item |
| `coordination_threads[].task` | Full task shape |
| `coordination_threads[].task.customer_coordination` | Always an array with the single coordination record linked to the thread |
| `coordination_threads[].primary_item` | Serialized primary item for the task, or `null` if the task has no primary item |
| `coordination_threads[].item_images` | Ordered image list for the primary item. The first entry uses the full `serialize_image` shape, later entries use `serialize_image_light`. Empty array when there is no primary item or no images. |
| `coordination_threads[].message_count` | Total number of persisted `EmailMessage` rows in the thread. Returned from a grouped aggregate query across the current page, so the UI can show message volume without fetching the full conversation. |
| `coordination_threads[].last_messages` | Array of up to the 2 newest messages in the thread, ordered newest first. Each entry matches `serialize_email_message`. Empty array when the thread has no messages. |
| `coordination_threads[].last_message` | Most recent message in the thread regardless of direction, or `null` when the thread has no messages yet. Shape matches `serialize_email_message`. |
| `GET /api/v1/email-threads/{thread_id}/messages` | Message payloads for these threads now include `send_attempted_at` and `send_error` so the UI can show queued, sent, or failed delivery state |
| `coordination_threads_pagination.has_more` | Derived from fetching `limit + 1` rows |

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Role not allowed (`WORKER` is excluded — only `ADMIN`, `MANAGER`, `SELLER`) |

Unknown filter values are not translated into a special error by this endpoint; they simply match zero rows when no record has that enum value.

---

### 6. `POST /api/v1/tasks/{task_id}/customer-coordination/fail`

Marks one or more task customer coordination records as failed. Use this when an operator explicitly abandons a coordination attempt, the customer is unreachable, or the thread should stop being treated as active coordination.

#### Request body

```json
{
  "coordination_ids": ["tcc_1", "tcc_2"]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `coordination_ids` | `string[] \| null` | No | When provided and non-empty, every matching coordination record for the task is marked failed in one request. When omitted or empty, the backend falls back to the single active coordination record for the task. |

#### Success response `200`

```json
{
  "failed_ids": ["tcc_1", "tcc_2"]
}
```

#### Guard behavior

- Records already in `failed` or `completed` state are rejected with `400`.
- If `coordination_ids` is omitted or empty, the fallback only targets a coordination record whose state is neither `completed` nor `failed`.
- Each successful transition writes a history record and emits a `task_customer_coordination:failed` workspace event.

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | Validation error, including trying to fail a coordination record already in `failed` or `completed` state |
| `401` | Missing or invalid auth token |
| `403` | Role not allowed (`WORKER` is excluded — only `ADMIN`, `MANAGER`, `SELLER`) |

---

### 7. `GET /api/v1/email-threads/{thread_id}/messages`

Returns a paginated list of email messages in chronological order (oldest first) for a given thread.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the email thread |

#### Query parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `limit` | `int` | No | Default `50`, max `200` |
| `offset` | `int` | No | Default `0` |

#### Success response `200`

```json
{
  "email_messages": [
    {
      "client_id": "emsg_1",
      "workspace_id": "wrk_1",
      "connection_id": "ecn_1",
      "thread_id": "eth_123",
      "direction": "inbound",
      "provider_folder": "INBOX",
      "provider_uid": "1001",
      "from_address": "customer@example.com",
      "from_name": "Customer Name",
      "to_addresses_json": ["store@example.com"],
      "cc_addresses_json": [],
      "bcc_addresses_json": [],
      "subject": "Re: din order",
      "text_body": "Full message body...",
      "html_body": null,
      "body_preview": "Full message body...",
      "rfc_message_id": "<abc@mail.example.com>",
      "in_reply_to": "<prev@mail.example.com>",
      "references_json": ["<prev@mail.example.com>"],
      "tracking_token": null,
      "sent_or_received_at": "2026-07-04T12:00:00+00:00",
      "created_by_user_id": null,
      "send_attempted_at": null,
      "send_error": null,
      "created_at": "2026-07-04T12:01:00+00:00"
    }
  ],
  "email_messages_pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Field notes

| Field | Notes |
|---|---|
| `direction` | `"inbound"` for messages received from the customer; `"outbound"` for messages sent from the store |
| `text_body` | Full plain-text body; may be `null` for HTML-only messages |
| `html_body` | Full HTML body; may be `null` for plain-text-only messages |
| `body_preview` | First 300 chars of `text_body`, suitable for list previews |
| `send_attempted_at` | Set once the SMTP worker attempts delivery. `null` while the message is still queued. |
| `send_error` | Non-`null` string when SMTP delivery failed. `null` on success or while queued. |
| `created_by_user_id` | `user_id` of the staff member who sent the message; `null` for inbound messages |

#### Access rule

The requesting user must either be the owner of the email connection or have role `ADMIN` or `MANAGER`. A `403` is returned if the connection is owned by a different user and the requesting role is `SELLER` or `WORKER`.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread not found or connection not found |

---

### 8. `POST /api/v1/email-threads/{thread_id}/read`

Marks a thread as read for the current user by recording `last_read_at = now()` on the user-state record. Creates the user-state record if it does not yet exist. After this call, `thread.is_unread` will be `false` for the requesting user until a new inbound message arrives.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the email thread |

#### Request body

None.

#### Success response `200`

```json
{ "marked_read": true }
```

#### Behavior notes

- Idempotent. Calling it multiple times is safe; `last_read_at` is always updated to the current timestamp.
- The unread badge in the coordination thread inbox should be recalculated after calling this endpoint, either by re-fetching `GET /api/v1/email-threads/unread-count` or by toggling the `is_unread` flag optimistically on the local thread record.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread or connection not found |

---

### 9. `POST /api/v1/email-threads/{thread_id}/send`

Sends an outbound reply email within an existing thread. The backend resolves the correct `in_reply_to` and `References` headers automatically from the thread's latest message so the reply is threaded correctly in the customer's email client.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the thread to reply within |

#### Request body

```json
{
  "connection_client_id": "ecn_abc",
  "to_addresses": ["customer@example.com"],
  "cc_addresses": [],
  "bcc_addresses": [],
  "subject": "Re: din order",
  "text_body": "Hej, din möbel är klar för upphämtning.",
  "html_body": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `connection_client_id` | `string` | Yes | Must be an active connection owned by the requesting user |
| `to_addresses` | `string[]` | Yes | Recipient email addresses |
| `cc_addresses` | `string[]` | No | Default `[]` |
| `bcc_addresses` | `string[]` | No | Default `[]` |
| `subject` | `string` | Yes | The reply subject. Convention: prefix with `Re: ` to match thread. |
| `text_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` required |
| `html_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` required |

`entity_type`, `entity_client_id`, `major_entity_type`, `major_entity_client_id`, and `topic` fields in the body model are ignored when `thread_client_id` is supplied because the thread already carries its entity linkage.

#### Success response `200`

```json
{
  "thread_client_id": "eth_123",
  "message_client_id": "emsg_new",
  "send_success": true,
  "send_error": null
}
```

| Field | Notes |
|---|---|
| `send_success` | `true` when SMTP delivery succeeded synchronously |
| `send_error` | `null` on success; error string on SMTP failure. The message record is still persisted even on failure. |

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | Neither `text_body` nor `html_body` provided |
| `401` | Missing or invalid auth token |
| `403` | `connection_client_id` is owned by a different user |
| `404` | Connection or thread not found |

---

### 10. `POST /api/v1/email-threads/sync-targeted`

Triggers a targeted IMAP sync to pull in any inbound replies for one or more specific threads. The backend searches for RFC message IDs of the most recent outbound messages from each thread, then fetches matching inbound messages from the IMAP folder. Use this after sending an email to proactively check for a reply.

#### Request body

```json
{
  "connection_client_id": "ecn_abc",
  "thread_client_ids": ["eth_1", "eth_2"],
  "entity_type": null,
  "entity_client_ids": [],
  "major_entity_type": null,
  "major_entity_client_id": null,
  "max_threads": 50
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `connection_client_id` | `string \| null` | No | Limit sync to a specific connection. Required when scoping by connection. |
| `thread_client_ids` | `string[]` | No | Sync specific thread IDs directly. Default `[]`. |
| `entity_type` | `string \| null` | No | Filter threads by entity type. Used together with `entity_client_ids`. |
| `entity_client_ids` | `string[]` | No | Filter threads linked to these entity IDs. Default `[]`. |
| `major_entity_type` | `string \| null` | No | Filter threads by major entity type. Used together with `major_entity_client_id`. |
| `major_entity_client_id` | `string \| null` | No | Filter threads by a single major entity instance. |
| `max_threads` | `int` | No | Maximum number of threads to sync. Default `50`, max `50`. |

At least one scoping field should be provided. If no scoping fields narrow the query, up to `max_threads` most-recently-active threads on the connection are synced.

Typical usage for coordination inbox: pass `thread_client_ids` with the IDs of threads currently visible in the inbox, or pass `entity_type = "task_customer_coordination"` with `entity_client_ids` for the visible coordination records.

#### Success response `200`

```json
{
  "requested_thread_count": 2,
  "synced_thread_count": 2,
  "searched_rfc_message_id_count": 4,
  "matched_uid_count": 1,
  "fetched_message_count": 1,
  "created_message_count": 1,
  "existing_message_count": 0,
  "threads_with_new_messages": ["eth_1"],
  "thread_errors": {},
  "sync_success": true,
  "sync_error": null
}
```

| Field | Notes |
|---|---|
| `requested_thread_count` | Number of threads matched by the request scoping filters |
| `synced_thread_count` | Number of threads that had at least one outbound RFC message ID to search for |
| `searched_rfc_message_id_count` | Total unique RFC IDs searched across IMAP |
| `matched_uid_count` | Number of IMAP UIDs found matching the RFC IDs |
| `fetched_message_count` | Number of messages downloaded from IMAP |
| `created_message_count` | Number of new `EmailMessage` records persisted |
| `existing_message_count` | Messages already in the DB and therefore skipped |
| `threads_with_new_messages` | Array of `thread_client_id` strings that received at least one new message |
| `thread_errors` | Map of `thread_client_id -> error string` for threads that failed individually |
| `sync_success` | `true` when no thread-level errors occurred |
| `sync_error` | Error string when any thread failed; `null` on full success |

After receiving the response: if `threads_with_new_messages` is non-empty, re-fetch `GET /api/v1/email-threads/{thread_id}/messages` for those threads to show the new inbound messages. Also re-fetch `GET /api/v1/email-threads/unread-count` to update the inbox badge.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | A referenced connection does not exist |

---

### 11. `POST /api/v1/email-threads/{thread_id}/sync`

Triggers a targeted IMAP sync for a single thread. The backend takes the most recent outbound RFC message IDs from the thread and searches the IMAP inbox for matching replies. Use this when the user opens a conversation view to check for new replies in real time.

This is the single-thread variant of `POST /api/v1/email-threads/sync-targeted` (section 10). Prefer this endpoint when only one thread needs to be refreshed; use the batch variant when refreshing the whole inbox.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the thread to sync |

#### Request body

None.

#### Success response `200`

```json
{
  "thread_client_id": "eth_123",
  "searched_rfc_message_id_count": 2,
  "matched_uid_count": 1,
  "fetched_message_count": 1,
  "created_message_count": 1,
  "existing_message_count": 0,
  "sync_success": true,
  "sync_error": null
}
```

| Field | Notes |
|---|---|
| `thread_client_id` | The thread that was synced |
| `searched_rfc_message_id_count` | Number of outbound RFC message IDs searched in IMAP (up to 10 most recent outbound messages). `0` when the thread has no outbound messages yet; sync is skipped and `sync_success` is still `true`. |
| `matched_uid_count` | IMAP UIDs found matching the searched IDs |
| `fetched_message_count` | Messages downloaded from IMAP |
| `created_message_count` | New `EmailMessage` records persisted |
| `existing_message_count` | Messages already in DB and therefore skipped |
| `sync_success` | `true` when the IMAP search and processing succeeded |
| `sync_error` | `null` on success; error string when IMAP search failed |

After receiving the response: if `created_message_count > 0`, re-fetch `GET /api/v1/email-threads/{thread_id}/messages` to show the new inbound messages. Also refresh `GET /api/v1/email-threads/unread-count` if the thread was previously marked read.

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | IMAP provider search failed |
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread not found, connection not found, or sync state not initialised for the connection |

---

### 12. `POST /api/v1/tasks/{task_id}/customer-coordination/complete`

Marks a task customer coordination record as completed. Use this when the coordination flow is finished and the thread should leave the active coordination queue.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `task_id` | `string` | `client_id` of the task that owns the coordination record |

#### Request body

```json
{
  "coordination_id": "tcc_123"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `coordination_id` | `string \| null` | No | When provided, completes that exact coordination record. When omitted, the backend resolves the first non-completed coordination record for the task. |

#### Success response `200`

```json
{
  "client_id": "tcc_123"
}
```

| Field | Notes |
|---|---|
| `client_id` | `client_id` of the coordination record that was marked completed |

#### Behavior notes

- If `coordination_id` is provided together with `task_id`, both must match the same record.
- When `coordination_id` is omitted, the backend looks up a coordination record for the task whose state is not `completed`.
- A history record is written for the state change and a `task_customer_coordination:completed` workspace event is emitted after commit.

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | Neither `task_id` nor `coordination_id` is available to resolve a record, or the target coordination record is already completed |
| `401` | Missing or invalid auth token |
| `403` | Role not allowed (`WORKER` is excluded — only `ADMIN`, `MANAGER`, `SELLER`) |
| `404` | Active task customer coordination instance not found |

---

## Validation notes

- Backend validation run: compile check passed for the new coordination thread query and router wiring. Earlier validation from the same backend delivery still applies for the batch email, counts, and unread count work: 9 unit tests pass covering happy path, skip reasons, partial SMTP failure, connection not found, permission denied, empty task list validation, missing body validation, auto-resolve single connection, auto-resolve no connection (NotFound), auto-resolve multiple connections (ValidationError).
- Suggested frontend validation:
  - Disable the send button if `task_ids` is empty.
  - Warn the user if neither `text_body` nor `html_body` is filled in before submitting.
  - Treat the POST response as queue confirmation only. Show enqueue feedback from `queued_count` and `skipped[]`, then read message-level delivery state from the thread messages view.
  - If a 422 is returned with "Multiple email connections", prompt the user to select which connection to use and resubmit with `connection_client_id`.
  - For unread count polling: treat a `0` response as valid — it does not indicate a missing entity, only no unread threads.
  - For the inbox view, preserve `limit`/`offset` in local state and append pages based on `coordination_threads_pagination.has_more`.
  - Sort controls should be avoided on the client for unread/read state — the backend already enforces unread-first ordering.
  - After calling `POST /api/v1/tasks/{task_id}/customer-coordination/complete`, optimistically remove the thread/task from active coordination views or re-fetch the coordination list/counts so completed records disappear from pending/coordinating filters.
  - After calling `POST /{thread_id}/read`, optimistically clear `is_unread` on the thread in local state and refresh `unread-count`.
  - After `POST /{thread_id}/send`, re-fetch `GET /{thread_id}/messages` to show the sent message in the conversation view.
  - After `POST /{thread_id}/sync`, if `created_message_count > 0` re-fetch the message list and refresh `unread-count`.
  - After `POST /sync-targeted`, iterate `threads_with_new_messages` and re-fetch messages for each thread that received new content.
  - `send_error` on a message in the messages list means SMTP delivery failed even though the message is persisted — show a delivery-failed indicator on that message.

---

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_task_customer_coordination_email_batch_20260704.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_customer_coordination_email_batch_20260704.md`
- Related debug plan: none
