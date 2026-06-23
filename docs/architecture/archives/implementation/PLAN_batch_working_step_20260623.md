# PLAN_batch_working_step_20260623

## Metadata

- Plan ID: `PLAN_batch_working_step_20260623`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-23T00:00:00Z`
- Last updated at (UTC): `2026-06-23T08:43:57Z`
- Related issue/ticket: `<none>`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_batch_working_step_20260623.md` (not yet authored — optional)

## Goal and intent

- Goal: Allow steps belonging to a *batch-capable working section* to be worked, paused, ended-shift, and completed in parallel by the same user, while preserving the existing "one active (non-batch) step per user" guard for all other steps.
- Business/user intent: Some working sections represent batchable work where one worker legitimately runs several steps at once (e.g. a process that supervises multiple items simultaneously). Today's auto-pause guard in `transition_step_state` forces serialization, which is wrong for that kind of work.
- Non-goals:
  - No change to how a non-batch step behaves (still exactly one open `WORKING` record per user).
  - No cross-category interaction. Batch steps are **fully independent** of the guard in both directions — starting/stopping a non-batch step never touches running batch steps, and vice versa (product decision confirmed).
  - No frontend UI work; no exposure of the flag on task-step serializers.
  - No retroactive reclassification of already-created steps when a section is later toggled (snapshot semantics — see Assumptions).

## Scope

- In scope:
  - New boolean column `allows_batch_working` on `working_sections` (source of truth, manager-configured).
  - New boolean snapshot column `allows_batch_working` on `task_steps`, copied from the section at step creation.
  - Alembic migration adding both columns (`server_default false`, backfill existing rows to `false`).
  - Persist + read the flag through working-section create/edit commands, request schemas, router bodies, and **both** the `serialize_working_section_full` and `serialize_working_section_compact` read shapes.
  - Snapshot the flag at the two step-creation sites.
  - Seed the `ground oil` and `hardwax oil` working sections as batch-capable during bootstrap (`seed_working_sections.py`).
  - Author a frontend hand-off document in `docs/handoff/to_frontend/` documenting the new `allows_batch_working` field on the compact and full working-section response shapes.
  - Teach the guard (`transition_step_state` entry condition) and the conflict query (`fetch_open_user_working_record`) to ignore batch steps.
  - Unit tests covering the new guard semantics.
- Out of scope:
  - Task-step serializers (flag stays backend-internal on the step side).
  - Any analytics / metrics interpretation changes.
- Assumptions:
  - **Snapshot semantics (Option A):** a step's batch behavior is frozen at creation time from the section's current value. Flipping a section's flag affects only future steps. This is intentional, to avoid a manager silently changing what pauses what mid-shift.
  - The guard's `effective_user_ids` (performer + credited user) behavior is unchanged and continues to apply.
  - Current single Alembic head is `71df9b8c4a2e` (uncommitted, part of in-flight workspace_role work). Implementer must re-confirm the head with `alembic heads` at implementation time and chain off whatever is current.

## Clarifications required

- [x] Coexistence semantics between batch and non-batch steps for the same user — resolved: **fully independent** (batch steps exempt from the guard in both directions).
- [x] Should `serialize_working_section_compact` (used by `get_worker_working_sections`) also carry the flag? — resolved: **yes**, the worker-facing section list exposes it too.

## Acceptance criteria

1. A section can be created and edited with `allows_batch_working` true/false; the value round-trips through `GET` working section (`serialize_working_section_full`) and through the worker section list (`serialize_working_section_compact`).
2. Existing sections after migration have `allows_batch_working = false` (behavior identical to today).
3. Steps created for a batch section have `task_steps.allows_batch_working = true`; steps for a non-batch section have `false`.
4. Starting a **non-batch** step into `WORKING` auto-pauses the user's other open **non-batch** `WORKING` step (unchanged behavior) and does **not** pause any open batch step.
5. Starting a **batch** step into `WORKING` pauses **nothing** and creates no auto-pause record; the user may hold multiple batch steps in `WORKING` simultaneously.
6. `pause` / `ended_shift` / `completed` transitions continue to work per-step for batch steps (already true; verified not regressed).
7. New unit tests pass; full unit suite green.
8. After a fresh bootstrap, the `ground oil` and `hardwax oil` sections have `allows_batch_working = true`; all other seeded sections have `false`.

## Contracts and skills

Read order (apply local-overrides-baseline precedence):

### Contracts loaded

