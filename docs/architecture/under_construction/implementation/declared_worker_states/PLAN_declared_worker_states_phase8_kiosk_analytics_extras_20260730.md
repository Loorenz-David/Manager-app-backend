# PLAN_declared_worker_states_phase8_kiosk_analytics_extras_20260730

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase8_kiosk_analytics_extras_20260730`
- Status: `under_construction`
- Owner agent: `claude-fable-5` (plan) → implementer TBD
- Created at (UTC): `2026-07-30T16:00:00Z`
- Last updated at (UTC): `2026-07-30T16:00:00Z`
- Related issue/ticket: `docs/handoff/from_frontend/BACKEND_REQUIREMENTS_clock_kiosk_20260729.md`
- Intention plan: `.../declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 8)
- Prerequisite: **Phase 7 archived** (the `analytics` composite must exist before keys are added to it).

## Goal and intent

- Goal: Satisfy the frontend's clock-out screen with two additive keys inside `analytics` —
  **`completed_items`** (per-item cards) and **`week`** (per-day worked-time bars) — plus two cheap
  roster items the kiosk needs (worker working-sections on floor items; a workable page cap).
- Business/user intent: the clock-out moment shows the worker *what they made* and *how their week is
  going*, not just seconds in buckets.
- Non-goals: **Shift scheduling** (operator ruling 2026-07-30: does not exist, explicitly skipped —
  no `scheduled_seconds`, no shift-time rows). **Floor announcements** (separate future feature set).
  **Badge numbers** (no data exists; deferred). A units-per-hour `rate` key (derivable later from
  `completed_items` + `timeline`; not requested for v1). New product/domain tables of any kind.

## Scope

- In scope:
  1. `analytics.completed_items` — one entry per item the worker completed on the clock-out date.
  2. `analytics.week` — Monday–Sunday of the clock-out date: per-day `working/pause/idle` seconds plus
     range totals.
  3. Floor roster: expose the worker's working sections on floor-scope items (kiosk confirm-screen
     subtitle). Same conditional and merge point as Phase 6's `clock_in_code` — floor only, absent for
     every other scope.
  4. Roster page cap: `GET /users` currently caps `limit` at 200 (`le=200`), silently truncating the
     kiosk's identification set in workspaces above 200 workers. Raise the cap for floor-scope
     sessions (or document the pagination walk as sufficient — `users_pagination` already returns
     `has_more`/`total`). Whichever you choose, prove it with a test above 200.
