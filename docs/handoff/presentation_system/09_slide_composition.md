# 09 — Slide Timeline Composition

Slides are **timed compositions**. A slide contains independently timed, layered
**elements** — `media` and `text` are both first-class element types (text is
never subordinate to media). This powers: video with timed captions, text-only
timed slides, static captions over/under an image, multiple overlays, etc.

The backend persists and validates the composition; the **frontend** owns the
playback clock, animation rendering, scrubbing, and responsive positioning.

---

## The slide shape (now)

Every serialized slide (in `/active`, `/history`, `/preview`, admin `get`) now
includes timeline fields and an `elements` array:

```json
{
  "client_id": "aups_...",
  "sequence_order": 1,
  "title": null,
  "description": null,
  "layout_type": "media_top",
  "playback_mode": "timed",
  "duration_ms": 8000,
  "composition_schema_version": 1,
  "background_color": null,
  "media": [ /* raw media assets on the slide (see below) */ ],
  "action": null,
  "elements": [
    {
      "client_id": "aupe_...",
      "element_type": "media",
      "sequence_order": 0,
      "layer_index": 0,
      "start_ms": 0,
      "end_ms": null,
      "media": { "client_id": "aupm_...", "media_type": "video", "media_url": "...", "poster_url": "...", "fallback_url": null, "width": 1080, "height": 1920, "duration_ms": 8000, "is_looping": false, "alt_text": "..." },
      "text_content": null,
      "layout": { "x": 0, "y": 0, "width": 1, "height": 1, "fit": "cover" },
      "style": null,
      "enter_animation": null,
      "exit_animation": null
    },
    {
      "client_id": "aupe_...",
      "element_type": "text",
      "sequence_order": 1,
      "layer_index": 10,
      "start_ms": 1000,
      "end_ms": 4000,
      "media": null,
      "text_content": "Switch users instantly",
      "layout": { "x": 0.08, "y": 0.72, "width": 0.84, "height": 0.15 },
      "style": { "text_role": "headline", "text_align": "center" },
      "enter_animation": { "type": "fade_up", "duration_ms": 350, "easing": "ease_out" },
      "exit_animation": { "type": "fade", "duration_ms": 200, "easing": "ease_in" }
    }
  ]
}
```

**Render from `elements`.** The `media` array is the raw asset list (used for
uploads/carousels and legacy compatibility); the **composition to render is
`elements`**.

### Element ordering

Render in this deterministic order (do not rely on array order alone, though the
API already returns them sorted this way):

```
layer_index ASC, sequence_order ASC, start_ms ASC, client_id ASC
```

`layer_index` is the z-index (higher = on top).

### Timing semantics (authoritative)

- `start_ms` — when the **entrance** animation begins.
- `end_ms` — when the **exit** animation begins. `null` = stay until the slide
  timeline ends.
- "Slide timeline ends" means: `duration_ms` for a `timed` slide, the video end
  for a `media_driven` slide, or when the user advances for a `manual` slide.

### Playback & duration

| `playback_mode` | How it advances | `duration_ms` |
|---|---|---|
| `manual` | User taps next. | Optional (bounds timed elements if set). |
| `timed` | Auto-advances at `duration_ms`. | **Required.** |
| `media_driven` | The primary (video) media element drives completion. | Optional hint. Requires ≥1 media element. |

### `composition_schema_version`

Governs how to interpret `layout` / `style` / `*_animation` for this slide.
Current version is `1`. When the config contract evolves, the backend bumps this
per slide and the frontend selects the matching renderer/adapter — so already
published slides keep rendering correctly.

---

## Config schemas

All three are **validated, structured JSON** — never raw CSS. Unknown keys are
rejected.

### `layout` (all elements)

Normalized coordinates (0..1) so one composition renders on any screen size.

| Field | Type | Notes |
|---|---|---|
| `x`, `y` | float 0..1 | top-left position |
| `width`, `height` | float (0,1] | size |
| `fit` | `cover`\|`contain`\|`fill`\|`none` | media fit |
| `anchor` | `top_left` … `bottom_right` | optional |
| `align` | `left`\|`center`\|`right`\|`justify` | optional |
| `rotation_deg` | float -360..360 | optional |
| `scale` | float (0,10] | optional |

### `style` (text elements only)

| Field | Notes |
|---|---|
| `text_role` | `headline`\|`subheadline`\|`body`\|`caption`\|`overline` |
| `text_align` | `left`\|`center`\|`right`\|`justify` |
| `font_size` | 8..200 |
| `font_weight` | 100..900 (steps of 100) |
| `text_color`, `background_color` | hex `#RRGGBB` or `#RRGGBBAA` |
| `border_radius`, `padding` | 0..400 |
| `max_lines` | 1..50 |
| `overflow` | `clip`\|`ellipsis`\|`visible` |

Prefer `text_role` (semantic) over hardcoding sizes where possible.

### `enter_animation` / `exit_animation` (all elements)

| Field | Notes |
|---|---|
| `type` (required) | `none`, `fade`, `fade_up`, `fade_down`, `slide_left`, `slide_right`, `scale_in`, `scale_out` |
| `duration_ms` | 0..60000 (default 300) |
| `delay_ms` | 0..60000 |
| `easing` | `linear`\|`ease`\|`ease_in`\|`ease_out`\|`ease_in_out` |
| `distance`, `opacity` | 0..1 |
| `scale` | 0..10 |

