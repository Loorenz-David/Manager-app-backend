# 04 — Admin: Presentation Lifecycle

Roles: **admin, manager**. Payloads shown are the inner `data`. Admin responses
use the **full** presentation shape (metadata + `slides` + `audience`).

The full shape returned by create/get/update/publish/archive/new-version:

Each slide in `presentation.slides` includes the nullable `background_color`
field described in [05_admin_slides_media.md](05_admin_slides_media.md).

```json
{
  "presentation": {
    "client_id": "aup_01J...",
    "logical_client_id": "aup_01J...",
    "version": 1,
    "workspace_id": "ws_01J...",
    "title": "A faster way to find products",
    "summary": "…",
    "status": "draft",
    "presentation_type": "slide_page",
    "category": "improvement",
    "audience_mode": "all_matching",
    "display_priority": 100,
    "is_dismissible": true,
    "starts_at": null,
    "expires_at": null,
    "published_at": null,
    "archived_at": null,
    "created_at": "2026-07-22T09:00:00+00:00",
    "created_by_id": "usr_01J...",
    "updated_at": null,
    "slides": [ /* see 05_admin_slides_media.md */ ],
    "audience": {
      "audience_mode": "all_matching",
      "app_keys": [],
      "role_keys": [],
      "workspace_ids": [],
      "user_ids": []
    }
  }
}
```

---

## PUT `` — create a draft

Creates a **v1 draft** of a new announcement (`logical_client_id` = the new
`client_id`, `version` = 1, `status` = `draft`).

**Body** (all optional except `title`)

```json
{
  "title": "A faster way to find products",
  "summary": "Search by SKU, article number, or customer.",
  "presentation_type": "slide_page",
  "category": "improvement",
  "audience_mode": "all_matching",
  "display_priority": 100,
  "is_dismissible": true,
  "starts_at": null,
  "expires_at": null,
  "client_id": null
}
```

| Field | Default | Notes |
|---|---|---|
| `title` | — | Required, non-blank. |
| `presentation_type` | `slide_page` | See [07_enums.md](07_enums.md). |
| `category` | `null` | Drives default `display_priority` if you omit it. |
| `audience_mode` | `all_matching` | |
| `display_priority` | derived from `category` | Explicit value wins; else `alert=300, workflow=200, improvement=100, news/none=0`. |
| `is_dismissible` | `true` | |
| `starts_at` / `expires_at` | `null` | Scheduling window (UTC ISO-8601). |
| `client_id` | server-generated | Optional client-supplied id. |

**Response**: `{ "presentation": <full> }` (status `draft`).

---

## GET `` — list / search (admin)

Lists presentations in your workspace, **all statuses and all versions** (this is
the admin console list, not the consumer feed).

**Query params**: `limit`, `offset`, plus optional filters:

| Param | Filters by |
|---|---|
| `q` | title/summary (case-insensitive contains). |
| `status` | `draft` \| `published` \| `archived`. |
| `logical_client_id` | all versions of one announcement. |
| `version` | exact version number. |
| `app_key` | presentations targeting that app. |
| `role_key` | presentations targeting that role. |
| `published_before` / `published_after` | `published_at` range (ISO-8601). |

**Response** — compact items (no full slides/audience) **plus per-deck card
preview fields** (`slide_count`, `media_kinds`, `cover_url`):

```json
{
  "app_update_presentations_pagination": {
    "items": [
      {
        "client_id": "aup_01J...",
        "logical_client_id": "aup_01J...",
        "version": 2,
        "workspace_id": "ws_01J...",
        "title": "…",
        "summary": "…",
        "status": "published",
        "presentation_type": "slide_page",
        "category": "improvement",
        "audience_mode": "all_matching",
        "display_priority": 100,
        "is_dismissible": true,
        "starts_at": null,
        "expires_at": null,
        "published_at": "2026-07-21T18:00:00+00:00",
        "archived_at": null,
        "created_at": "2026-07-20T10:00:00+00:00",
        "created_by_id": "usr_01J...",
        "updated_at": "2026-07-21T18:00:00+00:00",
        "slide_count": 3,
        "media_kinds": ["image", "video"],
        "cover_url": "https://<s3-presigned-GET>"
      }
    ],
    "has_more": false,
    "limit": 50,
    "offset": 0
  }
}
```

