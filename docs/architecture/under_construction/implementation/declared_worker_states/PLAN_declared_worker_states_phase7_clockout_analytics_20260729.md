# PLAN_declared_worker_states_phase7_clockout_analytics_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase7_clockout_analytics_20260729`
- Status: `under_construction` (**rev 2, 2026-07-30 — rewritten**)
- Owner agent: `claude-fable-5` (plan) → implementer TBD
- Created at (UTC): `2026-07-29T12:00:00Z`
- Last updated at (UTC): `2026-07-30T16:30:00Z`
- Related issue/ticket: `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md`
- Intention plan: `.../declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (D14)
- Prerequisite: Phases 2, 4 and 6 archived.

> **Rev 2 supersedes rev 1 and absorbs the former Phase 8.** Rev 1 planned to extract a seam from
> `get_worker_linear_timeline_breakdown` and ship `segments[]` + time-based `insights`. Operator
> rulings 2026-07-30, after the frontend's requirements doc landed: the kiosk renders **totals only**
> (no per-segment step drill-down) and its comparison rows are **unit-based**, which the existing
> insights engine cannot express. So the breakdown seam is dropped entirely, and this phase composes a
> purpose-built payload from the cheap shared helpers instead. The manager drill-down endpoints are
> untouched and remain the home of `segments[]`.

## Goal and intent

- Goal: Populate the clock-out `analytics` envelope with exactly what the kiosk screen renders —
  **`timeline`** (day totals), **`pause_reasons`** (label lookup), **`completed_items`** (per-item
  cards), **`week`** (per-day worked-time bars) and **`rate`** (units/hour vs baseline) — composed
  after the clock-out transaction from existing tables. Plus two roster items the kiosk needs.
- Business/user intent: the clock-out moment shows the worker their day, what they made, and how their
  week is going — in one response, at the busiest moment of the day.
- Non-goals: `segments[]` / per-step drill-down (manager app keeps it). The time-based `insights`
  engine (cannot express units). **Shift scheduling** — does not exist; no `scheduled_seconds`, no
  shift-time rows (operator ruling). Floor announcements and badge numbers (no data; separate future
  work). New tables of any kind. Changing manager worker-stats endpoints.

## Scope

- In scope:
  1. Composite query service (e.g. `services/queries/worker_stats/get_worker_clock_out_analytics.py`)
     returning the handoff §5.1 payload.
  2. Wiring: `/clock-out` and the `/clock` toggle's clock-out branch compute it **after** the write
     transaction and attach it. `clock_out_shift_for_user` stays untouched — the midnight safeguard and
     Connecteam paths never compute analytics.
  3. Floor roster: expose the worker's working sections on floor-scope items (kiosk confirm-screen
     subtitle), using Phase 6's exact conditional and merge point.
  4. Roster page cap: `GET /users` caps `limit` at 200 (`le=200`), truncating identification in
     workspaces above 200 workers. Raise it for floor scope or prove the pagination walk is sufficient
     (`users_pagination` already returns `has_more`/`total`); test with >200 rows.
  5. Carried from the Phase 6 review (small, unrelated to analytics — see Clarifications).
- Out of scope: everything in non-goals.
- Assumptions (data paths verified 2026-07-30 — no new tables):
  - **`timeline` + `pause_reasons`**: reuse `load_recorded_shift_records` +
    `build_recorded_shift_timeline` + the pause-reason lookup helper from
    `list_workers_linear_timeline.py`. **This is the anti-drift property**: the kiosk's day totals come
    from the same function as the manager roster's, so they cannot disagree. `ended_shift_seconds` is
    not part of the kiosk payload (§5.1 omits it).
  - **`week`**: Monday–Sunday containing the clock-out date; **one** range query via the same helpers,
    bucketed per day; days with no shift present with zeros; `totals` = sum of `days`. Do NOT use
    `UserDailyWorkStats` (no idle bucket, async lag).
  - **`completed_items`**: one entry per item completed on the date —
    `{item_id, reference, image_url, working_section: {client_id, name} | null, units, total_seconds, issues_count}`.
    - `reference` = `Item.article_number` → `Item.sku` → `null` (no product-name entity exists).
    - `units` = `Item.quantity`.
    - `image_url` = first linked item image via `image_links` (`entity_type` = item,
      `entity_client_id` = item id) → `images.image_url`. **Verify-first**: the enum member name and
      whether links carry an ordering column; if not, define "first" deterministically and record it.
    - `working_section` = section of the completing step (the id the analytics worker already stamps on
      section daily stats); `null` if unresolvable.
    - `total_seconds` = time booked against that item's steps (`TaskStep.total_*`). **Verify-first**:
      state which fields constitute it, and that it is task-level rather than this worker's share.
    - `issues_count` = count of `ItemIssue` rows for the item.
    - Item identity per step reuses the existing task→item mapping (`item_by_task`) from
      `get_worker_linear_timeline_breakdown` — reuse, do not fork.
    - Ordered by completion time; defensively capped with `completed_items_truncated` surfaced.
  - **`rate`**: `units_per_hour` = today's total units ÷ today's `working_seconds` (hours);
    `baseline_units_per_hour` = mean over the most recent days **with recorded working time**, up to 5,
    searched within a 14-day lookback ending the day before the clock-out date; `baseline_days` reports
    how many contributed, and is `0` with `baseline_units_per_hour: null` when there is no history.
    Compute the baseline from the same batched item/shift queries — no per-day round trips.
  - **Degradation is a hard rule** (unchanged from rev 1): any exception in the composition →
    `analytics: null` **in full** + structured error log (`worker_shift.clock_out_analytics_failed`);
    the clock-out must never fail or roll back because stats could not be computed.
  - **Work date** = UTC date of `clock_out_at`.
  - Ordering: the composite reads `UserShiftStateRecord`, so it is only correct **after** the clock-out
    rebuild has been committed/flushed — same request, same session, after the transaction.

## Clarifications required

- [x] Reuse the breakdown seam? — resolved (rev 2): **no**. Kiosk renders totals only; the seam's ~5
  queries + per-segment step assembly are manager-drilldown cost at the busiest moment. Reuse the
  cheap shared helpers instead, which preserves the anti-drift property at ~1 query.
- [x] Ship `insights`? — resolved: **no**. It computes from `UserDailyWorkStats` time metrics and
  cannot express the design's unit-based comparisons; it also carries async staleness. `rate` replaces
  it.
- [x] Product identity for the cards? — resolved: per item, labelled `article_number` → `sku`.
- [x] Scheduled hours? — resolved: skipped; scheduling does not exist.
- [x] **Carried from the Phase 6 review (small, include here):**
  - **R1-1:** `update_user_admin`'s `IntegrityError → 409` race for duplicate `clock_in_code` has no
    committed test (the pre-check short-circuits every duplicate case), and the index-name string is
    duplicated in three places — a rename would silently degrade the race to a `500`. Add an assertion
    pinning the constant to the model's `Index` name (single-source it if trivial) plus a test that
    exercises the race path.
  - **Q1 operational cost:** a code held by a **deactivated** worker stays reserved but is un-findable
    (no read-back surface, by ruling), so the `409` is opaque. Change the duplicate-code `409` message
    to say the code is already in use in this workspace and may belong to an inactive worker.
    Message only.
- [ ] `total_seconds` definition — implementer proposes from the code, records it; operator vetoes in
  review if wrong.

## Acceptance criteria

1. `/clock-out` returns `analytics` with all six keys per handoff §5.1; `timeline.pause_by_reason`
   sums to `pause_seconds`; every reason key resolves in `pause_reasons`.
2. Actor/target split: on-behalf clock-out (manager token + worker `user_id`) returns the **worker's**
   analytics — proven with the acting manager holding their own same-day activity that must not
   appear. The composite takes the resolved target id as an explicit argument; `ctx.user_id` is
   attribution only.
3. `timeline` equals a same-range `build_recorded_shift_timeline` computation (invariant assertion, not
   hard-coded numbers) — proving the shared helper is actually shared.
4. `completed_items`: all seven fields; `reference` fallback tested in all three cases; `image_url`
   null with no linked image; `issues_count` matches `ItemIssue` rows; `working_section` from the
   completing step; `units` = `Item.quantity`; `[]` when nothing was completed; truncation surfaced.
5. `week`: Mon–Sun of the clock-out date, all days present (zeros where no shift), `totals` = sum of
   `days` (invariant), boundaries correct for a Monday clock-out and one spanning midnight.
6. `rate`: `units_per_hour` consistent with `completed_items` units and `timeline.working_seconds`;
   `baseline_days` = 0 with `baseline_units_per_hour: null` for a first-ever shift; a worker with
   history gets a baseline over the correct days.
7. **Query budget**: the whole composite adds a bounded, batched set of queries — no per-item, no
   per-day, no per-baseline-day round trips. Proven with a query-count listener (the shared
   `count_queries` fixture is broken — use a local one, as Phase 6 did) and a mutation check.
8. Degradation: a forced exception anywhere in the composition → clock-out still `200`, shift closed,
   `analytics: null` in full (never partial), structured error log asserted.
9. `/clock` toggle's clock-out branch returns the same `analytics`; its clock-in branch has no such key.
10. Safeguard + Connecteam compute nothing (no analytics reachable from `clock_out_shift_for_user`);
    their suites unmodified and green.
11. Floor roster carries the worker's working sections for floor scope only — **absent** (not `null`)
    for manager/worker/admin/seller in compact and full modes, probed through the real ASGI app with
    minted tokens (mirror the Phase 6 review's method).
12. Roster cap: a >200-worker workspace is fully reachable; test with >200 rows.
13. Carried items: R1-1 pin + race test; duplicate-code `409` message updated.
14. Manager worker-stats endpoints, shared serializers and Phase 4's `analytics: null` pinning tests
    untouched. Quiet-tree suite with no new failure nodes vs the recorded baseline; `ruff check` clean.

## Contracts and skills

### Contracts loaded

- `07_queries.md` (+ local): composite query service.
- `06_commands.md` (+ local): analytics stays out of the write command.
- `09_routers.md`: post-transaction composition at the route layer.
- `46_serialization.md` (+ local): new payload shapes.
- `20_api_versioning.md`: additive-only inside `analytics`.
- `22_performance.md`: query budget at the busiest UX moment.
- `24_multi_tenancy.md`: every new query workspace-scoped.
- `15_testing.md`, `49_observability_runtime.md`.

### File read intent — pattern vs. relational

Permitted relational reads: `list_workers_linear_timeline.py` (the shared helpers),
`get_worker_linear_timeline_breakdown.py` (`item_by_task` mapping only — do not extract a seam),
`clock_out_worker_shift.py`, `toggle_worker_shift.py`, `routers/api_v1/worker_shifts.py`,
`models/tables/items/item.py`, `item_issue.py`, `images/image_link.py`, `images/image.py`,
`tasks/task_item.py`, `tasks/task_step.py`, `working_sections/*`,
`services/queries/users/list_users.py`, `routers/api_v1/users.py`,
`services/commands/users/update_user_admin.py`, and handoff §3/§5.1/§5.3.

Prohibited pattern reads: other query services for skeleton → `07_queries.md`.

## Risks and mitigations

- Risk: per-item work explodes the query budget when several workers clock out at shift end.
  Mitigation: batched loads only, defensive cap + truncation flag, acceptance 7's mutation-proofed
  query count; composition runs outside the write transaction; `analytics: null` is the escape valve.
- Risk: kiosk totals drift from the manager view.
  Mitigation: same `build_recorded_shift_timeline` helper, pinned by acceptance 3.
- Risk: `total_seconds` semantics mislead (task-level vs this worker's share).
  Mitigation: definition recorded in the Review log; handoff already states the caveat.
- Risk: the rate baseline is noisy or undefined early in a worker's history.
  Mitigation: `baseline_days` is reported; `null` baseline when there is no history; the frontend
  renders today's rate alone.
- Risk: exposing sections widens the floor payload.
  Mitigation: Phase 6's conditional and merge point; acceptance 11 probes the real app.

## Validation plan

- Focused: analytics composite suites, roster floor-exposure suites, >200-row pagination test, carried
  R1-1 race test.
- Full suite on a **quiet tree**; compare failure node sets, not counts.
- `ruff check` on touched files.

## Review log

- (empty)

## Lifecycle transition

- Current state: `under_construction` (rev 2)
- Next state: `approved` → implement → independent review → archive (review-first gate).
- Transition owner: `David`
