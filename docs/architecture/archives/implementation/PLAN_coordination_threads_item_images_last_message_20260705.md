# PLAN_coordination_threads_item_images_last_message_20260705

## Metadata

- Plan ID: `PLAN_coordination_threads_item_images_last_message_20260705`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-05T00:00:00Z`
- Last updated at (UTC): `2026-07-05T08:08:29Z`
- Related issue/ticket: —
- Intention plan: —

## Goal and intent

- Goal: Enrich the `list_task_coordination_threads` query response to include `primary_item`, `item_images` (batch-loaded for the primary item on each task), and `last_message` (the most recent sent or received email message of each thread, serialized via `serialize_email_message`).
- Business/user intent: The coordination thread inbox needs the same item context that the task list provides so that operators can identify which furniture item each thread belongs to without navigating away. The last message preview lets operators assess urgency without opening the thread.
- Non-goals: No new endpoint, no schema migration, no change to router wiring, no change to filter/ordering logic on the thread query.

## Scope

- In scope:
  - Three post-query batch loads added to `list_task_coordination_threads`:
    1. `TaskItem` → primary `Item` per task
    2. `Image` + `ImageLink` → image list per primary item (same pattern as `list_tasks`)
    3. `EmailMessage` → last message per thread (via `DISTINCT ON (thread_id)` in PostgreSQL)
  - Updated return shape per element: adds `primary_item`, `item_images`, `last_message`
  - New imports in `list_task_coordination_threads.py`
- Out of scope:
  - Changes to the router handler (`tasks.py`) — no new query params or response wrapper needed
  - Changes to `serialize_email_thread`, `serialize_task`, or any serializer
  - Any write path

## Clarifications required

_(none — all patterns are derivable from `list_tasks` and existing serializers)_

## Acceptance criteria

1. Each element in `coordination_threads` contains `primary_item` (serialized item or `None`), `item_images` (list, possibly empty), and `last_message` (serialized message or `None`).
2. Images are batch-loaded in a single query across the entire page — no per-row query.
3. Last messages are batch-loaded in a single `DISTINCT ON (thread_id)` query — no per-row query.
4. A thread whose task has no primary item returns `"primary_item": null` and `"item_images": []`.
5. A thread with no messages returns `"last_message": null`.
6. `from beyo_manager.routers.api_v1.tasks import router` → no import error (router file is not changed).

## Contracts and skills

### Contracts loaded

- `architecture/07_queries.md`: query shape, `select()` API, `await ctx.session.execute()`, single-file pattern
- `architecture/07_queries_local.md`: offset pagination convention (already used in this file)
- `architecture/01_architecture.md`: layer rules — queries are pure read, zero writes
- `architecture/21_naming_conventions.md`: variable naming conventions

### Local extensions loaded

- `architecture/07_queries_local.md`: offset pagination overrides cursor — already applied in this file

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead
- **What exists** → reading is legitimate

Permitted relational reads for this plan:
- `app/beyo_manager/services/queries/tasks/list_task_coordination_threads.py` — current implementation, starting point for changes
- `app/beyo_manager/services/queries/tasks/tasks.py` lines 310–370 — exact batch image-load pattern (`select(Image, ImageLink.entity_client_id).join(ImageLink, ...)`, serialize-first-vs-rest logic)
- `app/beyo_manager/domain/emails/serializers.py` — confirm `serialize_email_message` signature and return shape
- `app/beyo_manager/models/tables/emails/email_message.py` — confirm field names (`thread_id`, `sent_or_received_at`) and index presence
- `app/beyo_manager/models/tables/emails/email_thread.py` — confirm `messages` relationship is `lazy="raise"` (so we cannot use `selectinload`)
- `app/beyo_manager/models/tables/tasks/task_item.py` — confirm `role`, `task_id`, `item_id`, `removed_at` fields
- `app/beyo_manager/models/tables/images/image_link.py` — confirm `entity_type`, `entity_client_id`, `display_order` fields

Prohibited:
- Reading other query files to understand `select()` / `execute()` / pagination shape → `07_queries.md` covers it
- Reading another serializer to understand output shape → `46_serialization.md` covers it

### Skill selection

- Primary skill: `architecture/07_queries.md`
- Router trigger terms: none — no router change
- Excluded alternatives: none

## Implementation plan

### Step 1 — Add new imports to `list_task_coordination_threads.py`

File: `app/beyo_manager/services/queries/tasks/list_task_coordination_threads.py`

Add the following imports (alongside the existing ones):

```python
from sqlalchemy.orm import selectinload

