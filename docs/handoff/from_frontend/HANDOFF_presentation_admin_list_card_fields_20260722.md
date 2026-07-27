# Handoff to backend — enrich the admin presentations list for dashboard cards

- Originating plan: `docs/architecture/under_construction/implementation/PLAN_presentation_phase3_corrections_20260722.md` (frontend Phase 3 — announcements dashboard)
- Date: 2026-07-22
- Requested by: frontend

Paste the block below to the backend agent.

---

## Prompt for the backend agent

In the **app update presentations** system (`/api/v1/app-update-presentations`), the admin list endpoint (`GET` collection root, response key `app_update_presentations_pagination`) returns compact items with no slide data. The frontend dashboard renders announcement cards that need a per-deck preview (slide count, media type chips, cover thumbnail), and currently must issue one `GET /{id}` per card (N+1, with full-deck presigning) just to show it.

Add **three read-only fields to each admin list item**. No other endpoint, write path, or field changes.

| Field | Type | Derivation |
|---|---|---|
| `slide_count` | int ≥ 0 | Count of the version's non-deleted slides. |
| `media_kinds` | array of `"image" \| "video"` | One entry per non-deleted media asset across the deck, ordered by slide `sequence_order`, then media `sequence_order`. Empty array when the deck has no media. |
| `cover_url` | string \| null | Presigned GET URL for the deck cover: take the first non-deleted slide (lowest `sequence_order`) that has media, then its first media. If `image` → its media URL; if `video` → its `poster_url`, else its `fallback_url`, else skip to the next media/slide. `null` when nothing usable exists. Same short-lived presigning semantics as the other `*_url` fields. |

Rules:

- Applies to the **admin list only** — the consumer endpoints (`/active`, `/history`) already return full slides and must not change.
- Soft-deleted slides/media are excluded from all three derivations.
- Every status (draft / published / archived) and every version gets the fields — the admin list shows all of them.
- Avoid per-row N+1 queries in the list implementation (batch/aggregate the slide + media lookup).
- Backward compatible: purely additive fields; existing clients unaffected.

Tests to add:

1. Deck with image + video slides → correct `slide_count`, ordered `media_kinds`, `cover_url` from the first slide's image.
2. First slide's media is a video with a poster → `cover_url` = poster; video without poster or fallback but a later image exists → that image; no media at all → `cover_url: null`, `media_kinds: []`, count still correct.
3. Soft-deleted slide/media excluded from all three.
4. List implementation does not execute per-row slide/media queries (whatever your standard query-count assertion pattern is).

Documentation: update the admin list response example in `04_admin_presentations.md` (the frontend consumes a copy of this doc — it will be re-synced after your change).

---

## After the backend agent finishes (operator checklist)

- [ ] Re-sync the updated backend doc into `docs/presentation_capability/backend/04_admin_presentations.md`.
- [ ] Tell Claude-builder — it will amend `PLAN_presentation_phase3_corrections_20260722.md` to consume the three fields directly (dropping the `GET /{id}` enrichment approach) before the Codex corrections session runs.
