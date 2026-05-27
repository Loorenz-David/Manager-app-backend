# HANDOFF_TO_FRONTEND_cases_router_contract_20260525

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_cases_router_contract_20260525`
- Created at (UTC): `2026-05-25T18:01:42Z`
- Owner agent: `copilot`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - A full cases API surface under `/api/v1/cases` for case creation, listing, linking entities, participant management, conversations, messages, and unread tracking.
- API or contract changes:
  - `GET /api/v1/cases` now returns the enriched list-card payload (`case_type`, `created_by`, `entity_type`, `last_message_seq`, optional nested `task.item.item_image`).
  - `GET /api/v1/cases/{case_client_id}` now supports `before_message_seq` and `messages_limit` and returns paginated `case_conversation_messages` with `created_by`, `images`, and `mentions`.
  - `GET /api/v1/cases/{case_client_id}` returns `case.mentions` as a de-duplicated mention list resolved from mention links.
- Feature flags/toggles (if any):
  - None in the cases router flow.

## Frontend action required

1. Integrate against the exact response envelope used by all case endpoints: success is `{ "ok": true, "data": ..., "warnings": [] }`, failure is `{ "ok": false, "error": "..." }`.
2. Preserve the backend's current request quirks: several endpoints require an ID in both the path and the JSON body because the FastAPI body models mark that field as required even though the router overwrites it with the path value.
3. Use the enum and content-block values below exactly as written; some invalid enum inputs currently fall through to a generic `500` instead of a validation `422`.

## Interface details

### Base route

- Prefix: `/api/v1/cases`
- Auth: all endpoints require a valid JWT via `get_jwt_claims`
- Shared success envelope:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- Shared error envelope:

```json
{
  "ok": false,
  "error": "..."
}
```

- Standard error statuses:
  - `404` for `NotFound`
  - `409` for `ConflictError`
  - `422` for `ValidationError`
  - `500` for unexpected internal errors

### Shared object shapes

#### `Case`

```json
{
  "client_id": "ca_...",
  "state": "open",
  "type_label": "Customer return",
  "participants_count": 0,
  "conversations_count": 0,
  "messages_count": 0,
  "created_at": "2026-05-25T17:40:10.123456+00:00",
  "created_by_id": "usr_..."
}
```

#### `CaseLink`

```json
{
  "client_id": "clk_...",
  "entity_type": "task",
  "entity_client_id": "tsk_...",
  "role": "subject",
  "created_at": "2026-05-25T17:41:10.123456+00:00"
}
```

#### `CaseParticipant`

```json
{
  "client_id": "cpt_...",
  "user_id": "usr_...",
  "last_read_message_seq": 0,
  "joined_at": "2026-05-25T17:42:10.123456+00:00"
}
```

#### `CaseConversation`

```json
{
  "client_id": "ccv_...",
  "state": "open",
  "messages_count": 0,
  "last_message_seq": 0,
  "created_at": "2026-05-25T17:43:10.123456+00:00",
  "last_messages": []
}
```

#### `CaseConversationMessage`

```json
{
  "client_id": "ccm_...",
  "message_seq": 1,
  "content": [
    {
      "type": "text",
      "text": "Hello",
      "mention": null,
      "label_value": null,
      "link": null
    }
  ],
  "plain_text": "Hello",
  "has_been_edited": false,
  "has_been_deleted": false,
  "created_at": "2026-05-25T17:44:10.123456+00:00"
}
```

If a message has been soft-deleted, the returned object becomes:

```json
{
  "client_id": "ccm_...",
  "message_seq": 1,
  "content": null,
  "plain_text": "",
  "has_been_edited": false,
  "has_been_deleted": true,
  "created_at": "2026-05-25T17:44:10.123456+00:00"
}
```

### Enum values

- `case.state` and `new_state`: `open` | `resolving` | `resolved`
- `link.entity_type`: `task` | `customer`
- `link.role`: `origin` | `subject` | `context` | `actor` | `resolution`
- `message.content[].type`: `text` | `mention` | `label` | `link`

### Message content block request shapes

All message write endpoints accept `content` as an array of blocks.

Text block:

```json
{
  "type": "text",
  "text": "Plain text"
}
```

Mention block:

```json
{
  "type": "mention",
  "text": "@Jane Doe",
  "mention": {
    "mention_table": "users",
    "mention_id": "usr_123",
    "client_id": "usr_123"
  }
}
```

Label block:

```json
{
  "type": "label",
  "text": "Urgent",
  "label_value": "urgent"
}
```

Link block:

```json
{
  "type": "link",
  "text": "Open spec",
  "link": "https://example.com/spec"
}
```

Validation rules enforced by backend:

- `content` must be a JSON array.
- Every block must be an object.
- Every block needs `type` and `text`.
- `mention` blocks must include `mention.mention_table`, `mention.mention_id`, and `mention.client_id`.
- `label` blocks must include `label_value`.
- `link` blocks must include `link`.

## Endpoint-by-endpoint contract

### 1. Create case

- Method: `POST`
- URL: `/api/v1/cases`
- What it does:
  - Creates a new case in `open` state and returns the serialized case.
- Request body:

```json
{
  "client_id": "ca_custom_optional",
  "case_type_id": "cat_123_optional",
  "type_label": "Customer return"
}
```

- Notes:
  - All fields are optional.
  - If `client_id` is provided, it must be a valid case client ID and must be unique.
  - If `case_type_id` resolves to a case type and `type_label` is omitted, backend copies the case type name into `type_label`.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case": {
      "client_id": "ca_...",
      "state": "open",
      "type_label": "Customer return",
      "participants_count": 0,
      "conversations_count": 1,
      "messages_count": 0,
      "created_at": "2026-05-25T17:40:10.123456+00:00",
      "created_by_id": "usr_...",
      "conversation_client_id": "ccv_...",
      "conversation_messages_count": 0,
      "conversation_last_message_seq": 0,
      "conversation_created_at": "2026-05-25T17:40:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `409`: `Provided client_id is already in use.`
  - `422`: parser or client ID validation errors

### 2. List cases

- Method: `GET`
- URL: `/api/v1/cases`
- What it does:
  - Lists cases ordered by creation time descending (newest first), with optional filters for state, creator, linked entity, and free-text search.
- Query params:
  - `state` optional (single value, backward-compatible)
  - `case_state` optional comma-separated list of values, for example `open,resolving`
  - `q` optional string search (max length `200`)
  - `created_by_id` optional
  - `entity_type` optional, only effective when `entity_client_id` is also present
  - `entity_client_id` optional
  - `offset` optional, default `0`
  - `limit` optional, default `50`
- Search behavior for `q`:
  - Matches the case's stored type label value.
  - Matches `case conversation message.plain_text`.
  - For links where `entity_type = task`, also matches related task item `article_number` and `sku`.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "cases": [
      {
        "client_id": "ca_...",
        "created_at": "2026-05-25T17:40:10.123456+00:00",
        "state": "open",
        "case_type_id": "cty_...",
        "case_type": {
          "name": "Customer return",
          "image": "https://cdn.example.com/case-types/customer-return.webp"
        },
        "participant_count": 2,
        "messages_count": 4,
        "created_by": {
          "client_id": "usr_...",
          "username": "jane",
          "profile_picture": "https://..."
        },
        "entity_type": "task",
        "last_message_seq": 4,
        "task": {
          "client_id": "tsk_...",
          "state": "working",
          "return_source": "after_purchase",
          "task_type": "return",
          "ready_by_at": "2026-05-26T12:00:00+00:00",
          "item": {
            "client_id": "itm_...",
            "article_number": "ART-123",
            "sku": "SKU-123",
            "item_image": {
              "client_id": "img_...",
              "image_url": "https://...",
              "width_px": 1200,
              "height_px": 800,
              "file_size_bytes": 234567
            }
          }
        }
      }
    ]
  }
}
```

