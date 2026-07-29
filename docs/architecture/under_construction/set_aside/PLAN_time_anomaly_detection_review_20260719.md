# PLAN_time_anomaly_detection_review_20260719

## Metadata

- Plan ID: `PLAN_time_anomaly_detection_review_20260719`
- Status: `under_construction`
- Owner agent: `claude-opus-4-8` (plan) → `codex` (implementation)
- Created at (UTC): `2026-07-19T00:00:00Z`
- Last updated at (UTC): `2026-07-19T00:00:00Z`
- Related issue/ticket: `—`

## Goal and intent

- **Goal:** Automatically flag completed task steps whose recorded time is a statistical **outlier** versus comparable trusted steps, and give managers a **review queue** to confirm (→ mark the step's time inaccurate) or dismiss (→ leave it, don't re-flag). This catches steps a worker marked *accurate* but whose timing looks wrong.
- **Business/user intent:** Reduce reliance on workers self-reporting inaccurate time. The system *suggests* suspicious steps with evidence; the **manager decides**. Confirming reuses the existing inaccurate-time flow (the flagged step leaves trusted, its wasted time is captured, and the median estimate patches it).
- **Non-goals:**
  - **No auto-marking.** Detection only *suggests*; `recorded_time_marked_wrong` flips only when a manager confirms. False positives must never corrupt trusted data.
  - Not scoring **paused**/ended-shift time in v1 (working only; the schema leaves room to extend).
  - No section-wide/global baseline fallback in v1 (worker×section only; skip when the baseline is thin — see Resolved decisions).
  - No anomaly types beyond duration (pauses, choppy state changes, mid-shift ends are future work).

## Scope

- **In scope:**
  - Pure-domain **anomaly scorer** (ratio-to-median + magnitude floor + confidence gate).
  - **Write-time detection** in the analytics worker (`process_step_transition`) on step completion, persisting to a **queue table**.
  - A **`GET` list endpoint** (the review queue, manager-only) and a **`POST` review endpoint** (confirm/dismiss), with a dedicated **review/audit table**.
  - Confirm wires to the existing `mark_step_time_inaccurate` **and** enqueues the analytics reconcile so the correction reflects immediately.
  - Migration (2 tables), backfill to score history, tests, frontend handoff.
- **Out of scope:** anything under Non-goals; changing trusted/wasted/estimate math (this only *feeds* the existing inaccurate-time flow on confirm).
- **Assumptions:** the estimation sample loader + concurrency-averaged per-step durations already exist and are reused for the baseline.

## Resolved decisions (2026-07-19)

- [x] **Detection rule** — **ratio-to-median + magnitude floor**: flag when `recorded_seconds ≥ ANOMALY_RATIO × peer_median` **and** `(recorded_seconds − peer_median) ≥ ANOMALY_FLOOR_SECONDS`, **and** the peer sample is solid (`≥ ANOMALY_MIN_SAMPLE`). Constants (tunable): `ANOMALY_RATIO = 3.0`, `ANOMALY_FLOOR_SECONDS = 600` (10 min), `ANOMALY_MIN_SAMPLE = 8`. Upper tail only (inflated time).
  - **Calibrated (2026-07-19)** against real data (458 trusted completed working steps): `3.0× / 600s / 8` flags **28 steps (~6%)** — a reviewable rate, not noisy. The floor barely binds at 3× (guard only); `min_sample` 5–12 all yield 28 (91% of steps have ≥8 peers). Alternatives: `2.5×` → 34 (~7.4%), `4.0×` → 15 (~3.3%).
- [x] **Architecture** — **persisted queue via the analytics worker**: score each step on completion, write/upsert a row in `step_time_anomalies`. Reads are cheap (query the table).
- [x] **Review state** — **dedicated audit table** `step_time_anomaly_reviews` (one row per manager action), plus a `status` on the queue row for fast filtering.
- [x] **Baseline grain (baked)** — `worker × section × working` over the estimation lookback (`ESTIMATION_LOOKBACK_DAYS = 28`), **excluding the step being scored**. If the worker's sample for that section `< ANOMALY_MIN_SAMPLE` → **do not score** (no flag). No section-wide fallback in v1 (avoids false positives on thin data; different from the *estimation* fallback by design).

