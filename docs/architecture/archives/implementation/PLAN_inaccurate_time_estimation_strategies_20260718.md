# PLAN_inaccurate_time_estimation_strategies_20260718

## Metadata

- Plan ID: `PLAN_inaccurate_time_estimation_strategies_20260718`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-18T00:00:00Z`
- Last updated at (UTC): `2026-07-18T18:56:00Z`
- Related issue/ticket: `—`

## Goal and intent

- **Goal:** Make the time recorded on records flagged inaccurate (`recorded_time_marked_wrong = true`) usable again. Persist the *discarded* ("wasted") time as a first-class fact next to the trusted totals, and expose a read-time **estimation** of it via user-selectable statistical strategies (mean / median / IQR-trimmed mean), so a manager can view **trusted-only**, **wasted-only**, or **trusted + estimated** totals.
- **Business/user intent:**
  - On `GET /worker-stats/totals` (`list_workers_totals` — the split's roster totals service): return, per worker, a **usable working/paused total** = trusted + a chosen strategy's fill, alongside the raw trusted and wasted numbers, so the frontend can render all three views.
  - On `get_worker_daily_step_breakdown_route` (drill-down): surface the **flagged steps** (with `is_time_inaccurate`, their wasted time, and the underlying time-bearing records) and show **how each strategy (mean/median/IQR) would contribute** to the patched value, per step.
  - The **frontend performs the final sum** — the backend returns the components (trusted, wasted, estimated-fill), never a single opinionated "real" total.
- **Non-goals:**
  - Changing trusted semantics **for non-flagged steps**. Trusted stays exactly as today for any step/worker with no flagged steps (deterministic, idempotent projection). Flagged steps **do** change — their *whole* time now leaves trusted (see "Inaccuracy is step-grained"); that is an intended correctness fix applied by the backfill, not a behavior we preserve.
  - Wiring the standalone `mark_step_time_inaccurate` (CMD-13) endpoint into the analytics reconcile flow. That drift is known and deliberately deferred (owner decision) to a later pass; this plan assumes flags are set on the transition path (which already reconciles) or corrected by the backfill.
  - Costing inaccurate/estimated time. Cost (`total_cost_minor`) stays trusted-only.
  - Any frontend summation logic (frontend owns it).

## Scope

- **In scope:**
  - New persisted **facts** — `inaccurate_*_seconds` + `inaccurate_step_count` on the four analytics tables, and `inaccurate_*_seconds` on `TaskStep` (its inaccurate boolean already exists) — computed from records by the existing reconcile/step-recompute path and the backfill.
  - A pure-domain **estimation** package (strategies: `mean`, `median`, `iqr`) + a read-time IO primitive to load the trusted-duration sample for median/IQR.
  - Extending both worker-stats query services + serializers + router params to expose trusted / wasted / estimated components.
  - Migration (columns + a partial index on flagged records), backfill extension, tests, handoff docs.
- **Out of scope:** anything under Non-goals; changing the roster/breakdown existing shapes beyond additive fields; new endpoints.
- **Assumptions:**
  - "Wasted" = the concurrency-averaged time of **flagged steps** (all time-bearing records of any step whose `recorded_time_marked_wrong` is set), computed via a flagged-only sweep. A flagged step contributes its whole averaged time to wasted and `0` to trusted. Trusted-view and wasted-view are alternatives the frontend never sums together.
  - The estimate is **policy**, not fact → it is computed at read, never materialized. Facts (trusted totals, wasted totals, flagged step counts) are materialized so big windows stay cheap.

## Inaccuracy is step-grained (2026-07-18 correction — authoritative)

In practice "mark time inaccurate" is only ever used **at step completion**, which flags the **whole step** (`step.recorded_time_marked_wrong = True`). Per-record marking is **not** used and won't be for the foreseeable future. So inaccuracy is a **step-level** property, and this plan treats it as such (this section overrides any narrower record-level wording elsewhere in the plan):

- **Read side keys off the step flag.** In `compute_record_contributions`, a record counts as inaccurate when `record.recorded_time_marked_wrong OR TaskStep.recorded_time_marked_wrong` (the `TaskStep` is already joined). This propagates a completion-time mark to **all** of the step's time-bearing records — so the *entire* step's time is wasted, not just the closing interval. (Marking at completion currently flags only the closing record at the record level; keying off the step flag is what makes "whole step inaccurate" true.)
- **A flagged step is binary:** `trusted = 0`, `wasted = the step's full concurrency-averaged time` (per state). Its records never split between trusted and wasted.
- **Counts are step counts.** Materialize/expose `inaccurate_step_count` (distinct flagged steps) instead of per-record counts; the breakdown carries a per-step `is_time_inaccurate` boolean (reuse `TaskStep.recorded_time_marked_wrong`). Note it is bucketed **per UTC day** like the time facts, so a step whose flagged records straddle midnight counts once per day it touched (v1 approximation; consistent with per-day time bucketing).
- **Estimation is per-step.** The fill replaces each flagged **step** with a typical step duration: `fill_state = inaccurate_step_count × strategy(sample of trusted per-step <state> durations in that section)`. `mean` stays free from stored aggregates (`Σ trusted_<state>_seconds ÷ (Σ total_completed_count − Σ inaccurate_step_count)` ≈ avg <state> time per **trusted completed** step); **guard the denominator: `≤ 0` → fill `0`** (no trusted step to estimate from). `median`/`iqr` pull per-step trusted durations over the lookback, counting **only steps with `> 0` in that state** (a step that never paused is not evidence of a typical pause duration).
- **Consequence for trusted:** this **moves trusted totals for already-flagged steps** (they currently exclude only the closing record; now they exclude the whole step) — a correctness fix applied by the backfill. Trusted is unchanged for any worker/step with **no** flagged steps; that is the regression gate.