- Common errors:
  - `422`: invalid `state`, invalid `case_state` value, or invalid `entity_type`.

### 3. Get unread counts

- Method: `GET`
- URL: `/api/v1/cases/unread-counts`
- What it does:
  - Returns unread counts keyed by case client ID for the authenticated user.
- Query params:
  - `case_client_ids` optional comma-separated string, for example `ca_1,ca_2`
- Behavior notes:
  - If `case_client_ids` is omitted, backend only returns entries whose unread count is greater than `0`.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case_unread_counts": {
      "ca_123": 3,
      "ca_456": 0
    }
  }
}
```

### 4. Get case

- Method: `GET`
- URL: `/api/v1/cases/{case_client_id}`
- What it does:
  - Fetches one case by client ID and returns a paginated page of conversation messages.
- Query params:
  - `before_message_seq` optional integer. When set, returns older messages with `message_seq < before_message_seq`.
  - `messages_limit` optional integer, default `10`, max `50`.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case": {
      "client_id": "ca_...",
      "state": "open",
      "type_label": "Customer return",
      "participants_count": 2,
      "conversations_count": 1,
      "messages_count": 4,
      "created_at": "2026-05-25T17:40:10.123456+00:00",
      "created_by_id": "usr_...",
      "conversation_client_id": "ccv_...",
      "conversation_messages_count": 4,
      "conversation_last_message_seq": 4,
      "conversation_created_at": "2026-05-25T17:40:10.123456+00:00",
      "mentions": [
        {
          "mention_table": "users",
          "mention_id": "usr_...",
          "mention_data": {
            "client_id": "usr_...",
            "username": "jane",
            "profile_picture": "https://..."
          }
        }
      ]
    },
    "case_conversation_messages": [
      {
        "case_id": "ca_...",
        "client_id": "ccm_...",
        "message_seq": 91,
        "created_at": "2026-05-25T17:44:10.123456+00:00",
        "created_by": {
          "client_id": "usr_...",
          "username": "jane",
          "profile_picture": "https://..."
        },
        "content": [
          {
            "type": "text",
            "text": "Hello"
          }
        ],
        "plain_text": "Hello",
        "has_been_edited": false,
        "updated_at": null,
        "images": [
          {
            "client_id": "img_...",
            "image_url": "https://...",
            "storage_provider": "s3",
            "source_type": "uploaded",
            "source_reference": "s3_image_url",
            "width_px": 1200,
            "height_px": 800,
            "file_size_bytes": 234567,
            "created_at": "2026-05-25T17:44:12.000000+00:00",
            "last_event": null,
            "events": [],
            "image_annotation": null
          }
        ],
        "mentions": [
          {
            "mention_table": "users",
            "mention_id": "usr_...",
            "mention_data": {
              "client_id": "usr_...",
              "username": "jane",
              "profile_picture": "https://..."
            }
          }
        ]
      }
    ],
    "messages_pagination": {
      "limit": 10,
      "has_more": true,
      "next_before_message_seq": 82
    }
  }
}
```

