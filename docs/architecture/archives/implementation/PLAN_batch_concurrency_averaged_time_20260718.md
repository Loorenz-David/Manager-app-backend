# PLAN_batch_concurrency_averaged_time_20260718

## Metadata

- Plan ID: `PLAN_batch_concurrency_averaged_time_20260718`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-18T10:00:00Z`
- Last updated at (UTC): `2026-07-18T11:30:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`
- Related: analytics pipeline (`process_step_transition`), worker-stats endpoints, `PLAN_worker_daily_step_breakdown_20260716`

## Goal and intent

- Goal: Fix time accounting for **batch-worked** steps. When multiple steps are worked concurrently (batchable working sections), each moment of real time must be **divided by the number of concurrently-open steps in that state** — so the per-step time is the fair average and the steps sum back to the real wall-clock time, instead of each booking the full interval (today's N× over-count).
- Business/user intent: The point of batching is throughput — a worker runs N steps at once, and the real time is shared across them. Stats (worked/paused/ended-shift seconds) must reflect that. Sections can become batchable or not at any time; the fix must stay correct across that toggle and across mid-batch drift (start another step, pause one, complete some-not-all).
- **Reconstructability is a first-class requirement**: the aggregates must be a **deterministic, idempotent projection of the raw `step_state_records`** — recomputing from records always yields the same stats.
- Non-goals:
  - No change to completion **counts** (1 per completed step regardless of batch — already correct).
  - No change to cost/issue metrics semantics (cost still derives from booked seconds; it inherits the corrected seconds).
  - Not introducing a stored "batch id / batch size" — concurrency is derived from actual record overlap (see rationale).

## Scope

- In scope:
  - A **pure domain function** computing per-record concurrency-averaged seconds (the single definition of "batch averaging"), per worker, per state.
  - Rework the analytics worker (`process_step_transition`) to book **averaged** seconds instead of the full interval.
  - Make the **breakdown** endpoint's per-step `contribution`/`totals` and the **`running`** sidecar concurrency-averaged (they read raw records today → same over-count).
  - The synchronous step-level `TaskStep.total_*` time metrics (`increment_step_time_metrics`) corrected to averaged (or moved to the worker — see clarifications).
  - An idempotent **reconstruct/backfill** that rebuilds all affected aggregates from records.
  - A supporting index for the per-worker sweep query.
- Out of scope:
  - Completion count, issue counts, cost formula.
  - Cross-midnight bucketing change — keep the existing "book on the record's `entered_at` day" rule; only replace "full interval" with "averaged share".
- Assumptions:
  - Concurrency is **per worker, per state**: a worker splits their own attention across the steps they have open in the same state; different workers never share a divisor. Attribution is `COALESCE(credited_user_id, created_by_id)` (matches the rest of analytics).
  - **Only batchable steps divide** (resolved decision). A batchable step's divisor `k(t)` counts only the worker's **concurrently-open batchable** steps in that state; a **non-batch step always accrues full time** and never counts toward anyone's divisor. This is because a non-batch step *can* overlap a batch: starting a batchable step **skips** the one-active-step auto-pause (`_step_transition_core.py:78` — the guard only fires for non-batch starts), so a non-batch step already WORKING stays open when a batch begins (e.g. hand-finishing while a machine runs a batch). Two non-batch steps still cannot overlap (auto-pause), so a non-batch step is always solo → full time. The sweep therefore needs each record's `allows_batch_working` (from `TaskStep`).
  - `allows_batch_working` remains a **gate** (what overlaps are allowed going forward); stats are computed from **actual recorded overlap** using each step's stored `allows_batch_working`, so toggling a section's flag never corrupts history or requires reprocessing.
  - Records already contain everything the sweep needs (`entered_at`, `exited_at`, `state`, `credited_user_id`, `recorded_time_marked_wrong`, `step_id`, `workspace_id`) plus `TaskStep.allows_batch_working` (one join) — **no new column** is required for correctness or reconstruction.

## Clarifications required

All resolved (2026-07-18):
- [x] **Which metrics average?** Working, paused, **and** ended-shift are all concurrency-averaged the same way. Completion counts are not (per-step counts, already correct).
- [x] **Mixed batch/non-batch overlap → divisor.** **Only batchable steps divide.** A non-batch step always accrues full time and is excluded from the divisor. (See Assumptions + AC #1.)
- [x] **Step-level `TaskStep.total_*` timing.** **Computed in the async analytics worker** via the shared function; `TaskStep.total_*` becomes eventually-consistent (like issues/cost). The synchronous `increment_step_time_metrics` full-interval calls are retired.
- [x] **Live maintenance strategy.** **Recompute-and-SET the affected worker's day** (user-daily + user-section-daily) from records on each transition via the shared function (idempotent); maintain lifetime as `Σ daily` by applying the day's delta.
- [x] **Backfill scope.** **Rebuild all** — `user_daily_work_stats`, `user_section_daily_work_stats`, `working_section_daily_work_stats`, `user_lifetime_stats`, and `TaskStep.total_*` time fields, from the corrected function (counts/issues untouched).

## Acceptance criteria

1. **Averaging law (batchable steps).** For one worker, one state: the **batchable** steps' averaged seconds sum to the real wall-clock time the worker had ≥1 batchable step open in that state (within rounding). A batch of N steps open for the same real duration D each books `D/N`. Non-batch steps accrue full time on top (so the *global* sum across all steps can exceed real wall-clock during a mixed overlap — intended: the batch runs in parallel with the active step).
2. **Drift-correct.** Partial overlaps are handled per-instant: a batchable record's averaged seconds = `∫ dt / k(t)` over its interval, where `k(t)` = the worker's count of **batchable** records **open in that state at instant t** (open records count toward `k` even while computing a closed record's share). Starting another step mid-batch, pausing one, or completing some-not-all all produce correct shares (e.g. 6 steps for 10 min then a 7th joins for 60 min → early steps `10/6 + 60/7`, late step `60/7`, summing to 70 min).
3. **Non-batch full time.** A non-batch step always books its full interval and never counts toward any divisor; a worker who never batch-overlaps gets numbers identical to today.
4. **Reconstructable/idempotent.** A pure function `records → aggregates` exists; running it twice on the same records yields identical stats, and it is the definition the live path and the backfill both use.
5. **Flag-agnostic history.** Toggling a section's `allows_batch_working` does not change any already-recorded stats and requires no reprocessing; only future overlap behavior changes.
6. **All consumers corrected**, all using the one function:
   - `user_daily_work_stats` / `user_section_daily_work_stats` / `working_section_daily_work_stats` / `user_lifetime_stats` seconds fields.
   - `TaskStep.total_working_seconds` / `total_pause_seconds` / `total_ended_shift_seconds`.
   - Breakdown endpoint `contribution` (per step) and `totals`.
   - `running` sidecar (open intervals averaged by current concurrency).
7. **`recorded_time_marked_wrong` still excluded** from all time (unchanged rule), and pause/ended-shift averaged identically to working.
8. **Backfill** rebuilds historical aggregates to the corrected values and is safe to re-run (idempotent).
9. Cross-workspace isolation preserved; completion counts, issues, and cost-per-second behavior unchanged (cost inherits corrected seconds).

## Contracts and skills

### Read order block

- `../architecture/06_commands.md` → `../architecture/06_commands_local.md`
- `../architecture/07_queries.md` → `../architecture/07_queries_local.md`

### Contracts loaded

- `01_architecture.md`, `04_context.md`, `05_errors.md`, `21_naming_conventions.md`, `40_identity.md`, `41_user.md`, `42_event.md`, `48_presence.md`.
- `08_domain.md` — the concurrency-averaging **sweep is pure domain logic** (no IO, fully typed, unit-tested without a DB). This is the backbone and the reconstruction oracle.
- `06_commands.md`(+local) — changes to the transition command / step-metric write path.
- `07_queries.md`(+local) — breakdown/running read paths recompute averaged time.
- `16_background_jobs.md` + `51_worker_runtime.md` — the analytics worker (`PROCESS_STEP_TRANSITION`) is reworked to book averaged time.
- `52_replayability.md` + `53_operational_cli.md` — the idempotent reconstruct/backfill (records are the replayable source of truth).
- `49_observability_runtime.md` — logging around the reworked booking + backfill.
- `30_migrations.md` — supporting index for the per-worker sweep (no table/column changes otherwise).
- `15_testing.md` — pure unit tests for the sweep (the core), integration for worker/endpoints/backfill.
- `46_serialization.md` — breakdown/running output shapes (mostly unchanged; `running` semantics note).

### Excluded contracts

- `03_models.md` beyond the index — **no new column**; records are already sufficient (rationale in Scope).
- `13_sockets.md`/`11_infra_events.md` — no new realtime surface (existing `PROCESS_STEP_TRANSITION` event reused).

### File read intent — pattern vs relational

Relational reads already performed (what exists): `process_step_transition.py` (booking sites), `aggregate_metrics.py` (`increment_step_time_metrics`), `_step_transition_core.py` / `transition_step_state.py` / `transition_step_state_batch.py` (record lifecycle + batch driver), `get_worker_daily_step_breakdown.py` + `list_workers_last_interacted_step.py` (read-side time aggregation + `running`), `step_state_record.py` (fields + indexes), the analytics table mixins. No pattern reads needed — command/worker/query/serializer shapes come from their contracts.

### Skill selection

- Primary: contract-goal-mapping guide. Trigger terms: `worker`, `replay/reprocess/recover` (backfill), `deterministic testing`.

## The core algorithm (pure)

New `domain/analytics/concurrency.py` — pure, fully typed, no IO:

```
@dataclass(frozen=True)
class TimeInterval:
    record_id: str
    step_id: str
    state: str              # "working" | "paused" | "ended_shift"
    entered_at: datetime
    exited_at: datetime | None   # None = still open
    marked_wrong: bool
    is_batchable: bool           # TaskStep.allows_batch_working (snapshot on the step)

