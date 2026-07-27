# 03 — Consumer Endpoints (the end-user app)

These are the only three endpoints the end-user app needs. Roles: **any**
(`admin`, `manager`, `worker`, `seller`). Payloads shown are the inner `data`.

---

## GET `/active`

Return the single presentation this user should see right now, or `null`.

**Query params**

| Param | Required | Notes |
|---|---|---|
| `app_key` | ✅ | Must equal the token's `app_scope` (`manager`/`worker`/`seller`/`admin`). Mismatch → `422`. |

**Request**

```
GET /api/v1/app-update-presentations/active?app_key=worker
Authorization: Bearer <token>
```

**Response** — `{ "presentation": <object> | null }`

```json
{
  "presentation": {
    "client_id": "aup_01J...",
    "logical_client_id": "aup_01J...",
    "version": 2,
    "title": "A faster way to find products",
    "summary": "Search by SKU, article number, or customer.",
    "presentation_type": "slide_page",
    "category": "improvement",
    "is_dismissible": true,
    "display_priority": 100,
    "published_at": "2026-07-21T18:00:00+00:00",
    "starts_at": null,
    "expires_at": null,
    "slides": [
      {
        "client_id": "aups_01J...",
        "sequence_order": 1,
        "title": "Search from one place",
        "description": "Use SKU, article number, or customer name.",
        "layout_type": "media_top",
        "media": [
          {
            "client_id": "aupm_01J...",
            "sequence_order": 1,
            "media_type": "video",
            "media_url": "https://<s3-presigned-GET-url>",
            "poster_url": "https://<s3-presigned-GET-url>",
            "fallback_url": null,
            "alt_text": "Demo of the new product search",
            "mime_type": "video/mp4",
            "width": 1280,
            "height": 720,
            "duration_ms": 5000,
            "is_looping": true
          }
        ],
        "action": { "label": "Try product search", "route": "/products/search" }
      }
    ],
    "view_state": { "status": "unseen", "last_slide_index": 0 }
  }
}
```

**Notes**

- `presentation` is `null` when the user has nothing to see. Treat `null` as "no
  popup."
- `view_state.status` is `unseen | shown | dismissed | completed`. On first fetch
  it's `unseen`.
- `media_url` / `poster_url` / `fallback_url` are **short-lived presigned S3 GET
  URLs** (≈24h). Don't cache them long-term; refetch `/active` to refresh.
- `action` is `null` when the slide has no call-to-action. `action.route` is
  always a **relative in-app path** (never an external URL) — safe to navigate.
- Only **one** presentation is returned even if several are eligible (highest
  `display_priority`, then newest). After the user finishes it, call `/active`
  again to get the next one.
- Each slide also carries **timeline composition** fields (`playback_mode`,
  `duration_ms`, `composition_schema_version`, and an `elements` array of timed,
  layered text/media). Render from `elements`. Full details in
  **[09_slide_composition.md](09_slide_composition.md)**.

**Errors**: `422` (missing `app_key` or mismatch with `app_scope`).

---

## GET `/history` — "What's New" feed

Every announcement the user is eligible for (newest version each), newest first —
including already-seen and expired ones so they can browse/revisit. Future-dated
presentations are excluded.

**Query params**

| Param | Required | Notes |
|---|---|---|
| `app_key` | ✅ | Must equal `app_scope`. |
| `limit` | ❌ | Default `50`, max `200`. |
| `offset` | ❌ | Default `0`. |

**Request**

```
GET /api/v1/app-update-presentations/history?app_key=worker&limit=20&offset=0
```

**Response** — items are the **same full presentation shape as `/active`**
(including `slides` and `view_state`):

```json
{
  "app_update_whats_new_pagination": {
    "items": [
      { "client_id": "aup_01J...", "version": 2, "title": "...", "slides": [ ... ], "view_state": { "status": "completed", "last_slide_index": 2 } }
    ],
    "has_more": false,
    "limit": 20,
    "offset": 0
  }
}
```

**Notes**

- Because each item carries its slides + the user's `view_state`, you can render a
  "What's New" list and open any item without extra calls.
- Ordering is by `published_at` desc.

---

## POST `/{presentation_client_id}/view-state`

Record how the user interacted with the presentation. Idempotent and safe to
retry.

**Path param**: `presentation_client_id` — the specific version's `client_id`
(the `client_id` from the `/active` payload).

**Body**

```json
{ "version": 2, "action": "shown", "last_slide_index": 0 }
```

| Field | Required | Notes |
|---|---|---|
| `version` | ✅ | Must match the presentation's `version` (guards against stale clients). Mismatch → `422`. |
| `action` | ✅ | `shown` \| `progressed` \| `dismissed` \| `completed`. |
| `last_slide_index` | ❌ | 0-based furthest slide seen. Validated against slide count (`0..count-1`, or `0` if no slides). Out of range → `422`. |

**Semantics**

| Action | Effect |
|---|---|
| `shown` | Sets first/last shown timestamps, increments `view_count`, status → `shown` (unless already `completed`). |
| `progressed` | Advances `last_slide_index` (monotonic — only moves forward). |
| `dismissed` | Allowed only if `is_dismissible` (else `409`). Status → `dismissed`. |
| `completed` | Status → `completed`. **Terminal** — later `dismissed` → `409`; repeated `completed` stays completed. |

Send `last_slide_index` with `shown`/`progressed` as the user advances.

**Response** — `{ "view_state": <object> }`

```json
{
  "view_state": {
    "client_id": "aupv_01J...",
    "presentation_id": "aup_01J...",
    "status": "shown",
    "last_slide_index": 0,
    "view_count": 1,
    "first_shown_at": "2026-07-22T09:00:00+00:00",
    "last_shown_at": "2026-07-22T09:00:00+00:00",
    "dismissed_at": null,
    "completed_at": null
  }
}
```

**Errors**

- `404` — presentation not found, not published, or the user isn't eligible for
  it (you can only record state for presentations you can actually see).
- `409` — dismiss when not dismissible, or dismiss after completion.
- `422` — bad `version`, invalid `action`, or `last_slide_index` out of range.

**Typical loop**

1. `GET /active` → render the presentation.
2. `POST view-state {action: "shown", last_slide_index: 0}`.
3. As the user swipes: `POST view-state {action: "progressed", last_slide_index: n}`.
4. On finish: `POST view-state {action: "completed"}` (or `dismissed`).
5. `GET /active` again → next eligible presentation (or `null`).