**Card preview fields** (admin list only — the consumer `/active` and `/history`
already return full slides and are unchanged):

| Field | Type | Meaning |
|---|---|---|
| `slide_count` | int ≥ 0 | Number of the version's non-deleted slides. |
| `media_kinds` | `("image"\|"video")[]` | One entry per non-deleted media across the deck, ordered by slide `sequence_order`, then media `sequence_order`. `[]` when the deck has no media. |
| `cover_url` | string \| null | Short-lived presigned cover URL: the first usable media scanning slides then media in order — an `image`'s own URL, or a `video`'s `poster_url` then `fallback_url`. `null` when nothing usable exists. Same presigning semantics as other `*_url` fields. |

Soft-deleted slides/media are excluded from all three. Every status/version gets
them.

---

## GET `/{id}` — full detail

**Response**: `{ "presentation": <full> }` (metadata + slides + audience). `404`
if not found in your workspace.

---

## PATCH `/{id}` — edit draft metadata

Update any subset of metadata fields (same fields as create, minus `client_id`).
Fields you omit are left unchanged.

**Body** (example)

```json
{ "title": "New title", "category": "news", "display_priority": 50 }
```

- **Only allowed on `draft`.** Editing a published/archived presentation → `409`.
- Note: `category` on PATCH does **not** re-derive `display_priority` — set
  `display_priority` explicitly if you want to change it.

**Response**: `{ "presentation": <full> }`. Errors: `404`, `409` (not draft), `422`.

---

## POST `/{id}/publish`

Validate and publish a draft. On success `status` → `published`, `published_at`
set. Multiple published versions of one announcement may coexist — publishing
does **not** archive the previous version (newest-version-wins handles it).

**Publish validation** (all must pass, else `422`):

- At least one slide.
- Every slide has content — **any** of: timeline composition elements, media, or a
  title/description. A slide whose only content is timed **text elements** is
  valid (text-only timed slides are first-class).
- Every media item has a supported `media_type` and a storage reference.
- Slide & media sequences are normalized to contiguous `1..N` during publish.
- `expires_at` (if set) is after `starts_at`.
- `selected_users_only` mode has at least one user target.
- All app/role target keys are recognized.

**Errors**: `422` (validation), `409` (not a draft — e.g. already published or
archived), `404`.

**Response**: `{ "presentation": <full> }` (status `published`).

### Realtime (socket) events

On **publish** and **archive**, the backend emits a socket.io event to the
workspace room `workspace:{workspace_id}` (clients auto-join their workspace room
on connect). These are **change signals only** — on receipt, refetch `/active`
(and/or `/history`); the payload deliberately carries no slide/content data.

| Socket event name | Emitted when |
|---|---|
| `app_update_presentation:published` | a version is published |
| `app_update_presentation:archived` | a presentation is archived |

Payload (emitted directly, no outer envelope):

```json
{ "client_id": "aup_...", "logical_client_id": "aup_...", "version": 2 }
```

There are **no** `created`/`updated` socket events — only `published` and
`archived`. (Push notifications on publish are not implemented; offline users
discover new content on their next `GET /active`.)

---

## POST `/{id}/archive`

Retire a presentation. Allowed from `draft` or `published`. `status` → `archived`,
`archived_at` set. Archived presentations never appear in `/active` or `/history`.

**Errors**: `409` (already archived), `404`. **Response**: `{ "presentation": <full> }`.

---

## POST `/{id}/new-version`

Create the next **draft** version of the announcement. The backend:

- computes `version = max(existing) + 1`,
- keeps the same `logical_client_id`,
- **copies** slides, media references, audience targets, scheduling, category,
- sets `status = draft`, clears `published_at` / `archived_at`,
- does **not** copy view records.

Use this to correct/re-issue an existing announcement. Then edit the draft and
publish it.

**Response**: `{ "presentation": <full> }` (the new draft, `version + 1`).

---

## GET `/{id}/preview`

Render **any** presentation (including a `draft`) in the **consumer shape** (same
as `/active`, with `slides` + your `view_state`). Use this to preview a draft in
the admin console without publishing. Previewing does not make a draft eligible
via `/active`.

**Response**: `{ "presentation": <active-shape> }`. `404` if not found.
