# 05 — Admin: Slides & Media

Roles: **admin, manager**. Everything here works **only on `draft`** presentations
— any slide/media edit on a published/archived presentation returns **`409`**.

> **All slide/media endpoints return the whole updated presentation**
> (`{ "presentation": <full> }`, the same full shape as
> [04_admin_presentations.md](04_admin_presentations.md)), so the console always
> has the fresh, re-ordered graph after every change. There is no separate
> "slide" or "media" response object.

> **Media here is the asset layer.** Uploading media (below) creates the reusable
> `aupm_...` asset on a slide. **How that media is placed, timed, layered, and
> animated** in the slide is the *timeline composition* — set separately via
> `PUT /{id}/slides/{slide_id}/composition`. See
> **[09_slide_composition.md](09_slide_composition.md)**. Slides also gained
> `playback_mode`, `duration_ms`, `composition_schema_version`, and nullable
> `background_color` (hex `#RRGGBB` or `#RRGGBBAA`; `null` means no background),
> settable on create/update slide or via the composition endpoint.

---

## Slide object shape (inside `presentation.slides`)

```json
{
  "client_id": "aups_01J...",
  "sequence_order": 1,
  "title": "Search from one place",
  "description": "Use SKU, article number, or customer name.",
  "layout_type": "media_top",
  "background_color": null,
  "media": [ /* media objects, see below */ ],
  "action": { "label": "Try product search", "route": "/products/search" }
}
```

`action` is `null` unless `action_label` or `action_route` is set.

## Media object shape (inside `slide.media`)

```json
{
  "client_id": "aupm_01J...",
  "sequence_order": 1,
  "media_type": "video",
  "media_url": "https://<s3-presigned-GET>",
  "poster_url": "https://<s3-presigned-GET>",
  "fallback_url": null,
  "alt_text": "…",
  "mime_type": "video/mp4",
  "width": 1280,
  "height": 720,
  "duration_ms": 5000,
  "is_looping": true
}
```

`*_url` fields are derived presigned S3 GET URLs (read-only, short-lived).

---

## Slides

### POST `/{id}/slides` — add a slide

Appends a slide (next `sequence_order` is assigned automatically).

**Body** (all optional)

```json
{
  "title": "Search from one place",
  "description": "…",
  "layout_type": "media_top",
  "action_label": "Try product search",
  "action_route": "/products/search"
}
```

- `layout_type`: `media_top` (default) \| `media_full` \| `text_overlay`.
- `action_route`, if set, **must be a relative in-app path** starting with `/`
  (no `http(s)://`, no `//`). Otherwise `422`.

### PATCH `/{id}/slides/{slide_id}` — edit a slide

Same optional fields; omitted fields unchanged.

### DELETE `/{id}/slides/{slide_id}` — remove a slide

Soft-deletes the slide **and cascades** to its media.

### POST `/{id}/slides/reorder` — reorder slides

**Body**: the full ordered list of the presentation's current slide ids.

```json
{ "ordered_slide_ids": ["aups_b", "aups_a", "aups_c"] }
```

Must list **exactly** the presentation's current (non-deleted) slides — otherwise
`422`. New `sequence_order` = list position (`1..N`).

---

## Media — the 2-step S3 upload flow

Media bytes go **straight to S3**; the backend never receives the file. Three
steps:

```
1. POST .../media/upload-url   → presigned PUT url + pending upload record
2. PUT <upload_url> (to S3)    → the browser uploads the bytes
3. POST .../media              → confirm: backend verifies + records the media
```

### Step 1 — POST `/{id}/slides/{slide_id}/media/upload-url`

**Body**

```json
{ "media_type": "video", "content_type": "video/mp4", "file_name": "demo.mp4", "file_size_bytes": 4200000 }
```

| Field | Required | Notes |
|---|---|---|
| `media_type` | ✅ | `image` \| `video`. |
| `content_type` | ✅ | MIME; must be allowed for the `media_type` (below). |
| `file_name` | ❌ | Used for the object key extension. |
| `file_size_bytes` | ❌ | Validated against the max (below). |

Allowed content types & size caps:

| `media_type` | Allowed `content_type` | Max size |
|---|---|---|
| `image` | `image/jpeg`, `image/png`, `image/webp`, `image/gif` | 20 MB |
| `video` | `video/mp4`, `video/webm`, `video/quicktime` | 200 MB |

Anything else → `422`.

**Response** (note: **not** wrapped as a presentation)

```json
{
  "upload_url": "https://<s3-presigned-PUT-url>",
  "pending_upload_client_id": "pu_01J...",
  "storage_key": "app_update_presentations/ws_.../aup_.../aups_.../<uuid>.mp4",
  "expires_in": 900
}
```

The presigned PUT URL is valid for `expires_in` seconds (900 = 15 min).

### Step 2 — upload to S3

`PUT` the raw file bytes to `upload_url`. Set the request `Content-Type` header to
the **same `content_type`** you sent in step 1. No auth header on this request
(the URL is presigned). Example:

```
PUT <upload_url>
Content-Type: video/mp4
<binary body>
```

### Step 3 — POST `/{id}/slides/{slide_id}/media` — confirm & attach

**Body**

```json
{
  "media_type": "video",
  "pending_upload_client_id": "pu_01J...",
  "poster_storage_key": null,
  "fallback_storage_key": null,
  "alt_text": "Demo of the new product search",
  "mime_type": "video/mp4",
  "width": 1280,
  "height": 720,
  "duration_ms": 5000,
  "is_looping": true
}
```

| Field | Required | Notes |
|---|---|---|
| `media_type` | ✅ | `image` \| `video`. |
| `pending_upload_client_id` | one of these | The `pu_...` from step 1 (preferred). |
| `storage_key` | one of these | Or pass a known object key directly. |
| `poster_storage_key` | ❌ | S3 key for a video poster image (upload it via the same flow with `media_type=image`). |
| `fallback_storage_key` | ❌ | S3 key for a fallback asset. |
| `alt_text`, `mime_type`, `width`, `height`, `duration_ms`, `is_looping` | ❌ | Metadata. |

The backend verifies the object exists in S3 (`404`/`422` if it never landed),
records the media at the next `sequence_order`, and returns the full presentation.

- Missing both `pending_upload_client_id` and `storage_key` → `422`.
- Uploaded object not found in storage → `422`.

### PATCH `/{id}/slides/{slide_id}/media/{media_id}` — edit media metadata

Editable: `poster_storage_key`, `fallback_storage_key`, `alt_text`, `mime_type`,
`width`, `height`, `duration_ms`, `is_looping`. (The main `storage_key` and
`media_type` are not editable — replace the media instead.)

### DELETE `/{id}/slides/{slide_id}/media/{media_id}`

Soft-deletes the media row. (The S3 object is left in place; cleanup is a separate
backend concern.)

### POST `/{id}/slides/{slide_id}/media/reorder`

**Body**: `{ "ordered_media_ids": ["aupm_b", "aupm_a"] }` — must list exactly the
slide's current media, else `422`.

---

## Carousels

A carousel is just **several `image` media on one slide**, ordered by
`sequence_order`. Upload each image via the 2-step flow, then optionally reorder
with `media/reorder`.
