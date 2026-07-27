# 02 — Conventions: Auth, Envelope, Errors, Pagination

Everything in this file applies to **every** endpoint in the system.

---

## Authentication & authorization

- All endpoints require a valid **Bearer JWT** (`Authorization: Bearer <token>`),
  same as the rest of the API.
- **Role gating** (`role_name` claim):
  - **Consumer** endpoints (`/active`, `/history`, `/{id}/view-state`): any role —
    `admin`, `manager`, `worker`, `seller`.
  - **Admin** endpoints (everything else): `admin` or `manager` only.
- **App scope** (`app_scope` claim): the app the user signed into
  (`manager | worker | seller | admin`). The consumer endpoints require an
  `app_key` query param that **must equal** the token's `app_scope` — you cannot
  request content for an app you are not signed into. Mismatch → `422`.

The frontend never sends the acting user, workspace, or app in a request body —
they come from the token.

### Role vs. app_scope — two independent axes (read this)

These are **separate concerns**; don't conflate them:

| | Governs | Presentation system |
|---|---|---|
| **Role** (`role_name`) | *What you can do* | Authoring (create/edit/publish/manage) = **`admin` or `manager`**. Consuming = any role. |
| **`app_scope`** | *Which app you're signed into* | Only used to match `app_key` on the **consumer** read endpoints. **Not** an authoring gate. |

Consequences for the frontend:

- **Managers are not restricted.** A `manager`-role user can do everything an
  `admin` can in the authoring UI — authoring is gated by **role**, and it accepts
  both. `app_scope` plays no part in authoring authorization.
- **The authoring console never needs `app_scope`** *unless* it also displays the
  logged-in operator their own eligible announcements (i.e. calls `/active` or
  `/history`). A pure authoring/build UI can ignore `app_scope` entirely.
- **For any consumer call**, send `app_key` equal to the token's `app_scope` (read
  it from the JWT claims). Do **not** hardcode `"admin"` — that value is only
  correct for `admin`-role users; a manager's scope is `"manager"`. Hardcoding it
  makes a manager's `/active` call fail with `422`.
- Note on login: the `admin` **scope** is restricted to the `admin` **role** at
  sign-in, so a manager signs in with `app_scope="manager"` (which permits both
  `manager` and `admin` roles). This is a login rule, not an authoring rule.

---

## Response envelope

Every **successful** response is wrapped:

```json
{ "data": { /* endpoint payload */ }, "ok": true, "warnings": [] }
```

Throughout these docs, the "Response" sections show the **inner `data` payload**.
So when a doc says the response is `{ "presentation": {...} }`, the wire response is:

```json
{ "data": { "presentation": {...} }, "ok": true, "warnings": [] }
```

---

## Error shapes

There are **two** error shapes depending on where the error is raised.

### 1. Domain errors (from the service layer)

```json
{ "error": "Presentation not found.", "ok": false }
```

| HTTP | When |
|---|---|
| `404` | Not found / not in your workspace / soft-deleted. |
| `409` | Conflict — e.g. editing a non-draft, invalid state transition. |
| `422` | Validation — bad field, invalid publish, `app_key` mismatch, invalid slide index. |
| `403` | Permission — e.g. targeting users/workspaces outside your scope. |
| `500` | Unexpected server error. |

### 2. Framework errors (FastAPI, before the service runs)

Raised for role rejection and request-shape validation. Shape:

```json
{ "detail": "Insufficient role permissions." }
```

or, for body/query validation:

```json
{ "detail": [ { "loc": ["body", "title"], "msg": "...", "type": "..." } ] }
```

| HTTP | When |
|---|---|
| `401` | Missing/invalid/expired token. |
| `403` | Role not allowed for this endpoint. |
| `422` | Missing required query param / malformed body (Pydantic). |

**Frontend takeaway:** check `ok === false` for domain errors and read `error`;
handle `401/403/422` framework errors by reading `detail`.

---

## Pagination

List endpoints use **offset pagination**. Query params: `limit` (default `50`,
max `200`) and `offset` (default `0`).

The paginated payload is nested under a single key with `items`:

```json
{
  "<name>_pagination": {
    "items": [ /* ... */ ],
    "has_more": true,
    "limit": 50,
    "offset": 0
  }
}
```

- `has_more` tells you whether another page exists (fetch `offset + limit`).
- Pagination key names: `app_update_presentations_pagination` (admin list) and
  `app_update_whats_new_pagination` (consumer history).

---

## Identifiers

All IDs are prefixed ULID strings (`String(64)`), stable across the API.

| Entity | Prefix | Example |
|---|---|---|
| Presentation (a version) | `aup_` | `aup_01J...` |
| Announcement group | `logical_client_id` (an `aup_` value — the v1's id) | `aup_01J...` |
| Slide | `aups_` | `aups_01J...` |
| Slide media | `aupm_` | `aupm_01J...` |
| Pending upload | `pu_` | `pu_01J...` |
| View record | `aupv_` | `aupv_01J...` |

Use `client_id` everywhere. There are no integer IDs.

---

## Timestamps

All timestamps are **UTC ISO-8601 strings** (`2026-07-22T18:00:00+00:00`), or
`null` when unset. Nullable time fields you'll see: `starts_at`, `expires_at`,
`published_at`, `archived_at`, and the view timestamps.
