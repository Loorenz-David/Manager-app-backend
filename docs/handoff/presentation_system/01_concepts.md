# 01 — Concepts & Mental Model

Read this before wiring endpoints. The API is small; the semantics are where the
behavior lives.

---

## The object graph

```
Presentation (one published version of an announcement)
  ├── Slides            (ordered pages of the deck)
  │     └── Media       (image OR video on that page; a carousel = many images)
  ├── Audience targets  (who sees it: apps / roles / workspaces / users)
  └── Views             (per-user: shown / dismissed / completed)
```

- A **presentation** is a slide deck shown to a user (modal, full-screen, or a
  slide page).
- A **slide** is one page. It has a title/description, a layout, an optional
  call-to-action (`action.label` + `action.route`), and ordered **media**.
- **Media** is an image or a video. A carousel is simply several ordered image
  media on one slide.

> **Slides are timeline compositions.** Beyond static media, a slide can contain
> independently timed, layered **elements** (text and media) — timed captions over
> video, text-only timed slides, static captions, overlays. That model is
> documented separately in **[09_slide_composition.md](09_slide_composition.md)**;
> the serialized slide always includes an `elements` array (real or, for legacy
> slides, synthesized from the old title/description/media).

---

## Announcements vs versions (important)

Two identifiers on every presentation:

| Field | Meaning |
|---|---|
| `logical_client_id` | The **announcement** — stable across all its versions. |
| `client_id` | This **specific version** of that announcement. |
| `version` | Integer, `1, 2, 3, …` within the announcement. |

- **Same announcement, corrected** → a new **version** (same `logical_client_id`,
  `version + 1`). Use `POST /{id}/new-version`.
- **A different message** → a new **announcement** (new `logical_client_id`).
  Use `PUT` (create).

> **Rule of thumb:** "fix / re-issue *this* message" = new version. "a *different*
> message" = new presentation. Getting this wrong matters — see *newest-version-wins*.

### Newest-version-wins

Multiple versions of one announcement can be published at once. For each user,
the backend serves **the newest version they are eligible for**; older versions
are superseded (not shown). Publishing v2 does **not** require archiving v1 — the
backend supersedes it automatically at read time.

Consequence: a **broad re-issue supersedes a narrower earlier one** within the
same announcement. If managers saw a manager-only v3 and you then publish an
"all apps" v4, managers now see v4. If you want a narrow message to persist,
make it a **separate announcement** (different `logical_client_id`), not a
version.

Completion is tracked **per version**: completing v1 then publishing v2 means the
user sees v2 as new (`unseen`).

---

## Eligibility (resolved entirely by the backend)

The frontend never decides who sees what. On `GET /active` / `GET /history`, the
backend evaluates the acting user against each published presentation's audience:

- **App** — must match the app the user is signed into (`app_scope`, passed as
  `app_key`).
- **Workspace** — the user's current workspace.
- **Role** — the user's role.
- **Direct user** — the user's `client_id`.

Matching rules:

- **Within one dimension → OR** (`role = worker OR supervisor`).
- **Across dimensions → AND** (`app AND workspace AND role AND user`).
- **An empty dimension → unrestricted** (no app targets = every app).
- **`selected_users_only` mode** → the user MUST be directly targeted; role
  targets are ignored; app & workspace still apply.

See [06_admin_audience.md](06_admin_audience.md) for the full matrix.

---

## The active queue: one at a time

`GET /active` returns **at most one** presentation, chosen by:

1. `display_priority` (higher wins),
2. then `published_at` (newer wins),
3. then a deterministic tiebreak.

So a user who was away for several releases is not buried under stacked popups —
they see them one at a time. After they `complete`/`dismiss` the current one, the
next eligible one surfaces on the next `GET /active`.

`GET /history` ("What's New") returns the **full list** of eligible announcements
(newest version each), including already-seen and expired ones, so the user can
browse/revisit.

---

## View-state (per user)

Each user has one view record per presentation version. Actions:

| Action | Meaning |
|---|---|
| `shown` | The user was shown the presentation (first + latest shown, view count). |
| `progressed` | Advance the furthest-seen slide index. |
| `dismissed` | User dismissed it (only allowed if `is_dismissible`). |
| `completed` | User finished it. **Terminal** — cannot regress. |

- Before any action, a presentation's `view_state.status` is `"unseen"`.
- `completed` is terminal: a completed presentation can't be dismissed or
  reverted, and it drops out of `GET /active`.
- View-state is **per user, not per device** — the acting user is taken from the
  auth token; the frontend must never send a user/device id in the body.

---

## Category & default priority

`category` (`improvement | workflow | news | alert`) labels the *topic* (distinct
from `presentation_type`, which is about *rendering*). Use it to badge/route/filter
in the UI.

If the admin does not set `display_priority` on create, the backend derives a
default from category so severity drives ordering out of the box:

| category | default `display_priority` |
|---|---|
| `alert` | 300 |
| `workflow` | 200 |
| `improvement` | 100 |
| `news` / none | 0 |

An explicit `display_priority` always overrides this.

---

## Lifecycle & immutability

```
draft ──publish──▶ published ──archive──▶ archived
  └──────────────archive─────────────────▶ archived
```

- Only **draft** presentations are editable. Any edit to a published/archived
  presentation (metadata, slides, media, audience) returns **409 Conflict**.
- To change published content, create a **new version** (`new-version`), edit the
  draft, and publish it.
- Archiving is allowed from draft or published.