- Common errors:
  - `404`: `Case not found`

### 5. Update case

- Method: `PATCH`
- URL: `/api/v1/cases/{case_client_id}`
- What it does:
  - Updates case type and or type label, then returns the updated case.
- Request body:

```json
{
  "case_client_id": "ca_same_as_path_required_by_body_model",
  "case_type_id": "cat_123_optional",
  "type_label": "Warranty issue"
}
```

- Important frontend note:
  - `case_client_id` is required in the body by the router model even though the path value is what the router actually sends to the service.
  - If both `case_type_id` and `type_label` are omitted, backend returns `422`.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case": {
      "client_id": "ca_...",
      "state": "open",
      "type_label": "Warranty issue",
      "participants_count": 2,
      "conversations_count": 1,
      "messages_count": 4,
      "created_at": "2026-05-25T17:40:10.123456+00:00",
      "created_by_id": "usr_...",
      "conversation_client_id": "ccv_...",
      "conversation_messages_count": 4,
      "conversation_last_message_seq": 4,
      "conversation_created_at": "2026-05-25T17:40:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `404`: `Case not found`
  - `422`: `case_type_id or type_label is required`

### 6. Update case state

- Method: `PATCH`
- URL: `/api/v1/cases/{case_client_id}/state`
- What it does:
  - Changes the case state and returns the updated case.