from beyo_manager.domain.emails.serializers import serialize_email_message, serialize_email_thread
from beyo_manager.domain.images.enums import ImageLinkEntityTypeEnum
from beyo_manager.domain.images.serializers import serialize_image, serialize_image_light
from beyo_manager.domain.tasks.serializers import serialize_item, serialize_task
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.images.image import Image
from beyo_manager.models.tables.images.image_link import ImageLink
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.tasks.task_item import TaskItem
```

Note: `serialize_email_thread` and `serialize_task` are already imported — do not duplicate them. Only add what is missing.

### Step 2 — Collect page-level ID sets after the main query

After the existing `page = rows[:limit]` line, add:

```python
task_ids = [task.client_id for _, _, task, _ in page]
thread_ids = [thread.client_id for thread, _, _, _ in page]
```

### Step 3 — Batch-load primary items and their images

Replicate the pattern from `list_tasks` lines 310–349 exactly:

```python
# Load TaskItem records for every task on this page
task_items_result = await ctx.session.execute(
    select(TaskItem).where(
        TaskItem.workspace_id == ctx.workspace_id,
        TaskItem.task_id.in_(task_ids),
        TaskItem.removed_at.is_(None),
    )
)
task_items = task_items_result.scalars().all()

primary_item_ids = [ti.item_id for ti in task_items if ti.role.value == "primary"]
task_to_primary_item_id = {ti.task_id: ti.item_id for ti in task_items if ti.role.value == "primary"}

items_map: dict[str, Item] = {}
if primary_item_ids:
    items_result = await ctx.session.execute(
        select(Item).where(
            Item.workspace_id == ctx.workspace_id,
            Item.client_id.in_(primary_item_ids),
            Item.is_deleted.is_(False),
        )
    )
    items_map = {item.client_id: item for item in items_result.scalars().all()}

# Batch-load images for all primary items in a single query
item_images_map: dict[str, list] = {}
if primary_item_ids:
    img_result = await ctx.session.execute(
        select(Image, ImageLink.entity_client_id)
        .join(
            ImageLink,
            and_(
                ImageLink.image_id == Image.client_id,
                ImageLink.entity_type == ImageLinkEntityTypeEnum.ITEM,
                ImageLink.entity_client_id.in_(primary_item_ids),
            ),
        )
        .options(selectinload(Image.last_event))
        .where(Image.deleted_at.is_(None))
        .order_by(ImageLink.entity_client_id, ImageLink.display_order.asc())
    )
    for image, item_id in img_result.all():
        image_list = item_images_map.setdefault(item_id, [])
        image_list.append(
            serialize_image(image) if not image_list else serialize_image_light(image)
        )
```

### Step 4 — Batch-load last message per thread

```python
# Fetch the latest message per thread using DISTINCT ON (PostgreSQL)
last_message_map: dict[str, EmailMessage] = {}
if thread_ids:
    msg_result = await ctx.session.execute(
        select(EmailMessage)
        .where(EmailMessage.thread_id.in_(thread_ids))
        .distinct(EmailMessage.thread_id)
        .order_by(
            EmailMessage.thread_id,
            EmailMessage.sent_or_received_at.desc().nullslast(),
        )
    )
    for msg in msg_result.scalars().all():
        last_message_map[msg.thread_id] = msg
```

`DISTINCT ON (thread_id)` combined with `ORDER BY thread_id, sent_or_received_at DESC` is served by the existing composite index `ix_email_messages_thread_time` on `(thread_id, sent_or_received_at)`. No migration needed.

### Step 5 — Update the return serialization

Replace the existing return block:

```python
# BEFORE
return {
    "coordination_threads": [
        {
            "thread": serialize_email_thread(thread, user_state),
            "task": serialize_task(task, customer_coordination_instances=[coordination]),
        }
        for thread, coordination, task, user_state in page
    ],
    ...
}
```

With:

```python
# AFTER
return {
    "coordination_threads": [
        {
            "thread": serialize_email_thread(thread, user_state),
            "task": serialize_task(task, customer_coordination_instances=[coordination]),
            "primary_item": serialize_item(items_map.get(task_to_primary_item_id.get(task.client_id))),
            "item_images": item_images_map.get(task_to_primary_item_id.get(task.client_id), []),
            "last_message": (
                serialize_email_message(last_message_map[thread.client_id])
                if thread.client_id in last_message_map
                else None
            ),
        }
        for thread, coordination, task, user_state in page
    ],
    "coordination_threads_pagination": {
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
    },
}
```

`serialize_item(None)` already returns `None` by the domain serializer convention — verify this in `app/beyo_manager/domain/tasks/serializers.py` before applying (relational read permitted: confirming `None`-safety of an existing function signature).

### Step 6 — Update the frontend handoff document

File: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_customer_coordination_email_and_counts_20260704.md`

