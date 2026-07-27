# 08 — Recipes (end-to-end flows)

Concrete request sequences for the common tasks. All paths are relative to
`/api/v1/app-update-presentations`. Bearer token assumed on every call.

---

## A. Admin: build & publish an announcement

```
1. PUT ""                                   # create draft  -> presentation.client_id = P
   { "title": "A faster way to find products", "category": "improvement" }

2. POST "/P/slides"                          # add slide     -> slide S
   { "title": "Search from one place", "description": "…", "layout_type": "media_top",
     "action_label": "Try it", "action_route": "/products/search" }

3. POST "/P/slides/S/media/upload-url"       # get upload url
   { "media_type": "video", "content_type": "video/mp4", "file_name": "demo.mp4" }
   -> { upload_url, pending_upload_client_id: PU, storage_key, expires_in }

4. PUT <upload_url>                           # upload bytes straight to S3
   Content-Type: video/mp4  + <file>

5. POST "/P/slides/S/media"                   # confirm/attach
   { "media_type": "video", "pending_upload_client_id": "PU",
     "alt_text": "Demo", "duration_ms": 5000, "is_looping": true }

6. PUT "/P/audience"                          # who sees it
   { "audience_mode": "all_matching", "app_keys": ["worker","manager"] }

7. GET "/P/preview"                           # (optional) preview the draft

8. POST "/P/publish"                          # go live
```

Repeat steps 2–5 per slide; add multiple `image` media to one slide for a carousel.

---

## B. Admin: correct a published announcement