- Request body:

```json
{
  "case_client_id": "ca_same_as_path_required_by_body_model",
  "new_state": "resolved"
}
```

- Important frontend note:
  - `case_client_id` is required in the body by the model, but the router overwrites it with the path parameter.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "case": {
      "client_id": "ca_...",
      "state": "resolved",
      "type_label": "Customer return",
      "participants_count": 2,
      "conversations_count": 1,
      "messages_count": 4,
      "created_at": "2026-05-25T17:40:10.123456+00:00",
      "created_by_id": "usr_...",
      "conversation_client_id": "ccv_...",
      "conversation_messages_count": 4,
      "conversation_last_message_seq": 4,
      "conversation_created_at": "2026-05-25T17:40:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `404`: `Case not found`
  - Invalid `new_state` currently risks a generic `500` instead of a `422`.

### 7. Link entity to case

- Method: `POST`
- URL: `/api/v1/cases/{case_client_id}/links`
- What it does:
  - Creates a new case link to a task or customer.
- Request body:

```json
{
  "case_client_id": "ca_same_as_path_required_by_body_model",
  "entity_type": "task",
  "entity_client_id": "tsk_123",
  "role": "subject"
}
```

- Important frontend note:
  - `case_client_id` is required in the body by the model, but the router overwrites it with the path parameter.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "link": {
      "client_id": "clk_...",
      "entity_type": "task",
      "entity_client_id": "tsk_123",
      "role": "subject",
      "created_at": "2026-05-25T17:41:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `404`: `Case not found`
  - Invalid `entity_type` or `role` currently risks a generic `500` instead of a `422`.

### 8. Unlink entity from case

- Method: `DELETE`
- URL: `/api/v1/cases/links/{case_link_client_id}`
- What it does:
  - Deletes a case link.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "deleted": true
  }
}
```

- Common errors:
  - `404`: `CaseLink not found`

### 9. List case links

- Method: `GET`
- URL: `/api/v1/cases/{case_client_id}/links`
- What it does:
  - Lists links for a case, optionally filtered by entity type and role.
- Query params:
  - `entity_type` optional
  - `role` optional
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "links": [
      {
        "client_id": "clk_...",
        "entity_type": "task",
        "entity_client_id": "tsk_123",
        "role": "subject",
        "created_at": "2026-05-25T17:41:10.123456+00:00"
      }
    ]
  }
}
```

- Common errors:
  - Invalid `entity_type` or `role` currently risks a generic `500` instead of a `422`.

### 10. Add participants

- Method: `POST`
- URL: `/api/v1/cases/{case_client_id}/participants`
- What it does:
  - Adds one or more users as case participants and returns only the newly created participant rows.
- Request body:

```json
{
  "case_client_id": "ca_same_as_path_required_by_body_model",
  "user_ids": ["usr_1", "usr_2"]
}
```

- Important frontend note:
  - `case_client_id` is required in the body by the model, but the router overwrites it with the path parameter.
