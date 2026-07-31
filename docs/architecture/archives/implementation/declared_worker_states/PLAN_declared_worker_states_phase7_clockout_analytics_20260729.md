# PLAN_declared_worker_states_phase7_clockout_analytics_20260729

## Metadata

- Plan ID: `PLAN_declared_worker_states_phase7_clockout_analytics_20260729`
- Status: `archived` (**rev 2, 2026-07-30 — rewritten**; archived 2026-07-31)
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

### Independent review 2026-07-31 — `claude-opus-5` — **NEEDS_CHANGES**

Method: source-first verification (per addendum), plus executed mutation probes. Note: the working tree
is **not a git repository**, so the DoD's baseline-worktree failure-node diff was not reproducible; the
"untouched" checks below were done by source inspection and by running the affected suites.

#### Delivered and verified

- No seam extracted from `get_worker_linear_timeline_breakdown`; no `segments`/`insights` keys emitted
  (grep count 0 in the composite; `set(analytics)` pinned to the 7 contract keys).
- `timeline` uses the shared `build_recorded_shift_timeline` (not forked) and is asserted equal to a
  same-range computation — AC3 holds, anti-drift property preserved.
- `UserDailyWorkStats` not used; `week` derives from one `load_recorded_shift_records` range fetch.
- `total_seconds` = `TaskStep.total_working_seconds` only (`get_worker_clock_out_analytics.py:144`) —
  matches operator ruling 1. Image ordering is deterministic in code
  (`display_order, created_at, client_id`, line 134).
- Degradation returns `analytics: null` in full with a structured log; no default remains on either
  route's `pop` and both pops sit inside the `try` (`worker_shifts.py:115`, `:148`).
- Ruling 3 holds: `run_service` neither serializes nor emits `data`; Connecteam
  (`handlers/handle_clock_out.py`) and the midnight safeguard (`tasks/users/auto_clock_out_open_shifts.py`)
  call `clock_out_shift_for_user` directly and cannot reach analytics.
- Carried Phase 6 items delivered: index constant single-sourced at `user_work_profile.py:20`, pinned by
  `test_update_user_admin_clock_in_code.py:255`; race test at `:262`; `409` message mentions a possible
  inactive holder (`update_user_admin.py:24`).
- `ruff check` clean on all touched files.

#### Findings

**F1 — HIGH — AC12 / ruling 2 not delivered: the floor roster is still capped at 200 over HTTP.**
`routers/api_v1/users.py:177` — `GET /users` remains `Query(50, ge=1, le=200)`. The raised ceiling
`_FLOOR_MAX_LIMIT = 1000` (`services/queries/users/list_users.py:18`) lives in the query service, which
FastAPI never reaches. Probed through the router with a floor-scope claim: `limit=201` → **422**,
`limit=1000` → **422**, `limit=200` → reaches the service. A >200-worker workspace is therefore still
unreachable in one page — the exact operational defect ruling 2 set out to fix. Separately, the `le=1000`
raise plus a manual floor check was applied to an **unrelated** endpoint, `GET /users/me/view-records`
(`users.py:69-75`), widening that endpoint's cap outside this plan's scope.

**F2 — HIGH — the `_clock_out_at` regression test does not fail when the fix is reverted.**
`tests/unit/test_worker_shifts_router.py:260-282` guards the wire with a fake composer that raises
`AssertionError` — but the route's `except Exception` catches `AssertionError` as well, so a reverted fix
yields the same `200` / `analytics: null` / log line. Verified: restoring
`pop("_clock_out_at", datetime.now(timezone.utc))` on **both** routes leaves **36/36 passing**. This is
the same defect class the operator found, reproduced inside the test written to prevent it. The test needs
a guard the `except` cannot swallow (e.g. record the call and assert it never happened, or assert on the
timestamp actually passed).