- Out of scope: everything in non-goals; changing `analytics`' existing five keys; manager endpoints.
- Assumptions (data paths verified 2026-07-30 — no new tables required):
  - **`completed_items` shape** (handoff §5.2 is authoritative):
    `{item_id, reference, image_url, working_section: {client_id, name} | null, total_seconds, issues_count}`
    - `reference` = `Item.article_number`, falling back to `Item.sku`, else `null`. This system has no
      product-name entity — the reference *is* the label (operator ruling).
    - `image_url` = first linked item image via `image_links` (`entity_type` = item,
      `entity_client_id` = the item id) → `images.image_url`. **Verify-first**: confirm the enum member
      name and whether image links carry an ordering column; if not, define "first" deterministically
      (e.g. lowest `client_id`) and state the choice in the Review log.
    - `working_section` = the section of the step that completed the item (the same
      `working_section_id` the analytics worker already stamps on section daily stats); `null` if
      unresolvable.
    - `total_seconds` = time booked against that item's steps (`TaskStep.total_working_seconds`
      family — **verify-first** which fields constitute "time to complete" and state the definition in
      the Review log; document that it is task-level, not this worker's share alone).
    - `issues_count` = count of `ItemIssue` rows for the item (`ItemIssue.item_id`).
    - Item identity per step comes from the existing task→item mapping used by
      `get_worker_linear_timeline_breakdown` (`item_by_task`); **reuse it, do not fork it**.
    - Ordered by completion time. Cap the list defensively (mirror `_MAX_SEGMENTS`'s spirit) and
      surface truncation rather than silently dropping.
  - **`week` shape**: `{days: [{date, working_seconds, pause_seconds, idle_seconds}], totals: {...}}`,
    Monday–Sunday containing the clock-out date, days without a shift present with zeros. Source is
    `UserShiftStateRecord` via the existing `build_recorded_shift_timeline` /
    `load_recorded_shift_records` helpers — **one query for the range, bucketed by day; not seven
    queries**. Do NOT use `UserDailyWorkStats`: it has no idle bucket and lags asynchronously.
  - Both keys are composed in the Phase 7 composite, **after** the clock-out transaction, and inherit
    its degradation rule: any failure → the whole `analytics` object is `null`, never a partial or a
    failed clock-out.
  - Absent-until-shipped: no key is emitted as `null` before this phase; the frontend treats absent and
    `null` alike (handoff §5.3).

## Clarifications required

- [x] Product identity for the carousel? — resolved (operator 2026-07-30): per **item**, labelled by
  `article_number` → `sku`; no grouping by category, no product table.
- [x] Scheduled hours in `week`? — resolved: **skipped**; scheduling does not exist. Bars are
  worked-time only, segmented working/pause/idle.
- [ ] `total_seconds` definition — implementer proposes from the code and records it; operator vetoes
  in review if the semantics are wrong.

## Acceptance criteria

1. `completed_items` returns one entry per item completed on the date with all six fields; `reference`
   falls back correctly (article → sku → null) — all three cases tested; `image_url` null when the item
   has no linked image; `issues_count` matches `ItemIssue` rows; `working_section` resolved from the
   completing step.
2. A worker who completed nothing gets `completed_items: []` (not absent, not null) — the key exists
   once this phase ships.
3. `week` covers Mon–Sun of the clock-out date with every day present (zeros where no shift), buckets
   matching a same-range `build_recorded_shift_timeline` computation, and `totals` equal to the sum of
   `days` — asserted as an invariant, not by hard-coded numbers.
4. Query budget: `completed_items` and `week` each add a **bounded, batched** set of queries — no
   per-item and no per-day query. Prove with a query-count listener (the shared `count_queries` fixture
   is broken — see the master baseline; use a local listener as Phase 6 did).
5. Degradation unchanged: a forced exception inside either new composer → `analytics: null`, clock-out
   still `200` with the shift closed, structured error log (extends Phase 7's acceptance 6).
6. Floor roster carries the worker's working sections for floor scope only; **absent** for
   manager/worker/admin/seller in both compact and full modes — probed through the real ASGI app with
   minted tokens, as the Phase 6 review did.
7. Roster page cap: a workspace with >200 workers is fully reachable by the kiosk (raised cap or a
   proven pagination walk); test with >200 rows.
8. Phase 7's five `analytics` keys, the manager worker-stats endpoints, and the shared serializers are
   untouched (empty diffs / unmodified tests).
9. Quiet-tree suite: no new failure nodes vs the recorded baseline; `ruff check` clean on touched files.

## Contracts and skills

### Contracts loaded

- `07_queries.md` (+ local): composite/aggregation query services.
- `06_commands.md` (+ local): the analytics composition stays out of the write command.
- `46_serialization.md` (+ local): new payload shapes.
- `20_api_versioning.md`: additive-only inside `analytics`.
- `22_performance.md`: batching/query-budget discipline at the busiest UX moment.
- `24_multi_tenancy.md`: every new query workspace-scoped.
- `15_testing.md`, `49_observability_runtime.md`.

### File read intent — pattern vs. relational

Permitted relational reads: `get_worker_clock_out_analytics.py` (Phase 7 output — the composition
point), `get_worker_linear_timeline_breakdown.py` (`item_by_task` mapping to reuse),
`list_workers_linear_timeline.py` (`build_recorded_shift_timeline` / `load_recorded_shift_records`),
`models/tables/items/item.py`, `item_issue.py`, `images/image_link.py`, `images/image.py`,
`tasks/task_item.py`, `tasks/task_step.py`, `working_sections/*`, `services/queries/users/list_users.py`
and `routers/api_v1/users.py` (roster items), and the handoff §3/§5.2/§5.3.

Prohibited pattern reads: other query services for skeleton → `07_queries.md`.

## Risks and mitigations

- Risk: per-item work explodes the clock-out query budget at shift end (many workers at once).
  Mitigation: batched loads only, defensive cap + truncation flag, acceptance 4's query-count proof;
  the composite already runs outside the write transaction, and `analytics: null` remains the escape.
- Risk: `total_seconds` semantics mislead (task-level vs this worker's share).
  Mitigation: definition stated in the Review log and in the handoff before shipping; the handoff
  already says it is task-level.
- Risk: `week` recomputed per day drifts from the day view.
  Mitigation: same helper, one range query, and acceptance 3 compares against the helper's own output.
- Risk: exposing sections on the roster widens the floor payload again.
  Mitigation: same floor-only conditional and merge point as Phase 6; acceptance 6 probes the real app.

## Validation plan

- Focused: new analytics-extras suites, roster floor-exposure suites, >200-row pagination test.
- `pytest` full suite on a **quiet tree**; compare failure node sets, not counts.
- `ruff check` on touched files.

## Review log

- (empty)

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` → implement → independent review → archive (review-first gate applies).
- Transition owner: `David`