- Behavior notes:
  - Existing participants are ignored.
  - Duplicate `user_ids` in the request are deduplicated because backend converts the list into a set.
  - Response `added` can be an empty array.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "added": [
      {
        "client_id": "cpt_...",
        "user_id": "usr_1",
        "last_read_message_seq": 0,
        "joined_at": "2026-05-25T17:42:10.123456+00:00"
      }
    ]
  }
}
```

- Common errors:
  - `404`: `Case not found`

### 11. Remove participant

- Method: `DELETE`
- URL: `/api/v1/cases/participants/{case_participant_client_id}`
- What it does:
  - Removes one participant row from a case.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "deleted": true
  }
}
```

- Common errors:
  - `404`: `CaseParticipant not found`

### 12. List participants

- Method: `GET`
- URL: `/api/v1/cases/{case_client_id}/participants`
- What it does:
  - Lists all participant rows for a case.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "participants": [
      {
        "client_id": "cpt_...",
        "user_id": "usr_1",
        "last_read_message_seq": 3,
        "joined_at": "2026-05-25T17:42:10.123456+00:00"
      }
    ]
  }
}
```

### 13. Get conversation

- Method: `GET`
- URL: `/api/v1/cases/conversations/{conversation_client_id}`
- What it does:
  - Fetches one conversation by client ID.
- Behavior notes:
  - `last_messages` is always an empty array in the current implementation because this query does not populate it.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "conversation": {
      "client_id": "ccv_...",
      "state": "open",
      "messages_count": 4,
      "last_message_seq": 4,
      "created_at": "2026-05-25T17:43:10.123456+00:00",
      "last_messages": []
    }
  }
}
```

- Common errors:
  - `404`: `Conversation not found`

### 14. Send message

- Method: `POST`
- URL: `/api/v1/cases/conversations/{conversation_client_id}/messages`
- What it does:
  - Validates message content, allocates the next message sequence number, creates the message, updates counters, and returns the created message.
- Request body:

```json
{
  "client_id": "ccm_custom_optional",
  "conversation_client_id": "ccv_same_as_path_required_by_body_model",
  "content": [
    {
      "type": "text",
      "text": "Hello"
    }
  ],
  "plain_text": "Hello"
}
```

- Important frontend note:
  - `conversation_client_id` is required in the body by the model, but the router overwrites it with the path parameter.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "message": {
      "client_id": "ccm_...",
      "message_seq": 5,
      "content": [
        {
          "type": "text",
          "text": "Hello",
          "mention": null,
          "label_value": null,
          "link": null
        }
      ],
      "plain_text": "Hello",
      "has_been_edited": false,
      "has_been_deleted": false,
      "created_at": "2026-05-25T17:44:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `404`: `Conversation not found`
  - `409`: `Provided client_id is already in use.`
  - `422`: content block validation errors

### 15. List messages

- Method: `GET`
- URL: `/api/v1/cases/conversations/{conversation_client_id}/messages`
- What it does:
  - Lists messages for a conversation ordered by `message_seq` descending.
- Query params:
  - `before_seq` optional, returns only messages whose `message_seq` is less than this value
  - `limit` optional, default `50`
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "messages": [
      {
        "client_id": "ccm_...",
        "message_seq": 5,
        "content": [
          {
            "type": "text",
            "text": "Newest first",
            "mention": null,
            "label_value": null,
            "link": null
          }
        ],
        "plain_text": "Newest first",
        "has_been_edited": false,
        "has_been_deleted": false,
        "created_at": "2026-05-25T17:44:10.123456+00:00"
      },
      {
        "client_id": "ccm_...",
        "message_seq": 4,
        "content": null,
        "plain_text": "",
        "has_been_edited": true,
        "has_been_deleted": true,
        "created_at": "2026-05-25T17:43:10.123456+00:00"
      }
    ]
  }
}
```

### 16. Edit message

- Method: `PATCH`
- URL: `/api/v1/cases/messages/{message_client_id}`
- What it does:
  - Replaces message content and plain text, marks the message as edited, and returns the updated message.
- Request body:

```json
{
  "message_client_id": "ccm_same_as_path_required_by_body_model",
  "content": [
    {
      "type": "text",
      "text": "Updated message"
    }
  ],
  "plain_text": "Updated message"
}
```

- Important frontend note:
  - `message_client_id` is required in the body by the model, but the router overwrites it with the path parameter.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "message": {
      "client_id": "ccm_...",
      "message_seq": 5,
      "content": [
        {
          "type": "text",
          "text": "Updated message",
          "mention": null,
          "label_value": null,
          "link": null
        }
      ],
      "plain_text": "Updated message",
      "has_been_edited": true,
      "has_been_deleted": false,
      "created_at": "2026-05-25T17:44:10.123456+00:00"
    }
  }
}
```