Do **not** edit the live one (it's immutable). Branch a new version:

```
1. POST "/P/new-version"        # -> new draft P2 (version+1, content+targets copied)
2. PATCH "/P2"  or edit slides/media/audience on P2
3. POST "/P2/publish"           # P2 supersedes P for eligible users (newest wins)
```

`P` stays published but is superseded at read time; you don't need to archive it.

> If the "correction" is really a **different message** (different audience, new
> topic), create a **new announcement** with `PUT ""` instead of `new-version` —
> otherwise the new version supersedes the old one for overlapping users.

---

## C. Admin: target a specific role or specific people

**A specific role:**

```
PUT "/P/audience"
{ "audience_mode": "all_matching", "role_keys": ["worker"] }
```

**Specific people only:**

```
PUT "/P/audience"
{ "audience_mode": "selected_users_only", "user_ids": ["usr_a","usr_b"] }
```

(Users must be active members of your workspace.)

---

## D. Consumer: the display loop

```
on app open / resume:
  GET "/active?app_key=<my app_scope>"
  if data.presentation == null: done (nothing to show)
  else render presentation

when shown:
  POST "/{presentation.client_id}/view-state"
  { "version": presentation.version, "action": "shown", "last_slide_index": 0 }

as the user advances slide n:
  POST "/{id}/view-state" { "version": v, "action": "progressed", "last_slide_index": n }

on finish:
  POST "/{id}/view-state" { "version": v, "action": "completed" }
on dismiss (if presentation.is_dismissible):
  POST "/{id}/view-state" { "version": v, "action": "dismissed" }

then:
  GET "/active?app_key=…"   # fetch the next eligible one (or null)
```

- Always echo `presentation.version` back in the body.
- Only send `dismissed` when `presentation.is_dismissible` is `true`.
- `completed` is terminal — the presentation won't return from `/active` again.

---

## E. Consumer: the "What's New" feed

```
GET "/history?app_key=<my app_scope>&limit=20&offset=0"
-> app_update_whats_new_pagination.items[]  # full presentation shape + view_state each
```

- Includes already-seen and expired items so users can revisit.
- Each item carries its slides and the user's `view_state` — render the list and
  open items with no extra calls.
- Page with `offset += limit` while `has_more` is `true`.

---

## F. Admin: author a slide with media + timed captions (upload → composition)

This is the **full chain** from an empty presentation to a published slide that
plays a video with synchronized caption text. It shows exactly **where the
`aupm_` media id comes from** (step 5's confirm response) and how it feeds the
composition (step 6). See [09_slide_composition.md](09_slide_composition.md) for
the composition contract and [05_admin_slides_media.md](05_admin_slides_media.md)
for the upload flow.

```
1. PUT ""                                      # create draft -> presentation P
   { "title": "New: quick user switching", "category": "improvement" }

2. POST "/P/slides"                            # add slide -> slide S
   { }                                         # (timeline is set in step 6)

3. POST "/P/slides/S/media/upload-url"         # ask for a presigned S3 PUT url
   { "media_type": "video", "content_type": "video/mp4", "file_name": "demo.mp4" }
   -> { "upload_url": "...", "storage_key": "...", "pending_upload_client_id": "pu_..." }

4. PUT <upload_url>                             # browser uploads the bytes to S3
   Content-Type: video/mp4  +  <binary body>   # (no auth header; presigned)

5. POST "/P/slides/S/media"                     # confirm -> records the media asset
   { "media_type": "video", "pending_upload_client_id": "pu_...",
     "duration_ms": 8000, "alt_text": "Quick user switching demo" }
   -> { "presentation": { ... } }
   #    ^^^ READ THE NEW MEDIA ID HERE:
   #    const mediaId = presentation.slides.find(x => x.client_id === "S")
   #                                .media.at(-1).client_id;   // "aupm_..."

6. PUT "/P/slides/S/composition"                # place + time the elements
   { "playback_mode": "media_driven",
     "elements": [
       { "element_type": "media", "media_id": "aupm_...", "layer_index": 0,
         "layout": { "x": 0, "y": 0, "width": 1, "height": 1, "fit": "cover" } },
       { "element_type": "text", "text_content": "Tap your avatar",
         "layer_index": 10, "start_ms": 1000, "end_ms": 4000,
         "layout": { "x": 0.08, "y": 0.72, "width": 0.84, "height": 0.15 },
         "style": { "text_role": "headline", "text_align": "center" },
         "enter_animation": { "type": "fade_up", "duration_ms": 350, "easing": "ease_out" } },
       { "element_type": "text", "text_content": "Switch instantly",
         "layer_index": 10, "start_ms": 4000, "end_ms": 8000,
         "layout": { "x": 0.08, "y": 0.72, "width": 0.84, "height": 0.15 },
         "style": { "text_role": "headline", "text_align": "center" },
         "enter_animation": { "type": "fade_up", "duration_ms": 350, "easing": "ease_out" } }
     ] }

7. POST "/P/publish"                            # go live
```

Key points:

- **The media id is not returned by `upload-url`.** `upload-url` gives you a
  `pending_upload_client_id` (the upload handshake) and a `storage_key`. The
  durable `aupm_...` **media id** only exists after **step 5 (confirm)** — read it
  from the returned presentation's `slides[].media[]`.
- Repeat steps 3–5 for each asset (e.g. a poster image, or several images for a
  carousel), then reference each `aupm_...` id in step 6.
- For a **poster on the video**: upload a poster image via steps 3–5 with
  `media_type: "image"`, take its `aupm_...`/`storage_key`, and set it on the
  video media (`poster_storage_key`) via `PATCH .../media/{media_id}` — or pass a
  poster key when confirming.
- For a **text-only slide**, skip steps 3–5 entirely and send only `text`
  elements with `playback_mode: "timed"` + `duration_ms` in step 6.
- The composition in step 6 **replaces** the slide's whole element set atomically;
  re-send the full list to edit.

---

## Gotchas checklist

- `app_key` on consumer endpoints **must equal** the token's `app_scope` (`422`
  otherwise).
- Slide/media/audience edits only work on **drafts** (`409` on published/archived).
- Slide/media/audience mutations return the **whole presentation**, not the sub-object.
- `action_route` must be a **relative** in-app path (starts with `/`, no scheme).
- Presigned `media_url`/`poster_url` are **short-lived** — refetch to refresh.
- View-state is **per user**; never send a user or device id in the body.
- Reorder calls must list **exactly** the current child ids.
- A composition element's `media_id` (`aupm_...`) comes from the **confirm** step
  (`POST .../media`), not from `upload-url`. Upload → confirm → read the id →
  reference it in the composition (recipe F).