The stored config is **animation intent**, not CSS. The frontend maps `type` →
actual animation via its own registry.

---

## Editing a composition — `PUT /{id}/slides/{slide_id}/composition`

Roles: **admin, manager**. Draft only (`409` on published). This is an **atomic
aggregate replace**: it sets the slide's timeline settings and replaces the whole
element set in one transaction — no partial states.

**Body**

```json
{
  "playback_mode": "timed",
  "duration_ms": 8000,
  "composition_schema_version": 1,
  "background_color": "#102A43CC",
  "elements": [
    { "element_type": "media", "media_id": "aupm_...", "layer_index": 0, "start_ms": 0, "layout": { "x": 0, "y": 0, "width": 1, "height": 1, "fit": "cover" } },
    { "element_type": "text", "text_content": "Switch users instantly", "layer_index": 10, "start_ms": 1000, "end_ms": 4000,
      "layout": { "x": 0.08, "y": 0.72, "width": 0.84, "height": 0.15 },
      "style": { "text_role": "headline", "text_align": "center" },
      "enter_animation": { "type": "fade_up", "duration_ms": 350, "easing": "ease_out" } }
  ]
}
```

`background_color` is nullable and accepts `#RRGGBB` or `#RRGGBBAA`; `null`
means the slide has no solid background.

- `elements` are stored in the **order you send them** (`sequence_order` is
  assigned by position, 0-based). Reorder by resending in the new order.
- `composition_schema_version` is optional (defaults to the current version).
- **Media must already exist on this slide.** Upload media first via the 2-step
  flow ([05_admin_slides_media.md](05_admin_slides_media.md)), then reference its
  `aupm_...` id here as `media_id`. The `aupm_...` id comes from the **confirm**
  step's response (`POST .../media`), not from `upload-url` — see the full
  upload→composition walkthrough in
  [08_recipes.md → recipe F](08_recipes.md#f-admin-author-a-slide-with-media--timed-captions-upload--composition).

**Response**: `{ "presentation": <full> }` (the whole presentation, with the
updated slide).

**Validation errors (`422` unless noted)**

- `start_ms < 0`, or `end_ms <= start_ms`.
- Element timing outside an explicit `duration_ms` (timed slides).
- `media` element without `media_id`; `text` element without `text_content`; type/payload mismatch.
- `media_id` that doesn't belong to this slide (or is deleted).
- `timed` without `duration_ms`; `media_driven` without a media element.
- Invalid `layout` / `style` / animation config (bad enum, out-of-range, unknown key).
- `style` on a non-text element.
- `409` if the presentation is not a draft.

---

## Backward compatibility (legacy slides)

Slides created before timeline support have **no elements**. The backend
**synthesizes** an effective composition at serialization time, so they render
uniformly:

- one full-bleed `media` element per media asset (ordered by the media's
  `sequence_order`),
- a `headline` text element from `title`, a `body` text element from `description`
  (if present),
- all running for the whole slide (`start_ms: 0`, `end_ms: null`).

Synthetic elements have **`client_id: null`** (they're not stored). The frontend
renders them exactly like real elements — no special-casing needed. Once you save
a real composition via the endpoint, the real elements take over.

---

## Versioning & immutability

Timeline elements are part of the version snapshot:

- `new-version` copies slide timeline settings **and** elements, remapping each
  media reference to the new version's copied media.
- Published compositions are immutable (edits require a new version).
- Deleting a slide soft-deletes its elements; deleting a media soft-deletes the
  elements that referenced it.

---

## Recipes

**Text-only timed slide** (`0–3s "A"`, `3–6s "B"`, `6–8s "C"`)

```json
{ "playback_mode": "timed", "duration_ms": 8000, "elements": [
  { "element_type": "text", "text_content": "A faster workflow", "start_ms": 0, "end_ms": 3000 },
  { "element_type": "text", "text_content": "Fewer taps",        "start_ms": 3000, "end_ms": 6000 },
  { "element_type": "text", "text_content": "More control",      "start_ms": 6000, "end_ms": 8000 } ] }
```

**Video with synchronized captions** — use `media_driven`; the frontend uses the
video's `currentTime` as the clock and shows each text element within its
`[start_ms, end_ms)` window:

```json
{ "playback_mode": "media_driven", "elements": [
  { "element_type": "media", "media_id": "aupm_video", "layer_index": 0 },
  { "element_type": "text", "text_content": "Step one", "layer_index": 10, "start_ms": 1000, "end_ms": 4000 },
  { "element_type": "text", "text_content": "Step two", "layer_index": 10, "start_ms": 4000, "end_ms": 7000 } ] }
```

**Static caption under an image** (both for the whole slide)

```json
{ "playback_mode": "manual", "elements": [
  { "element_type": "media", "media_id": "aupm_img", "layer_index": 0, "layout": { "x": 0, "y": 0, "width": 1, "height": 0.7, "fit": "cover" } },
  { "element_type": "text", "text_content": "Now available on all devices", "layer_index": 10, "layout": { "x": 0.05, "y": 0.75, "width": 0.9, "height": 0.2 }, "style": { "text_role": "caption", "text_align": "center" } } ] }
```
