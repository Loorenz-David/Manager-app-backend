# PLAN_worker_daily_step_breakdown_20260716

## Metadata

- Plan ID: `PLAN_worker_daily_step_breakdown_20260716`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-16T10:00:00Z`
- Last updated at (UTC): `2026-07-16T12:30:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`
- Predecessors: `PLAN_worker_stats_last_interacted_steps_20260715`, `PLAN_worker_stats_daily_metrics_20260715` (both implemented)

## Goal and intent

- Goal: A **manager-only drill-down** endpoint that, for one worker on one day, returns the **per-task-step breakdown** of that day's totals — how much each step contributed to worked / paused / ended-shift time and completions — plus the day's grand totals, reconciled against the maintained daily stats.
- Business/user intent: The list endpoint answers *"what did this worker do today"* (daily totals). This answers *"where did those totals come from"* — the manager clicks a worker and sees the individual steps behind the numbers.
- Non-goals:
  - No new aggregate table — the breakdown is computed on-the-fly from `StepStateRecord` (drill-down, not a hot path).
  - No change to the existing list endpoint's per-worker `daily_stats` shape.
  - **No per-step flagging/insights yet** — that is a planned follow-up (see [Future extension points](#future-extension-points)); this plan only exposes the raw per-step contributions it will consume.

## Scope

- In scope:
  - New route `GET /api/v1/worker-stats/{user_id}/daily-steps?work_date=&limit=&offset=` (ADMIN/MANAGER), in the existing `worker_stats` router.
  - New query service `services/queries/worker_stats/get_worker_daily_step_breakdown.py`.
  - On-the-fly per-step aggregation of `StepStateRecord` for `(user, day)`.
  - A **light** step item (step + task-light + item-light + images + `contribution`) — reusing the existing serializers, not the heavy `list_working_section_steps` shape.
  - A shared **batched entity loader** helper (tasks, primary items + upholstery + requirements, images by step_ids) so the light assembly is efficient and reusable.
  - `totals` (breakdown, **settled** only) + echoed maintained `daily_stats` for reconciliation.
  - Per-step **`active_record`** — the currently-open (not-yet-closed) record for that worker/step, with its `state` + `entered_at`, so the frontend can add the live running time to the displayed total. Kept **out** of the settled `totals`/`contribution`.
  - A **`sort_by` + `order`** query param so the frontend can reorder. Fields: `contribution` (default active-first composite), `working` / `paused` (biggest settled contribution), `completed`, `last_activity` (recency). `order` (`desc` default / `asc`) flips each.
  - **`completed` is an intention, not just a sort**: `sort_by=completed` **scopes the listed steps to those completed that day** and orders them by completion time. It's the only terminal state, so it reads as "show what they finished." `working` / `paused` / `last_activity` / `contribution` are sort-only over **all** touched steps. `totals` stay full-day regardless (see reconciliation).
- Out of scope:
  - Per-step positive/negative flagging (future).
  - Metrics beyond worked / paused / ended-shift / completed (more to come; design for easy addition).
  - Refactoring `list_working_section_steps` to adopt the shared loader (optional, low-risk follow-up — see Risks).
- Assumptions:
  - Attribution matches the analytics worker: `COALESCE(credited_user_id, created_by_id)` (the column added in `PLAN_worker_stats_daily_metrics`). Confirmed in `process_step_transition.py`.
  - Maintained totals bucket time on the closed record's `entered_at` (UTC) and completions on the completion moment; the breakdown's **settled** figures apply the **same** rules so they reconcile.
  - An open record (`exited_at IS NULL`) is a currently-running interval the worker has not yet folded into any total; there is at most one open record per step (`uix_step_state_records_active` unique index). Its running time only exists on the day it `entered_at` — which is why it never appears on past-date breakdowns.
  - `serialize_step`, `serialize_task_light`, `serialize_item_worker_light`, `serialize_image`/`serialize_image_light` are the light-shape building blocks (relational read of `list_working_section_steps`).

## Clarifications required

Resolved with the requester on 2026-07-16:

- [x] **Metrics** — worked, paused, ended-shift, completed for now; more later → design the aggregation + serializer so adding a metric is one column + one field.
- [x] **Reconciliation** — Option (b): return breakdown `totals` **and** echo the maintained `daily_stats` so any gap (e.g. from deleted steps) is explicit.
- [x] **Item richness** — **light**: `serialize_step` (step light) + `serialize_task_light` + `serialize_item_worker_light` + images + `contribution`. No created_by/updated_by, last_state_record, cases, dependencies, or reassigned flags.
- [x] **Shared loader** — extract shared **batched entity loaders** (not a monolithic item builder), so the two endpoints compose their own shapes and expand independently.

## Acceptance criteria

1. `GET /api/v1/worker-stats/{user_id}/daily-steps` returns `200` for ADMIN/MANAGER, `403` for WORKER/SELLER, `404` when `{user_id}` is not an active member of the caller's workspace.
2. `work_date` resolves like the list endpoint: `?work_date=YYYY-MM-DD` when valid, else UTC today; an invalid value → validation error (not 500). `sort_by` (default `contribution`) and `order` (default `desc`) are validated against their allowed sets; unknown values → validation error (not silently ignored).
3. Response shape:
   ```json
   {
     "user": { "client_id": "...", "username": "...", "profile_picture": "...", "last_online": "..." },
     "work_date": "2026-07-16",
     "totals": { "total_working_seconds": 0, "total_pause_seconds": 0,
                 "total_ended_shift_seconds": 0, "total_completed_count": 0 },
     "daily_stats": { "work_date": "2026-07-16", "total_working_seconds": 0,
                      "total_pause_seconds": 0, "total_ended_shift_seconds": 0,
                      "total_completed_count": 0 },
     "steps": {
       "items": [
         { "...": "serialize_step fields", "task": {...}, "item": {...}, "item_images": [...],
           "contribution": { "working_seconds": 0, "pause_seconds": 0,
                             "ended_shift_seconds": 0, "completed_count": 0 },
           "active_record": { "state": "working", "entered_at": "2026-07-16T09:30:00+00:00" },
           "last_activity_at": "2026-07-16T09:30:00+00:00",
           "last_completed_at": "2026-07-16T09:10:00+00:00" }
       ],
       "limit": 50, "offset": 0, "has_more": false
     }
   }
   ```
   `active_record` is `null` when the worker has no open record on that step for the day.
4. Each `contribution` is that worker's **settled** share of the metric on `work_date` for that step, computed from `StepStateRecord` with the **worker's rules**: time from **closed** records (`exited_at` not null) excluding `recorded_time_marked_wrong`, bucketed on `entered_at` within the UTC day; completions counted on the completion moment. The currently-open interval is **excluded** from `contribution` and surfaced only in `active_record`.
5. `active_record` reflects the step's single open record (`exited_at IS NULL`) for that worker whose `entered_at` is within the UTC day: its `state` and `entered_at` (start). The frontend computes running time as `now − entered_at` and adds it to the matching metric **for display only** — the backend never folds it into `contribution`/`totals`. On a past `work_date` there are no open records, so every `active_record` is `null`.
6. Attribution uses `COALESCE(credited_user_id, created_by_id) == user_id`.
8. `totals` = the sum of every contributing step's **settled** contribution that day (over **all** steps, independent of `sort_by` and pagination — never scoped by the `completed` filter). Running time is never in `totals`. Summing the page's `contribution`s across all pages equals `totals` **only for the unfiltered sorts** (`contribution`/`working`/`paused`/`last_activity`); under `sort_by=completed` the listed steps are a subset, so they sum to ≤ `totals`.
9. `daily_stats` echoes the maintained `user_daily_work_stats` row (zeros when absent). `totals` and `daily_stats` are per-metric comparable; they may legitimately differ (documented) when a contributing step was later deleted.
10. The step set is the **union** of steps with settled contributions and steps with an `active_record` that day — a step whose only activity is a currently-open interval (settled contribution all-zero) still appears. Ordering is **deterministic and controlled by `sort_by` + `order`**, always with `step_id` as the final tie-break so pages are stable. `order` defaults to `desc`; a `NULLS LAST` rule keeps steps missing the sort metric at the bottom regardless of direction:
    - `contribution` (default): **active steps first**, then `working_seconds` desc, then `completed_count` desc — a fixed composite (`order` not applied; inherently "biggest first").
    - `working` / `paused`: by `working_seconds` / `pause_seconds` in the `order` direction (`desc` = biggest contribution first).
    - `completed`: **scopes `items` to steps completed that day** (a filter intention, not just a sort — it's the sole terminal state) and orders them by completion time `last_completed_at` (`= MAX(entered_at) FILTER (state=COMPLETED)`) in the `order` direction (`desc` = most recently completed first). Steps with no completion that day are excluded from `items` under this sort only.
    - `last_activity`: by `last_activity_at` (`= MAX(entered_at)` over the worker's records on the step that day) in the `order` direction.
    Every sort key is a **stable value** (a boolean flag or a fixed historical timestamp/number — never the live running duration), so page order does not drift between requests. Offset-paginated per `07_queries_local` (`steps.{items,limit,offset,has_more}`, `has_more` via `limit + 1`). `last_activity_at` and `last_completed_at` are also returned on each item so the client can display / re-sort locally.
11. Query budget is independent of step count: one settled-aggregation query + one open-record query (both over all steps) + the batched light-bundle loaders for the page — **no N+1** (asserted with `count_queries`).
12. Cross-workspace isolation: no step/task/item/image/record from another workspace appears.

## Contracts and skills

### Read order block

- `../architecture/07_queries.md` (baseline) → `../architecture/07_queries_local.md` (offset pagination — apply exactly)

### Contracts loaded

- `01_architecture.md`, `04_context.md`, `05_errors.md` — layering, `ServiceContext`, error/validation contract.
- `07_queries.md` + `07_queries_local.md` — read-only query; offset pagination for `steps`; `has_more` via `limit + 1`; `steps` pagination key required on empty and non-empty paths.
- `09_routers.md` — handler wiring (`require_roles`, `ServiceContext`, `run_service`, `build_ok`/`build_err`); path param `{user_id}`.
- `21_naming_conventions.md` — file/route/function naming.
- `41_user.md` / `48_presence.md` — `user` object (`username`, `profile_picture`, `last_online`).
- `46_serialization.md` — light item composition from existing serializers; module-local pattern (query service returns the serialized dict payload, mirroring `list_working_section_steps`).
- `15_testing.md` — integration test for the aggregation + assembly (SQL path); light unit coverage for pure helpers (date range, totals fold).

### Contracts considered, not driving code

- `08_domain.md` — no pure domain logic in this plan; noted as the home for the **future** per-step flagger.
- Trigger map `"date filter" -> 55`: not pulled — `work_date` is a single UTC-day **scope** (same pattern already shipped in the list endpoint), not the search/`ilike` surface `55` governs.

### Excluded contracts

- `03_models`, `30_migrations` — no schema change (on-the-fly aggregation).
- `11`/`13`/`16`/`51`/`42` — read-only; no realtime, workers, or events.

### File read intent — pattern vs relational

Relational reads (what exists — legitimate): `list_working_section_steps.py` (light-shape serializers + batched-load pattern), `step_state_record.py` (`credited_user_id`, `entered_at`, `exited_at`, `recorded_time_marked_wrong`, `state`), `process_step_transition.py` (attribution + bucketing rules to mirror), `user_daily_work_stats.py` (maintained totals to echo). No pattern reads needed — query/pagination from `07(+local)`, route from `09`, serialization from `46`.

## Implementation plan

1. **Shared batched loaders** — new `services/queries/tasks/step_light_bundle.py` (or `working_sections/`): pure-IO helpers keyed by `step_ids`, each one batched (`... IN (step_ids)` / `IN (task_ids)`):
   - `load_steps_by_ids(ctx, step_ids) -> dict[str, TaskStep]`
   - `load_tasks_for_steps(ctx, steps) -> dict[str, Task]`
   - `load_primary_item_bundle(ctx, task_ids) -> (items, requirements_by_item, upholstery_by_id, task_to_primary_item_id)`
   - `load_item_images(ctx, item_ids) -> dict[str, list[dict]]`
   These are exactly the batched blocks already in `list_working_section_steps` (lines ~269–422), lifted verbatim so behavior is identical. **Do not** touch `list_working_section_steps` in this plan; adopting these there is a separate follow-up (Risks).
2. **Aggregation query** — in the new service, one grouped query over `StepStateRecord`:
   - Filter (WHERE): `workspace_id == ctx.workspace_id`, `COALESCE(credited_user_id, created_by_id) == user_id`, `entered_at >= day_start_utc AND entered_at < day_end_utc`. Note: `exited_at` is **not** filtered here — the closed-only rule lives in the metric `FILTER`s below, so this single query returns the **full** touched-step set (settled + open) and a `last_activity_at` for every one.
   - Per-step aggregates (extensible — one expression per metric):
     - `working_seconds = SUM(GREATEST(0, EXTRACT(EPOCH FROM exited_at - entered_at))) FILTER (state=WORKING AND exited_at IS NOT NULL AND NOT recorded_time_marked_wrong)`
     - `pause_seconds`, `ended_shift_seconds` — same with their states.
     - `completed_count = COUNT(*) FILTER (state=COMPLETED)`.
     - `last_activity_at = MAX(entered_at)` (over all the user's records on the step that day — `last_activity` sort + returned per item).
     - `last_completed_at = MAX(entered_at) FILTER (state=COMPLETED)` (completion time; `null` if not completed that day — `completed` sort + returned per item).
   - Only **closed** records feed the time sums (via the `FILTER`), matching the worker.
   - `GROUP BY step_id`. Cheap — no joins.
3. **Open records** — a second small query: `SELECT step_id, state, entered_at FROM step_state_records WHERE workspace_id=:ws AND COALESCE(credited_user_id, created_by_id)=:user AND exited_at IS NULL AND entered_at >= :day_start AND entered_at < :day_end`. At most one row per step (unique active index). Build `active_record_by_step[step_id] = {state, entered_at}`.
4. **Totals + display set + ordering + page** — first fold the settled sums of **all** step-2 rows into `totals` (always full-day, before any filter). Then build the **display set**:
   - `sort_by=completed` → keep only rows with `last_completed_at IS NOT NULL` (completed that day), ordered `(last_completed_at <order>, step_id)`.
   - `sort_by=contribution` → all rows, `(has_active_record desc, working_seconds desc, completed_count desc, step_id)` (`has_active_record` = presence in `active_record_by_step`).
   - `sort_by=working` / `paused` → all rows, `(working_seconds <order>, step_id)` / `(pause_seconds <order>, step_id)`.
   - `sort_by=last_activity` → all rows, `(last_activity_at <order>, step_id)`.
   Then `has_more` via `limit + 1` **on the display set**; slice the page. (Totals are unaffected by the `completed` scoping.)
5. **Light bundle for the page** — call the shared loaders for `page_step_ids`; assemble each light item: `{**serialize_step(step), "task": serialize_task_light(task), "item": serialize_item_worker_light(item, reqs, upholstery_by_id), "item_images": images, "contribution": {...}, "active_record": active_record_by_step.get(step_id), "last_activity_at": <iso>, "last_completed_at": <iso|null>}` (timestamps ISO; `active_record` / `last_completed_at` are `null` when absent).
6. **User + reconciliation** — load the target `User` (404 if not an active workspace member); fetch the maintained `user_daily_work_stats` row for `(user, work_date)` and echo it via a `serialize_user_daily_work_stats_full` (4 metrics incl. ended-shift — new serializer, leaves the existing 3-field one untouched). Build `contribution` / `totals` with a small `serialize_step_contribution` helper.
7. **Router** — add the route to `worker_stats.py`: `{user_id}` path param + `work_date`/`limit`/`offset`/`sort_by`/`order` query params; `require_roles([ADMIN, MANAGER])`; standard `run_service` + `build_ok`/`build_err`. Define the allowed sets as constants in the query module — `sort_by ∈ {contribution, working, paused, completed, last_activity}`, `order ∈ {asc, desc}` — mapped to their sort keys via a small dict so adding a field is one entry.
8. **Tests** — integration: seeded records across two days / two users → correct per-step split, attribution (credited vs performer), marked-wrong excluded from time but completions counted, **an open record surfaced in `active_record` but excluded from `contribution`/`totals`**, a step whose only activity is an open record still listed, **each sort returns the expected order** (`contribution` active-first; `working`/`paused` biggest-first; `last_activity` desc/asc) and **`sort_by=completed` returns only completed steps ordered by completion time while `totals` still reflect the full day** (a non-completed working step is absent from `items` but present in `totals`), invalid `sort_by`/`order` → validation error, cross-workspace isolation, `totals == Σ contributions`, reconciliation gap when a contributing step is deleted, pagination, `count_queries` to prove no N+1. Unit: the UTC day-range helper and the totals fold.
9. **Handoff doc** — new `HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`: endpoint, params (incl. `sort_by`/`order` with allowed values, and the note that **`sort_by=completed` also filters `items` to completed steps while `totals` stay full-day**), the light item + `contribution` + `active_record` + `last_activity_at` + `last_completed_at` + `totals` + `daily_stats` shapes, **how to add running time client-side** (`now − active_record.entered_at`, added to the metric matching `active_record.state`, display-only), and the reconciliation note.

## Future extension points

- **More metrics** (planned): each is one aggregate expression (step 2) + one field in `serialize_step_contribution` / totals. Keep the aggregate list in one place so additions are mechanical.
- **Per-step flagger** (planned, next): a step-level analogue of the daily insights engine — flag each step's contribution as positive/negative vs a baseline. It will live in `domain/analytics/insights` (pure, per `08_domain`) and consume the per-step `contribution` this endpoint already produces, so no rework of this service is expected — only an added `flags`/`insights` field per step item.

## Risks and mitigations

- Risk: **Reconciliation gap** — breakdown `totals` (visible, non-deleted steps) can be ≤ maintained `daily_stats` (which counted now-deleted steps or edge cases).
  Mitigation: return both (Option b) and document the reason; never silently reconcile.
- Risk: **Bucketing/attribution drift** from the analytics worker → breakdown wouldn't match totals.
  Mitigation: mirror the worker exactly (closed-record time, marked-wrong exclusion, UTC `entered_at` range, `COALESCE` attribution); an integration test asserts `totals` reconciles to a hand-seeded expectation.
- Risk: **No index on `credited_user_id`/`created_by_id`** — filtering a user's day could scan.
  Mitigation: the `entered_at` range uses the existing `(workspace, step, entered_at)` index and one user's day is a tiny slice; acceptable for a drill-down. Add `(workspace_id, entered_at)` or a user-scoped index only if it shows up hot.
- Risk: **Shared-loader coupling** as the two endpoints expand.
  Mitigation: share only the low-level batched entity loaders (maps), not the item assembly — each endpoint composes its own shape. `list_working_section_steps` is left untouched here; adopting the shared loaders there is an isolated, separately-tested follow-up.
- Risk: **`::date` timezone trap** if bucketing were done in SQL casts.
  Mitigation: use an explicit UTC `entered_at` **range**, not `::date`.
- Risk: **Running time leaking into settled totals** would break reconciliation with `daily_stats` (which excludes open intervals until close).
  Mitigation: the open record feeds only `active_record`; `contribution`/`totals` filter `exited_at IS NOT NULL`. A test asserts an open record moves the settled numbers by zero. The frontend adds running time for display only.

## Validation plan

- Seed a worker with WORKING/PAUSED/ENDED_SHIFT (closed) + COMPLETED records across one step and across two steps; assert per-step `contribution` and that `totals == Σ contributions == ` the independently-computed daily figure.
- Marked-wrong record excluded from time but its completion still counted.
- Attribution: a record credited to another user does not appear under the performer; historical (null credited) falls back to performer.
- Open record present: appears in `active_record` with its `state`/`entered_at`, contributes **0** to `contribution`/`totals`; a step whose only activity today is the open record still appears in `items`.
- Sorting: `contribution` → active step first then biggest settled time; `working`/`paused` → biggest that-metric contribution first; `completed&order=desc` → **only completed steps**, most-recently-completed first (and `totals` still full-day); `last_activity&order=asc` → oldest first; repeated identical requests return identical page order (stable keys).
- Deleted contributing step → breakdown omits it and `totals < daily_stats` (reconciliation gap visible).
- Role gate (403), non-member `{user_id}` (404), invalid `work_date` (validation error), cross-workspace isolation.
- `count_queries`: constant query count regardless of number of steps.
- `alembic` unaffected (no schema change); `ruff`/`mypy` clean.

## Review log

- `2026-07-16` requester: build a granular drill-down of the daily totals per task step, light item shape, reconcile against maintained totals, design for more metrics and a future per-step flagger.
- `2026-07-16` owner: chose on-the-fly aggregation (no new table), shared batched loaders (not shared item assembly), light item, Option-b reconciliation; captured the flagger as a non-disruptive future field.
- `2026-07-16` requester: also return the currently-open record with its start time so the frontend can add live running time to the displayed total.
- `2026-07-16` owner: added per-step `active_record` (state + entered_at), kept **out** of settled `contribution`/`totals` to preserve reconciliation; step set now unions settled + open-record steps; running time is a display-only frontend addition.
- `2026-07-16` requester: sort active (currently-open) steps first.
- `2026-07-16` owner: ordering is now `(has_active_record desc, working_seconds desc, completed_count desc, step_id)` — a stable boolean flag, not the running duration, so pagination order stays deterministic.
- `2026-07-16` requester: expose a sort parameter so the frontend can sort by time (recent ↔ oldest).
- `2026-07-16` owner: added `sort_by` (`contribution` default, `last_activity`) + `order` (`desc`/`asc`); added `last_activity_at = MAX(entered_at)` to the aggregation and per item; all sort keys are stable values (flags/timestamps), preserving deterministic pagination; the single aggregation now returns the full touched-step set (closed-filter moved into `FILTER`).
- `2026-07-16` requester: also sort by `working` / `paused` (biggest that-metric contribution) and `completed` (by completion time, most recent first).
- `2026-07-16` owner: expanded `sort_by` to `{contribution, working, paused, completed, last_activity}`; `working`/`paused` sort by their settled seconds, `completed` by a new `last_completed_at = MAX(entered_at) FILTER (state=COMPLETED)`; both new timestamps returned per item; sort keys held in an extensible dict.
- `2026-07-16` requester: `completed` is an intention — passing it should show **only** the completed steps (granularity of what was finished), sorted by completion time; `working`/`paused` are focuses already covered by their sorts (completed is the sole terminal state needing a filter).
- `2026-07-16` owner: made `sort_by=completed` also **scope `items`** to steps completed that day (filter + completion-time order); kept `totals`/`daily_stats` full-day (reconciliation anchor), so the completed view is a subset that sums to ≤ `totals` (documented). Considered a separate filter param but folded it into the single `completed` intention per the "only terminal state" framing.

## Lifecycle transition

- Current state: `archived`
- Implemented by: `claude-opus-4-8` (direct implementation, not Codex)
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_daily_step_breakdown_20260716.md`
- Related handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_daily_step_breakdown_20260716.md`
