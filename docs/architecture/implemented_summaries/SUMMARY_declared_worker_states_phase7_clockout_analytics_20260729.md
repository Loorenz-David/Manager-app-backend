# SUMMARY_declared_worker_states_phase7_clockout_analytics_20260729

## Metadata

- Summary ID: `SUMMARY_declared_worker_states_phase7_clockout_analytics_20260729`
- Status: `summarized`
- Owner agent: implementer (implementation) / `claude-opus-5` + `claude-sonnet-5` (independent review
  rounds 1 and 2) / `claude-opus-5` (F13/F14 fast-follow + lifecycle)
- Created at (UTC): `2026-07-31T00:00:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md` (rev 2)
- Master plan: `.../under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md` (Phase 7 of 7 — **final**)
- Baseline commit for suite comparison: `f26ecc6`

## What was implemented

- **`get_worker_clock_out_analytics`** (`services/queries/worker_stats/get_worker_clock_out_analytics.py`)
  — a purpose-built composite returning the handoff §5.1 payload:
  `{date, timeline, pause_reasons, completed_items, completed_items_truncated, week, rate}`. It takes the
  **resolved target worker id as an explicit argument**; `ctx.user_id` is attribution only, so an
  on-behalf clock-out returns the worker's day and never the acting manager's.
  - `timeline` and `week` come from the **shared** `load_recorded_shift_records` +
    `build_recorded_shift_timeline` helpers — not a fork. This is the anti-drift property: kiosk day
    totals are computed by the same function as the manager roster's, so the two surfaces cannot
    disagree. `week` is Mon–Sun of the clock-out date, bucketed in memory from **one** range fetch, all
    seven days present with zeros where no shift. `UserDailyWorkStats` is deliberately not used.
  - `completed_items`: one card per item completed on the date, deduplicated per item.
    `reference` = `article_number` → `sku` → `null`; `units` = `Item.quantity`;
    `total_seconds` = `TaskStep.total_working_seconds` **only**; `working_section` from the completing
    step (null-safe); `issues_count` from `ItemIssue`. Capped at 100 with
    `completed_items_truncated` surfaced.
  - `rate`: `units_per_hour` from today's units ÷ today's working hours;
    `baseline_units_per_hour` = mean over up to 5 days with recorded working time inside a 14-day
    lookback, `baseline_days: 0` → `baseline_units_per_hour: null` for a first-ever shift. Computed from
    batched queries — no per-day round trips.
- **Wiring** — `/clock-out` and the `/clock` toggle's clock-out branch compose analytics **after** the
  write transaction and attach it (`routers/api_v1/worker_shifts.py`). The clock-in branch has no such
  key. `clock_out_shift_for_user` is untouched, so the midnight safeguard
  (`tasks/users/auto_clock_out_open_shifts.py`) and the Connecteam handler
  (`handlers/handle_clock_out.py`) call it directly and cannot reach analytics at all.
- **Degradation is all-or-nothing** — any exception in composition yields `analytics: null` **in full**
  (never partial) plus a structured `worker_shift.clock_out_analytics_failed` log; the clock-out still
  returns `200` and the shift stays closed.
- **Floor roster working sections** — exposed on floor-scope items only, through Phase 6's exact
  conditional and merge point; **absent (not `null`)** for manager/worker/admin/seller in compact and
  full modes.
- **Roster page cap raised for floor scope** — `GET /users` is now `Query(50, ge=1, le=1000)` with a
  router-level guard rejecting `limit > 200` for non-floor scopes (`422`), so a >200-worker workspace is
  reachable in one page from the kiosk.
- **Carried Phase 6 items** — the duplicate-`clock_in_code` index name is single-sourced on the model
  (`user_work_profile.py:20`) and pinned by a test, the `IntegrityError → 409` race path now has a
  committed test, and the `409` message states the code may belong to an inactive worker.

## Cross-endpoint change outside this phase's scope (F13 — disclosed)

`_load_step_and_primary_item` in `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`
was changed during the round-1 fixes. Its intermediate map was keyed by `item_id`
(`{row.item_id: row.task_id}`) and is now keyed by `task_id` (`{row.task_id: row.item_id}`, resolved
against a `client_id`-keyed item map). The old keying collapsed an item that is PRIMARY on **two** tasks
into a single entry, leaving one task absent from the final `task_id → Item` dict.