Core (always):
- `../architecture/01_architecture.md`: command/query/router layering baseline.
- `../architecture/04_context.md`: `ServiceContext` (`session`, `workspace_id`, `user_id`).
- `../architecture/05_errors.md`: `ValidationError` / `ConflictError` / `NotFound` raising shape.
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: command structure; local adds `maybe_begin` transaction utility, session-call safety, subordinate-command event rule — the guard change lives inside `transition_step_state`'s existing `maybe_begin` block.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: read path for `get_working_section` (offset pagination noted by local, not used here).
- `../architecture/09_routers.md`: router body + handler wiring for the working-section create/edit endpoints.
- `../architecture/21_naming_conventions.md`: column/field naming (`allows_batch_working`).
- `../architecture/40_identity.md`, `../architecture/41_user.md` (+ `_local` if present), `../architecture/42_event.md`, `../architecture/48_presence.md`: core identity/event/presence baseline.

Goal bundle — **CRUD + realtime**:
- `../architecture/03_models.md`: adding a column to existing SQLAlchemy models (`WorkingSection`, `TaskStep`), default + check semantics.
- `../architecture/08_domain.md`: serializer placement (`domain/working_sections/serializers.py`).
- `../architecture/11_infra_events.md`: existing `working_section:updated` / `:created` dispatch is unchanged but confirm no new event needed.
- `../architecture/13_sockets.md`: confirm no new socket payload is required (guard already emits `task:step-state-changed`).
- `../architecture/30_migrations.md`: Alembic revision authoring, `server_default`, backfill, downgrade.
- `../architecture/15_testing.md`: unit test placement/fixtures for the new guard behavior.
- `../architecture/46_serialization.md`: explicit-allowlist serializer rule — adding `allows_batch_working` to `serialize_working_section_full` and `serialize_working_section_compact` (and its call site), but to no task-step serializer.

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin` + session-safety + subordinate event rule.
- `../architecture/07_queries_local.md`: offset pagination override (informational; not exercised).
- Any `*_local.md` companions present for the core contracts above must be loaded canonical-first, local-second.

### Excluded contracts

- `../architecture/22_*` (bulk insert / batch write): **excluded** — the word "batch" here is a domain concept (parallel step working), not DB bulk-writes. Do not let the trigger map mislead.
- Worker-driven / replayability / CI bundles (`16`, `12`, `51`, `52`, `53`, `54`, `33`, `31`): excluded — no worker, retry, replay, or pipeline surface in this change. The existing `PROCESS_STEP_TRANSITION` instant task is reused unchanged.
- `../architecture/55_*` (search/filter): excluded — no query filtering work.

### File read intent — pattern vs. relational

All implementation-file reads below are **relational** (what exists: exact column names, kwargs at construction sites, request-schema field sets, head revision) — not pattern reads. Do not open sibling commands/routers/serializers to re-learn structure; the contracts above define that.

Permitted relational reads (already performed during planning, re-verify only if stale):
- `models/tables/working_sections/working_section.py`, `models/tables/tasks/task_step.py` — exact column definitions.
- `services/commands/working_sections/create_working_section.py`, `edit_working_section.py` — where to add the field (note: `create` builds `WorkingSection(...)`; `edit` uses `model_fields_set` guards).
- `services/commands/working_sections/requests/create_working_section_request.py`, `edit_working_section_request.py` — Pydantic field sets + `at_least_one_updatable_field` validator (must add the new field to the updatable set).
- `routers/api_v1/working_sections.py` — `WorkingSectionCreateBody` / `WorkingSectionEditBody`.
- `services/queries/working_sections/get_working_section.py` + `domain/working_sections/serializers.py` — read shape (`_full` and `_compact`).
- `services/queries/working_sections/get_worker_working_sections.py` (~line 119) — the `serialize_working_section_compact` call site (positional args from the `section` model).
- `services/commands/tasks/create_task.py` (~line 234) and `services/commands/task_steps/add_task_steps.py` (~line 105) — step construction kwargs.
- `services/commands/bootstrap/phases/seed_working_sections.py` — per-attribute seed maps + `WorkingSection(...)` constructor (~line 104) and the idempotency `continue` guard.
- `routers/api_v1/working_sections.py` — the `get_worker_working_sections_route` (`/me`) and `get_working_section_route` (`/{working_section_id}`) handlers, for the hand-off doc.
- `routers/api_v1/__init__.py` (~line 48) — confirms router prefix `/api/v1/working-sections`.
- `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md` — hand-off doc structure/convention.
- `services/commands/task_steps/transition_step_state.py` (guard, line ~192) and `services/commands/task_steps/_user_working_record.py` — guard + conflict query.

### Skill selection

- Primary skill: standard backend command/model/migration implementation (no specialized skill file required).
- Router trigger terms: `working section`, `task step`, `migration`, `model column`.
- Excluded alternatives: search/query-filter skills — `not a filtering change`.

## Implementation plan

1. **Model — `WorkingSection`** (`models/tables/working_sections/working_section.py`): add
   `allows_batch_working: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))`.
   (`text` is already imported in this module.)

2. **Model — `TaskStep`** (`models/tables/tasks/task_step.py`): add the same column as a snapshot
   `allows_batch_working: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))`.
   Add `text` to the `sqlalchemy` import line. Place the column near `working_section_name_snapshot` to signal it is a section snapshot.

3. **Migration** (`app/migrations/versions/<rev>_add_allows_batch_working.py`):
   - Confirm current head via `alembic heads`; set `down_revision` to it (expected `71df9b8c4a2e`, verify).
   - `upgrade`: `op.add_column("working_sections", sa.Column("allows_batch_working", sa.Boolean(), nullable=False, server_default=sa.text("false")))` and the same for `task_steps`. Existing rows backfill to `false` via the server default. (Optionally drop the server_default after add to keep app-level control; keep it for safety — matches default-false intent.)
   - `downgrade`: `op.drop_column(...)` for both tables.

4. **Request schemas**:
   - `create_working_section_request.py`: add `allows_batch_working: bool = False`.
   - `edit_working_section_request.py`: add `allows_batch_working: bool | None = None` and add `"allows_batch_working"` to the `updatable` set inside `at_least_one_updatable_field`.

5. **Router bodies** (`routers/api_v1/working_sections.py`):
   - `WorkingSectionCreateBody`: add `allows_batch_working: bool = False`.
   - `WorkingSectionEditBody`: add `allows_batch_working: bool | None = None`.

6. **Create command** (`create_working_section.py`): pass `allows_batch_working=request.allows_batch_working` into the `WorkingSection(...)` constructor.

7. **Edit command** (`edit_working_section.py`): inside the `ctx.session.begin()` block, add
   `if "allows_batch_working" in request.model_fields_set: section.allows_batch_working = request.allows_batch_working`
   alongside the other field guards. (`updated_at`/`updated_by_id` already set at the end.)

8. **Read serializers** (`domain/working_sections/serializers.py`):
   - `serialize_working_section_full`: add `"allows_batch_working": section.allows_batch_working`.
   - `serialize_working_section_compact`: add an `allows_batch_working: bool` positional parameter and `"allows_batch_working": allows_batch_working` in the returned dict. Then update the only call site, `services/queries/working_sections/get_worker_working_sections.py` (~line 119), to pass `section.allows_batch_working` (the loaded `section` model already has it).
   - Do **not** add the flag to any task-step serializer.

9. **Snapshot at step creation** — set `allows_batch_working=section.allows_batch_working` in the `TaskStep(...)` constructor at:
   - `services/commands/tasks/create_task.py` (~line 234), and
   - `services/commands/task_steps/add_task_steps.py` (~line 105).
   Both already hold the resolved `section` object, so no extra query is needed.

10. **Bootstrap seeding** (`services/commands/bootstrap/phases/seed_working_sections.py`): add a
    `_SECTION_BATCH_MAP: dict[str, bool]` (or a `_BATCHABLE_SECTIONS: set[str] = {"ground oil", "hardwax oil"}`) following the existing per-attribute map pattern, and pass
    `allows_batch_working=_SECTION_BATCH_MAP.get(name, False)` into the `WorkingSection(...)` constructor at line ~104.
    Caveat: this phase is idempotent — it `continue`s when a section already exists, so re-running bootstrap on a workspace that already has these sections will **not** retro-update the flag. Only fresh seeds get it. Acceptable for local/dev bootstrap; flag explicitly in case an existing seeded environment needs a manual update.

11. **Conflict query** (`services/commands/task_steps/_user_working_record.py`): add
    `TaskStep.allows_batch_working.is_(False)` to the `where(...)`. This makes the guard only ever find/pause non-batch steps; `.limit(1)` remains correct because the "≤1 open non-batch WORKING per user" invariant holds.

12. **Guard entry condition** (`services/commands/task_steps/transition_step_state.py`, line ~192): change
    `if request.new_state == TaskStepStateEnum.WORKING:` to
    `if request.new_state == TaskStepStateEnum.WORKING and not step.allows_batch_working:`.
    Starting a batch step thus skips the auto-pause block entirely. No other change in the transition flow (close record, open new record, metrics, outbox event, notifications) is needed.

13. **Tests** (`app/tests/unit/...`): add cases per Acceptance criteria 4 & 5 — (a) non-batch start pauses other non-batch but not batch; (b) batch start pauses nothing and allows two concurrent batch `WORKING` steps; (c) section create/edit round-trips the flag; (d) step snapshot is set from the section.

14. **Frontend hand-off doc** (final deliverable, authored after implementation + validation pass): create
    `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_working_section_20260623.md` from
    `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`. It must document the new
    `allows_batch_working: boolean` field now returned by the two read routes in
    `routers/api_v1/working_sections.py`:
    - `get_worker_working_sections_route` — `GET /api/v1/working-sections/me` → each item in `working_sections[]` (the **compact** shape) now includes `allows_batch_working`.
    - `get_working_section_route` — `GET /api/v1/working-sections/{working_section_id}` → the **full** shape now includes `allows_batch_working`.
    Also note (as a related, secondary change) that `PUT /api/v1/working-sections` (`create_working_section_route`) and `PATCH /api/v1/working-sections/{working_section_id}` (`edit_working_section_route`) now **accept** `allows_batch_working` in the request body (optional; defaults `false` on create, unchanged-if-omitted on edit), so the section create/edit UI can set it.
    Fill the template's Metadata `Source plan` / `Source summary` with this plan and the eventual `SUMMARY_batch_working_step_20260623.md`. Include explicit before/after JSON response snippets for both shapes, and state that the field is **absent on task-step payloads by design**.

## Risks and mitigations

- Risk: Alembic head is in flux (`71df9b8c4a2e` uncommitted), so a wrong `down_revision` creates a branch.
  Mitigation: implementer runs `alembic heads` immediately before authoring and chains off the actual single head; if multiple heads exist, stop and resolve before adding.
- Risk: `at_least_one_updatable_field` validator on edit would reject an edit that only sets `allows_batch_working` if the field is not added to the updatable set.
  Mitigation: explicitly add `"allows_batch_working"` to that set (step 4).
- Risk: Stale `.limit(1)` assumption if data ever holds >1 open non-batch WORKING record for a user.
  Mitigation: out of scope to fix here; the new filter does not worsen it, and the guard itself preserves the invariant. Note for a follow-up data-integrity check.
- Risk: Snapshot drift confusion — managers may expect toggling a section to affect in-flight steps.
  Mitigation: documented as intentional (Assumptions); if live semantics are later desired, that is Option B (guard joins section live) and a separate change.

## Validation plan

- `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`: clean round-trip, no errors.
- `pytest app/tests/unit` (or project unit target): all green, including new batch-guard tests.
- Manual/contract check: `PUT`/`PATCH` working section with `allows_batch_working: true`, then `GET` returns it; create a task with a step in that section and confirm `task_steps.allows_batch_working = true`.
- Behavioral check via existing transition tests: non-batch auto-pause path unchanged for non-batch sections.
- Hand-off doc exists at `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_working_section_20260623.md`, follows the template, and documents `allows_batch_working` on both the compact (`/me`) and full (`/{id}`) response shapes plus the create/edit request field.

## Review log

- `2026-06-23` `claude-opus-4-8`: Initial plan authored from confirmed design (section-level flag, step snapshot, fully-independent coexistence).
- `2026-06-23` `David`: Flag must also be exposed in `serialize_working_section_compact` (worker section list).
- `2026-06-23` `claude-opus-4-8`: Added compact serializer + its call site to scope, steps, acceptance criteria, and contract notes.
- `2026-06-23` `David`: `ground oil` and `hardwax oil` must be seeded as batch-capable in bootstrap.
- `2026-06-23` `claude-opus-4-8`: Added bootstrap-seeding step (new step 10) with idempotency caveat, plus scope, acceptance criterion 8, and relational read.
- `2026-06-23` `David`: Implementation must end with a frontend hand-off doc (in `docs/handoff/to_frontend/`) covering the compact (`get_worker_working_sections_route`) and full (`get_working_section_route`) serialization changes.
- `2026-06-23` `claude-opus-4-8`: Added hand-off deliverable as step 14 with exact endpoints/prefix, plus scope, validation note, and relational reads.
- `2026-06-23` `codex`: Implemented the schema, command/query, bootstrap, serializer, migration, tests, summary, and frontend handoff changes. Resolved the existing Alembic multi-head state by merging both heads into the new revision.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
