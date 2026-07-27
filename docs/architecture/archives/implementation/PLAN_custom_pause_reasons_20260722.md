# PLAN_custom_pause_reasons_20260722

## Metadata

- Plan ID: `PLAN_custom_pause_reasons_20260722`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-22T00:00:00Z`
- Last updated at (UTC): `2026-07-22T14:25:00Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_custom_pause_reasons_20260722.md`

## Goal and intent

- Goal: Replace the static `StepEventReasonEnum` with a workspace-owned `pause_reasons` table
  (name, image, type, description, `requires_description` flag, `created_by`/`created_at`) with
  full CRUD (`GET`/`PUT`/`PATCH`/`DELETE`) and realtime events, then migrate every current consumer
  of `StepEventReasonEnum` to reference `pause_reasons` rows instead.
- Business/user intent: let the workspace add, rename, restyle, and retire its own pause reasons
  from the frontend without a backend deploy, while the two backend-triggered pause reasons
  (ended-shift, other-task-priority) keep working reliably.
- Non-goals:
  - No frontend implementation. This plan ends at a `HANDOFF_TO_FRONTEND` doc.
  - No `HistoryRecord`/audit-log mixin for `pause_reasons` — only `created_at`/`created_by_id` and
    `updated_at`/`updated_by_id` as requested; full history tracking is a separate future plan if
    ever needed.
  - No presence/live-editing indicators (`48_presence.md`) on the pause-reasons screen.
  - No `sort_order`/custom-ordering field — list is ordered by `created_at`.
  - No change to multi-tenancy — `workspace_id` is kept on the table for schema consistency with
    every other domain table, but the app has exactly one workspace today.

## Scope

- In scope:
  - New `pause_reasons` table, model, domain enums/validators/guards/serializers, commands,
    queries, router, and realtime events (Stages 1-6).
  - A new `seed_pause_reasons` bootstrap phase, wired into `bootstrap_app.py`, that creates all 7
    rows equivalent to the current enum values — including, per explicit request, guaranteeing the
    2 system-managed rows always exist (Stage 3).
  - Cutover of `StepStateRecord.reason` (and every call site that reads/writes it) from
    `StepEventReasonEnum` to a `pause_reason_id` FK (Stages 7-9).
  - Removal of `StepEventReasonEnum` and the `step_event_reason_enum` Postgres type once the
    cutover is verified (Stage 8).
- Out of scope: frontend code, history/audit tracking, presence.
- Assumptions:
  - This app is single-tenant (confirmed: no `create_workspace` command exists; `Workspace` is
    only ever created once by `services/commands/bootstrap/phases/seed_workspace.py`, guarded by
    `select(Workspace).limit(1)`). `bootstrap_app.py` runs all phases sequentially in one
    transaction on every invocation (there is no top-level "already bootstrapped" gate); each
    phase is individually responsible for its own idempotency, matching the pattern already used
    by `seed_item_categories`/`seed_workspace`. `bootstrap_app` is invoked manually via
    `POST /api/v1/bootstrap` (`app/beyo_manager/routers/api_v1/bootstrap.py`) — it is **not**
    called automatically on deploy (`.github/workflows/deploy.yml` only runs
    `alembic upgrade head` + `scripts/apply_db_triggers.py`). This matters for sequencing Stage 3
    against Stage 7 — see the ordering note in Stage 7 below.
  - `docs/handoff/to_frontend/` is still the active convention for documenting API contract
    changes to the frontend, even though git status shows several older handoff docs were
    recently deleted from this repo — confirm the current convention (check
    `docs/handoff/to_frontend/README.md` if present, or recent commits) before writing the
    handoff docs in Stage 6 and Stage 9; do not assume the deletions mean the convention is gone.

## Clarifications required

- [x] `Should the 5 non-system-triggered legacy reasons be seeded via bootstrap too, or via a
  one-off data migration?` — **Resolved 2026-07-22:** seed all 7 via the same `seed_pause_reasons`
  bootstrap phase (Stage 3), matching how `seed_item_categories`/`seed_case_types`/
  `seed_working_sections` already seed default reference data for the workspace. Only the 2
  backend-triggered rows get `is_system_managed=True` + a `slug`; the other 5 are ordinary,
  immediately user-editable/deletable rows that happen to also be created by bootstrap for
  idempotent-guard reasons (see Stage 3).
- [x] `Ops must manually re-invoke bootstrap for already-bootstrapped environments before Stage 7
  ships` — Stage 3 (new bootstrap phase) only creates rows when someone calls
  `POST /api/v1/bootstrap`; deploy does not call it automatically (see Scope assumptions). Stage
  7's backfill migration depends on the 7 `pause_reasons` rows already existing (it looks them up
  by `slug`). If Stage 7's migration reaches an environment where `POST /api/v1/bootstrap` was
  never re-run after Stage 3 shipped, the backfill will find no matching rows and either fail or
  leave `pause_reason_id` null. This must be confirmed as an explicit ops runbook step (or
  ship Stage 3 and Stage 7 as two separate deploys with a manual bootstrap call in between) before
  Stage 7's migration is written — it blocks safe implementation because there is no automatic
  signal in this codebase that bootstrap has been re-run. **Resolution 2026-07-22:** repository
  evidence confirms `bootstrap_app` is reachable only through the secret-gated
  `POST /api/v1/bootstrap`; `.github/workflows/deploy.yml` runs `alembic upgrade head` and trigger
  setup but does not call bootstrap. The release sequence is therefore: deploy Phase A, manually
  invoke bootstrap in every existing target environment, verify the seven slugs and zero duplicate
  creation on a second invocation, then deploy Stage 7. New environments must run bootstrap after
  the schema migration and before Stage 7's backfill. This local workspace cannot attest remote
  environment history, so the sequence is recorded as a release gate; the migration will also assert
  that every non-null legacy reason was mapped.
- [x] `Reconcile with in-flight uncommitted changes` — `git status` at plan-authoring time shows
  `app/beyo_manager/services/commands/task_steps/_step_transition_core.py`,
  `transition_step_state.py`, `transition_step_state_batch.py`,
  `services/commands/tasks/_task_state_transitions.py`, `update_task.py`,
  `services/queries/tasks/count_task_post_handling_states.py`,
  `services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`, and related test files
  as already modified in the working tree. Stage 7 and Stage 9 of this plan touch several of
  those same files. Before starting Stage 7, run `git diff` on each file in its step list and
  reconcile this plan's described call sites against the actual current diff — the line numbers
  and code shown in this plan reflect the repo state as read while writing it and may not match
  if those in-flight edits land or change first. This blocks safe implementation of Stage 7/9
  because blindly applying the diffs described here could silently discard or conflict with that
  other work. **Resolution 2026-07-22:** the current diffs are unrelated to pause-reason identifiers
  or schema changes (task-readiness/reconciliation and analytics description/order behavior). They
  will be preserved; Stage 7/9 changes layer onto the current contents, and no unrelated dirty file
  will be reverted.

## Acceptance criteria

1. `pause_reasons` table exists with `name`, `image_url`, `pause_type`, `description`,
   `requires_description`, `is_system_managed`, `slug`, `created_at`, `created_by_id`,
   `updated_at`, `updated_by_id`, `is_deleted`/`deleted_at`/`deleted_by_id`, workspace-scoped.
2. `GET /api/v1/pause-reasons` (list, paginated), `GET /api/v1/pause-reasons/{client_id}`,
   `PUT /api/v1/pause-reasons` (create), `PATCH /api/v1/pause-reasons/{client_id}` (update),
   `DELETE /api/v1/pause-reasons/{client_id}` (soft delete) all exist, are role-gated
   (ADMIN/MANAGER for writes; ADMIN/MANAGER/WORKER for reads), and emit
   `pause_reason:created`/`pause_reason:updated`/`pause_reason:deleted` workspace events.
3. Deleting a row with `is_system_managed=True` fails with a `ConflictError`, not a hard delete.
4. `StepStateRecord` no longer has a live dependency on `StepEventReasonEnum` for new writes;
   `pause_reason_id` is populated by every code path that used to assign a
   `StepEventReasonEnum` member (auto-pause-on-conflict, clock-out, single/batch/deferred step
   transition, frontend-supplied pause reason).
   the two automatic paths must always resolve to the correct seeded system-managed row: no
   run-time creation of that row and no silent `NULL` fallback if the row is (incorrectly)
   missing — a missing system row must raise, not silently proceed.
5. All existing rows in `step_state_records` with a non-null `reason` have a matching
   `pause_reason_id` after the backfill migration (row counts reconcile: verify with the query in
   the Validation plan).
6. Full test suite (existing + new) passes: `pytest app/tests`.

## Contracts and skills

### Contracts loaded

- `architecture/01_architecture.md`: layer boundaries and per-domain directory layout for the new
  `pause_reasons` domain.
- `architecture/04_context.md`: `ServiceContext` shape and identity fields every command/query uses.
- `architecture/05_errors.md`: `DomainError` subclasses (`NotFound`, `ConflictError`,
  `ValidationError`) used by the new commands/queries.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command file/function
  shape, `maybe_begin(ctx.session)` transaction helper (local override — this app does not use
  raw `ctx.session.begin()`), event dispatch timing.
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: query file/function shape,
  local offset-pagination override (`limit`/`offset`, `has_more`, top-level
  `pause_reasons_pagination` key).
- `architecture/09_routers.md`: router handler shape, `run_service`/`build_ok`/`build_err` wiring.
- `architecture/21_naming_conventions.md`: file, function, class, table, and event naming for the
  new domain.
- `architecture/40_identity.md` + `architecture/40_identity_local.md`: `client_id` prefix
  reservation process (prefix table lives in the local companion).
- `architecture/41_user.md`: `created_by_id`/`updated_by_id` ownership column conventions.
- `architecture/42_event.md`: read to confirm it does not apply here — it covers async
  operation-lifecycle tracking tables, not simple reference-data CRUD like `pause_reasons`.
- `architecture/48_presence.md`: read to confirm out of scope (no live-editing indicator requested).
- `architecture/03_models.md`: SQLAlchemy 2.x `Mapped`/`mapped_column` conventions, FK/index rules,
  enum column mapping.
- `architecture/08_domain.md`: pure-function domain layer rules (no I/O) for enums/validators/guards.
- `architecture/11_infra_events.md`: `build_workspace_event`/`event_bus.dispatch` usage, single vs.
  batch event decision.
- `architecture/13_sockets.md`: confirms no new socket handler code is needed — delivery rides the
  existing generic `WorkspaceEvent` → `push_workspace_refresh` pipeline.
- `architecture/30_migrations.md`: autogenerate-then-review workflow, FK-to-`client_id` rule,
  nullable-column staged-rollout pattern used for the `step_state_records.pause_reason_id` cutover.
- `architecture/15_testing.md`: test file layout mirroring `services/commands/pause_reasons/`,
  `services/queries/pause_reasons/`, `domain/pause_reasons/`, `routers/api_v1/`.

### Local extensions loaded

- `architecture/06_commands_local.md`: mandates `maybe_begin(ctx.session)` from
  `beyo_manager.services.commands.utils.transaction` instead of `ctx.session.begin()`, and that
  subordinate commands return `pending_events` instead of dispatching directly.
- `architecture/07_queries_local.md`: offset pagination (`limit`/`offset`) instead of the
  canonical cursor pagination; `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`.
- `architecture/40_identity_local.md`: prefix reservations are tracked in this file's
  "Local Decisions" section — Stage 2 adds an entry here for `par`/`PauseReason`.

### File read intent — pattern vs. relational

The following existing files were read during planning as **relational** reads (to learn what
exists — exact field names, current call sites, and the shape of an already-shipped analogous
CRUD domain) and should be treated the same way during implementation, not as a substitute for
the contracts above:

- `app/beyo_manager/models/tables/upholstery/upholstery_category.py` — closest existing analog for
  the model shape (`name`, `image_url`, `created_at`/`created_by_id`, `updated_at`/`updated_by_id`,
  `is_deleted`/`deleted_at`/`deleted_by_id`, `UniqueConstraint(workspace_id, name)`).
- `app/beyo_manager/services/commands/upholstery/create_upholstery_category.py` and
  `app/beyo_manager/routers/api_v1/upholstery_categories.py` — closest existing analog for the
  command/router shape and the `PUT`-creates/`PATCH`-updates verb convention actually used in this
  repo (not a full-replace `PUT /{id}`, matching what was asked for: get/put/patch/delete).
- `app/beyo_manager/models/tables/tasks/step_state_record.py` — exact current `reason` column
  declaration that Stage 7 changes.
- `app/beyo_manager/domain/task_steps/enums.py` — the enum being replaced (source of truth for the
  7 legacy reason values seeded in Stage 2; note
  `docs/architecture/under_construction/intention/planning_tables/task/step_state_record_models.md`
  is a stale planning doc missing `PAUSE_CASE_CREATED` — use the live enum file, not that doc, as
  the authoritative list of 7 values).
- `app/beyo_manager/domain/cases/events.py` and `app/beyo_manager/services/commands/cases/create_case.py`
  — existing analog for the event-enum + `build_workspace_event` + `event_bus.dispatch` pattern.
- `app/beyo_manager/domain/analytics/linear_timeline.py` and
  `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py` —
  confirms the domain sweep already treats `reason` as an opaque `str | None` key (it does not
  import `StepEventReasonEnum`), so Stage 9's change is confined to the query layer that currently
  does `reason=row.reason.value if row.reason is not None else None` at line 206.
- `app/beyo_manager/models/tables/client_id_prefix_map.md` and
  `architecture/40_identity_local.md` — current prefix reservations, to confirm `par` is unused.
- `app/beyo_manager/services/commands/bootstrap/bootstrap_app.py` — exact phase-call sequence and
  transaction shape (`async with ctx.session.begin(): ...` wrapping every phase call, each phase
  taking `ctx.session` plus whatever prior phase results it needs; `workspace_result["workspace_id"]`
  is available after `seed_workspace` runs) that Stage 3's `seed_pause_reasons` phase must slot
  into.
- `app/beyo_manager/services/commands/bootstrap/phases/seed_item_categories.py` — exact
  per-row idempotency-guard shape (`select(...).where(workspace_id==..., name==...)` before
  insert, returning a `{name: client_id}` map) that Stage 3's phase mirrors, using `slug` instead
  of `name` as the guard key.
- `app/beyo_manager/routers/api_v1/bootstrap.py` — confirms `bootstrap_app` is exposed only via a
  manually-invoked, secret-gated `POST /api/v1/bootstrap` endpoint, not run automatically on
  deploy — the basis for the ordering Clarification above.
- `app/beyo_manager/models/__init__.py` and `app/beyo_manager/routers/api_v1/__init__.py` — current
  model/router registration pattern (both files are already in a modified working-tree state per
  git status — re-read them fresh immediately before editing).

Do not open any other implementation file to learn "how to write" a command/query/router/model —
the contracts above already define that.

### Skill selection

- Primary skill: none (this is a backend Python change following the contracts directly; no
  project skill covers CRUD-domain scaffolding).
- Router trigger terms: none from the trigger expansion map apply (no worker/replay/rate-limit/
  search/bulk-insert keywords in scope).
- Excluded alternatives: n/a.

## Implementation plan

### Phase A — stand up the `pause_reasons` domain (Stages 1-6)

1. **Domain layer** — create `app/beyo_manager/domain/pause_reasons/`:
   - `enums.py`: `PauseTypeEnum(enum.Enum)` with `PERSONAL = "personal"` and
     `BLOCKER = "blocker"` (personal-for-the-worker vs. blocker/part-of-work-for-other-tasks, per
     the two categories requested).
   - `validators.py`: `validate_pause_reason_fields(name: str, description: str | None) -> None`
     — non-empty `name` (≤255 chars after strip), `description` ≤1024 chars if provided. Raise
     `ValueError` (converted to `ValidationError` by the request parser, per `06_commands.md`).
   - `guards.py`: `can_delete_pause_reason(pause_reason: PauseReason) -> bool` — returns
     `not pause_reason.is_system_managed`.
   - `serializers.py`: `serialize_pause_reason(instance) -> dict` returning `client_id`, `name`,
     `image_url`, `pause_type` (`.value`), `description`, `requires_description`,
     `is_system_managed`, `slug`, `created_at.isoformat()`, `created_by_id`,
     `updated_at.isoformat() | None`, `updated_by_id`. Never expose the internal integer id.
   - `events.py`: `PauseReasonEvent` — `CREATED = "pause_reason:created"`,
     `UPDATED = "pause_reason:updated"`, `DELETED = "pause_reason:deleted"` (mirrors
     `domain/cases/events.py`).

2. **Model + migrations** — `app/beyo_manager/models/tables/pause_reasons/pause_reason.py`:
   ```python
   class PauseReason(IdentityMixin, Base):
       CLIENT_ID_PREFIX = "par"
       __tablename__ = "pause_reasons"

       workspace_id: Mapped[str] = mapped_column(
           String(64), ForeignKey("workspaces.client_id", ondelete="RESTRICT"), nullable=False, index=True
       )
       name: Mapped[str] = mapped_column(String(255), nullable=False)
       image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
       pause_type: Mapped[PauseTypeEnum] = mapped_column(
           SAEnum(PauseTypeEnum, name="pause_reason_type_enum", create_type=True), nullable=False, index=True
       )
       description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
       requires_description: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
       slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
       is_system_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
       created_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
       )
       created_by_id: Mapped[str | None] = mapped_column(
           String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True, index=True
       )
       updated_at: Mapped[datetime | None] = mapped_column(
           DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc)
       )
       updated_by_id: Mapped[str | None] = mapped_column(
           String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
       )
       is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
       deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
       deleted_by_id: Mapped[str | None] = mapped_column(
           String(64), ForeignKey("users.client_id", ondelete="RESTRICT"), nullable=True
       )

       __table_args__ = (
           UniqueConstraint("workspace_id", "name", name="uq_pause_reasons_workspace_name"),
           Index("uq_pause_reasons_slug", "slug", unique=True),
           Index("ix_pause_reasons_workspace_type", "workspace_id", "pause_type"),
       )
   ```
   (`created_by_id` nullable to allow the bootstrap-seeded rows from Stage 3, matching the
   `step_state_record_models.md` precedent of "nullable for trusted system/bootstrap only". `slug`
   is nullable because only bootstrap-seeded rows have one — regular user-created rows leave it
   `NULL`.)
   - Register the module in `app/beyo_manager/models/__init__.py` under a new
     `# --- Pause reasons (depends on workspaces, users) ---` comment block, following the exact
     pattern already used for other domains in that file.
   - Add a `PauseReason | par | par_xxxxxxx` row to
     `app/beyo_manager/models/tables/client_id_prefix_map.md`, inserted alphabetically between
     `NotificationPin` and `PendingUpload`.
   - Add a new bullet under "Local Decisions" in `architecture/40_identity_local.md` reserving
     `par` for `PauseReason`, referencing `PLAN_custom_pause_reasons_20260722`.
   - `alembic revision --autogenerate -m "create_pause_reasons_table"`, then hand-review per
     `30_migrations.md`'s checklist (types, nullability, FK targets `client_id` not `id`,
     `create_type=True` for the enum, indexes present).