#### 6a — Update section 5 response shape

In **section 5** (`GET /api/v1/tasks/customer-coordination/threads`), extend the `coordination_threads[]` example JSON to add the three new keys after `"task"`:

```json
{
  "thread": { ... },
  "task": { ... },
  "primary_item": {
    "client_id": "itm_abc",
    "workspace_id": "wrk_1",
    "article_number": "ABC-123",
    "sku": "SKU-XYZ",
    "designer": "Cassina",
    "item_position": "Living room",
    "item_category_snapshot": "Sofa",
    "item_major_category_snapshot": "Upholstery",
    "height_in_cm": 85,
    "width_in_cm": 210,
    "depth_in_cm": 95,
    "item_value_minor": 120000,
    "item_cost_minor": null,
    "item_currency": "sek",
    "quantity": 1,
    "external_id": null,
    "external_url": null,
    "external_source": null,
    "external_order_id": null,
    "is_deleted": false,
    "created_at": "2026-06-01T10:00:00+00:00",
    "updated_at": null
  },
  "item_images": [
    {
      "client_id": "img_1",
      "url": "https://...",
      "thumbnail_url": "https://...",
      "display_order": 0
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
```

Add the following rows to the **Response notes** table in section 5:

| Field | Notes |
|---|---|
| `coordination_threads[].primary_item` | Serialized primary item for the task, or `null` if the task has no primary item |
| `coordination_threads[].item_images` | Ordered image list for the primary item. First entry uses full `serialize_image` shape (includes `last_event`); subsequent entries use `serialize_image_light` shape. Empty array when the task has no primary item or the item has no images. |
| `coordination_threads[].last_message` | Most recent message (by `sent_or_received_at DESC`) in the thread regardless of direction, or `null` when the thread has no messages yet. See `serialize_email_message` shape in section 7. |

Also add to the **Backend delivery context → API or contract changes** bullet list:

```
- **Extended** `GET /api/v1/tasks/customer-coordination/threads` — each element now includes `primary_item`, `item_images`, and `last_message`
```

#### 6b — Add section 7: `GET /api/v1/email-threads/{thread_id}/messages`

Insert after section 6 (before `## Validation notes`):

```markdown
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

\`\`\`json
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
\`\`\`

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

The requesting user must either be the **owner** of the email connection or have role `ADMIN` or `MANAGER`. A `403` is returned if the connection is owned by a different user and the requesting role is `SELLER` or `WORKER`.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread not found or connection not found |
```

#### 6c — Add section 8: `POST /api/v1/email-threads/{thread_id}/read`

```markdown
### 8. `POST /api/v1/email-threads/{thread_id}/read`

Marks a thread as read for the current user by recording `last_read_at = now()` on the user-state record. Creates the user-state record if it does not yet exist. After this call, `thread.is_unread` will be `false` for the requesting user (until a new inbound message arrives).

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the email thread |

#### Request body

None — no body required.

#### Success response `200`

\`\`\`json
{ "marked_read": true }
\`\`\`

#### Behavior notes

- Idempotent — calling it multiple times is safe; `last_read_at` is always updated to the current timestamp.
- The unread badge in the coordination thread inbox should be recalculated after calling this endpoint (either by re-fetching `GET /api/v1/email-threads/unread-count` or by toggling the `is_unread` flag optimistically on the local thread record).

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread or connection not found |
```

#### 6d — Add section 9: `POST /api/v1/email-threads/{thread_id}/send`