Phase 7 depends on this helper for card completeness (a dropped mapping silently omits a card), but the
helper **also backs the manager-facing linear-timeline breakdown endpoint**
(`GET /users/{user_id}/linear-timeline/breakdown`), which this phase's prompt scoped read-only. On that
endpoint the old keying rendered `"item": null` in the affected task's step details. The fix is correct
and was kept; it was found by reading the `git diff` rather than from the Review log, and is recorded
here because the archive record must describe everything that shipped.

Regression coverage was added **on the breakdown endpoint itself**, not the clock-out composite:
`test_get_worker_linear_timeline_breakdown.py::test_step_details_resolve_the_primary_item_of_each_task`.
Mutation-verified — with the old keying restored verbatim the new test fails while the file's five
pre-existing tests all still pass, confirming the scenario was genuinely uncovered before.

## Contract adherence

- `07_queries.md`: the composite is a query service; the floor conditional stays at Phase 6's merge
  point in `list_users`, not in the shared domain serializers.
- `20_api_versioning.md`: `analytics` is additive and `null` remains a valid value; floor-only roster
  fields are absent rather than null for every other scope.
- `18_security.md` / `28_roles_permissions.md`: every new query is workspace-scoped (the image-link join
  is transitively scoped through workspace-scoped item ids — `ImageLink`/`Image` carry no
  `workspace_id`); cross-workspace leakage is probed.
- No new tables, no migration in this phase.

## Validation evidence

- **Independent review round 1 (`claude-opus-5`) — NEEDS_CHANGES**, blocking on F1 (floor roster still
  capped at 200 at the router — the raised ceiling lived in the query service FastAPI never reaches),
  F2 (the `_clock_out_at` regression test could not fail, because the route's `except Exception`
  swallowed the `AssertionError` it guarded with) and F3 (two committed tests left red). F4–F12 medium
  and low.
- **Independent re-review (`claude-sonnet-5`) — APPROVED.** All three blockers independently reproduced
  as fixed under hands-on mutation, not merely re-read: reintroducing the prohibited
  `pop("_clock_out_at", …)` default failed the new `composer_calls == []` guard; reintroducing a per-day
  `load_recorded_shift_records` call inside the week loop failed the absolute `<= 11` statement-count
  assertion.
- **Suite parity by node set**, reproduced by the reviewer from its own `git worktree` at `f26ecc6`
  rather than trusting reported numbers: baseline 28 failed / 1317 passed, current 28 failed / 1335
  passed, sorted `FAILED`-node diff **empty**. The 28 failures are the documented pre-existing
  `pause_ended_shift`-not-configured baseline defect.
- **Query budget**: absolute bound `<= 11` statements for the whole composite, plus a 1-item-vs-3-item
  comparison; both mutation-verified.
- **Composite latency**: 101-item realistic-day fixture completes in well under 500 ms (asserted and
  printed).
- **Real-ASGI probes**: floor roster exposure and the roster cap are probed through `create_app()` with
  minted JWTs so middleware and `require_roles` are in the path — the methodology whose absence let F1
  through in round 1.
- **Fast-follow (post-approval, pre-archive)**: F13 and F14 closed with regression tests, each
  mutation-verified against the code it guards; no production file changed in that pass.
  `tests/integration/services/queries/worker_stats/` 26 passed / 0 failed; `ruff check` clean.

## Known gaps or deferred items

- **F15 (deferred by operator ruling, low)** — **no fixture exercises a shift that literally spans a UTC
  midnight boundary.** Every seeded shift in the Phase 7 suite starts and ends within one day, or lands
  right at a boundary at :00/:10. Acceptance criterion 5 names a midnight-spanning shift, so this is a
  known, accepted shortfall against it: `timeline` and `week` bucketing across a true midnight split is
  covered only transitively, through the shared `build_recorded_shift_timeline` helper's own separate
  test suite. Ruled out of this phase; not built.
- **F7 residual** — the `rate` baseline and today's units are consistent **by construction** (both
  deduplicate per item), and the "today" dedup path is tested, but the baseline side is not separately
  stress-tested with duplicate completions.
- **Repo-health, pre-existing and out of scope** — the shared `count_queries` fixture is broken (local
  listeners are used instead, as Phase 6 did), and the `pause_ended_shift`-not-configured seeding defect
  accounts for the 28 baseline failures.

## Handoff notes

- `HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` is **operator-owned**: §5.1's `total_seconds`
  wording has already been updated by the operator, and the §3 liveness-row flip is the operator's.
  Not edited by this phase.

## Lifecycle transition

- Plan archived to `backend/docs/architecture/archives/implementation/declared_worker_states/`.
- Master plan Phase 7 → `archived`. **All seven phases are archived; the feature set is complete.**
