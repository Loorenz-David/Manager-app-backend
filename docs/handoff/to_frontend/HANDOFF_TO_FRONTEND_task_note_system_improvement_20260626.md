# HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_task_note_system_improvement_20260626`
- Created at (UTC): `2026-06-26T10:56:46Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_task_note_system_improvement_20260626.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_task_note_system_improvement_20260626.md`

## Backend delivery context

- What backend implemented:
  - Moved task-note fetching out of `GET /api/v1/tasks/{task_id}` into a dedicated notes endpoint.
  - Changed task-note content payloads from a single dict to a list of validated content blocks.
  - Added `plain_text`, `users_read_list`, note images, and compact creator/updater user-role payloads to task-note responses.
  - Added a lightweight read-by write endpoint for append-only note read markers.
  - Added note image-link support in the image subsystem (`entity_type="note"`).
- API or contract changes:
  - `GET /api/v1/tasks/{task_id}` no longer returns `data.task_notes`.
  - `GET /api/v1/tasks/{task_id}/notes`
  - `POST /api/v1/tasks/{task_id}/notes`
  - `PATCH /api/v1/tasks/{task_id}/notes/{note_id}`
  - `POST /api/v1/tasks/{task_id}/notes/{note_id}/read-by`
  - `DELETE /api/v1/tasks/{task_id}/notes/{note_id}`
- Feature flags/toggles (if any):
  - None.
- Explicitly excluded from this handoff:
  - Pagination for task notes.
  - Realtime/WebSocket read-receipt events.

## Frontend action required

1. Stop reading task notes from `GET /api/v1/tasks/{task_id}` and load them from `GET /api/v1/tasks/{task_id}/notes` instead.
2. Send note `content` as an array of block objects, not a single dict.
3. Include `plain_text` when creating or updating notes if the UI keeps a flattened text representation.
4. Read note creator/updater data from `note.created_by` and `note.updated_by`, not separate ids.
5. Read attached images from `note_images`.
6. When marking a note read, call `POST /api/v1/tasks/{task_id}/notes/{note_id}/read-by` with the string identifiers the frontend wants appended.
7. If the frontend uses the generic image upload/link flows for note attachments, pass `entity_type: "note"` and `entity_client_id: "<note_id>"`.

## Interface details

- Response envelope for all success cases:

```json
{
  "ok": true,
  "data": {},
  "warnings": []
}
```

- Error envelope for all failure cases:

```json
{
  "ok": false,
  "error": "Human-readable message"
}
```

### 0. Create task with inline notes

- Endpoint:
  - `POST /api/v1/tasks`
- Notes can be created inline during task creation by including a `notes` array in the request body.
- Each note follows the same shape as the standalone create-note endpoint.
- `client_id` per note is optional. When provided, use the `tno_` prefix.
- Notes are committed in the same transaction as the task. All writes succeed or all fail together.

Request body excerpt:

```json
{
  "task_type": "repair",
  "notes": [
    {
      "client_id": "tno_01...",
      "note_type": "user_note",
      "content": [
        {"type": "text", "text": "Picked up from customer"}
      ],
      "plain_text": "Picked up from customer",
      "users_read_list": []
    }
  ]
}
```

- Success payload:
  - `POST /api/v1/tasks` still returns the task payload only. If the frontend needs note ids without pre-generating them, fetch them afterward from `GET /api/v1/tasks/{task_id}/notes`.

### 1. Get task detail

- Endpoint:
  - `GET /api/v1/tasks/{task_id}`
- Contract change:
  - `data.task_notes` has been removed.
- Frontend migration note:
  - Treat notes as a second request.

### 2. List task notes

- Endpoint:
  - `GET /api/v1/tasks/{task_id}/notes`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Path params:
  - `task_id: string`
- Success payload:

```json
{
  "ok": true,
  "data": {
    "task_notes": [
      {
        "note": {
          "client_id": "tno_01...",
          "task_id": "tsk_01...",
          "note_type": "user_note",
          "content": [
            {"type": "text", "text": "Customer called back"}
          ],
          "plain_text": "Customer called back",
          "users_read_list": ["usr_01...", "usr_02..."],
          "created_at": "2026-06-26T10:00:00+00:00",
          "created_by": {
            "client_id": "usr_01...",
            "username": "Anna",
            "profile_picture": null,
            "role": {"client_id": "role_01...", "name": "worker"},
            "workspace_role": {"client_id": "wrole_01...", "name": "worker"}
          },
          "updated_at": "2026-06-26T10:05:00+00:00",
          "updated_by": null,
          "is_deleted": false,
          "deleted_at": null
        },
        "note_images": [
          {
            "client_id": "img_01...",
            "image_url": "https://...",
            "storage_provider": "s3",
            "source_type": "uploaded",
            "source_reference": "s3_image_url",
            "width_px": 1200,
            "height_px": 800,
            "file_size_bytes": 123456,
            "created_at": "2026-06-26T10:00:01+00:00",
            "last_event": {
              "client_id": "iev_01...",
              "event_type": "upload_note_image",
              "state": "requested",
              "created_at": "2026-06-26T10:00:01+00:00",
              "last_error": null
            },
            "events": [],
            "image_annotation": null
          }
        ]
      }
    ]
  },
  "warnings": []
}
```

- Notes:
  - Ordering is ascending by note `created_at`.
  - No pagination keys are returned in this first version.

### 3. Create task note

- Endpoint:
  - `POST /api/v1/tasks/{task_id}/notes`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Request body:

```json
[
  {
    "client_id": "tno_01...",
    "note_type": "user_note",
    "content": [
      {"type": "text", "text": "First note"}
    ],
    "plain_text": "First note",
    "users_read_list": []
  },
  {
    "client_id": "tno_02...",
    "note_type": "user_note",
    "content": [
      {"type": "text", "text": "Second note"}
    ],
    "plain_text": "Second note"
  }
]
```

- Success payload:

```json
{
  "ok": true,
  "data": {
    "client_ids": ["tno_01...", "tno_02..."]
  },
  "warnings": []
}
```

- Notes:
  - `content` must be a list of content blocks.
  - `plain_text` defaults to `""` if omitted.
  - `users_read_list` defaults to `[]` if omitted.
  - To create a single note, wrap it in an array: `[{...}]`.
  - The array must not be empty. Sending `[]` is a validation error.
  - `client_id` is optional per note. When provided, it must use the `tno_` prefix and must not collide with an existing note id.

### 4. Update task note

- Endpoint:
  - `PATCH /api/v1/tasks/{task_id}/notes/{note_id}`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Request body:

```json
{
  "note_type": "correction_note",
  "content": [
    {"type": "text", "text": "Corrected customer callback note"}
  ],
  "plain_text": "Corrected customer callback note"
}
```

- Notes:
  - All fields are optional.
  - If `content` is provided, it must still be a list of blocks.
  - `plain_text` may be sent as `null` to clear it.

### 5. Mark note read-by

- Endpoint:
  - `POST /api/v1/tasks/{task_id}/notes/{note_id}/read-by`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Request body:

```json
{
  "user_ids": ["usr_01...", "usr_02..."]
}
```

- Success payload:

```json
{
  "ok": true,
  "data": {
    "client_id": "tno_01..."
  },
  "warnings": []
}
```

- Semantics:
  - Appends only.
  - Duplicate values are ignored.
  - The backend does not interpret the strings; it only stores them.

### 6. Delete task note

- Endpoint:
  - `DELETE /api/v1/tasks/{task_id}/notes/{note_id}`
- Auth and role access:
  - `ADMIN`, `MANAGER`, `WORKER`, `SELLER`
- Path params:
  - `task_id: string`
  - `note_id: string`
- Success payload:

```json
{
  "ok": true,
  "data": {
    "client_id": "tno_01..."
  },
  "warnings": []
}
```

- Semantics:
  - Soft-deletes the note rather than hard-deleting it.
  - Deleted notes are excluded from the default `GET /api/v1/tasks/{task_id}/notes` response.
  - The frontend should treat this as a destructive action and remove the note from the active note list after success.

## Notes for rollout

- The frontend should treat the `GET /tasks/{task_id}` note removal and `GET /tasks/{task_id}/notes` addition as one coordinated API-contract migration.
- Existing note UIs that already build rich content blocks for case messages can reuse the same block-array structure for task notes.