## Future extensions (out of scope for v1 — keep the door open)

- **Per-section thresholds / strategy.** Different sections run at different tempos, so eventually the `ratio`/`floor` (and the estimation strategy) may want per-section overrides.
  - **Note the baseline is already section-adaptive:** the peer median is computed per `(worker, section)`, so `ratio` ("3× *this* section's typical") auto-adjusts to each section's pace. A per-section override really only buys a section-specific **absolute floor** (fast vs slow sections) and strategy choice.
  - **Deferred not for lack of data** (this workspace has **15 sections**, ~9 with solid volume — wood-fix 80 … padding 12 steps — and calibration showed 419/458 steps are scoreable today; thin sections like sewing/assembly self-exclude via `min_sample`), **but for lack of observed evidence**: run the global calibrated defaults, watch the review queue, and only override the handful of sections that demonstrably misfire. With ~15 sections that's hand-tunable later.
  - **v1 guardrail:** keep the constants isolated behind a small resolver (a `resolve_anomaly_config(section_id) -> (ratio, floor, min_sample)` that returns the globals for now), **not inlined**, so a per-section config table/columns is a drop-in later with no change to the pure scorer.
- **Temporal baselines** (time-of-day / shift-windowed peers) and **non-duration anomalies** (excessive pauses, choppy state changes, mid-shift ends) are later work.

## Acceptance criteria

1. A completed working step whose averaged duration is ≥ 3× its section peer median (and ≥ 10 min over, with ≥ 8 peers) produces one `step_time_anomalies` row (`status=pending`) with the evidence (`recorded_seconds`, `peer_median_seconds`, `ratio`, `sample_size`); a normal step produces none; a step scored against `< 8` peers produces none.
2. Re-running the worker for the same step is idempotent (unique `(workspace_id, step_id, state)` → upsert, never duplicate); an already-reviewed anomaly is not resurrected to `pending`.
3. `GET /api/v1/time-anomalies` (ADMIN/MANAGER) returns pending anomalies for a date range with evidence + a light step/worker payload, paginated; excludes confirmed/dismissed.
4. `POST /api/v1/time-anomalies/{anomaly_id}/review` with `decision=confirm` sets `status=confirmed`, writes a `step_time_anomaly_reviews` audit row, marks the step's time inaccurate (existing command), **and enqueues the analytics reconcile** so trusted/wasted update; `decision=dismiss` sets `status=dismissed` + audit row and leaves the step trusted.
5. Detection is pure-domain-tested (ratio/floor/min-sample edge cases) and the worker/endpoint paths are integration-tested; the step being scored is excluded from its own baseline.
6. Migration up/down round-trips; single alembic head; backfill scores history idempotently; ruff clean; app + worker + backfill import cleanly.

## Contracts and skills

> Read order per `task_system/backend_contract_goal_mapping_guide.md`: canonical first, then `*_local.md`.

### Contracts loaded

- `backend/architecture/08_domain.md` — pure anomaly scorer (no IO).
- `backend/architecture/16_background_jobs.md` + `51_worker_runtime.md` + `52_replayability.md` — worker scoring stays an idempotent projection; confirm enqueues reconcile.
- `backend/architecture/06_commands.md` (+`_local`) — the review command (`maybe_begin`, subordinate-command/event rule for the reconcile enqueue).
- `backend/architecture/07_queries.md` (+`_local`) — the list-anomalies query service (offset pagination, serialized dicts).
- `backend/architecture/09_routers.md` — the two routes (`require_roles([ADMIN, MANAGER])`).
- `backend/architecture/03_models.md` + `30_migrations.md` — two new tables + migration.
- `backend/architecture/42_event.md` + `11_infra_events.md` — realtime/`task:updated` on confirm (optional).
- `backend/architecture/53_operational_cli.md` — backfill (dry-run first).
- `backend/architecture/46_serialization.md` — anomaly + review serializers.
- `backend/architecture/15_testing.md` — unit (domain) + integration split.

