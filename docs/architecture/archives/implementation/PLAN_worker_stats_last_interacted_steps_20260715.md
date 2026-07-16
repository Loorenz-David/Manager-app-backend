# PLAN_worker_stats_last_interacted_steps_20260715

## Metadata

- Plan ID: `PLAN_worker_stats_last_interacted_steps_20260715`
- Status: `archived`
- Owner agent: `claude-opus-4-8`
- Created at (UTC): `2026-07-15T13:47:57Z`
- Last updated at (UTC): `2026-07-15T14:12:38Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/worker_stats_modification.md`

## Goal and intent

- Goal: Introduce a new **manager-only** family of "worker stats" endpoints. The first endpoint returns the workspace's workers, each paired with a serialized payload for the task step that worker **last interacted with** (regardless of that step's current state).
- Business/user intent: Give managers a roster-style view of every worker and the last task step each one touched, so they can see at a glance what each person was most recently doing. This is the read-only, manager-facing counterpart to the worker-facing `get_user_last_active_step_record` endpoint.
- Non-goals:
  - No writes, no realtime/socket events, no schema/migration changes.
  - Not restricted to *active* (WORKING/PAUSED/ENDED_SHIFT) steps — see clarified decision below.
  - Not the worker-facing "resume card" endpoint (that already exists).
  - **No full-payload batch expansion.** When the worker's last interaction was a batch, we return **one** full-payload representative plus a **compact `batch` descriptor** (count + ids + shared timestamp + state) — not a full payload per batch member. This bounds per-page query cost; the frontend drills into members on demand.

## Scope

- In scope:
  - New router file `app/beyo_manager/routers/api_v1/worker_stats.py`, registered under prefix `/api/v1/worker-stats`, restricted to `[ADMIN, MANAGER]`.
  - First endpoint: `GET /api/v1/worker-stats/last-interacted-steps` (offset-paginated).
  - New query service `app/beyo_manager/services/queries/worker_stats/list_workers_last_interacted_step.py`.
  - Extraction of the existing per-step payload builder into a shared module so both the existing endpoint and the new one use one implementation (DRY).
  - New user serializer for the worker-stat "main object" (`client_id`, `username`, `profile_picture`, `last_online`).
  - Frontend handoff doc under `backend/docs/handoff/to_frontend/`.
- Out of scope:
  - Any additional worker-stats endpoints (this router is a home for future ones, but only one endpoint ships now).
  - Aggregate/analytics tables, time totals, salaries.
  - Changing the behavior or response shape of `get_user_last_active_step_record`.
- Assumptions:
  - "Worker" here means a **human employee** with the `worker` role in the workspace — **not** a background/job worker. The trigger-map term "worker → 16/12/51" does **not** apply.
  - Workers are identified exactly like `list_users` does: `WorkspaceMembership` (active) → `WorkspaceRole` → `Role`, filtered to the `worker` role name/specialization, scoped to `ctx.workspace_id`.
  - The step's `latest_state_record` relationship holds the step's most recent record and is the same one `_build_step_record_payload` already relies on.
  - **Batch cohort signal.** `transition_step_state_batch` stamps every step in a batch with one shared `now` (`entered_at`/`exited_at`) and the same `created_by_id`; there is **no stored batch/group id**. Batch membership is therefore reconstructed implicitly as: a worker's set of steps whose latest worker-authored record shares the same `entered_at`, on `allows_batch_working` steps. `entered_at` (not `created_at`) is the reliable key — `created_at` may differ by microseconds per row.

## Clarifications required

All three blocking product decisions were resolved with the requester on 2026-07-15:

- [x] **Step semantics** — "last interacted step" = the worker's **most-recently-authored `StepStateRecord`, regardless of state** (not limited to the existing endpoint's active-state filter). Resolution: *any last step, regardless of state*.
- [x] **Worker set + empty handling** — return **all** `worker`-role users active in the workspace; `last_interacted_step` is `null` when a worker has authored no step records. Resolution: *all workers, null step if none*.
- [x] **Route naming** — new file `worker_stats.py`, prefix `/api/v1/worker-stats`. Resolution: *`/api/v1/worker-stats/*`*.

Remaining (non-blocking, decided by defaults — flagged for review, not implementation blockers):