## Clarifications required (resolved 2026-07-18)

- [x] **Strategy exposure** — Roster takes `?time_strategy=mean|median|iqr` (default `mean`, free) and returns a single `estimated_fill`. Breakdown returns **all three** per step (`estimated_fill_by_strategy`) for side-by-side comparison, plus a top-level usable total honoring `time_strategy`.
- [x] **Sample grain + lookback** — the sample is **per-trusted-step durations** at grain `worker × section × state` (each sample point = one non-flagged completed step's total averaged `<state>` seconds, **counting only steps with `> 0` in that state**), over a rolling `ESTIMATION_LOOKBACK_DAYS = 28` window ending at the range end (`date_to`); sample size `< ESTIMATION_MIN_SAMPLE = 4` → fall back to the worker's **mean** (from stored aggregates; denominator-guarded). No cross-user/section-wide sample in v1.
- [x] **IQR strategy** — "IQR-trimmed mean": drop values outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]`, average the rest (empty result → `0.0`).

## Sequencing note (cross-plan)

Both prerequisites are now **implemented** — this plan is unblocked:
1. ✅ **`PLAN_worker_stats_endpoint_split_20260718`** (done) — split the roster into `/last-interacted-steps`, `/totals`, `/insights`. Track C of *this* plan targets the **`/totals`** service (`list_workers_totals`) and the breakdown, never the last-interacted-steps service.
2. ✅ **Date-range change** (done) — `/totals` and `/{user_id}/daily-steps` now take `date_from`/`date_to` (inclusive, default today→today; `work_date` removed on those two). `daily_stats` on `/totals` is now a **range summary** `{date_from, date_to, total_*}` (summed), and the breakdown's top-level `work_date` became `date_from`/`date_to`. **Track C must add its `time_quality`/`estimated_fill` fields onto these range shapes**, and read `inaccurate_step_count` + `inaccurate_*_seconds` summed over the range (same as trusted). Track A (facts) and Track B (estimation) are view-agnostic and unaffected.

Range interaction (still holds): trusted/wasted/counts are **summed per-day-row** over the range (cheap) and the `mean` fill stays derivable from summed aggregates — **but the range totals query in `list_workers_totals` currently sums only `working/pause/completed`; Track C must also sum `total_completed_count` + the `*_count` columns (needed for the mean = Σseconds/Σcount) and the new `inaccurate_*_seconds`/`inaccurate_step_count`**. The **median/IQR sample window is a fixed rolling `ESTIMATION_LOOKBACK_DAYS` lookback ending at the range's end date (`date_to`) — decoupled from the view range** (so estimate quality/cost don't swing with how wide a range the manager views); only the `inaccurate_step_count` multiplier comes from the view range.

## Acceptance criteria

1. A **flagged** step whose whole averaged working time is D produces `inaccurate_working_seconds ≈ D`, contributes `0` to `total_working_seconds` (trusted), and increments `inaccurate_step_count` by 1 on `user_daily_work_stats`, the Σ tables, and the step's own `TaskStep.inaccurate_working_seconds` — while trusted totals for **non-flagged** steps are byte-identical to today.
2. `reconcile_user_day_time` is still idempotent: running it twice yields identical trusted **and** inaccurate values on all tables.
3. `/totals` returns, per worker, `trusted` (existing), `wasted`, `inaccurate_step_count`, and `estimated_fill` (for the requested `time_strategy`) for working + paused; with `time_strategy=mean` no per-worker record scan is issued (fill = `inaccurate_step_count × Σtrusted_seconds/(Σcompleted − Σinaccurate_step_count)`, all from the range-grouped aggregate query; **denominator `≤ 0` → fill `0`**).
4. Breakdown returns, per step, `is_time_inaccurate`, its `wasted` (whole-step averaged time), `estimated_fill_by_strategy` (mean/median/iqr), and a light list of the step's time-bearing records; plus top-level `wasted`/`estimated` totals and an `inaccurate_step_count`. An `only_inaccurate` intention returns only the flagged steps.
5. Strategy functions are pure and unit-tested (mean/median/IQR on known samples, empty-sample → 0, single-value, outlier trimming).
6. Backfill rebuilds `inaccurate_*` alongside trusted; `alembic upgrade head` / `downgrade` round-trips; ruff clean; single alembic head; app + worker + backfill import cleanly.

## Contracts and skills

### Contracts loaded

- `backend/architecture/08_domain.md`: pure estimation strategies + the sweep refactor (no IO in domain).
- `backend/architecture/07_queries.md` + `07_queries_local.md`: the read-time sample loader and the two query-service extensions (module returns serialized dicts).
- `backend/architecture/16_background_jobs.md` + `51_worker_runtime.md` + `52_replayability.md`: reconcile/step-recompute stay a deterministic idempotent projection.
- `backend/architecture/53_operational_cli.md`: backfill extension (dry-run default).
- `backend/architecture/46_serialization.md`: additive serializer fields.
- `backend/architecture/03_models.md` + `30_migrations.md`: new mixin/columns + partial index migration.
- `backend/architecture/09_routers.md`: new query params on the two routes.
- `backend/architecture/15_testing.md`: unit (domain) + integration (reconcile/endpoints) split.
- `task_system/backend_contract_goal_mapping_guide.md`: goal → contract mapping.

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: query services return already-serialized dicts via domain serializers; router just `build_ok(outcome.data)`.

### File read intent — pattern vs. relational

Relational reads already done (existing behavior / field names): `domain/analytics/concurrency.py`, `services/queries/analytics/averaged_time.py`, `services/queries/analytics/reconcile_user_time.py`, `services/tasks/analytics/process_step_transition.py`, both `worker_stats` query services, `domain/analytics/serializers.py`, `models/base/aggregate_metrics.py`, `models/tables/analytics/*`, `models/tables/tasks/{step_state_record,task_step}.py`, `routers/api_v1/worker_stats.py`, `scripts/backfill/backfill_averaged_time.py`. No pattern reads required — contracts cover the "how to write."

### Skill selection

- Primary skill: `—` (follow the architecture contracts directly, as with the batch-averaging plan).
- Router trigger terms: `analytics, reconcile, estimation, worker-stats`.
- Excluded alternatives: `—`.

## Implementation plan

### A. Facts (persist the wasted time)

1. **Sweep refactor (pure)** — `domain/analytics/concurrency.py`: extract the per-state sweep into `_sweep(intervals, now) -> dict[record_id, float]` (no marked filtering). Keep `averaged_seconds_by_record` = `_sweep(non-marked)` (unchanged behavior/trusted). Add `wasted_seconds_by_record(intervals, now) = _sweep(marked-only)`. New unit tests for the wasted path (batch-of-N flagged → sums to D; lone flagged → full duration).
2. **Reconstruct primitive** — `services/queries/analytics/averaged_time.py`: also select `TaskStep.recorded_time_marked_wrong`; build each `TimeInterval` with **`marked_wrong = record.recorded_time_marked_wrong OR TaskStep.recorded_time_marked_wrong`** (step-grained — see "Inaccuracy is step-grained"). Add `wasted_seconds: float` and `marked_wrong: bool` to `RecordContribution`; compute both `averaged_seconds_by_record` (→ trusted `seconds`) and `wasted_seconds_by_record` (→ `wasted_seconds`) from the already-fetched rows (no extra query).
3. **Columns** — new mixin `AggregateMetricsInaccurateTimeMixin` in `models/base/aggregate_metrics.py`: `inaccurate_{working,pause,ended_shift}_seconds` (wasted per state) **plus a single `inaccurate_step_count`** (distinct flagged steps — not per-record counts) (Integer, default 0, `server_default="0"`). Add the mixin to `UserDailyWorkStats`, `UserSectionDailyWorkStats`, `UserLifetimeStats`, `WorkingSectionDailyWorkStats`. On `TaskStep` add only the three `inaccurate_*_seconds` columns — its "is inaccurate" boolean already exists (`TaskStep.recorded_time_marked_wrong`), and its trusted `total_*_seconds` go to `0` when flagged.
4. **Reconcile** — `services/queries/analytics/reconcile_user_time.py`: extend `_TimeTotals` with the three `inaccurate_*_seconds` + `inaccurate_step_count`; `_snapshot`/`_apply_set`/`_apply_delta`/`as_delta` cover them; in `reconcile_user_day_time` accumulate settled flagged records' `wasted_seconds` into `inaccurate_*_seconds` and count **distinct flagged `step_id`s** into `inaccurate_step_count` (per-day + per-section), SET on the daily rows, delta to the Σ tables. Inaccurate time is **not** costed.
5. **Step recompute** — `services/tasks/analytics/process_step_transition.py::_recompute_step_time_totals`: set `TaskStep.inaccurate_*_seconds` from the step's `wasted_seconds`; when the step is flagged its trusted `total_*_seconds` compute to `0` (its records are all `marked_wrong` via the step flag).
6. **Migration** — one revision (branch off the verified `alembic heads`, do not hardcode): add the 4 columns (`inaccurate_{working,pause,ended_shift}_seconds` + `inaccurate_step_count`) to the 4 analytics tables and the 3 `inaccurate_*_seconds` columns to `TaskStep`; add a **partial index** `... ON step_state_records (workspace_id, COALESCE(credited_user_id, created_by_id), entered_at) WHERE recorded_time_marked_wrong` for fast flagged pulls. Reversible `downgrade`.
7. **Backfill** — `scripts/backfill/backfill_averaged_time.py`: zero + rebuild `inaccurate_*_seconds`/`inaccurate_step_count` **and** re-derive trusted `total_*` (which now drop to `0` for flagged steps) — same absolute-SET, idempotent shape. This is the run that applies the whole-step correction to history.

### B. Estimation (read-time policy)

8. **Strategy domain** — new package `domain/analytics/estimation/`: `strategies.py` with pure `mean(sample)`, `median(sample)`, `iqr_trimmed_mean(sample)` (each `list[float] -> float`, empty → `0.0`); a `TimeEstimationStrategy` enum (`mean|median|iqr`) + a `resolve(strategy)` registry. `estimate_fill(step_count, per_step_value) -> float` (= `step_count × per_step_value`).
9. **Sample loader (IO)** — `services/queries/analytics/estimation_sample.py`: `load_trusted_step_duration_sample(session, workspace_id, user_id, window_start, window_end, now) -> dict[(section_id, state), list[float]]` — via `compute_record_contributions` (settled, not open, not flagged), **summed per (step, state)** so each sample point is one trusted completed step's total `<state>` seconds, then bucketed by `(section, state)`. Used only for `median`/`iqr`. `mean` needs no sample (derived from stored aggregates). Constants `ESTIMATION_LOOKBACK_DAYS`, `ESTIMATION_MIN_SAMPLE`; sub-`MIN_SAMPLE` → fall back to stored mean.

### C. Endpoints (expose components)

10. **Serializers** — `domain/analytics/serializers.py`: add `serialize_time_quality(trusted, wasted, inaccurate_step_count, estimated_fill)` and a `serialize_estimated_fill_by_strategy(...)` helper (breakdown). Additive only.
11. **Roster/totals** — target the **`list_workers_totals`** service (`GET /worker-stats/totals`; split + range already landed). Its `daily_stats` is a **range-grouped `SUM` per worker** over `[date_from, date_to]`; extend that same grouped query to also `SUM` `total_completed_count`, the new `inaccurate_*_seconds`, and `inaccurate_step_count`. Compute `estimated_fill` for the requested `time_strategy`: `mean` = `Σ inaccurate_step_count × (Σ trusted_<state>_seconds ÷ (Σ total_completed_count − Σ inaccurate_step_count))` at worker level, all from that one grouped query (no per-worker record scan); `median`/`iqr` via one `load_trusted_step_duration_sample` per active worker (lookback ends at `date_to`). Serialize a `time_quality` block per worker (`trusted`/`wasted`/`inaccurate_step_count`/`estimated_fill` for working + paused) onto the existing range `daily_stats` shape. Router: add `time_strategy: str = Query("mean")`.
12. **Breakdown** — `services/queries/worker_stats/get_worker_daily_step_breakdown.py` (already range-aware via `date_from`/`date_to`): per step add `is_time_inaccurate` (= `TaskStep.recorded_time_marked_wrong`), `wasted` (the step's whole averaged time when flagged — from `compute_record_contributions` `wasted_seconds`, bucketed like the trusted `contribution` with the same `date_from <= entered_at.date() <= date_to` filter), `estimated_fill_by_strategy` (all three; per-step sample pulled once for this worker, lookback ends at `date_to`), and `inaccurate_records: [...]` (light: `record_id, state, entered_at, exited_at, wasted_seconds` — the flagged step's time-bearing records, so a manager can inspect what was logged). A flagged step therefore shows `contribution` all-zero + `wasted` full. Top-level `wasted`/`estimated` totals + `inaccurate_step_count` alongside the existing range `totals`/`daily_stats`. Add an `only_inaccurate` filter intention (returns only steps where `is_time_inaccurate`). Router: add `time_strategy` (top-level usable total) and the filter param.
13. **Remove the TEMP MOCK blocks** in both services if still present, replacing mock estimation with the real path.

### D. Docs & validation

14. **Handoffs** — write a **new** handoff (per the convention of not editing prior ones) for the `/totals` and `/{user_id}/daily-steps` additions: the new `time_quality` / `estimated_fill(_by_strategy)` / `inaccurate_records` fields layered onto the **range** shapes from `HANDOFF_TO_FRONTEND_worker_stats_date_range_20260718.md`, the "frontend does the sum: trusted | wasted | trusted+estimated" contract, and the `time_strategy` param + defaults. (Do **not** target the last-interacted-steps handoff — that endpoint no longer carries totals.)
15. **Tests** — unit: strategy functions + `wasted_seconds_by_record`. Integration: reconcile with a **flagged step** → its whole averaged time moves trusted→`inaccurate_*_seconds`, `inaccurate_step_count` increments, idempotent; a dataset with **no** flagged steps yields byte-identical trusted totals (regression gate); step recompute (`TaskStep.total_*=0`, `inaccurate_*_seconds=full`); both endpoints (mean fill from the grouped aggregate query issues no sample query; median/iqr per-step sample path; `only_inaccurate` filter; `is_time_inaccurate` per step).

## Risks and mitigations

- **Risk:** median/IQR sample pulls on a large roster (one per worker) get expensive.
  **Mitigation:** `mean` is the default and is derived from stored aggregates (zero record scans); median/iqr are opt-in via `time_strategy`; the partial flagged index + bounded lookback keep each pull cheap; a short-TTL response cache can be added if a view proves hot.
- **Risk:** "wasted" semantics (whole flagged step, flagged-only sweep) confuse consumers into summing trusted + wasted.
  **Mitigation:** handoff states explicitly that the three views are alternatives; the usable total is trusted + **estimated**, never trusted + wasted. A flagged step is `trusted=0`/`wasted=full`, so no per-step double-count is possible.
- **Risk:** column sprawl / migration on 5 tables.
  **Mitigation:** single shared mixin + one migration; all columns default 0 with `server_default` so existing rows are valid pre-backfill.
- **Risk:** trusted totals for **non-flagged** steps accidentally change during the refactor. (Trusted for *flagged* steps is intended to change — whole step now excluded.)
  **Mitigation:** the pure `averaged_seconds_by_record` keeps identical filtering; the step-flag OR happens only in the IO layer building `TimeInterval`. A dataset with **no flagged steps** must yield byte-identical trusted totals — the existing concurrency + reconcile integration tests (all unflagged) are the regression gate; add a paired test proving a flagged step moves its whole time trusted→wasted.
- **Risk:** stored `inaccurate_*` drifts when the standalone mark endpoint is used (still no reconcile — deferred).
  **Mitigation:** documented Non-goal; the backfill corrects it; breakdown's live per-step path already reflects flags immediately.

## Validation plan

- `pytest app/tests/unit/domain/analytics` : strategy + sweep unit tests pass; existing concurrency tests unchanged.
- `pytest app/tests/integration/services/queries/analytics/test_reconcile_user_time.py` : trusted identical to today for **unflagged** data; a **flagged step** moves its whole time to `inaccurate_*_seconds` (+`inaccurate_step_count`), trusted → 0; idempotency holds.
- `pytest` (worker-stats integration) : roster `mean` path issues no per-worker sample query; median/iqr + `only_inaccurate` behave.
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` : clean round-trip; `alembic heads` shows the intended single head.
- `ruff check` clean on new/touched files; `python -c "import app..."` for app, worker, backfill entrypoints.

## Review log

- `2026-07-18` owner: initial draft pending answers to the three Clarifications.
- `2026-07-18` owner: three Clarifications resolved (mean-default/all-three; worker×section×28d/mean-fallback; IQR-trimmed mean).
- `2026-07-18` owner: reconciled against the now-landed split + date-range work — Track C retargeted to `list_workers_totals` (range-grouped `SUM`, must also sum `*_count` + `inaccurate_*`), breakdown noted range-aware, Track D handoff retargeted to `/totals` + breakdown (new handoff). No open decisions remain; ready for implementation.
- `2026-07-18` owner: **step-grained correction** — marking is only ever whole-step at completion, so inaccuracy keys off `TaskStep.recorded_time_marked_wrong` (OR'd in `compute_record_contributions`); a flagged step is `trusted=0`/`wasted=full`; counts became `inaccurate_step_count` + per-step `is_time_inaccurate`; estimation moved to per-step durations (`mean` still free); trusted now changes for flagged steps (backfill-applied), regression gate = unchanged for unflagged. Updated the new "Inaccuracy is step-grained" section, non-goal/assumptions, sample-grain clarification, acceptance 1/3/4, Track A 2–7, Track B 8–9, Track C 10–12, risks, tests, validation.
- `2026-07-18` owner: final consistency pass — restored `inaccurate_records` list in Track C step 12 (was referenced by acceptance #4/Track D but dropped); added the **mean denominator `≤0 → 0` guard**; the per-state median/IQR sample now counts **only steps with `>0` in that state** (pause zeros were skewing it); noted `inaccurate_step_count` is per-UTC-day bucketed (cross-midnight steps count per day); de-staled `inaccurate_*_count`→`inaccurate_step_count` in the sequencing note and reframed the Goal to step-oriented. No open decisions remain.
- `2026-07-18` implementation complete: persisted inaccurate facts, step-grained trusted/wasted sweep, pure mean/median/IQR estimation, range-aware worker-stats fields and filters, reversible migration, backfill extension, tests, summary, and frontend handoff completed. Migration `74f152a8b9d1` is the single Alembic head.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `claude-opus-4-8`
