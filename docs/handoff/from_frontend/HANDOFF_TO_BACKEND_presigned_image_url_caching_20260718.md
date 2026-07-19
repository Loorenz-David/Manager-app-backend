# HANDOFF_TO_BACKEND_presigned_image_url_caching_20260718

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_presigned_image_url_caching_20260718`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Owner agent: `claude-opus-4-8`
- Source frontend plan: `docs/architecture/under_construction/implementation/PLAN_backend_image_stable_rendering_20260718.md`

## Request to backend

- Required backend behavior: **stop generating a fresh presigned GET URL on every
  serialization of the same image.** Return a *stable* URL string for a given storage key for
  most of its validity window, so repeated API responses are byte-identical for unchanged
  images.
- User-facing impact: today every query refetch makes all visible images flicker and re-download
  from S3 — the frontend re-renders because the URL string (its `X-Amz-Date`/`X-Amz-Signature`)
  changes each response even though the image didn't. Stable URLs restore browser HTTP caching,
  TanStack structural sharing, and cut S3 GET egress.
- Desired timeline: independent of the frontend plan (frontend ships its own render-layer fix);
  whenever convenient — but it multiplies the benefit app-wide, including any client that never
  migrates.

## Frontend context

- Why the frontend needs this: the frontend is shipping a `BackendImage` primitive that
  stabilizes the *rendered* `src` client-side (cache keyed on `origin + pathname`). That kills
  the flicker, but response-payload churn still breaks TanStack structural sharing — every list
  object containing an image gets a new identity per refetch, causing unnecessary re-renders of
  entire cards/lists. Only the backend can make the payload byte-stable.
- Blocked frontend plan (if any): none — the frontend plan proceeds regardless.
- Clarifications required:
  - [ ] Is the API served by multiple worker processes? A naive per-process in-memory cache
    yields *different* signatures per worker, so responses would still alternate between a small
    set of URLs. If multi-worker, a shared cache (Redis) or a deterministic scheme is needed for
    full stability. (Frontend tolerates alternation — its pathname-keyed cache absorbs it — but
    structural sharing would only be partially restored.)

## Expected backend deliverables

1. Presigned GET URL caching at the two generation points:
   - `beyo_manager/domain/images/serializers.py` → `_resolve_image_url` (feeds
     `serialize_image` / `serialize_image_light`, i.e. every embedded image in list/detail
     responses).
   - `beyo_manager/services/queries/images/get_download_url.py` (and, if desired,
     `services/queries/files/get_pending_upload_download_url.py`).
2. Suggested policy (mirror of the frontend's): cache entry keyed by storage key; reuse the
   generated URL while its remaining validity exceeds a margin (e.g. regenerate when < 4 h of
   the 24 h `_IMAGE_URL_TTL` remain). Cap/evict the cache (LRU or TTL dict).
3. Acceptance: two consecutive calls to any image-bearing endpoint within the reuse window
   return **byte-identical** `image_url` values for unchanged images; a URL is never returned
   with less remaining validity than the agreed margin.
4. No schema change: `image_url` / `download_url` / `expires_in` shapes stay exactly as today.

## Interface expectations

- Endpoint(s): unchanged — this is response-stability only (`/api/v1/images`,
  `/api/v1/images/{id}/download-url`, and every endpoint embedding `serialize_image*`).
- Request shape: unchanged.
- Response shape: unchanged; `expires_in` on the download-url endpoint should reflect the
  *actual remaining* validity of the returned (possibly cached) URL, not always the full TTL.
- Error cases: unchanged. Note: cached URLs must never be served past expiry minus margin.
- Socket events (if applicable): n/a.

## Frontend contract implications

- Architecture contracts affected:
  - none — no shape changes; `architecture/04_api_client.md` untouched.
- Local extension updates needed:
  - none.
