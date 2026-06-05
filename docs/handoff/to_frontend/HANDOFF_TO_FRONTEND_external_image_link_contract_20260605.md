# HANDOFF_TO_FRONTEND_external_image_link_contract_20260605

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_external_image_link_contract_20260605`
- Created at (UTC): `2026-06-05T07:22:31Z`
- Owner agent: `codex`
- Source plan: `application_contracts/backend/docs/architecture/archives/implementation/PLAN_external_image_link_20260604.md`
- Source summary: `application_contracts/backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_external_image_link_20260604.md`

## Backend delivery context

- What backend implemented:
  - New write endpoint to register an already-hosted image URL and attach it to an entity in one call.
  - No upload URL, S3 upload, or confirm-upload flow is required for this path.
  - Optional inline annotations are supported on create.
- API or contract changes:
  - New endpoint: `POST /api/v1/images/from-url`
  - Existing image endpoints were not changed.
- Feature flags/toggles (if any):
  - None.

## Frontend action required

1. Use `POST /api/v1/images/from-url` when the image already exists at an external CDN/hosted URL and should be attached directly to an item, case, case message, or item category.
2. Send either a single object or a top-level JSON array of objects. Batch mode is all-or-nothing: if one item is invalid, none of the images are created.
3. Restrict usage to `admin` and `manager` sessions. `worker` and `seller` sessions should expect HTTP 403.
4. After a successful create, refetch `GET /api/v1/images?entity_type=<...>&entity_client_id=<...>` if the UI needs `display_order`, `link_client_id`, or the full linked gallery shape. The create response returns image records only, not image-link records.
5. Treat the returned `image_url` as immediately renderable in `<img src>`. The backend stores and returns the absolute URL exactly as provided.

## Interface details

- Endpoint: `POST /api/v1/images/from-url`
- Auth: Bearer JWT required. Allowed roles: `admin`, `manager`.

- Supported `entity_type` values:
  - `item`
  - `case`
  - `case_conversation_message`
  - `item_category`

- Single-item request shape:

```json
{
  "image_url": "https://cdn.example.com/items/itm_1/main.webp",
  "entity_type": "item",
  "entity_client_id": "itm_01JXABCDEF1234567890ABCDE",
  "image_client_id": "img_external_1",
  "width_px": 1600,
  "height_px": 900,
  "image_annotations": [
    {
      "tool": "text",
      "x": 10,
      "y": 20,
      "text": "Existing scratch"
    }
  ]
}
```

- Batch request shape:

```json
[
  {
    "image_url": "https://cdn.example.com/items/itm_1/front.webp",
    "entity_type": "item",
    "entity_client_id": "itm_01JXABCDEF1234567890ABCDE"
  },
  {
    "image_url": "https://cdn.example.com/items/itm_1/back.webp",
    "entity_type": "item",
    "entity_client_id": "itm_01JXABCDEF1234567890ABCDE"
  }
]
```

- Field notes:

| Field | Type | Required | Notes |
|---|---|---|---|
| `image_url` | `string` | yes | Must start with `http://` or `https://` |
| `entity_type` | `string` | yes | Must be one of the supported values above |
| `entity_client_id` | `string` | yes | Entity public `client_id` |
| `image_client_id` | `string \| null` | no | Optional optimistic client ID; if provided it must start with `img_` |
| `width_px` | `number \| null` | no | Positive integer only |
| `height_px` | `number \| null` | no | Positive integer only |
| `image_annotations` | `object[] \| null` | no | Same payload rules as `confirm-upload` annotations |

- Success response shape, single item:

```json
{
  "ok": true,
  "data": {
    "image": {
      "client_id": "img_external_1",
      "image_url": "https://cdn.example.com/items/itm_1/main.webp",
      "storage_provider": "external",
      "source_type": "external_url",
      "source_reference": null,
      "width_px": 1600,
      "height_px": 900,
      "file_size_bytes": null,
      "created_at": "2026-06-05T07:22:31+00:00",
      "last_event": {
        "client_id": "iev_01JXABCDEF1234567890ABCDE",
        "event_type": "link_external_image",
        "state": "requested",
        "created_at": "2026-06-05T07:22:31+00:00",
        "last_error": null
      },
      "events": [],
      "image_annotation": {
        "client_id": "ian_01JXABCDEF1234567890ABCDE",
        "annotation_type": "text",
        "data": {
          "tool": "text",
          "x": 10,
          "y": 20,
          "text": "Existing scratch"
        },
        "accuracy": null,
        "created_at": "2026-06-05T07:22:31+00:00"
      },
      "image_annotations": [
        {
          "client_id": "ian_01JXABCDEF1234567890ABCDE",
          "annotation_type": "text",
          "data": {
            "tool": "text",
            "x": 10,
            "y": 20,
            "text": "Existing scratch"
          },
          "accuracy": null,
          "created_at": "2026-06-05T07:22:31+00:00"
        }
      ]
    }
  },
  "warnings": []
}
```

- Success response shape, batch:

```json
{
  "ok": true,
  "data": {
    "images": [
      {
        "client_id": "img_01",
        "image_url": "https://cdn.example.com/items/itm_1/front.webp",
        "storage_provider": "external",
        "source_type": "external_url"
      },
      {
        "client_id": "img_02",
        "image_url": "https://cdn.example.com/items/itm_1/back.webp",
        "storage_provider": "external",
        "source_type": "external_url"
      }
    ]
  },
  "warnings": []
}
```

- Error cases:

| HTTP | `ok` | Condition |
|---|---|---|
| 400 | `false` | Invalid `image_url`, unsupported `entity_type`, duplicate `image_client_id` in batch, invalid annotations, empty batch, or invalid dimensions |
| 403 | `false` | JWT role is not `admin` or `manager` |
| 401 | `false` | JWT missing or invalid |

Standard error shape:

```json
{
  "ok": false,
  "error": "Human-readable message"
}
```

## Validation notes

- Backend validation run:
  - Command import smoke test passed.
  - Focused unit tests passed for create command validation and router batch payload wrapping.
  - Alembic migration applied successfully and verified at head.
- Suggested frontend validation:
  - Create one external item image and confirm the image renders directly from the returned `image_url`.
  - Create two images in one batch and verify the gallery appends both after a refetch of the list endpoint.
  - Send one invalid URL in a batch and confirm the UI treats the entire request as failed.
  - Confirm `worker` or `seller` sessions receive HTTP 403 and do not expose this action in the UI.
  - Confirm annotation-enabled creates still render when `image_annotation` and `image_annotations` are both present.

## Trace links

- Parent plan: `application_contracts/backend/docs/architecture/archives/implementation/PLAN_external_image_link_20260604.md`
- Parent summary: `application_contracts/backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_external_image_link_20260604.md`
- Related debug plan (optional): `—`
