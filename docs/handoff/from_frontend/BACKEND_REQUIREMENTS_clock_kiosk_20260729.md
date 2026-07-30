# BACKEND_REQUIREMENTS_clock_kiosk_20260729

Companion to `PLAN_clock_kiosk_master_20260729.md`. The kiosk design
(`image_design/`) is ahead of what the backend contract
(`HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`) provides. The frontend
builds every design element now behind **adapter interfaces that default to
empty/null**, so each item below is purely additive backend work: when the data
exists, the frontend wires it into the adapter — no UI change.

Ordered by product value. "Where it plugs in" names the frontend seam that is
already waiting for the data.

## 1. Scheduled shift per worker — `scheduled_shift`

- Design use: confirm screen context row ("Today's shift 07:00 – 15:30") and the
  clock-in result dark plate ("SCHEDULED 07:00 – 15:30").
- Needed shape (suggested, additive on `GET /worker-shifts/current` — it is the
  fresh-per-worker call the kiosk already makes at exactly the right moment):
  ```json
  "scheduled_shift": { "start": "2026-07-29T04:00:00Z", "end": "2026-07-29T12:30:00Z" }
  ```
  `null` when the worker has no schedule for the day.
- Frontend seam: `ScheduledShiftAdapter` in `@beyo/clock-kiosk` (row/column hidden while null).

## 2. Floor announcements — "TODAY ON THE FLOOR"

- Design use: clock-in result screen; short dated list, three items maximum.
- Needed: a workspace-scoped listing endpoint readable by a floor token, e.g.
  `GET /api/v1/floor-announcements` →
  ```json
  [ { "client_id": "fan_…", "title": "Line 3 changeover at 11:00",
      "body": "Swap to the 60mm die set — Priya will run the checklist with you.",
      "accent": "info | success | neutral", "date": "2026-07-29" } ]
  ```
  Plus whatever manager-side authoring surface you choose (out of kiosk scope).
- Frontend seam: `AnnouncementsAdapter` (section hidden while empty).

## 3. Clock-out analytics: per-product completed items

- Design use: "ITEMS COMPLETED — 142 units · 4 lines" carousel with product
  image, name, units.
- Today: `analytics.timeline.completed_count` is a bare total; `segments[].steps`
  carries task-step detail but no product grouping/units/images.
- Needed (additive key inside `analytics`):
  ```json
  "completed_items": [
    { "item_id": "itm_…", "name": "Hex bolt M8", "image_url": "https://…", "units": 52 }
  ]
  ```
- Frontend seam: `SummaryExtrasAdapter.items` (carousel hidden while null/empty).

## 4. Clock-out analytics: week context

- Design use: "THIS WEEK 39.9h / 40h" daily bar chart (Mon–Fri, today
  highlighted) and the "39.9h logged this week of 40h scheduled" insight row.
- Today: `analytics` is strictly day-scoped.
- Needed (additive key inside `analytics`):
  ```json
  "week": {
    "scheduled_seconds": 144000,
    "days": [ { "date": "2026-07-27", "worked_seconds": 29520 }, … ]
  }
  ```
  (Alternative: the kiosk's manager-role token could call
  `GET /worker-stats/{user_id}/linear-timeline` with a week range, but that
  couples the kiosk to manager-app endpoints and adds a second request at the
  busiest moment — the additive key is preferred.)
- Frontend seam: `SummaryExtrasAdapter.week`.

## 5. Clock-out analytics: production rate

- Design use: "RATE TODAY 17.3 units / hour — 5-day average 15.9" tile and the
  "142 units completed vs 5-day average of 130 (+9%)" row.
- Today: `insights` can carry a `completed_count` comparison (baseline/delta),
  but nothing expresses units-per-hour, and units require item data (#3).
- Needed (additive key inside `analytics`), or as a dedicated `insights` code:
  ```json
  "rate": { "units_per_hour": 17.3, "baseline_units_per_hour": 15.9, "baseline_days": 5 }
  ```
- Frontend seam: `SummaryExtrasAdapter.rate`.

## 6. Roster identity extras: badge / station line

- Design use: confirm screen subtitle "Line 3 · Assembly · Badge NB-1148".
- Today: floor roster gives `username`, `profile_picture`, `role`,
  `clock_in_code`, `email` — no badge number, no line/station assignment.
- Needed (additive on the floor-scope roster items): `badge_number: string|null`
  and, if the concept exists, a station/line label. Until then the kiosk renders
  the role name alone.
- Frontend seam: identity view model in `@beyo/clock-kiosk` (fields optional).

## 7. Roster scale

- `GET /users?role=worker&compact=true&limit=200` caps at 200. A workspace above
  200 workers silently loses kiosk identification for the tail. Needs either a
  raised cap for floor scope or pagination the kiosk can walk. v1 logs a console
  warning when exactly 200 rows return.

## 8. Confirmations of existing contract points (no change requested)

- **Handoff doc request — make nullability explicit.** The handoff's JSON
  examples show every field populated and never state which are nullable or
  omissible. Phase 1 review (2026-07-29) found this produced overly strict
  schemas that live payloads would break (`profile_picture: null`,
  `pause_reason.image_url: null`, omitted analytics keys). The frontend now
  takes the tolerant reading, tie-broken by the live-proven sibling schemas in
  `@beyo/stats`/`@beyo/pause-reasons` — but please annotate nullability/
  optionality explicitly in the handoff (it is the edit-first authority) so
  future shapes don't rely on inference.

- `clock_in_code` is 4–16 chars server-side; the kiosk v1 keypad only expresses
  **numeric 4-digit** codes. Manager code-assignment UI (backend phase 6+) should
  default to that format or kiosk users will need the email fallback.
- `analytics: null` degradation, 409-as-normal-flow, anti-enumeration single
  error message, and client-side-only identification are implemented exactly as
  the handoff prescribes.
- No socket events exist for shifts under floor scope; the kiosk polls the
  roster (2 min) and always re-fetches `/current` per interaction. If shift
  socket events are ever emitted to floor tokens, the kiosk can adopt them in a
  later phase (`socket-registry.ts` ships empty but wired).