def averaged_seconds_by_record(intervals: Iterable[TimeInterval], now: datetime) -> dict[str, float]:
    """Per-record concurrency-averaged seconds for ONE worker.
    Group by state; per state, sweep-line over [entered_at, exited_at or now):
    at each sub-interval between event points, k = number of *batchable* intervals
    open, each open BATCHABLE interval's record accrues dt / k; each NON-batch
    interval accrues the full dt (it is excluded from k and never divided).
    marked_wrong intervals are filtered out first (accrue nothing, reduce nothing).
    Returns {record_id: seconds} (float)."""
```

Key rules the sweep must honor:
- **Per state, per worker.** Callers pass one worker's intervals; the function partitions by `state`.
- **Only batchable intervals divide.** `k(t)` counts only the concurrently-open **batchable** intervals; non-batch intervals get full time and are excluded from `k`. (Two non-batch intervals never overlap, so a non-batch interval is always solo.)
- **Open records count toward `k`.** A closed batchable record's share is reduced by any open batchable record overlapping it (concurrency is real presence, regardless of who closes first). So callers pass **all** the worker's overlapping records (open + closed); they then pick which record shares to *use* (closed → settled; open → running).
- **`marked_wrong`.** Excluded intervals must not accrue time to their own record. Decision to encode: they also **do not** reduce others' share (treat as absent) — i.e., filtered out before the sweep. (Matches "this interval's time is inaccurate" → ignore it entirely.)
- **Determinism.** Event-point ordering and tie handling fixed (e.g., process ends before starts at equal timestamps, then by `record_id`) so recompute is bit-identical → idempotency.
- Fractional seconds accumulate as float; callers round to int at the aggregation boundary (documented small rounding; `Σ` still equals real time within a couple seconds).

This one function is used by every consumer and by the backfill — it is the reconstruction oracle.

## Implementation plan

1. **Pure sweep** — add `domain/analytics/concurrency.py` (`TimeInterval`, `averaged_seconds_by_record`) with exhaustive unit tests (see Validation).
2. **Reconstruct helper** — `services/queries/analytics/` function: fetch one worker's time-bearing records overlapping a window (`entered_at < window_end AND (exited_at IS NULL OR exited_at > window_start)`, workspace-scoped, attributed via `COALESCE`), **joined to `TaskStep` for `allows_batch_working`**, build `TimeInterval`s (with `is_batchable`), call the sweep, and bucket closed-record shares by `(step_id, entered_at::date(UTC), state)`. This is the shared primitive for worker recompute, breakdown, and backfill.
3. **Analytics worker rework** (`process_step_transition.py`) — on a transition, **recompute-and-SET** the affected worker's day: user-daily + user-section-daily seconds from the reconstruct helper; update `user_lifetime_stats` by the day's delta; keep counts/issues/cost logic (cost recomputed from the corrected seconds). Replace the `_compute_interval_seconds` full-interval path. Structured log per recompute (`49`).
4. **Step-level totals (async).** Compute `TaskStep.total_working/pause/ended_shift_seconds` via the shared function in the analytics worker (recompute the step's time totals from its records) and **retire the synchronous `increment_step_time_metrics` full-interval calls** in `_step_transition_core` / `transition_step_state` (both the main and auto-pause paths). `TaskStep.total_*` becomes eventually-consistent — acceptable (issues/cost already are). Its count fields (`total_working_count`, etc.) are unaffected.
5. **Breakdown endpoint** — replace the raw `SUM(exited-entered)` per step with the averaged per-step seconds from the reconstruct helper; `totals` = `Σ` per-step averaged. Reconciliation note in the handoff updates accordingly.
6. **`running` sidecar** — average open intervals: each open record's running seconds = its averaged share up to `now` (via the sweep including all the worker's currently-open records). Update `build_running_totals` usage. **FE contract changes**: the worker-level running total for a state now advances at real time (≈1/sec when ≥1 open, since shares sum to 1), and a batch's per-step share ticks at `1/k` — document in the running handoff (the `*_open_count` tick math changes).
7. **Index** (`30`) — add `(workspace_id, credited_user_id, entered_at)` (or `(workspace_id, created_by_id, entered_at)`) on `step_state_records` to support the per-worker overlap sweep.
8. **Backfill / reconstruct CLI** (`52`/`53`) — `app/scripts/backfill/` typer command, dry-run-first: for each worker, run the reconstruct helper over all history and **SET** the affected aggregates + `TaskStep` time totals to the corrected values. Idempotent (absolute set), safe to re-run; run with the analytics queue drained.
9. **Tests** — unit (sweep) + integration (worker recompute, breakdown, running, backfill idempotency); see Validation.
10. **Handoffs** — update `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md` (contribution/totals now averaged) and `HANDOFF_TO_FRONTEND_worker_stats_running_live_totals_20260716.md` (averaged running + revised tick math). Write an implemented summary.

## Risks and mitigations

- Risk: **Semantic change to `running` tick math** breaks the FE's current ticking.
  Mitigation: document the new rule (worker-level ≈ real-time; per-step `1/k`) in the running handoff and coordinate; keep the field shape stable where possible.
- Risk: **Recompute-and-SET cost** per transition.
  Mitigation: bounded to one worker's day (tens of records); the new index supports the fetch; profile and fall back to incremental-averaged if needed (both match the reconstruct oracle).
- Risk: **Rounding drift** (`Σ` per-step ints vs real seconds).
  Mitigation: accumulate float, round at aggregation; document the ±1–2s tolerance; keep daily = `Σ` per-step so breakdown reconciles exactly.
- Risk: **Marked-wrong / edge overlaps** mis-handled.
  Mitigation: fixed, tested rules (filtered before sweep; deterministic tie-breaks); unit tests cover them.
- Risk: **Backfill vs live race** (absolute SET overwriting concurrent writes).
  Mitigation: run drained; idempotent absolute values; documented in the runbook.
- Risk: **`TaskStep.total_*` becomes eventually-consistent** (if moved to the worker).
  Mitigation: called out as a clarification; acceptable given issues/cost already async — confirm with product.

## Validation plan

- **Unit (the core, no DB)** — `averaged_seconds_by_record`:
  - N identical intervals `[t0,t1]` → each `= (t1-t0)/N`; `Σ = t1-t0`.
  - Partial overlap (A `[0,60]`, B `[20,40]`) → A gets `20 + 20/2 + 20 = 50`, B gets `10`; `Σ = 60`.
  - Single interval → full seconds (non-batch unchanged).
  - **Only-batch divides**: a non-batch interval overlapping a batch keeps full time and does not reduce the batch steps' shares (and vice-versa); a non-batch interval overlapping nothing is full.
  - **Late-join drift** (the worked example): 6 batchable `[0,70]` + 1 batchable `[10,70]` → early = `10/6 + 60/7`, late = `60/7`, batch `Σ = 70` min.
  - Open record reduces a closed record's overlapping share; marked-wrong excluded and doesn't reduce others.
  - Determinism: shuffled input → identical output.
- **Integration** — worker recompute produces averaged daily/section/lifetime + `TaskStep` totals; breakdown `contribution`/`totals` averaged and reconcile (`Σ contribution == totals`); `running` averaged; backfill run twice → identical (idempotent) and equal to a direct reconstruct; cross-workspace isolation.
- **Regression** — non-batch flows unchanged vs pre-change numbers.
- `alembic upgrade/downgrade` for the index; `ruff`/`mypy` clean.

## Review log

- `2026-07-18` requester: batch sections must average time by real concurrency; sections toggle batchable/not; must handle mid-batch drift; stats must be reconstructable/idempotent; pause and ended-shift averaged like working.
- `2026-07-18` owner: chose per-instant concurrency-averaging computed from record overlap (no stored batch id/size — records are sufficient and reconstructable); centralized the sweep as one pure function used by worker, endpoints, and backfill; flagged the step-level-total timing and live-maintenance strategy as decisions.
- `2026-07-18` owner: corrected a wrong assumption — non-batch steps *can* overlap a batch (batch-start skips auto-pause). Resolved all four decisions with the requester: only batchable steps divide (non-batch always full); `TaskStep.total_*` computed async in the worker; recompute-and-SET the worker's day; rebuild all historical aggregates.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `claude-opus-4-8`
