# 06 — Admin: Audience Targeting

Roles: **admin, manager**. Audience is set with a single atomic **replace**
operation (not per-target CRUD). Works only on `draft` presentations (`409`
otherwise).

---

## PUT `/{id}/audience` — replace the whole audience

Sets `audience_mode` and **replaces** all four target dimensions in one
transaction. Whatever you send is the complete new audience; anything omitted is
cleared.

**Body**

```json
{
  "audience_mode": "all_matching",
  "app_keys": ["worker", "manager"],
  "role_keys": ["worker", "supervisor"],
  "workspace_ids": ["ws_01J..."],
  "user_ids": ["usr_01J..."]
}
```

| Field | Notes |
|---|---|
| `audience_mode` | `all_matching` \| `selected_users_only`. Required. |
| `app_keys` | `manager` / `worker` / `seller` / `admin`. Empty = all apps. |
| `role_keys` | `admin` / `worker` / `manager` / `seller`. Empty = all roles. |
| `workspace_ids` | Must be **your own workspace** only (see below). Empty = your workspace. |
| `user_ids` | Must be **active members of your workspace**. Empty = no direct-user restriction. |

**Response**: `{ "presentation": <full> }` — check `presentation.audience`.

**Errors**

- `403` — a `workspace_id` other than your own (cross-workspace targeting is not
  allowed; there is no platform-admin tier).
- `422` — a `user_id` that is not an active member of your workspace; or
  `selected_users_only` with no `user_ids`.
- `409` — the presentation is not a draft.

---

## Matching semantics (how eligibility is computed)

For a given acting user, the backend evaluates each dimension:

- **Within a dimension → OR.** `role_keys: ["worker","supervisor"]` matches a
  user who has *either* role.
- **Across dimensions → AND.** The user must match app **and** workspace **and**
  role **and** (direct user, if any user targets exist).
- **Empty dimension → unrestricted.** No `app_keys` = every app; no `role_keys` =
  every role; etc.

### `all_matching` (the default)

Eligible when:

```
(no app_keys      OR user's app_key ∈ app_keys)
AND (no workspace_ids OR user's workspace ∈ workspace_ids)
AND (no role_keys     OR user's role ∈ role_keys)
AND (no user_ids      OR user ∈ user_ids)
```

Direct `user_ids` here act as an **extra restriction** on top of the others.

### `selected_users_only`

Eligible when:

```
user ∈ user_ids
AND (no app_keys      OR user's app_key ∈ app_keys)
AND (no workspace_ids OR user's workspace ∈ workspace_ids)
```

- The user **must** be directly targeted.
- **Role targets are ignored** in this mode.
- At least one `user_id` is required (enforced at publish and at audience-replace).

---

## Examples

**All workers and managers, in the worker and manager apps**

```json
{ "audience_mode": "all_matching", "app_keys": ["worker","manager"], "role_keys": ["worker","manager"] }
```

**Everyone (no restrictions)**

```json
{ "audience_mode": "all_matching", "app_keys": [], "role_keys": [], "workspace_ids": [], "user_ids": [] }
```

**Only two specific people, only in the manager app**

```json
{ "audience_mode": "selected_users_only", "app_keys": ["manager"], "user_ids": ["usr_a","usr_b"] }
```

---

## App key vs. app scope

`app_keys` uses the same values as the auth `app_scope` claim
(`manager | worker | seller | admin`). A user is "in" an app based on the app they
signed into — the consumer endpoints enforce that the requested `app_key` equals
the token's `app_scope`, so app targeting is unspoofable.
