# PLAN_worker_stats_endpoint_split_20260718

## Metadata

- Plan ID: `PLAN_worker_stats_endpoint_split_20260718`
- Status: `archived`
- Owner agent: `claude-opus-4-8` (plan) → `codex` (implementation)
- Created at (UTC): `2026-07-18T00:00:00Z`
- Last updated at (UTC): `2026-07-18T17:08:25Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`
- Precedes: `PLAN_inaccurate_time_estimation_strategies_20260718.md` (its Track C retargets onto the new `/totals` service after this split)

## Goal and intent

- **Goal:** Split the single `GET /api/v1/worker-stats/last-interacted-steps` endpoint (currently returning **three unrelated concerns** in one payload — the worker's last-interacted step, the worker's daily totals + live running, and the worker's insights) into **three focused, independently callable endpoints**, each a single-responsibility query service sharing one roster/pagination helper. The frontend composes them visually with parallel calls.
- **Business/user intent:** The three concerns have different **time models** and **refresh cadences**: the last step is a point-in-time "now" snapshot (no date range); totals are range-shaped aggregates (this is where the upcoming date-range + inaccurate-time work lands); insights have their own baseline window. Coupling them forces every cheap live refresh to recompute the expensive insights/estimates and blocks a coherent date-range API. Splitting lets each evolve, cache, and refresh on its own terms.
- **Non-goals:**
  - **No behavior change** to the underlying computations. This is an extract-and-split refactor: the last-step cohort/representative logic, the `daily_stats`/`running` computation, and `compute_worker_insights` are moved verbatim, not modified.
  - **No date-range** in this plan. Every new endpoint keeps the current single `work_date` (UTC-today fallback). Range is a *later* change on `/totals` (see the inaccurate-time plan sequencing).
  - No new tables, migrations, events, sockets, or workers. Read-only query surface only.
  - No changes to the existing drill-down `GET /worker-stats/{user_id}/daily-steps`.

## Sequencing note (cross-plan)

The **date-range** change that follows this split must apply to **`/totals` and `/{user_id}/daily-steps` together, as a pair** — the breakdown is the drill-down *behind* the totals, so a range on `/totals` with a single-day breakdown would not reconcile (drilling into a range must show the steps for that same range). Do not treat the breakdown as an afterthought when adding range.

Full order:
1. **This split** — no range; breakdown untouched (single `work_date` everywhere).
2. **Date-range** — applied to **both** `/totals` **and** `/{user_id}/daily-steps` in the same change; the median/IQR estimation *sample* window stays a fixed rolling lookback, decoupled from the view range (see `PLAN_inaccurate_time_estimation_strategies_20260718`).
3. **Inaccurate-time** (`PLAN_inaccurate_time_estimation_strategies_20260718`) Track C — lands on the now-range-aware `/totals` **and** the breakdown.

## Scope

- **In scope:**
  - Extract a shared roster helper (`_worker_membership_query`, `_worker_role_filter`, `_resolve_work_date`, pagination shape) out of `list_workers_last_interacted_step.py` into a reusable module.
  - Three query services + three router handlers:
    1. `list_workers_last_interacted_step` — slimmed to `user` + `last_interacted_step` + `batch`.
    2. `list_workers_totals` (new) — `user` + `daily_stats` + `running`.
    3. `list_workers_insights` (new) — `user` + `insights`.
  - Consistent envelope on all three: `{ "workers": [...], "workers_pagination": {...} }`, each item keyed by `user.client_id` so the frontend zips them.
  - Update handoff docs; add/adjust tests.
- **Out of scope:** anything under Non-goals; the inaccurate-time facts/estimation (separate plan); date-range.
- **Assumptions:**
  - `running` belongs with **totals**, not the last-step snapshot: it is the live add-on to settled `daily_stats` (`live = daily_stats + running`), as the running handoff already frames it.
  - The frontend is owner-controlled and will migrate to three parallel calls; a hard split (no compatibility shim) is acceptable given a handoff doc. (See Clarifications.)

## Clarifications required (resolved 2026-07-18)

- [x] **Compatibility window** — **Hard split**: remove `daily_stats`/`running`/`insights` from `/last-interacted-steps` in the same release the three endpoints ship; frontend migrates to three parallel calls. Covered by the handoff doc.
- [x] **URLs** — `GET /api/v1/worker-stats/totals` and `GET /api/v1/worker-stats/insights` (siblings of `/last-interacted-steps`).

## Acceptance criteria

1. `GET /worker-stats/last-interacted-steps` returns per worker only `{ user, last_interacted_step, batch }` + `workers_pagination`; no `daily_stats`, `running`, or `insights` keys.
2. `GET /worker-stats/totals` returns per worker `{ user, daily_stats, running }` + `workers_pagination`, with `running` today-only (zeros for a past `work_date`) — byte-identical values to what the combined endpoint produced for the same `work_date`.
3. `GET /worker-stats/insights` returns per worker `{ user, insights }` + `workers_pagination`, identical to the combined endpoint's `insights`.
4. All three share one roster/membership/pagination implementation (no duplicated `_worker_membership_query`), and the same pagination envelope + worker ordering (`username ASC`), so results zip by `user.client_id`.
5. All three are `ADMIN`/`MANAGER`-only; `401/403` unchanged; `422` on bad `work_date` unchanged.
6. Existing worker-stats tests updated to the new shapes and pass; ruff clean; app imports; all three routes register.

## Contracts and skills

> Read order per `task_system/backend_contract_goal_mapping_guide.md`: canonical first, then `*_local.md` companion; local overrides baseline for this app only.

### Contracts loaded

**Selected core (always):**
- `backend/architecture/01_architecture.md`: layering (router → query service → domain serializer).
- `backend/architecture/04_context.md`: `ServiceContext` / identity / `query_params`.
- `backend/architecture/05_errors.md`: `ValidationError` → `422` on `work_date`.
- `backend/architecture/07_queries.md` + `07_queries_local.md`: query services return already-serialized dicts; **offset** pagination (local overrides cursor) — the shared envelope.
- `backend/architecture/09_routers.md`: handler wiring, `require_roles([ADMIN, MANAGER])`, `build_ok`/`build_err`.
- `backend/architecture/21_naming_conventions.md`: service/module/route naming.
- `backend/architecture/40_identity.md`, `41_user.md`: `serialize_user_worker_stat`, worker identity.

**Added from guide (goal-driven):**
- `backend/architecture/08_domain.md`: serializers are pure domain (reused as-is: `serialize_insight`, `serialize_user_daily_work_stats`, `build_running_totals_averaged`).
- `backend/architecture/46_serialization.md`: the three response shapes.
- `backend/architecture/15_testing.md`: split test files; deterministic DB fixtures.

**Local extensions loaded:**
- `07_queries_local.md`: offset pagination (not cursor) — the `workers_pagination` envelope stays `{has_more, limit, offset, total}`.
- `06_commands_local.md`: N/A (no commands in this refactor) — loaded per core rule, not exercised.

**Excluded contracts:**
- `03_models.md`, `30_migrations.md`: no schema change.
- `16/51/52 (workers/replay)`, `11/13 (events/sockets)`, `12 (redis)`: read-only endpoints, no async/side-effects.
- `55 (search/date-filter)`: no range/filter added in this phase (deferred to the range change).

### File read intent — pattern vs. relational

Relational reads done (what exists): `list_workers_last_interacted_step.py`, `routers/api_v1/worker_stats.py`, `services/queries/analytics/compute_worker_insights.py`, `domain/analytics/serializers.py`, `domain/users/serializers.py`, `services/queries/working_sections/step_record_payload.py`. No pattern reads needed — the contracts above define "how to write."

### Skill selection

- Primary skill: `—` (follow contracts directly).
- Router trigger terms: `worker-stats, query, split, roster`.
- Excluded alternatives: `—`.

## Implementation plan

1. **Extract the shared roster module** — new `app/beyo_manager/services/queries/worker_stats/_roster.py`:
   - Move `_worker_role_filter`, `_worker_membership_query(ctx, columns)`, `_resolve_work_date`, and the constants `_MAX_LIMIT`/`_DEFAULT_LIMIT`/`_TIME_STATES`.
   - Add a small helper `load_worker_page(ctx) -> tuple[list[User], PaginationDict]` that runs the count + the `username ASC` offset page (`limit+1` has_more probe) and returns the workers + the `workers_pagination` dict. All three services call this so ordering/pagination are identical.
2. **Slim `list_workers_last_interacted_step.py`** — keep only: page load (via `_roster`), the latest-record CTE / cohort-rank / representative-state logic, `load_step_with_latest_record` + `build_step_record_payload(..., include_cases_summary=False)`, and the `batch` descriptor. Return per worker `{ user, last_interacted_step, batch }`. Remove the `daily_stats`, `running`, and `insights` code paths + their imports.
3. **New `list_workers_totals.py`** — page load (via `_roster`), then the moved `UserDailyWorkStats` select → `serialize_user_daily_work_stats` and the today-only `running` computation (open-record probe + per-active-worker `compute_record_contributions` + `build_running_totals_averaged`). Return per worker `{ user, daily_stats, running }`. Values must match the combined endpoint exactly.
4. **New `list_workers_insights.py`** — page load (via `_roster`), then `compute_worker_insights(ctx, worker_ids, work_date)` → `serialize_insight`. Return per worker `{ user, insights }`.
5. **Router** — `routers/api_v1/worker_stats.py`: keep `get_workers_last_interacted_step_route` (now slimmer); add `get_workers_totals_route` (`GET /totals`) and `get_workers_insights_route` (`GET /insights`), same `require_roles`, `limit`/`offset`/`work_date` params, same `ServiceContext` construction, `build_ok(outcome.data)`. Register both.
6. **Update `__init__.py`** exports if the package re-exports service functions.
7. **Handoff docs** — update `HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`: last-interacted-steps now returns only step+batch; add short handoffs (or sections) for `/totals` (daily_stats + running; live = daily_stats + running) and `/insights`. State the frontend makes three parallel calls and zips by `user.client_id`.
8. **Tests** — split the existing worker-stats roster test into three; assert each endpoint's shape, shared ordering/pagination, `ADMIN`/`MANAGER` gating, and that `/totals` running is zero for a past `work_date`. Reuse the existing DB seed helpers.

## Risks and mitigations

- **Risk:** Breaking change to the frontend (fields removed from `/last-interacted-steps`).
  Mitigation: owner-controlled FE + handoff doc; if a window is needed, Clarification allows keeping the combined endpoint temporarily as deprecated (add-only) instead of hard split.
- **Risk:** Behavioral drift while moving `running`/`daily_stats`/insights code.
  Mitigation: move verbatim; acceptance criteria require byte-identical values vs. the combined endpoint for the same `work_date`; keep the existing sweep/insights callees untouched.
- **Risk:** Ordering/pagination divergence across the three (frontend can't zip).
  Mitigation: single `load_worker_page` helper is the only source of the worker list + envelope; all three consume it.
- **Risk:** Three calls add latency.
  Mitigation: they're list endpoints; frontend fires them in parallel (latency ≈ max, not sum) — noted in the handoff.

## Validation plan

- `pytest` (worker-stats suites): three endpoints return the split shapes; `/totals` values equal pre-split values for a fixed `work_date`; `/totals` running zero on a past date; gating + `422` preserved.
- `ruff check` clean on new/touched files.
- `python -c "import app..."` app import; assert all three routes registered under `/api/v1/worker-stats`.
- Manual/rough: same `work_date` across the three yields the same worker set/order.

## Review log

- `2026-07-18` owner: initial draft; compatibility window and URLs clarified before implementation.
- `2026-07-18` codex: implemented the split, added focused shape/route tests, updated frontend handoffs, and validated with unit tests, Ruff, compilation, and route registration. The DB-backed daily-step regression was attempted but blocked by stale test-schema drift (`workspace_roles.specialization` is missing).

## Implementation outcome

- Shared worker roster, role filter, pagination, and date validation moved to `app/beyo_manager/services/queries/worker_stats/_roster.py`.
- `/last-interacted-steps` now returns only `user`, `last_interacted_step`, and `batch` per worker.
- `/totals` now returns `user`, `daily_stats`, and `running` per worker.
- `/insights` now returns `user` and `insights` per worker.
- The existing `/{user_id}/daily-steps` route was left unchanged.
- Frontend handoff documentation and intention-plan progress were updated.

## Lifecycle transition

- Current state: `archived`
- Previous state: `under_construction`
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_endpoint_split_20260718.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_stats_endpoint_split_20260718.md`