- Common errors:
  - `404`: `Message not found`
  - `422`: content validation errors
  - `422`: `deleted messages cannot be edited`

### 17. Soft delete message

- Method: `DELETE`
- URL: `/api/v1/cases/messages/{message_client_id}`
- What it does:
  - Marks a message as deleted and decrements message counters if this is the first delete.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "deleted": true
  }
}
```

- Common errors:
  - `404`: `Message not found`

### 18. Mark case participant read position

- Method: `POST`
- URL: `/api/v1/cases/messages/mark-read`
- What it does:
  - Advances a participant's `last_read_message_seq` to the max of the current value and the requested value.
- Request body:

```json
{
  "case_participant_client_id": "cpt_123",
  "up_to_message_seq": 5
}
```

- Behavior notes:
  - This endpoint never moves the read pointer backward.
- Success response:

```json
{
  "ok": true,
  "warnings": [],
  "data": {
    "last_read_message_seq": 5
  }
}
```

- Common errors:
  - `404`: `CaseParticipant not found`

## Behavior notes for frontend

- The cases router always wraps service output under `data`; there are no bare payload responses.
- Serializer output differs by endpoint:
  - `GET /api/v1/cases` returns list-card shape (`participant_count`, `created_by`, `entity_type`, `last_message_seq`, optional `task`).
  - Mutating case endpoints (`create`, `update`, `update state`) return case-first base shape with conversation expansion fields.
  - `GET /api/v1/cases/{case_client_id}` returns the base case shape plus `case.mentions`, `case_conversation_messages`, and `messages_pagination`.
  - `case_conversation_messages` from `GET /api/v1/cases/{case_client_id}` include `created_by`, `images`, and `mentions`, and are returned in ascending `message_seq` order within the page.
  - `list_messages` remains newest-first and uses the classic message serializer (`has_been_deleted` included).
- Message content stored by backend includes the normalized optional keys `mention`, `label_value`, and `link`, even when they are `null`.
- `add_participant` returns only newly added rows, not the full participant list after mutation.
- `mark-read` is monotonic and will not decrease `last_read_message_seq`.
- `get unread counts` is strict case-only: use `case_unread_counts`.

## Validation notes

- Backend validation run:
  - Contract compiled from router models, service commands and queries, serializers, content validators, enums, and shared response envelope code.
  - No executable test run was needed because this task is documentation-only.
- Suggested frontend validation:
  - Keep duplicated path IDs in request bodies where required by the current router models.
  - Enforce enum values client-side for `state`, `new_state`, `entity_type`, `role`, and message `content[].type`.
  - Validate message content blocks before submission to avoid backend `422` responses.

## Trace links

- Router: `backend/app/beyo_manager/routers/api_v1/cases.py`
- Success and error envelope: `backend/app/beyo_manager/routers/http/response.py`
- Case serializers: `backend/app/beyo_manager/domain/cases/serializers.py`
- Case enums: `backend/app/beyo_manager/domain/cases/enums.py`
- Message content validation: `backend/app/beyo_manager/services/infra/content.py`
- Request parsers: `backend/app/beyo_manager/services/commands/cases/requests/__init__.py`
- Service commands: `backend/app/beyo_manager/services/commands/cases/`
- Service queries: `backend/app/beyo_manager/services/queries/cases/`