```markdown
### 9. `POST /api/v1/email-threads/{thread_id}/send`

Sends an outbound reply email within an existing thread. The backend resolves the correct `in_reply_to` and `References` headers automatically from the thread's latest message so the reply is threaded correctly in the customer's email client.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the thread to reply within |

#### Request body

\`\`\`json
{
  "connection_client_id": "ecn_abc",
  "to_addresses": ["customer@example.com"],
  "cc_addresses": [],
  "bcc_addresses": [],
  "subject": "Re: din order",
  "text_body": "Hej, din möbel är klar för upphämtning.",
  "html_body": null
}
\`\`\`

| Field | Type | Required | Notes |
|---|---|---|---|
| `connection_client_id` | `string` | Yes | Must be an active connection owned by the requesting user |
| `to_addresses` | `string[]` | Yes | Recipient email addresses |
| `cc_addresses` | `string[]` | No | Default `[]` |
| `bcc_addresses` | `string[]` | No | Default `[]` |
| `subject` | `string` | Yes | The reply subject. Convention: prefix with `Re: ` to match thread. |
| `text_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` required |
| `html_body` | `string \| null` | Conditional | At least one of `text_body` or `html_body` required |

> `entity_type`, `entity_client_id`, `major_entity_type`, `major_entity_client_id`, and `topic` fields in the body model are **ignored** when `thread_client_id` is supplied — the thread already carries its entity linkage.

#### Success response `200`

\`\`\`json
{
  "thread_client_id": "eth_123",
  "message_client_id": "emsg_new",
  "send_success": true,
  "send_error": null
}
\`\`\`

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
```

#### 6e — Add section 10: `POST /api/v1/email-threads/sync-targeted`

```markdown
### 10. `POST /api/v1/email-threads/sync-targeted`

Triggers a targeted IMAP sync to pull in any inbound replies for one or more specific threads. The backend searches for RFC message IDs of the most recent outbound messages from each thread, then fetches matching inbound messages from the IMAP folder. Use this after sending an email to proactively check for a reply.

#### Request body

\`\`\`json
{
  "connection_client_id": "ecn_abc",
  "thread_client_ids": ["eth_1", "eth_2"],
  "entity_type": null,
  "entity_client_ids": [],
  "major_entity_type": null,
  "major_entity_client_id": null,
  "max_threads": 50
}
\`\`\`

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

**Typical usage for coordination inbox:** pass `thread_client_ids` with the IDs of threads currently visible in the inbox, or pass `entity_type = "task_customer_coordination"` with `entity_client_ids` for the visible coordination records.

#### Success response `200`

\`\`\`json
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
\`\`\`

| Field | Notes |
|---|---|
| `requested_thread_count` | Number of threads matched by the request scoping filters |
| `synced_thread_count` | Number of threads that had at least one outbound RFC message ID to search for |
| `searched_rfc_message_id_count` | Total unique RFC IDs searched across IMAP |
| `matched_uid_count` | Number of IMAP UIDs found matching the RFC IDs |
| `fetched_message_count` | Number of messages downloaded from IMAP |
| `created_message_count` | Number of new `EmailMessage` records persisted |
| `existing_message_count` | Messages already in the DB (skipped, not duplicated) |
| `threads_with_new_messages` | Array of `thread_client_id` strings that received at least one new message |
| `thread_errors` | Map of `thread_client_id → error string` for threads that failed individually |
| `sync_success` | `true` when no thread-level errors occurred |
| `sync_error` | Error string when any thread failed; `null` on full success |

**After receiving the response:** if `threads_with_new_messages` is non-empty, re-fetch `GET /api/v1/email-threads/{thread_id}/messages` for those threads to show the new inbound messages. Also re-fetch `GET /api/v1/email-threads/unread-count` to update the inbox badge.

#### Error responses

| HTTP | Condition |
|---|---|
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | A referenced connection does not exist |
```

#### 6f — Add section 11: `POST /api/v1/email-threads/{thread_id}/sync`

```markdown
### 11. `POST /api/v1/email-threads/{thread_id}/sync`

Triggers a targeted IMAP sync for a **single** thread. The backend takes the most recent outbound RFC message IDs from the thread and searches the IMAP inbox for matching replies. Use this when the user opens a conversation view to check for new replies in real time.

This is the single-thread variant of `POST /sync-targeted` (section 10). Prefer this endpoint when only one thread needs to be refreshed; use the batch variant when refreshing the whole inbox.

#### Path parameters

| Param | Type | Notes |
|---|---|---|
| `thread_id` | `string` | `client_id` of the thread to sync |

#### Request body

None — no body required.

#### Success response `200`

\`\`\`json
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
\`\`\`

| Field | Notes |
|---|---|
| `thread_client_id` | The thread that was synced |
| `searched_rfc_message_id_count` | Number of outbound RFC message IDs searched in IMAP (up to 10 most recent outbound messages). `0` when the thread has no outbound messages yet — sync is skipped and `sync_success` is `true`. |
| `matched_uid_count` | IMAP UIDs found matching the searched IDs |
| `fetched_message_count` | Messages downloaded from IMAP |
| `created_message_count` | New `EmailMessage` records persisted |
| `existing_message_count` | Messages already in DB (skipped, not duplicated) |
| `sync_success` | `true` when the IMAP search and processing succeeded |
| `sync_error` | `null` on success; error string when IMAP search failed |

**After receiving the response:** if `created_message_count > 0`, re-fetch `GET /{thread_id}/messages` to show the new inbound messages. Also refresh `GET /email-threads/unread-count` if the thread was previously marked read.

#### Error responses

| HTTP | Condition |
|---|---|
| `400` | IMAP provider search failed (wrapped as `DomainError`) |
| `401` | Missing or invalid auth token |
| `403` | Requesting user is not the connection owner and does not have ADMIN/MANAGER role |
| `404` | Thread not found, connection not found, or sync state not initialised for the connection |
```

