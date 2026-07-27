# 07 — Enum Reference

Every enum value the API accepts and returns. Values are lowercase strings.

---

## `status` (presentation lifecycle)

| Value | Meaning |
|---|---|
| `draft` | Editable; not visible to consumers. |
| `published` | Live; eligible users may see it. |
| `archived` | Retired; never shown. |

Transitions: `draft → published`, `draft → archived`, `published → archived`.
(`archived` is terminal.)

## `presentation_type` (rendering)

| Value | Meaning |
|---|---|
| `modal` | Dialog overlay. |
| `full_screen` | Full-screen takeover. |
| `slide_page` | Dedicated slide page (default). |

## `category` (topic / severity)

| Value | Default `display_priority` |
|---|---|
| `alert` | 300 |
| `workflow` | 200 |
| `improvement` | 100 |
| `news` | 0 |

Nullable. Used for UI badging/filtering and for the default priority when
`display_priority` is omitted on create.

## `audience_mode`

| Value | Meaning |
|---|---|
| `all_matching` | Match by app/workspace/role, plus optional direct-user restriction. |
| `selected_users_only` | Must be directly targeted; role targets ignored; requires ≥1 user. |

## `layout_type` (slide)

| Value | Meaning |
|---|---|
| `media_top` | Media above text (default). |
| `media_full` | Media fills the slide. |
| `text_overlay` | Text over media. |

## `media_type`

| Value | Allowed upload MIME types | Max size |
|---|---|---|
| `image` | `image/jpeg`, `image/png`, `image/webp`, `image/gif` | 20 MB |
| `video` | `video/mp4`, `video/webm`, `video/quicktime` | 200 MB |

## `app_key` / `app_scope`

`manager` · `worker` · `seller` · `admin`

Used for `app_keys` targeting and the consumer `app_key` query param. Must match
the token's `app_scope`.

## `role_key`

`admin` · `worker` · `manager` · `seller`

Used for `role_keys` targeting.

## View-state `status` (returned)

| Value | Meaning |
|---|---|
| `unseen` | No view record yet (only appears in `view_state`, never stored). |
| `shown` | Shown to the user. |
| `dismissed` | Dismissed (requires `is_dismissible`). |
| `completed` | Finished. Terminal. |

## View-state `action` (request body)

`shown` · `progressed` · `dismissed` · `completed`

---

## Timeline composition enums

See [09_slide_composition.md](09_slide_composition.md) for full context.

### `playback_mode` (slide)

| Value | Meaning |
|---|---|
| `manual` | User advances explicitly. |
| `timed` | Auto-advances after `duration_ms` (required). |
| `media_driven` | Primary video element drives completion (requires ≥1 media element). |

### `element_type`

`media` · `text`

### `animation.type` (enter/exit animation)

`none` · `fade` · `fade_up` · `fade_down` · `slide_left` · `slide_right` · `scale_in` · `scale_out`

### `animation.easing`

`linear` · `ease` · `ease_in` · `ease_out` · `ease_in_out`

### `layout.fit` (media)

`cover` · `contain` · `fill` · `none`

### `layout.anchor`

`top_left` · `top_center` · `top_right` · `center_left` · `center` · `center_right` · `bottom_left` · `bottom_center` · `bottom_right`

### `layout.align` / `style.text_align`

`left` · `center` · `right` · `justify`

### `style.text_role`

`headline` · `subheadline` · `body` · `caption` · `overline`