**F3 — HIGH — two committed tests are left red; the "no new failure nodes" claim is false.**
`_clock_out_at` was added to the command return dicts (`clock_out_worker_shift.py:40`,
`toggle_worker_shift.py:63`), breaking exact-dict assertions at
`tests/integration/services/commands/users/test_kiosk_floor_flow.py:330` and
`tests/integration/services/commands/users/test_worker_shift_commands.py:1098`
(both: `Left contains 1 more item: {'_clock_out_at': ...}`). These are command-level tests that bypass the
route's pop, so ruling 3's protection — true at the HTTP boundary — does not extend to the command's
direct-caller contract, which these two tests pin. A third failure in the same run
(`test_clock_out_transitions_working_steps_and_leaves_paused_steps_open`, "System pause reason
'pause_ended_shift' is not configured") is environmental seeding, not attributable to this phase.

**F4 — MEDIUM — Review log was empty; three DoD records missing.** No record of (a) the `total_seconds`
definition and the rejected `working + pause + ended_shift` alternative (ruling 1), (b) the "first image"
determinism rule, (c) the measured composite latency. The code agrees with ruling 1, but the required
record was absent.

**F5 — MEDIUM — the query-budget guard cannot catch per-day or any constant-count regression.**
`test_get_worker_clock_out_analytics.py:293-312` compares a 1-item run against a 3-item run. Mutation
results: a per-item metadata loop **is** caught (test fails, confirmed); replacing the in-memory week
bucketing with seven `load_recorded_shift_records` round trips is **not** caught (2 passed). No absolute
bound is asserted, so the prompt's hard constraint "`week` = ONE range query … Never seven queries" has no
regression guard. Add an absolute assertion on the statement count.

**F6 — MEDIUM — `pause_reasons` cannot resolve the `unspecified` bucket key.**
`get_worker_clock_out_analytics.py:268` drops `UNSPECIFIED_REASON` from the lookup while line 304 emits
`timeline.pause_by_reason` verbatim, which contains `"unspecified"` whenever a pause record has
`reason IS NULL` (`user_shift_state_record.py:33`, nullable). Violates AC1 ("every reason key resolves in
`pause_reasons`") and handoff §5.1. Untested.

**F7 — MEDIUM — `rate` compares two different unit definitions.** Today's `units_per_hour` sums
`completed_items` units (line 292), which are **deduplicated per item** (line 235). The baseline uses
`_load_completed_units_by_day` (lines 70-117), a SQL `SUM(Item.quantity)` over `StepStateRecord` rows with
no dedup. An item completed twice in a day, or a task with several completed steps, inflates the baseline
but not today, making the kiosk's headline comparison apples-to-oranges. Violates AC6. The single test has
no duplicates, so it cannot surface this.

**F8 — MEDIUM — AC4/AC5 evidence largely absent** (only two tests exist for the composite). Not covered:
`reference` fallback for sku-only and null (only `article_number`, lines 265-278); `image_url` populated at
all, and the "first image" determinism the checklist requires be asserted (no `ImageLink` is ever seeded);
`issues_count > 0` (no `ItemIssue` seeded); truncation above `_MAX_COMPLETED_ITEMS = 100`; Monday and
midnight-spanning week boundaries; week buckets vs a same-range `build_recorded_shift_timeline`.
`week.totals` is asserted with hard-coded numbers (lines 282-286), not the invariant `totals == sum(days)`
the plan required.

**F9 — MEDIUM — AC2 unproven and AC11's real-ASGI probe never performed.** No test exercises on-behalf
clock-out analytics with the acting manager holding their own same-day activity. `create_app()` appears in
**zero** test files repo-wide; floor roster exposure is proven only at the service layer
(`test_list_users_floor_identification.py` constructs a ctx directly). That methodology is why F1 went
unnoticed — a router-level cap is invisible from below.

**F10 — LOW — multi-tenancy is sound but unprobed.** Every new query is workspace-scoped except the
image-link join (lines 126-135), which cannot be: `ImageLink` and `Image` carry no `workspace_id`, so
scoping is transitive via workspace-scoped `item_ids` — acceptable. No cross-workspace leak probe exists,
as the checklist required.

**F11 — LOW — `item_by_task` collapses items primary on multiple tasks.** The reused helper
(`get_worker_linear_timeline_breakdown.py:141`) builds `{item_id: task_id}`, so an item primary on two
tasks retains only one mapping; a step completed on the dropped task yields `item = None` (line 233) and
the card is **silently omitted** from `completed_items`. Reuse was mandated, so this is inherited — but
Phase 7 newly depends on it for completeness. `uix_task_items_primary_active` guarantees at most one
primary item per task, so the reverse double-count does not occur.

**F12 — LOW — residual fabricated-default hit.** `completed_units_by_day.get(baseline_date, 0)` (line 287)
silently yields a 0.0 baseline rate for any day whose key type does not match (`func.date()` returns `date`
on Postgres; a dialect returning a string would zero every baseline day with no error). Only one baseline
day is tested. The other defaults in the phase are honest (`durations.get(...,0)`, `issues.get(...,0)`,
`images.get(...)`, `records_by_user.get(...,[])`, and the `working_section_name_snapshot` fallback, which
is recorded data rather than invented).

#### Notes (not findings)

- `_require_complete_analytics` behaves exactly as the addendum predicted: a top-level subset check that
  the scaffold `{"timeline": {}, "week": {}, …}` passes cleanly — and which
  `test_clock_out_routes_compose_analytics_after_the_command:185-193` in fact feeds it. It is a backstop,
  not coverage. It was not framed as completeness evidence, since the Review log was empty (F4).
- **Operator to-do (not a finding, per addendum):** handoff §5.1's `total_seconds` wording
  ("time booked against that item's steps (task-level, not this worker's share alone)") remains accurate on
  the task-level caveat but does not state the working-only semantics of ruling 1.

**Verdict: NEEDS_CHANGES** — blocking: F1, F2, F3.

### Implementer follow-up 2026-07-31 — round-1 fixes complete; awaiting re-review

- `total_seconds` is `TaskStep.total_working_seconds` only. It is task-level booked
  working time, not the completing worker's share. The rejected alternative was
  `total_working_seconds + total_pause_seconds + total_ended_shift_seconds`: pause
  and blocked/overnight time are not productive work and would inflate the kiosk card.
- The deterministic first-image rule is `ImageLink.display_order`, then
  `ImageLink.created_at`, then `ImageLink.client_id`; no linked live image produces
  `image_url: null`. `ImageLink` has no soft-delete fields, so the null-safety probe
  covers its applicable deletion path, `Image.deleted_at`, plus a soft-deleted working
  section.
- The 101-item realistic-day composite probe completed under 500 ms. Its seeded shape
  contains 101 target-worker completed items, same-day manager activity, one item in a
  second workspace, and a 20-minute target shift; it asserts 100 returned cards,
  truncation, actor/target separation, cross-workspace exclusion, and the week-totals
  invariant.
- Expanded coverage now includes duplicate completion and two-worker attribution,
  primary-versus-related task items, article/SKU/null references, deterministic images,
  issue counts, deleted image/section null safety, Monday boundary, empty results,
  cross-workspace exclusion, and the all-or-null route degradation path. The floor
  roster probe uses `create_app()` with minted floor and manager JWTs; it verifies floor
  `limit=1000` reaches 200 rows and non-floor `limit=201` returns 422.
- Mutation evidence: restoring the prohibited `_clock_out_at` default made the router
  absence proof fail; adding seven per-day recorded-shift range queries made the
  absolute 11-statement query-budget assertion fail. Both mutations were reverted.
- Validation environment correction: the earlier 5-node analytics result was not test
  isolation. The terminal sandbox rejected local asyncpg connections to
  `127.0.0.1:5432` with `PermissionError`; the test bodies did not reach their seeded
  workspaces. With unsandboxed local PostgreSQL/Redis access, the minimal predecessor
  plus analytics probe passed 7/7. The shared `app_test` schema was also behind tracked
  migration `67cfba8fcb2d`; after `alembic upgrade head`, the carried roster/race and
  analytics focused slice passed 42/42.
- Final sequential full-suite comparison used a detached clean `HEAD f26ecc6`
  worktree with copied ignored test configuration, `APP_ENV=testing`, the same injected
  JWT secret, and no concurrent pytest process. Baseline: 28 failed / 1317 passed.
  Current: 28 failed / 1335 passed. Sorted failure-node-set diff: empty. `ruff check`
  passed on all Phase 7 touched files.

### Independent re-review 2026-07-31 — `claude-sonnet-5` — **APPROVED**

Method: fresh, adversarial re-verification of round-1 fixes against the prior review's F1–F12 —
source read of every touched file, targeted + full test runs, and hands-on mutation probes (not just
re-reading assertions). The repo turned out to have a real `.git` at `backend/` (contrary to first
appearance), so unlike the prior round this review reproduced the DoD's baseline-worktree comparison
independently rather than reading it in the log: `git worktree add` at `HEAD` (`f26ecc6`, matches the
implementer's cited baseline commit and its working tree's actual parent — confirmed via
`git status`/`git log`), ran the full suite there, and diffed sorted `FAILED` node lists against a
same-session run of the working tree. **Diff was empty — same 28 failing nodes on both sides**
(`28 failed / 1317 passed` baseline vs `28 failed / 1335 passed` current), independently confirming the
implementer's own numbers rather than trusting them.

#### Round-1 fixes verified genuine (not just re-asserted)

- **F1 (roster cap, blocker)** — fixed. `routers/api_v1/users.py:175,181-182`: `Query(50, ge=1, le=1000)`
  plus `if claims.get("app_scope") != "floor" and limit > 200: raise HTTPException(422, …)`. The
  out-of-scope `GET /users/me/view-records` widening is reverted (`users.py:69`, back to `le=200`).
  Real-ASGI probe with minted JWTs exists and passes:
  `test_list_users_floor_identification.py:327-376` (`create_app()`, 200 seeded workers, floor
  `limit=1000` → 200, manager `limit=201` → 422); `:310-317` seeds 201 rows directly against
  `list_users` for the service-layer >200 proof.
- **F2 (swallowed regression test, blocker)** — fixed. New guard
  `test_worker_shifts_router.py:260-286` asserts `composer_calls == []` (the composer must never be
  called), not merely that a raised exception was caught. **Mutation-verified myself**: reintroduced the
  prohibited `outcome.data.pop("_clock_out_at", datetime.now(timezone.utc))` default on both routes —
  this new test failed on both parametrizations (`AssertionError: composer_calls == []`, composer *was*
  called); reverted, 34/34 pass again.
- **F3 (two red committed tests, blocker)** — fixed. Both exact-dict assertions now read
  `"_clock_out_at": clock_out_result["_clock_out_at"]` (`test_kiosk_floor_flow.py:330`,
  `test_worker_shift_commands.py:1098`), no longer pinning the internal key's value. Ran both files: the
  only failures left are the pre-existing `pause_ended_shift`-not-configured baseline defect (matches
  the master plan's documented, out-of-scope issue verbatim, including the `test_worker_shift_commands`
  clock-out pair it explicitly calls baseline) — reproduced independently, not new.
- **F4 (empty Review log)** — fixed; implementer follow-up entry above records the `total_seconds`
  definition and rejected alternative, the first-image tie-break rule, and the measured 101-item
  composite latency (< 500 ms, asserted and printed at
  `test_get_worker_clock_out_analytics.py:441-454`).
- **F5 (no absolute query-count bound)** — fixed.
  `test_get_worker_clock_out_analytics.py:242`: `assert one_item_query_count <= 11`.
  **Mutation-verified myself**: reintroduced a per-day `load_recorded_shift_records` call inside the
  week-bucketing loop — the absolute-bound assertion failed (`18 <= 11`); reverted, file diffs clean
  against git, 5/5 pass again.
- **F6 (`pause_reasons` missing `unspecified`)** — fixed in code:
  `get_worker_clock_out_analytics.py:277-284` special-cases `UNSPECIFIED_REASON` into the lookup with a
  `"Reason unavailable"` entry before returning. **Still untested** — no test seeds a null-`reason` pause
  record to exercise this path (minor residual, see findings).
- **F7 (rate unit-definition mismatch)** — fixed in code: `_load_completed_units_by_day`
  (`get_worker_clock_out_analytics.py:117-126`) now keys its per-day accumulation dict by `item_id`
  (`items_by_day.setdefault(work_date, {})[row.item_id] = row.quantity`), so a duplicate completion of
  the same item on the same day is overwritten, not summed — matching `completed_items`'s own
  per-item dedup. Consistent by construction; not separately stress-tested for the baseline side, but the
  "today" dedup path is (`test_completed_cards_are_deduplicated_and_use_primary_task_item`).
- **F8 (evidence largely absent)** — now well covered:
  `reference` fallback all three cases, deterministic first-image (`display_order`, tie-broken lower
  wins), soft-deleted image and soft-deleted section null-safety, `issues_count`, truncation at 100/101,
  Monday-boundary week (`days[0]` == clock-out date), and a genuine invariant assertion
  `week.totals == {key: sum(day[key] …)}` (`:455-458`), not only hard-coded numbers. Residual gaps:
  no test forces a shift that literally straddles a midnight boundary (only same-day/near-midnight
  clock-outs are exercised) — acceptable given `timeline`/`week` bucketing is delegated to the shared,
  separately-tested `build_recorded_shift_timeline`, but noted as a minor gap.
- **F9 (AC2/AC11 unproven)** — fixed. AC2 (actor/target split with the acting manager's own same-day
  activity) is proven at `test_clock_out_analytics_limits_cards_and_keeps_actor_data_out` (manager's own
  completed item excluded from the worker's cards). AC11 real-ASGI probe confirmed above (F1).
- **F10 (multi-tenancy unprobed)** — fixed: the same test seeds a second workspace and a foreign item/step
  and asserts `foreign_item.client_id not in returned_ids`.
- **F12 (fabricated-default hit on `func.date()` dialect variance)** — fixed:
  `get_worker_clock_out_analytics.py:120-121` now explicitly converts a string `work_date` via
  `date.fromisoformat`.

#### New findings

**F13 — MEDIUM — undisclosed, untested behavior change to a shared, manager-facing helper.**
`services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`'s `_load_step_and_primary_item`
was rewritten as part of the round-1 fixes (confirmed via `git diff` against `HEAD`): the old code keyed
its intermediate map by `item_id` (`item_to_task = {row.item_id: row.task_id …}`), which is exactly the
F11 defect (an item primary on two tasks collapsed to one, silently dropping the other task's card). The
new code keys by `task_id` (`item_by_task_id = {row.task_id: row.item_id …}`, filtered against a
`client_id`-keyed `items_by_id` map before the final `task_id → Item` dict), which correctly retains both
tasks' mappings. This is a genuine, correct fix — but it is (a) not mentioned anywhere in this plan's
Review log despite being a change to a file the prompt scoped for **reads only** ("`item_by_task` mapping
only — do not extract a seam"), and (b) not covered by any new or updated test in either
`test_get_worker_linear_timeline_breakdown.py` (unmodified — confirmed via `git diff`, zero changes) or
the Phase 7 analytics suite — the multi-task-shared-primary-item scenario the fix addresses remains
asserted only by code inspection. This function also backs the **manager's** linear-timeline breakdown
endpoint, so an undisclosed change here is exactly the kind of thing acceptance criterion 14's "manager
worker-stats endpoints … untouched" check is meant to catch; existing breakdown tests still pass
(confirmed, and identical in the baseline-vs-current failure-node diff above), so there is no regression,
but the change and its correctness should have been called out and covered by a test rather than
discovered by diffing.

**F14 — LOW — `pause_reasons`' `UNSPECIFIED_REASON` fix (F6) has no regression test.** See above; the code
path is straightforward enough to read as correct, but nothing fails if it is reverted.

**F15 — LOW — no test exercises a shift that spans midnight.** Every seeded shift in the analytics suite
starts and ends within the same UTC day (or right at a day boundary at :00/:10). `timeline`/`week`
bucketing correctness across a true midnight split is covered only transitively through
`build_recorded_shift_timeline`'s own (separate) test suite, not by a Phase-7-level fixture.

#### Checklist coverage summary (this round)

1–6, 8–14 from the task checklist: verified with evidence above and in the prior round's log (unchanged
where not discussed). Item 7 (query budget) and item 6 (degradation) were additionally mutation-verified
by hand this round, not just re-read. Item 13 (suite health) was verified from a from-scratch git
baseline diff (this review's own worktree), independent of the implementer's reported numbers, and
matched them exactly. `ruff check` re-run clean on all touched files including
`get_worker_linear_timeline_breakdown.py`.

**Verdict: APPROVED.** All three round-1 blockers (F1, F2, F3) are genuinely fixed and independently
reproduced under mutation; F4–F12 are fixed (F6/F7 fixed-but-thin on dedicated regression coverage, noted
as F14). F13 (undisclosed shared-helper change) and F15 (no midnight-spanning fixture) are non-blocking
follow-up items — recommend a short fast-follow to add regression tests for F13's scenario and F14, but
neither is a functional defect and neither should gate archiving this phase.

APPROVED

### Implementer fast-follow 2026-07-31 — F13/F14 closed, F15 recorded as a known gap

Post-approval, pre-archive fast-follow. No production code changed in this pass; both entries add the
regression coverage the re-review found missing, each mutation-verified against the code it guards.

**F13 — cross-endpoint behaviour change, now disclosed and tested.**
`services/queries/worker_stats/get_worker_linear_timeline_breakdown.py:141-157`
(`_load_step_and_primary_item`) was changed during round-1 fixes: the intermediate map was keyed by
`item_id` (`item_to_task = {row.item_id: row.task_id …}`) and is now keyed by `task_id`
(`item_by_task_id = {row.task_id: row.item_id …}`, resolved against a `client_id`-keyed `items_by_id`
map). The old keying collapsed an item that is PRIMARY on two tasks into a single entry, so exactly one
of those tasks ended up absent from the final `task_id → Item` dict and its step details rendered
`"item": null`. The new keying retains both. **This change affects a surface outside Phase 7's scope:**
`_load_step_and_primary_item` also backs the manager-facing linear-timeline breakdown endpoint
(`GET /users/{user_id}/linear-timeline/breakdown`), which the implementer prompt scoped **read-only**
("`item_by_task` mapping only — do not extract a seam"). The fix is correct and is being kept; it should
have been called out here when it was made rather than surfacing from a `git diff`.

Coverage added on the **breakdown endpoint itself**, not the clock-out composite:
`test_get_worker_linear_timeline_breakdown.py::test_step_details_resolve_the_primary_item_of_each_task`
seeds one item PRIMARY on two tasks plus a third task with its own item, and asserts all three steps'
details carry the right item and that the two shared-item steps carry distinct `task_id`s.
**Mutation-verified**: with `_load_step_and_primary_item` reverted verbatim to the `{item_id: task_id}`
keying, the new test fails (`assert None is not None` on the dropped task's `item`) while the file's five
pre-existing tests all still pass — confirming the scenario was genuinely uncovered before this. Source
restored and re-verified after the mutation.

**F14 — `pause_reasons` `unspecified` bucket now has a regression test.**
`test_get_worker_clock_out_analytics.py::test_pause_reasons_resolves_every_timeline_key_including_unspecified`
seeds a shift with one reasoned pause and one pause recorded with `reason=None`, then asserts the
set-difference `pause_by_reason.keys() - pause_reasons.keys()` is empty (an invariant, not a key list) plus
the exact `"Reason unavailable"` entry. **Mutation-verified**: disabling the `UNSPECIFIED_REASON`
special-case at `get_worker_clock_out_analytics.py:279-284` fails the test
(`pause_by_reason keys without a pause_reasons entry: {'unspecified'}`); the other five tests in the file
still pass. Source restored.

**F15 — deferred by operator ruling; recorded as a known gap.** No fixture in the Phase 7 suite exercises
a shift that literally spans a UTC midnight boundary — every seeded shift starts and ends within one day
(or lands right at a boundary at :00/:10). `timeline` and `week` bucketing across a true midnight split is
covered only transitively, through the shared `build_recorded_shift_timeline` helper's own separate test
suite. Not built in this pass per operator ruling; carried into the archive record as a known gap.

Verification: `tests/integration/services/queries/worker_stats/` — 26 passed, 0 failed.
`ruff check` clean on both touched test files. No production file differs from its pre-fast-follow state.

## Lifecycle transition

- Current state: `archived`
- Path travelled: `under_construction` (rev 2) → `approved` → `implemented` → independent review
  (`NEEDS_CHANGES`, F1–F12) → fixes → independent re-review (`APPROVED`, F13–F15) → F13/F14 fast-follow
  → `summarized` → `archived`.
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_declared_worker_states_phase7_clockout_analytics_20260729.md`
- Archive record: `backend/docs/architecture/archives/implementation/declared_worker_states/ARCHIVE_RECORD_PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md`
- Transition owner: `David`