- [ ] `last_state_record` inside the reused payload reflects the **step's** latest record (possibly authored by a different user), not necessarily the queried worker's own record. Default: keep it faithful to `_build_step_record_payload` as the intention requests. Revisit only if managers need "this worker's own last record on that step".

## Acceptance criteria

1. `GET /api/v1/worker-stats/last-interacted-steps` returns `200` for `ADMIN`/`MANAGER` and `403` for `WORKER`/`SELLER`/unauthenticated.
2. Response is `build_ok`-wrapped and shaped as:
   ```json
   {
     "workers": [
       {
         "user": { "client_id": "usr_…", "username": "…", "profile_picture": "… | null", "last_online": "ISO-8601 | null" },
         "last_interacted_step": { /* same shape as _build_step_record_payload output */ },
         "batch": {
           "count": 20,
           "step_ids": ["tsp_…", "tsp_…"],
           "shared_entered_at": "ISO-8601",
           "state": "WORKING"
         }
       }
     ],
     "workers_pagination": { "has_more": false, "limit": 50, "offset": 0, "total": 0 }
   }
   ```
   `last_interacted_step` is `null` when the worker has authored no step records. `batch` is `null` unless the last interaction was a batch cohort (see AC #8).
3. Every `worker`-role user active in the caller's workspace appears exactly once, ordered by `username` ascending; workers with no authored step records appear with `last_interacted_step: null` and `batch: null`.
4. For a worker who has authored step records, `last_interacted_step` corresponds to the worker's most-recently-**entered** step (the newest `entered_at` among that worker's per-step latest records), scoped to non-deleted `TaskStep`/`Task` in the workspace, and its payload matches the field-for-field shape produced by the existing `_build_step_record_payload`.
5. **Deterministic, majority-state selection.** When the newest `entered_at` maps to more than one step (a batch cohort), the representative surfaced in `last_interacted_step` is a step whose state is the cohort **majority state** (the modal state across the cohort). Ties are broken deterministically: (a) if two states share the max count, the winning state is the first one encountered scanning the cohort in total order (`created_at DESC, step client_id ASC`); (b) the representative is the first step in that total order whose state equals the winning state. The same worker+data always yields the same representative and state across requests.
6. Pagination is offset-based (per `07_queries_local.md`): `limit` (default 50, capped 200) and `offset` (≥ 0); `total` counts all matching workers; `has_more` computed via the `limit + 1` fetch technique.
7. Cross-workspace isolation: no worker, step, task, item, image, or case from another workspace appears in the response.
8. **Batch descriptor correctness.** When the representative step is `allows_batch_working` and ≥ 2 of the worker's steps share the winning `entered_at`, `batch` is populated: `count` = cohort size, `step_ids` = all cohort step client_ids (sorted, includes the representative), `shared_entered_at` = the winning `entered_at` (ISO-8601), `state` = the representative's state (the cohort majority state per AC #5) — always non-null when `batch` is present, and always equal to `last_interacted_step`'s state. A single-step last interaction (or a non-batch-capable step) yields `batch: null`.
9. The existing `get_user_last_active_step_record` endpoint continues to return its current shape unchanged after the payload-builder extraction (verified by its existing tests).

## Contracts and skills

### Read order block (document-only protocol)

Read order (canonical first, local delta second where present):
- `../architecture/06_commands.md` (baseline) → `../architecture/06_commands_local.md` (app delta)
- `../architecture/07_queries.md` (baseline) → `../architecture/07_queries_local.md` (app delta)

Applied precedence: local extension overrides baseline only for this app.

### Contracts loaded

- `../architecture/01_architecture.md`: overall layering (router → run_service → query service → serializer).
- `../architecture/04_context.md`: `ServiceContext` usage — `user_id`, `workspace_id`, `query_params`.
- `../architecture/05_errors.md`: error/outcome contract; `build_err` on `outcome.error`.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: this is a **read-only query**; local overrides pagination to **offset-based** — the new endpoint and count/`has_more` follow the offset convention (mirrors `list_users`).
- `../architecture/09_routers.md`: handler wiring — `require_roles`, `ServiceContext`, `run_service`, `build_ok`/`build_err`; router registration in `api_v1/__init__.py`.
- `../architecture/21_naming_conventions.md`: file/function/route naming for the new router, query, and serializer.
- `../architecture/40_identity.md` / `../architecture/41_user.md`: user identity fields; confirms `username`, `profile_picture`, `last_online`, `online` live on `User`.
- `../architecture/46_serialization.md`: how to write the new `serialize_user_worker_stat` serializer and shape the response.
- `../architecture/48_presence.md`: `last_online`/`online` semantics for the `user` object.

### Contracts consulted but not driving code

- `../architecture/06_commands.md` (+local): loaded per core policy, but **no command is written** (read-only feature). No `maybe_begin`/session-write rules apply.
- `../architecture/42_event.md`: core contract; **no events emitted** by this read-only query.

### Added from guide

- `../architecture/15_testing.md`: `n+1` trigger — the payload builder runs multiple queries per step; tests must assert workspace isolation and bounded per-page work.
- `../architecture/50_*` (deterministic testing / n+1): `n+1` trigger — informs the fixture/isolation approach and the N+1 mitigation (pagination-bounded payload builds). Load only if a companion exists; otherwise fold its intent into the `15_testing` approach.

### Excluded contracts

- `../architecture/03_models.md`: no new/changed model.
- `../architecture/08_domain.md`: no new domain aggregate; reusing existing serializers.
- `../architecture/11_infra_events.md`, `../architecture/13_sockets.md`: read-only; no realtime.
- `../architecture/30_migrations.md`: no schema change.
- `../architecture/16_background_jobs.md`, `../architecture/12_infra_redis.md`, `../architecture/51_worker_runtime.md`: **explicitly excluded** — "worker" here is a human role, not a job runtime. (Guards against the `worker` trigger mis-firing.)

### File read intent — pattern vs. relational

Relational reads already performed (understanding what exists — legitimate):
- `working_sections.py` router and `get_user_last_active_step_record.py` — the pattern to mirror and the exact payload builder to extract.
- `list_users.py` / `get_live_workspace_presence.py` — how workers are identified (WorkspaceMembership → WorkspaceRole → Role) and how offset pagination is shaped.
- `domain/users/serializers.py`, `models/tables/users/user.py`, `models/tables/tasks/step_state_record.py` — exact field names/types.

No prohibited pattern reads required: router skeleton comes from `09_routers.md`, query/pagination shape from `07(+local)`, serializer shape from `46_serialization.md`.

### Skill selection

- Primary skill: none beyond the contract-goal-mapping guide (`task_system/backend_contract_goal_mapping_guide.md`) — standard backend query/router work.
- Router trigger terms: `worker` (human), `query`, `router`, `serialization`, `pagination`.
- Excluded alternatives: background-worker / job-runtime skills — the human-vs-job "worker" collision must not pull them in.

## Implementation plan

1. **Extract the shared step-record payload builder.**
   - Create `app/beyo_manager/services/queries/working_sections/step_record_payload.py` exposing public `build_step_record_payload(ctx, step)` and `load_step_with_latest_record(ctx, step_id)`, moved verbatim from `get_user_last_active_step_record.py` (drop the leading underscore). Keep `_ACTIVE_STATES`/`_ACTIVE_RECORD_PRIORITY` in the original file (they are specific to the active-record selection, not the payload).
   - Update `get_user_last_active_step_record.py` to import `build_step_record_payload` / `load_step_with_latest_record` from the new module (replace the two local defs). No behavior change — its tests must still pass.

2. **Add the worker-stat user serializer.**
   - In `app/beyo_manager/domain/users/serializers.py`, add `serialize_user_worker_stat(user) -> dict` returning `{ "client_id", "username", "profile_picture", "last_online": user.last_online.isoformat() if user.last_online else None }` (per `46_serialization.md`).

3. **Write the query service.**
   - New package `app/beyo_manager/services/queries/worker_stats/` (`__init__.py` + `list_workers_last_interacted_step.py`).
   - Step 3a — **paginate the workers**: base query joins `WorkspaceMembership (is_active) → WorkspaceRole → Role`, filtered to `ctx.workspace_id` and the `worker` role (match `Role.name == "worker"` OR `WorkspaceRole.specialization == "worker"`, mirroring `list_users`' role filter). `total` = distinct user count; page = `order_by(User.username.asc()).offset(offset).limit(limit + 1)`; compute `has_more` from the extra row.
   - Step 3b — **resolve each worker's last-interacted step(s) + batch cohort, set-based**: for the page's `user_ids`, run **one** two-level window query over `StepStateRecord` joined to non-deleted `TaskStep`/`Task` (workspace-scoped), `WHERE created_by_id IN (user_ids)`:
     - Inner CTE — the worker's latest record **per step**: `ROW_NUMBER() OVER (PARTITION BY created_by_id, step_id ORDER BY entered_at DESC, created_at DESC, StepStateRecord.client_id DESC) = 1`, carrying `(created_by_id, step_id, entered_at, state, allows_batch_working)`.
     - Outer — keep the newest-entered cohort per worker: `RANK() OVER (PARTITION BY created_by_id ORDER BY entered_at DESC) = 1`. This returns **1 row** for a normal last step and **N rows** (one per cohort step, all sharing `entered_at`) for a batch — the tie is surfaced, never resolved arbitrarily.
   - Step 3c — **assemble per worker** (in username order):
     - Group the step-3b rows by `created_by_id`. No rows → `last_interacted_step: null`, `batch: null`.
     - Pick the deterministic **representative (majority state)**: order the cohort rows by `created_at DESC, step_id ASC` (all share `entered_at`); count states; winning state = the modal state, ties broken by the first state seen in that order; representative = the first row whose state equals the winning state. `load_step_with_latest_record` + `build_step_record_payload` for **only** that representative.
     - **Batch descriptor**: if representative `allows_batch_working` and cohort size ≥ 2 → `batch = { "count": len, "step_ids": sorted(step_ids), "shared_entered_at": entered_at.isoformat(), "state": representative.state.value }` (equals the representative's / majority state); otherwise `batch = null`.
     - Emit `{ "user": serialize_user_worker_stat(user), "last_interacted_step": payload_or_null, "batch": batch_or_null }`.
   - Cost note: exactly **one** full payload build per worker regardless of batch size (bounds the N+1 to page size).
   - Return `{ "workers": [...], "workers_pagination": {"has_more", "limit", "offset", "total"} }`.

4. **Write the router.**
   - New file `app/beyo_manager/routers/api_v1/worker_stats.py`: `router = APIRouter()`, handler `get_workers_last_interacted_step_route` at `@router.get("/last-interacted-steps")`, guarded by `Depends(require_roles([ADMIN, MANAGER]))`, `session = Depends(get_db)`, `limit: int = Query(50, le=200)`, `offset: int = Query(0, ge=0)`. Build `ServiceContext(incoming_data={}, query_params={"limit": limit, "offset": offset}, identity=claims, session=session)`, `run_service`, then `build_err`/`build_ok` — exactly the shape in `09_routers.md`.

5. **Register the router.**
   - In `app/beyo_manager/routers/api_v1/__init__.py`, add `worker_stats` to the import block and `app.include_router(worker_stats.router, prefix="/api/v1/worker-stats", tags=["worker-stats"])`.

6. **Tests** (`15_testing.md`): manager sees all workers ordered by username; worker with no records → `null`/`null`; worker with a single last step → correct step, `batch: null`; **batch cohort** → representative is deterministic (assert stable across repeated calls), `batch.count`/`step_ids`/`shared_entered_at` correct, and exactly one full payload built; **mixed-state cohort** → representative + `batch.state` = the majority state, and `last_interacted_step.state == batch.state`; non-batch-capable step never gets a `batch`; role gate (`WORKER`/`SELLER` → 403); cross-workspace isolation; offset pagination (`has_more`, `total`); regression pass on the existing `get_user_last_active_step_record` tests after extraction.

7. **Frontend handoff doc.**
   - After implementation, Codex writes `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md` from `TEMPLATE_HANDOFF_TO_FRONTEND.md`: endpoint, auth (manager-only), request (`limit`/`offset`), full response shape (nested step payload, the `null` case, **and the `batch` descriptor** — count/step_ids/shared_entered_at/state), how to render a batch ("representative card + '+N in batch', drill into members via existing per-step endpoints"), error cases (403), and a note that `last_interacted_step` mirrors the existing worker-facing resume-card payload shape.

## Risks and mitigations

- Risk: **N+1 on payload building** — `build_step_record_payload` issues several queries per step, so a page of N workers with steps ≈ N × M queries.
  Mitigation: pagination bounds N to `limit` (≤ 200); the per-worker last-step + batch-cohort lookup is collapsed into **one** two-level window query; **only the representative** gets a full payload (one build per worker, independent of batch size). If a page proves slow, batch-load task/item/image/case data across the page in a follow-up.
- Risk: **Non-deterministic batch representative** — batch steps tie on `entered_at`, so a naive "newest" pick is arbitrary and can flip between requests.
  Mitigation: RANK-based cohort detection keyed on `entered_at` plus a total-order tie-break (`entered_at DESC, created_at DESC, step_id ASC`); asserted stable in tests (AC #5).
- Risk: **Implicit batch reconstruction is heuristic** — there is no stored batch id; two unrelated single-step transitions by the same worker at the exact same instant could look like a cohort.
  Mitigation: gate the `batch` descriptor on `allows_batch_working`; near-impossible for genuine non-batch single-step transitions to collide on `entered_at`. If false grouping is ever observed, the durable fix is a stored batch/correlation id on `StepStateRecord` (out of scope here — flag for a follow-up).
- Risk: **Extraction regresses the existing endpoint.**
  Mitigation: move code verbatim (only the underscore/name changes), keep active-state constants in place, and rely on the existing endpoint's tests as the regression gate (AC #7).
- Risk: **`last_state_record` author ≠ queried worker** (payload surfaces the step's latest record, which may be another user's).
  Mitigation: faithful to the intention ("same serialization technique"). Flagged as a non-blocking clarification; revisit only if product wants the worker's own record.
- Risk: **Human-worker vs job-worker contract drift** — the `worker` trigger could pull job-runtime contracts.
  Mitigation: explicitly excluded in the contracts section; role identification copied from `list_users`, not from any job-runtime path.
- Risk: **Role identity mismatch** — role stored as `Role.name` vs `WorkspaceRole.specialization`.
  Mitigation: match both (OR), exactly as `list_users`' `role_filter` does.

## Validation plan

- `GET /api/v1/worker-stats/last-interacted-steps` as MANAGER → `200`, well-formed body per AC #2; as WORKER → `403`.
- Seed two workspaces; assert isolation (AC #6).
- Seed a worker with 0 records (→ `null`/`null`) and a worker whose newest authored record is on step X across mixed states (→ step X, `batch: null`). (AC #3/#4)
- Seed a worker whose last interaction is a batch of ≥ 3 `allows_batch_working` steps (shared `entered_at`): assert deterministic representative across repeated calls, `batch.count`/`step_ids`/`state` correct, one payload build. (AC #5/#8)
- Pagination: with `limit=1`, page through and assert `total`, `has_more`, and stable username ordering. (AC #5)
- Run existing `get_user_last_active_step_record` tests → still green (AC #7).
- `ruff`/`mypy` (or repo's configured lint/type checks) clean on new/edited files.

## Review log

- `2026-07-15` requester: resolved the three blocking decisions (any-state last step; all workers with null; `/api/v1/worker-stats/*`).
- `2026-07-15` owner: encoded decisions into scope, acceptance criteria, and route/response shape.
- `2026-07-15` requester: raised batch-step handling (batch steps share one timestamp). Decision: surface the cohort as **one representative + compact `batch` descriptor**.
- `2026-07-15` owner: confirmed via `transition_step_state_batch` that batch records share a single `entered_at`/`created_by_id` with no stored batch id; encoded set-based RANK cohort detection, deterministic tie-break, and the `batch` descriptor into scope/AC/implementation/risks/validation.
- `2026-07-15` requester: for mixed-state cohorts the representative (and `batch.state`) must reflect the **majority state**, never `null`.
- `2026-07-15` owner: replaced the "uniform-else-null" state rule with modal/majority-state selection (deterministic tie-break); representative is now chosen from the majority-state steps, and `batch.state == last_interacted_step.state`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`

## Implementation completion

- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_worker_stats_last_interacted_steps_20260715.md`
- Frontend handoff: `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_stats_last_interacted_steps_20260715.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_worker_stats_last_interacted_steps_20260715.md`
- Validation: static checks passed; existing PostgreSQL payload-regression suite passed (`4 passed`).