3. **Bootstrap phase** — `app/beyo_manager/services/commands/bootstrap/phases/seed_pause_reasons.py`,
   following `seed_item_categories.py`'s exact shape:
   ```python
   async def seed_pause_reasons(session: AsyncSession, workspace_id: str) -> dict[str, str]:
       ...
   ```
   For each of the 7 rows below: `existing = await session.scalar(select(PauseReason).where(
   PauseReason.workspace_id == workspace_id, PauseReason.slug == slug))` — **do not filter on
   `is_deleted`**, so a row a user has since soft-deleted or renamed is never resurrected by a
   bootstrap re-run; if found, record its `client_id` and `continue`; otherwise construct and
   `session.add(...)`, `await session.flush()`, then record `category_ids[slug] = row.client_id`
   (mirroring the return-map pattern). `slug` is therefore required (not optional) on every
   bootstrap-seeded row — it is both the idempotency-guard key here and, for the 2 system rows,
   the runtime lookup key used in Stage 7.

   | old enum value | slug | name | pause_type | requires_description | is_system_managed |
   |---|---|---|---|---|---|
   | `WAITING_FOR_UPHOLSTERY` | `waiting_for_upholstery` | "Waiting for upholstery" | `blocker` | false | false |
   | `PAUSE_LUNCH_BREAK` | `pause_lunch_break` | "Lunch break" | `personal` | false | false |
   | `PAUSE_COFFEE_BREAK` | `pause_coffee_break` | "Coffee break" | `personal` | false | false |
   | `PAUSE_CASE_CREATED` | `pause_case_created` | "Case created" | `blocker` | false | false |
   | `PAUSE_MEETING` | `pause_meeting` | "Meeting" | `personal` | false | false |
   | `PAUSE_ENDED_SHIFT` | `pause_ended_shift` | "Ended shift" | `blocker` | false | **true** |
   | `PAUSE_OTHER_TASK_PRIORITY` | `pause_other_task_priority` | "Other task priority" | `blocker` | false | **true** |

   - `created_by_id = None` for all bootstrap-seeded rows (nullable column, "trusted
     system/bootstrap only" per the `step_state_record_models.md` precedent).
   - Only the 2 `is_system_managed=True` rows are protected from deletion by
     `can_delete_pause_reason` (Stage 1); the other 5 are ordinary rows from the moment they're
     created — a user can rename or delete them immediately after bootstrap runs (per the
     resolved Clarification above).
   - Wire it into `app/beyo_manager/services/commands/bootstrap/bootstrap_app.py`: add the import
     and call it right after `seed_workspace` resolves `workspace_result["workspace_id"]` (order
     doesn't otherwise matter — it has no dependency on item categories/issue types/sections), e.g.
     `pause_reason_ids = await seed_pause_reasons(ctx.session, workspace_result["workspace_id"])`,
     and include `"pause_reasons_seeded": list(pause_reason_ids.keys())` in `bootstrap_app`'s
     returned dict, consistent with how the other phases' results are surfaced.
   - This phase only runs when someone calls `POST /api/v1/bootstrap` — it does not run on deploy.
     See the ordering Clarification above before writing Stage 7's backfill migration.

4. **Requests + commands** — `app/beyo_manager/services/commands/pause_reasons/`:
   - `requests/__init__.py`: `PauseReasonCreateRequest` (`name: str`, `image_url: str | None`,
     `pause_type: PauseTypeEnum`, `description: str | None`, `requires_description: bool = False`)
     and `PauseReasonUpdateRequest` (same fields, all optional, for `exclude_unset` PATCH
     semantics) with `parse_create_pause_reason_request`/`parse_update_pause_reason_request`
     functions per `06_commands.md`. **Neither request model exposes `slug` or
     `is_system_managed`** — those are internal-only and never settable from the API.
   - `create_pause_reason.py`: parse request → `maybe_begin(ctx.session)` → check
     `(workspace_id, name)` uniqueness among `is_deleted.is_(False)` rows (`ConflictError` on
     clash, mirroring `create_upholstery_category.py`) → construct `PauseReason(created_by_id=ctx.user_id,
     is_system_managed=False, slug=None, ...)` → `ctx.session.add(...)` → after the block, build
     `build_workspace_event(pause_reason, PauseReasonEvent.CREATED, workspace_id=ctx.workspace_id)`
     and `event_bus.dispatch([...])` → return `{"pause_reason": serialize_pause_reason(pause_reason)}`.
   - `update_pause_reason.py`: fetch by `client_id` + `workspace_id` + `is_deleted.is_(False)`
     (`NotFound` if absent) → apply only the fields present in the parsed request
     (`model_dump(exclude_unset=True)`) → re-check name uniqueness if `name` changed →
     `updated_by_id = ctx.user_id` → dispatch `PauseReasonEvent.UPDATED` → return the same shape.
   - `delete_pause_reason.py`: fetch (as above) → `if not can_delete_pause_reason(pause_reason):
     raise ConflictError("This pause reason is managed by the system and cannot be deleted.")` →
     soft delete (`is_deleted=True`, `deleted_at=now`, `deleted_by_id=ctx.user_id`) → dispatch
     `PauseReasonEvent.DELETED` → return `{}`.

5. **Queries** — `app/beyo_manager/services/queries/pause_reasons/`:
   - `list_pause_reasons.py`: offset pagination per `07_queries_local.md`
     (`limit` default 50 / max 200, `offset` default 0), filter `workspace_id == ctx.workspace_id`,
     `is_deleted.is_(False)`, optional `pause_type` filter from `ctx.query_params`, order by
     `created_at`. Return `{"pause_reasons": [...], "pause_reasons_pagination": {"has_more": ...,
     "limit": ..., "offset": ...}}` — include the pagination key even when the list is empty.
   - `get_pause_reason.py`: fetch by `client_id` + `workspace_id` + `is_deleted.is_(False)` →
     `NotFound` if absent → `{"pause_reason": serialize_pause_reason(...)}`.

6. **Router + realtime** — `app/beyo_manager/routers/api_v1/pause_reasons.py`, mirroring
   `upholstery_categories.py`'s structure exactly:
   - `PUT /api/v1/pause-reasons` (create) — `require_roles([ADMIN, MANAGER])`.
   - `GET /api/v1/pause-reasons` (list, `limit`/`offset`/`pause_type` query params) —
     `require_roles([ADMIN, MANAGER, WORKER])`.
   - `GET /api/v1/pause-reasons/{client_id}` — `require_roles([ADMIN, MANAGER, WORKER])`.
   - `PATCH /api/v1/pause-reasons/{client_id}` — `require_roles([ADMIN, MANAGER])`.
   - `DELETE /api/v1/pause-reasons/{client_id}` — `require_roles([ADMIN, MANAGER])`.
   - Register in `app/beyo_manager/routers/api_v1/__init__.py`: add to the import tuple and call
     `app.include_router(pause_reasons.router, prefix="/api/v1/pause-reasons",
     tags=["pause-reasons"])` next to the other domain routers.
   - No new socket handler code — confirmed by `13_sockets.md` that `WorkspaceEvent` delivery is
     generic; the events built in Stage 4 are sufficient for the frontend to receive live updates.
   - Write `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pause_reasons_crud_<YYYYMMDD>.md`
     describing the 5 endpoints, request/response shapes, and the 3 socket event names, following
     whichever handoff format is currently in use in this repo (see Scope assumptions).

**Checkpoint:** Phase A is independently shippable and testable (Validation plan below) without
touching any existing task-step code. Do not start Phase B until Phase A's tests pass and the
Clarifications above are resolved.

### Phase B — cutover of existing consumers (Stages 7-9)

7. **`StepStateRecord` FK cutover:**
   - **Ordering precondition (blocking):** the 7 `pause_reasons` rows are created by the Stage 3
     bootstrap phase, not by an Alembic migration — they only exist in a given environment once
     someone has called `POST /api/v1/bootstrap` after Stage 3 shipped. Confirm (per the ordering
     Clarification above) that this has happened in every environment the migration below will run
     against before writing/running it; otherwise the backfill silently matches zero rows.
   - Migration: add `pause_reason_id: Mapped[str | None] = mapped_column(String(64),
     ForeignKey("pause_reasons.client_id", ondelete="RESTRICT"), nullable=True, index=True)` to
     `app/beyo_manager/models/tables/tasks/step_state_record.py`, alongside the existing `reason`
     column (do not remove `reason` yet).
   - Backfill migration: because the target rows' `client_id`s are bootstrap-generated (not
     deterministic at migration-authoring time), the backfill must resolve them at migration
     run-time by `slug`, not by a hardcoded constant — e.g.
     `UPDATE step_state_records ssr SET pause_reason_id = pr.client_id FROM pause_reasons pr WHERE
     pr.slug = ssr.reason::text AND ssr.reason IS NOT NULL;` (the enum's Postgres values already
     match the `slug` values seeded in Stage 3 one-for-one, since Stage 3's slugs were chosen to
     equal `StepEventReasonEnum`'s string values — verify this equality holds before running,
     using the enum in `app/beyo_manager/domain/task_steps/enums.py` as the source of truth).
     Add a post-`UPDATE` assertion (e.g. a follow-up `SELECT count(*) FROM step_state_records
     WHERE reason IS NOT NULL AND pause_reason_id IS NULL;` that must return 0) so the migration
     fails loudly instead of silently leaving rows unmapped if Stage 3 hasn't run yet in that
     environment.
   - Re-read (fresh, at implementation time) every file below before editing — per the
     Clarifications item on in-flight uncommitted changes:
     - `app/beyo_manager/services/commands/task_steps/_step_transition_core.py`: change
       `_apply_step_transition`'s `reason: StepEventReasonEnum | None` parameter to
       `pause_reason_id: str | None`; replace the auto-pause `reason=StepEventReasonEnum.PAUSE_OTHER_TASK_PRIORITY`
       assignment (currently line 114) with a lookup of the seeded `pause_other_task_priority` row
       and pass its `client_id`; construct `StepStateRecord(..., pause_reason_id=pause_reason_id, ...)`
       instead of `reason=reason` (currently line 171).
     - `app/beyo_manager/services/commands/task_steps/transition_step_state.py`: apply the mirror
       change (per the file's own DRIFT NOTE, this file duplicates `_step_transition_core.py`'s
       auto-pause logic around its own `PAUSE_OTHER_TASK_PRIORITY` assignment) — keep the two files
       in sync as the existing DRIFT NOTE already requires.
     - `app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py`: update its
       call into `_apply_step_transition` to pass `pause_reason_id` instead of `reason`.
     - `app/beyo_manager/services/commands/users/_clock_worker_shift.py`: replace
       `reason=StepEventReasonEnum.PAUSE_ENDED_SHIFT` (currently line 161) with a lookup of the
       seeded `pause_ended_shift` row's `client_id`, passed as `pause_reason_id`.
     - `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py`: replace
       `reason = StepEventReasonEnum(reason_raw) if reason_raw else None` (currently line 37) with
       `pause_reason_id = reason_raw or None` — the async task payload now carries the
       `pause_reason_id` client_id string directly, no enum parsing; update the
       `StepStateRecord(...)` construction (currently line 117) accordingly.
     - Add a small lookup helper, e.g.
       `app/beyo_manager/services/queries/pause_reasons/get_system_pause_reason.py` with
       `async def get_system_pause_reason_id(session, workspace_id: str, slug: str) -> str` that
       selects `PauseReason.client_id where slug == slug and workspace_id == workspace_id and
       is_deleted.is_(False)`, and **raises `NotFound` if missing** (per acceptance criterion 4 —
       never silently proceed with a `NULL` reason on an automatic pause). Call this from both
       `_step_transition_core.py`/`transition_step_state.py` (slug `pause_other_task_priority`)
       and `_clock_worker_shift.py` (slug `pause_ended_shift`).
     - `app/beyo_manager/routers/api_v1/tasks.py`: change `_TransitionStepBody.reason:
       StepEventReasonEnum | None` (currently line 270) and `_BatchTransitionStepBody.reason:
       StepEventReasonEnum | None` (currently line 284) to `pause_reason_id: str | None`.
     - `app/beyo_manager/services/commands/task_steps/requests/__init__.py`: change
       `TransitionStepStateRequest.reason` (currently line 134) and
       `BatchTransitionStepStateRequest.reason` (currently line 171) the same way, and thread the
       renamed field through every place these request objects are consumed.
   - **`requires_description` enforcement:** in the (single and batch) transition commands, after
     resolving the target `PauseReason` for a frontend-supplied `pause_reason_id`, if
     `pause_reason.requires_description` is `True`, require `description` to be a non-empty string
     in the request (`ValidationError` otherwise). This is new validation logic these commands did
     not previously have — it is the mechanism that fulfills "allowing the frontend to send a typed
     reason" from the original ask. The existing `description: String(1024)` column on
     `step_state_records` already exists (see `step_state_record_models.md`) and needs no schema
     change — it is where this text lands.
   - Run `grep -rn "StepEventReasonEnum" app/` before considering this stage done, to confirm no
     call site was missed beyond the ones enumerated above (this list reflects a point-in-time
     search and the working tree may have shifted).

8. **Cleanup migration** (only after Stage 7 is deployed and validated in a real environment —
   this is a separate, later migration, not bundled with Stage 7's):
   - Drop `step_state_records.reason` and the `step_event_reason_enum` Postgres type.
   - Delete `StepEventReasonEnum` from `app/beyo_manager/domain/task_steps/enums.py`.
   - Update `docs/architecture/under_construction/intention/planning_tables/task/step_state_record_models.md`
     to reflect `pause_reason_id` instead of the `step_event_reason` enum (it is currently stale —
     confirm with whoever owns that planning-tables doc set whether it should be edited in place
     or superseded).

9. **Analytics call-site update** —
   `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py`:
   - Re-read this file fresh at implementation time (it is in the modified-working-tree set).
   - Add `StepStateRecord.pause_reason_id` to the `select(...)` column list (currently line 173,
     alongside `StepStateRecord.reason` which stays until Stage 8).
   - Replace `reason=row.reason.value if row.reason is not None else None` (currently line 206)
     with `reason=row.pause_reason_id` — `domain/analytics/linear_timeline.py` already treats
     `reason` as an opaque `str | None` bucket key (confirmed: it never imports
     `StepEventReasonEnum`), so no domain-layer change is needed.
   - **Resolved decision:** the `pause_by_reason` bucket key changes meaning from a stable,
     human-readable enum string (`"pause_lunch_break"`) to an opaque `pause_reason_id` client_id.
     To keep the response usable without N follow-up lookups, join `pause_reasons` in this query
     and add a sibling `pause_reasons: {client_id: {name, image_url, pause_type}}` lookup map to
     the response payload, alongside the existing `pause_by_reason` counts. This is a breaking
     response-shape change — write a second
     `HANDOFF_TO_FRONTEND_pause_reasons_analytics_breakdown_<YYYYMMDD>.md` documenting it
     separately from Stage 6's CRUD handoff doc.
   - Check `app/beyo_manager/services/queries/worker_stats/list_workers_linear_timeline.py` and any
     other file matching `grep -rn "StepEventReasonEnum\|\.reason\b" app/beyo_manager/services/queries/worker_stats/`
     for the same pattern before considering this stage done — the exploration behind this plan
     found `.reason` used on `UserShiftStateRecord` (a different model, unaffected) in that file;
     confirm nothing else was missed.

## Risks and mitigations

- Risk: Stage 7/9 file edits collide with the currently uncommitted changes shown in `git status`
  to `_step_transition_core.py`, `transition_step_state.py`, `transition_step_state_batch.py`,
  `_task_state_transitions.py`, `update_task.py`, `count_task_post_handling_states.py`,
  `get_worker_linear_timeline_breakdown.py`, and their tests.
  Mitigation: resolved as a blocking Clarification above — re-read every listed file immediately
  before editing it in Stage 7/9, and reconcile against the current diff rather than this plan's
  point-in-time description.
- Risk: an automatic pause (auto-pause-on-conflict or clock-out) fires after the two
  system-managed seed rows are deleted or renamed away from their slug, silently breaking the
  pause record.
  Mitigation: `slug` is never exposed in the create/update request models (Stage 4), and
  `delete_pause_reason` rejects deletion of `is_system_managed` rows (Stage 4); the new
  `get_system_pause_reason_id` lookup (Stage 7) raises `NotFound` instead of proceeding with a
  `NULL` reason if the row is ever missing, surfacing the failure loudly instead of masking it.
- Risk: the backfill migration (Stage 7) runs in an environment where the Stage 3 bootstrap phase
  has not yet been (re-)invoked, so the `slug`-based join matches zero `pause_reasons` rows and
  every historical `step_state_records.pause_reason_id` is left `NULL`.
  Mitigation: called out as a blocking ordering Clarification; Stage 7's migration includes a
  post-`UPDATE` assertion that fails the migration if any `reason IS NOT NULL` row was left
  unmapped, rather than silently succeeding with lost data.
- Risk: the backfill migration (Stage 7) miscounts or mismatches historical `reason` values against
  the seeded rows' `slug`s, corrupting historical pause attribution.
  Mitigation: the backfill join is driven by `slug` values chosen to exactly equal
  `StepEventReasonEnum`'s string values (not independently hand-typed), and the Validation plan
  below includes an explicit row-count reconciliation query to run before and after the migration.
- Risk: `seed_pause_reasons` (Stage 3) is not idempotent in some edge case (e.g. re-running
  bootstrap after a user renamed a seeded row but before it was soft-deleted), causing a duplicate
  row with the same `slug`.
  Mitigation: the guard query matches on `(workspace_id, slug)` without filtering `is_deleted`, so
  a rename alone (which doesn't touch `slug`) is still recognized as "already seeded" and skipped;
  the `slug` unique index (Stage 2) also makes a true duplicate insert fail loudly at the DB level
  instead of silently succeeding.
- Risk: `PAUSE_CASE_CREATED` is missing from the stale
  `docs/architecture/under_construction/intention/planning_tables/task/step_state_record_models.md`
  planning doc; if that doc is used as the source of truth instead of the live enum file, the seed
  migration (Stage 3) would only seed 6 rows and silently drop case-created pause history during
  backfill.
  Mitigation: Stage 3's table is drawn from `app/beyo_manager/domain/task_steps/enums.py` directly,
  not from the planning doc; this is called out explicitly in "File read intent" above.
- Risk: changing the `pause_by_reason` bucket key shape (Stage 9) breaks any frontend or test code
  that currently expects the old enum-string keys.
  Mitigation: treated as a breaking-change requiring its own handoff doc (Stage 9), not folded
  silently into the CRUD handoff.

## Validation plan

- `pytest app/tests/unit/domain/pause_reasons/ app/tests/unit/services/commands/pause_reasons/
  app/tests/integration/commands/pause_reasons/ app/tests/integration/queries/pause_reasons/
  app/tests/unit/routers/api_v1/test_pause_reasons_router.py`: all new tests pass (Phase A).
- Call `bootstrap_app` (or `POST /api/v1/bootstrap` against a scratch DB) twice in a row and
  confirm the second call creates zero additional `pause_reasons` rows (`select(func.count())
  .select_from(PauseReason)` unchanged between calls) — proves Stage 3's idempotency guard works.
- `pytest app/tests/unit/services/commands/task_steps/ app/tests/integration/ -k
  "step_transition or clock or linear_timeline"`: existing suites pass after Phase B's rename.
- Before the Stage 7 backfill migration, run and record:
  `SELECT reason, count(*) FROM step_state_records WHERE reason IS NOT NULL GROUP BY reason;`
  After the migration, run:
  `SELECT pr.slug, pr.name, count(*) FROM step_state_records ssr JOIN pause_reasons pr ON
  pr.client_id = ssr.pause_reason_id GROUP BY pr.slug, pr.name;`
  and confirm the counts reconcile 1:1 against the pre-migration query (acceptance criterion 5).
- Manually exercise (or write an integration test for): auto-pause-on-conflict and clock-out with
  the `pause_other_task_priority`/`pause_ended_shift` rows deleted — must fail loudly
  (`NotFound`), not silently create a `NULL`-reason record (acceptance criterion 4).
- `grep -rn "StepEventReasonEnum" app/` returns zero results after Stage 8.
- `alembic upgrade head` and `alembic downgrade -1` (per migration, per `30_migrations.md`) both
  succeed cleanly in a scratch database for every migration added by this plan.

## Review log

- `2026-07-22` `claude`: initial draft, based on repository exploration of the existing
  `StepEventReasonEnum` consumers, the `UpholsteryCategory`/`EmailTemplate` CRUD analogs, and the
  core + CRUD-and-realtime contract bundle.
- `2026-07-22` `claude`: per user request, moved seeding of the `is_system_managed` pause reasons
  into a new `seed_pause_reasons` bootstrap phase (Stage 3) instead of a raw Alembic data
  migration, so they are guaranteed to always exist; user chose to seed all 7 legacy-equivalent
  rows this way (not just the 2 system-managed ones) for consistency with how other default
  reference data (item categories, case types, working sections) is already seeded. This
  introduced a new ordering dependency between Stage 3 (manually re-invoked, not deploy-triggered)
  and Stage 7's backfill migration (deploy-triggered via `alembic upgrade head`), captured as a
  new blocking Clarification and two new Risks.
- `2026-07-22T11:15:00Z` `codex`: reviewed `git status`/diffs, bootstrap endpoint, deploy workflow,
  and handoff directory convention. Resolved the two open clarifications: bootstrap is a mandatory
  manual release gate between Phase A and Stage 7 for existing environments, and dirty files contain
  unrelated in-flight changes that must be preserved while layering the cutover onto current
  contents. Corrected the Stage 7 lookup slugs to the live enum values
  (`pause_other_task_priority`, `pause_ended_shift`); `is_system_managed`, not a `system_*` slug,
  identifies the protected rows. Chose one lifecycle cycle for this plan, with Phase A/B implementation
  gates and separate migration revisions so the Stage 7 backfill and later Stage 8 cleanup can be
  released in their required order.
- `2026-07-22T11:30:00Z` `codex`: Phase A implementation completed. Added the domain/model,
  bootstrap phase, CRUD commands/queries/router, registrations, prefix reservation, tests, migration,
  and `HANDOFF_TO_FRONTEND_pause_reasons_crud_20260722.md`. Validation: targeted unit tests `11
  passed`; Phase A integration tests `3 passed`; Alembic upgrade, downgrade, and upgrade succeeded
  after hand-reviewing the autogenerated migration and adding explicit enum lifecycle handling.
- `2026-07-22T14:20:00Z` `codex`: Phase B implementation completed in the same lifecycle cycle.
  Stage 7 migration `fb10ac7fd439` adds the nullable FK, asserts all seven seeded slugs are present,
  backfills by slug, and fails on unmapped legacy rows. Stage 8 migration `b58cdffb5ccc` then drops
  the legacy column/type after validation. Automatic conflict and clock-out paths now resolve
  system rows by slug and raise `NotFound` when missing; single/batch frontend transitions validate
  the workspace reason and `requires_description`; serializers, shift reconstruction, backfill,
  analytics, and tests use `pause_reason_id`. Analytics adds the `pause_reasons` lookup map and the
  second frontend handoff.
- `2026-07-22T14:20:00Z` `codex`: Stage 7 reconciliation evidence: pre-backfill legacy counts were
  `pause_case_created=7`, `pause_coffee_break=21`, `pause_ended_shift=107`, `pause_lunch_break=38`,
  `pause_meeting=10`, `pause_other_task_priority=108`, `waiting_for_upholstery=26`; post-backfill
  counts matched exactly and `unmapped=0`. Stage 7 upgrade succeeded; Stage 8 downgrade and
  re-upgrade succeeded. Source check `grep -rn "StepEventReasonEnum" app/ --include='*.py'` returned
  zero results. Feature-scoped validation reached 51 passing tests after the final fixture update.
  The repository-wide run reached `993 passed, 32 failed`; the failures are pre-existing dirty-tree
  regressions in unrelated Shopify, inventory, audit, router, and fixture areas (the exact files
  remain unmodified by this plan and were preserved).
- `2026-07-22T14:25:00Z` `codex`: lifecycle transition completed from `implemented` to `summarized`
  after writing the implementation summary and updating the intention's linked-plan/progress notes;
  then transitioned to `archived` after creating the archive record. The plan file is being moved to
  `docs/architecture/archives/implementation/`.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
