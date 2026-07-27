# App Update Presentation System — Frontend Guide

The **app update presentation system** is the backend-managed, versioned in-app
**announcement / "What's New" layer**. Admins and managers build presentations
(slide decks of images/videos), target an audience, and publish. The backend
decides which single presentation each user is eligible to see — the frontend
never computes eligibility.

Base path for every endpoint: **`/api/v1/app-update-presentations`**

> All examples show the **inner payload**. Every successful response is wrapped
> in the standard envelope `{ "data": <payload>, "ok": true, "warnings": [] }`.
> See [02_conventions.md](02_conventions.md).

---

## Who calls what

| Audience | Endpoints | Doc |
|---|---|---|
| **End-user app** (all roles) | `GET /active`, `GET /history`, `POST /{id}/view-state` | [03_consumer_endpoints.md](03_consumer_endpoints.md) |
| **Admin console** (admin, manager) | create / list / get / update / publish / archive / new-version / preview | [04_admin_presentations.md](04_admin_presentations.md) |
| **Admin console** — slides & media | slide CRUD + reorder, media upload + CRUD + reorder | [05_admin_slides_media.md](05_admin_slides_media.md) |
| **Admin console** — audience | `PUT /{id}/audience` | [06_admin_audience.md](06_admin_audience.md) |

---

## Documentation map

1. **[01_concepts.md](01_concepts.md)** — the mental model. Read this first: announcements vs versions, slides, media, targeting, eligibility, view-state, newest-version-wins, categories.
2. **[02_conventions.md](02_conventions.md)** — auth, roles/`app_scope`, the response envelope, error shapes & status codes, pagination, IDs, timestamps.
3. **[03_consumer_endpoints.md](03_consumer_endpoints.md)** — the runtime endpoints the app calls: `active`, `history`, `view-state`.
4. **[04_admin_presentations.md](04_admin_presentations.md)** — presentation lifecycle: create, list, get, update, publish, archive, new-version, preview.
5. **[05_admin_slides_media.md](05_admin_slides_media.md)** — building the deck: slide CRUD + reorder, and the 2-step S3 media upload flow.
6. **[06_admin_audience.md](06_admin_audience.md)** — audience targeting (apps / roles / workspaces / users) and matching semantics.
7. **[07_enums.md](07_enums.md)** — every enum value the API accepts and returns.
8. **[08_recipes.md](08_recipes.md)** — copy-paste end-to-end flows for the common tasks.
9. **[09_slide_composition.md](09_slide_composition.md)** — timeline composition: timed/layered text & media elements, playback modes, layout/style/animation config, the composition editor endpoint, and the legacy adapter.

---

## Endpoint index

### Consumer (roles: admin, manager, worker, seller)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/active?app_key=<key>` | The one presentation this user should see now (or `null`). |
| `GET` | `/history?app_key=<key>&limit=&offset=` | "What's New" feed of everything the user is eligible for. |
| `POST` | `/{presentation_client_id}/view-state` | Record `shown` / `progressed` / `dismissed` / `completed`. |

### Admin (roles: admin, manager)

| Method | Path | Purpose |
|---|---|---|
| `PUT` | `` (collection root) | Create a draft presentation. |
| `GET` | `` | List/search presentations (admin, all statuses & versions). |
| `GET` | `/{id}` | Full detail incl. audience. |
| `PATCH` | `/{id}` | Edit draft metadata. |
| `POST` | `/{id}/publish` | Publish a draft. |
| `POST` | `/{id}/archive` | Archive (draft or published). |
| `POST` | `/{id}/new-version` | Create a new draft version (copies content + targets). |
| `GET` | `/{id}/preview` | Render any version (incl. draft) in the consumer shape. |
| `POST` | `/{id}/slides` | Add a slide. |
| `PATCH` | `/{id}/slides/{slide_id}` | Edit a slide. |
| `DELETE` | `/{id}/slides/{slide_id}` | Remove a slide (soft delete). |
| `POST` | `/{id}/slides/reorder` | Reorder slides. |
| `POST` | `/{id}/slides/{slide_id}/media/upload-url` | Get a presigned S3 upload URL. |
| `POST` | `/{id}/slides/{slide_id}/media` | Attach uploaded media to a slide. |
| `PATCH` | `/{id}/slides/{slide_id}/media/{media_id}` | Edit media metadata. |
| `DELETE` | `/{id}/slides/{slide_id}/media/{media_id}` | Remove media (soft delete). |
| `POST` | `/{id}/slides/{slide_id}/media/reorder` | Reorder media within a slide. |
| `PUT` | `/{id}/slides/{slide_id}/composition` | Replace a slide's timeline composition (elements + playback). See [09](09_slide_composition.md). |
| `PUT` | `/{id}/audience` | Replace the whole audience configuration. |

---

## Status of this system

- Implemented and tested. Media storage is **S3** (presigned upload + presigned
  read URLs derived at read time).
- **Not yet implemented:** push notifications on publish (connected clients get
  a socket refresh signal `app_update_presentation:published`; offline users
  discover new content on their next `GET /active`).