#### 6g — Update `## Backend delivery context`

In the **Backend delivery context → What backend implemented** bullet, add:

```
  - Thread message list, mark-as-read, reply, and targeted IMAP sync endpoints for email threads (`/api/v1/email-threads/...`).
```

In **API or contract changes**, add:

```
  - **New** `GET /api/v1/email-threads/{thread_id}/messages`
  - **New** `POST /api/v1/email-threads/{thread_id}/read`
  - **New** `POST /api/v1/email-threads/{thread_id}/send` (reply within thread)
  - **New** `POST /api/v1/email-threads/{thread_id}/sync` (single-thread targeted IMAP sync)
  - **New** `POST /api/v1/email-threads/sync-targeted` (batch targeted IMAP sync)
```

#### 6h — Update `## Validation notes`

Append to the **Suggested frontend validation** list:

```
  - After calling `POST /{thread_id}/read`, optimistically clear `is_unread` on the thread in local state and refresh `unread-count`.
  - After `POST /{thread_id}/send`, re-fetch `GET /{thread_id}/messages` to show the sent message in the conversation view.
  - After `POST /{thread_id}/sync`, if `created_message_count > 0` re-fetch the message list and refresh `unread-count`.
  - After `POST /sync-targeted`, iterate `threads_with_new_messages` and re-fetch messages for each thread that received new content.
  - `send_error` on a message in the messages list means SMTP delivery failed even though the message is persisted — show a delivery-failed indicator on that message.
```

## Risks and mitigations

- Risk: `serialize_item(None)` raises `AttributeError` if the function does not guard against `None`.
  Mitigation: Before Step 5, read the `serialize_item` function signature in `domain/tasks/serializers.py`. If it does not handle `None`, wrap the call: `serialize_item(items_map.get(...)) if items_map.get(...) else None`.

- Risk: `Image.last_event` relationship may not exist on the `Image` model, causing a `selectinload` error.
  Mitigation: Read `app/beyo_manager/models/tables/images/image.py` to confirm `last_event` is a mapped relationship (relational read permitted). If absent, drop the `.options(selectinload(Image.last_event))` line — it is a performance hint only.

- Risk: `DISTINCT ON` is PostgreSQL-specific; SQLAlchemy's `.distinct(column)` generates it correctly only for PostgreSQL dialects.
  Mitigation: The project already uses PostgreSQL exclusively (confirmed by existing `op.execute("ALTER TYPE …")` migrations). No alternative is needed.

- Risk: `task_to_primary_item_id.get(task.client_id)` returns `None` when a task has no primary item, causing `item_images_map.get(None, [])` — which is safe but reads the wrong key if any image was stored under key `None`.
  Mitigation: `item_images_map` is only populated for `primary_item_ids` which are non-`None` strings. `dict.get(None, [])` will always return `[]` safely.

## Validation plan

- `python -c "from beyo_manager.services.queries.tasks.list_task_coordination_threads import list_task_coordination_threads"` → no import error
- `python -c "from beyo_manager.routers.api_v1.tasks import router"` → no import error
- `GET /api/v1/tasks/customer-coordination/threads` with at least one thread in the DB → response contains `primary_item`, `item_images`, `last_message` on each element
- Thread whose task has no primary item → `"primary_item": null`, `"item_images": []`
- Thread with no messages → `"last_message": null`
- Thread with messages → `"last_message"` contains the most recent message fields (`direction`, `body_preview`, `sent_or_received_at`)

## Review log

_(empty — awaiting first implementation pass)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
