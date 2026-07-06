# HANDOFF_TO_FRONTEND_task_customer_coordination_reply_20260706

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_customer_coordination_reply_20260706`
- Created at (UTC): `2026-07-06T08:30:00Z`
- Owner agent: `codex`
- Source plan: `n/a`
- Source summary: `n/a`

## Backend delivery context

- What backend implemented:
  - A new task-scoped customer-coordination reply endpoint that enriches `{{vars}}` from the same task/customer/item context as the coordination batch email endpoint.
  - The endpoint replies on an explicit existing coordination email thread and delegates to the existing async email reply flow.
- API or contract changes:
  - **New** `POST /api/v1/tasks/{task_id}/customer-coordination/reply`
- Feature flags/toggles: none

## Frontend action required

1. Add a reply action in the task customer-coordination UI that sends replies through the new task-scoped endpoint instead of calling the generic email-thread reply endpoint directly.
2. Pass the current `task_id` from the task context and the exact `thread_client_id` the user is replying on.
3. Allow `text_body` and/or `html_body` to contain the same `{{vars}}` supported by the batch coordination email sender.
4. Treat the response as an async queue acknowledgement, not a delivery result. Delivery status still comes from the thread message list via `send_attempted_at` and `send_error`.

## Interface details

### Endpoint

- `POST /api/v1/tasks/{task_id}/customer-coordination/reply`

### Path params

| Param | Type | Required | Notes |
|---|---|---|---|
| `task_id` | `string` | Yes | The task used to build the enrichment context. |

### Request body

```json
{
  "thread_client_id": "eth_abc123",
  "connection_client_id": null,
  "subject": "Uppdatering för {{customer_name}}",
  "text_body": "Hej {{customer_name}}, din {{task_type}} är {{task_state}}.",
  "html_body": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `thread_client_id` | `string` | Yes | Exact existing coordination thread to reply on. The backend does not auto-select a thread. |
| `connection_client_id` | `string \| null` | No | Optional override input. In normal reply usage the backend uses the selected thread’s existing connection. |
| `subject` | `string \| null` | No | Optional subject override. If omitted, the backend reuses the latest message subject from the selected thread. If provided, it is enriched before send. |
| `text_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` must be present. Supports `{{vars}}`. |
| `html_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` must be present. Supports `{{vars}}`. |

### Supported `{{vars}}`

This endpoint uses the same enrichment layer as `POST /api/v1/tasks/customer-coordination/email-batch`.

Supported placeholders:

- `{{customer_name}}`
- `{{customer_email}}`
- `{{customer_phone}}`
- `{{customer_address}}`
- `{{task_type}}`
- `{{task_state}}`
- `{{task_fulfillment_method}}`
- `{{task_scheduled_time}}`
- `{{item_article_number}}`
- `{{item_sku}}`
- `{{item_category}}`

Unknown placeholders are left unchanged.

### Subject behavior

- If `subject` is omitted:
  - the backend reuses the latest message subject already present on the selected thread
- If `subject` is provided:
  - the backend enriches it with the task context and uses that value for the reply

### Success response `200`

This endpoint delegates to the existing async email reply flow, so the response is a queue acknowledgement:

```json
{
  "enqueued": true,
  "task_client_id": "task_abc123",
  "thread_client_id": "eth_abc123",
  "message_client_id": "emsg_abc123"
}
```

| Field | Notes |
|---|---|
| `enqueued` | Always `true` on success. |
| `task_client_id` | Execution task id for the async outbound send worker. |
| `thread_client_id` | The same thread id passed in the request. |
| `message_client_id` | The newly created outbound reply message row. |

### Delivery status follow-up

The POST response does not contain final send success/failure.

To show status after enqueue:

1. Call `GET /api/v1/email-threads/{thread_id}/messages`
2. Find the returned message by `message_client_id`
3. Interpret the fields:
   - `send_attempted_at == null` → queued / not attempted yet
   - `send_attempted_at != null && send_error == null` → sent
   - `send_attempted_at != null && send_error != null` → failed

### Error cases

| HTTP | Condition |
|---|---|
| `400` / `422` | Invalid request body, including missing `thread_client_id` or missing both bodies |
| `404` | `task_id` not found, selected thread not found, or coordination reference behind the thread is missing |
| `422` | The selected thread is not a task customer-coordination thread, the thread belongs to a different task, the task customer has no primary email, or no reply subject could be resolved |

## Usage notes

- This is a reply-only endpoint. It does not create a new coordination thread.
- The frontend must store and pass the exact `thread_client_id` from the coordination-thread listing UI.
- If the UI already has a visible thread subject and the user is not editing it, omit `subject` and let the backend reuse the existing thread subject.
- Use this endpoint when reply content needs task/customer/item variable enrichment. For plain thread replies without task-driven template variables, the generic email-thread reply endpoint can still be used.

## Trace links

- Related list endpoint: `GET /api/v1/tasks/customer-coordination/threads`
- Related batch send endpoint: `POST /api/v1/tasks/customer-coordination/email-batch`
- Related message status endpoint: `GET /api/v1/email-threads/{thread_id}/messages`