### File read intent — pattern vs. relational

Relational reads (what exists): `services/tasks/analytics/process_step_transition.py`, `services/queries/analytics/estimation_sample.py`, `domain/analytics/estimation/strategies.py`, `services/commands/task_steps/mark_step_time_inaccurate.py`, `models/tables/tasks/task_step.py`, `models/tables/tasks/step_state_record.py`, `routers/api_v1/worker_stats.py`, `services/queries/tasks/step_light_bundle.py`, `scripts/backfill/backfill_averaged_time.py`. No pattern reads — contracts cover the "how to write."

### Skill selection

- Primary skill: `—` (follow contracts directly).
- Router trigger terms: `anomaly, analytics, worker, review`.

## Implementation plan

### A. Detection (domain + worker + storage)

1. **Pure scorer** — `domain/analytics/anomaly.py`: `score_duration_anomaly(recorded_seconds, peer_sample: list[float], *, ratio, floor_seconds, min_sample) -> DurationAnomaly | None` where `DurationAnomaly(recorded_seconds, peer_median, ratio, sample_size)`. Returns `None` unless `len(sample) >= min_sample AND recorded >= ratio*median AND (recorded-median) >= floor_seconds`. Pure, no IO, thresholds are **parameters** (never inlined). Unit-tested. Global defaults live in an `anomaly` config module and are sourced via a `resolve_anomaly_config(section_id) -> (ratio, floor_seconds, min_sample)` seam that returns the globals for now — so per-section overrides (see Future extensions) drop in with no change to the scorer or worker.
2. **Baseline loader** — extend/parallel `estimation_sample.load_trusted_step_duration_sample` to support **`exclude_step_id`** (so the scored step isn't its own peer). For scoring, use the `(section, "working")` bucket for the credited user over the lookback.
3. **Tables** — `models/tables/analytics/step_time_anomaly.py` (`step_time_anomalies`): `IdentityMixin` (`client_id` prefix `sta`), `workspace_id`, `step_id`, `credited_user_id`, `working_section_id`, `state` (enum, `working` for v1), `recorded_seconds`, `peer_median_seconds`, `ratio` (Numeric), `sample_size`, `status` (enum `pending|confirmed|dismissed`, default `pending`, `server_default`), `detected_at`, `created_at/updated_at`; **unique `(workspace_id, step_id, state)`**. And `models/tables/analytics/step_time_anomaly_review.py` (`step_time_anomaly_reviews`): `client_id` (prefix `star`), `workspace_id`, `anomaly_id` (FK), `step_id`, `decision` (enum `confirmed|dismissed`), `reason` (nullable), `reviewed_by_id`, `reviewed_at`.
4. **Worker scoring** — `process_step_transition.handle_process_step_transition`: when `new_state == COMPLETED` and a credited user exists, after `_recompute_step_time_totals`, take the step's averaged working seconds (`TaskStep.total_working_seconds`), load the peer sample (step 2, excluding this step), call the scorer, and **upsert** a `step_time_anomalies` row — but **skip if a review already exists / status ≠ pending** (never resurrect a reviewed anomaly). If not an anomaly, ensure no stale `pending` row lingers (delete/skip). Idempotent.
5. **Migration** — one revision (branch off verified `alembic heads`): both tables + enums + the unique index. Reversible.
6. **Backfill** — `scripts/backfill/backfill_time_anomalies.py` (typer, dry-run-first): score all historical completed, trusted, non-reviewed steps; upsert pending rows. Idempotent.

### B. List endpoint (the review queue)

7. **Query service** — `services/queries/analytics/list_time_anomalies.py`: manager-only; filters `date_from`/`date_to` (on `detected_at` or the step's completion), optional `user_id`/`section_id`, `status` (default `pending`); offset pagination; returns serialized anomalies with **evidence** (`recorded_seconds`, `peer_median_seconds`, `ratio`, `sample_size`, human-friendly derived like `over_seconds`) + a **light step/worker/task payload** (reuse `load_step_light_bundle` + `serialize_user_worker_stat`).
8. **Serializer** — `domain/analytics/serializers.py`: `serialize_time_anomaly(...)`.
9. **Router** — new `routers/api_v1/time_anomalies.py`: `GET /api/v1/time-anomalies` → `run_service(list_time_anomalies)`; register the router. `require_roles([ADMIN, MANAGER])`.

### C. Review endpoint (correct them)

10. **Command** — `services/commands/analytics/review_time_anomaly.py`: input `{anomaly_id, decision: confirm|dismiss, reason?}`. `maybe_begin`: load the anomaly (workspace-scoped, must be `pending` → else `409/validation`); write a `step_time_anomaly_reviews` row; set `status`. On **confirm**: call the existing `mark_step_time_inaccurate` core (`_apply_inaccurate_time_flag`) on the step **and enqueue `PROCESS_STEP_TRANSITION`** (or a lighter reconcile-day event) for the step's credited user/day so trusted→wasted updates immediately (this also closes the standalone-mark reconcile gap for this path). Dispatch `task:updated`.
11. **Router** — `POST /api/v1/time-anomalies/{anomaly_id}/review` in the same router → `run_service(review_time_anomaly)`.

### D. Docs & validation

12. **Handoff** — new `HANDOFF_TO_FRONTEND_time_anomaly_review_20260719.md`: the queue shape (+ evidence fields + light payload), the review endpoint (`confirm`/`dismiss` + optional `reason`), that confirm reuses the inaccurate-time flow (so `/totals` wasted/estimate shift after confirm), and that it's advisory (manager decides).
13. **Tests** — unit: scorer edge cases (ratio boundary, floor boundary, `< min_sample` → none, exclude-self). Integration: worker writes a pending anomaly for an inflated step + none for a normal one + none under thin sample; list endpoint filters to pending + shape; review confirm → status/audit/step-flagged/reconcile-enqueued + trusted drops; dismiss → status/audit + step still trusted; idempotent re-score.

## Risks and mitigations

- **Risk:** false positives erode manager trust.
  Mitigation: ratio **and** floor **and** `min_sample` all required; upper-tail only; human-in-the-loop (never auto-mark); dismiss suppresses re-flagging.
- **Risk:** baseline contamination — inflated steps marked "accurate" inflate the median and hide anomalies.
  Mitigation: robust **median** baseline resists some contamination; **self-correcting** — each confirmed anomaly leaves the trusted set, tightening the baseline. Documented.
- **Risk:** scoring at completion adds a per-completion sample query.
  Mitigation: completions are far rarer than reads; the baseline query is bounded (one worker×section, 28d) and uses the existing flagged index; skip entirely when the step has no credited user / section.
- **Risk:** batch steps look "long" and get flagged.
  Mitigation: score the **concurrency-averaged** duration (`TaskStep.total_working_seconds`), not raw, so batch `1/k` is already applied.
- **Risk:** confirm path doesn't reconcile (the known standalone-mark drift).
  Mitigation: confirm **explicitly enqueues** the reconcile; covered by an integration test asserting trusted drops after confirm.

## Validation plan

- `pytest app/tests/unit/domain/analytics/test_anomaly.py` — scorer edge cases.
- `pytest` (integration) — worker scoring (anomaly / no-anomaly / thin-sample / exclude-self / idempotent), list endpoint, review confirm+dismiss (status, audit, step flag, reconcile).
- `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — clean round-trip; single head.
- `python scripts/backfill/backfill_time_anomalies.py --dry-run` — runs, reports counts, no writes.
- `ruff check` clean; app/worker/backfill import.

## Review log

- `2026-07-19` owner: initial draft; decisions resolved (ratio+floor; worker-persisted queue; dedicated audit table; worker×section baseline, skip-if-thin). No open clarifications.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
