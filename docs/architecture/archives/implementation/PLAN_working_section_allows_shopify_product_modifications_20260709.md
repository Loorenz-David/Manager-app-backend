# PLAN_working_section_allows_shopify_product_modifications_20260709

## Metadata

- Plan ID: `PLAN_working_section_allows_shopify_product_modifications_20260709`
- Status: `archived`
- Owner agent: `Codex`
- Created at (UTC): `2026-07-09T14:42:00Z`
- Last updated at (UTC): `2026-07-09T14:47:34Z`
- Related issue/ticket: `Working sections — allows_shopify_product_modifications flag`
- Intention plan: `backend/docs/architecture/under_construction/intention/shopify_integration_improvements.txt`

## Goal and intent

- Goal: Add a new `allows_shopify_product_modifications` boolean column to `working_sections`, defaulted to `false`, and thread it through every place `allows_batch_working` is currently read, written, or serialized for that same table — no more, no less.
- Business/user intent: The frontend needs a per-working-section flag it can read to decide whether a worker acting inside that working section is allowed to trigger Shopify product modifications. This mirrors the existing `allows_batch_working` flag, which already changes frontend behavior for how a task step is completed for a given working section.
- Non-goals:
  - No new business logic that *acts* on this flag (no gating of any Shopify command, no backend enforcement). This plan only adds the column and threads it through existing read/write/serialize paths — same posture the frontend needs to consume, nothing more.
  - No propagation of this flag onto `task_steps` (unlike `allows_batch_working`, which is denormalized onto `TaskStep` at task/step creation for transition-time enforcement). This new flag has no task-step-level behavior today, so it must not be added to `models/tables/tasks/task_step.py`, `services/commands/tasks/create_task.py`, or `services/commands/task_steps/add_task_steps.py`.
  - No changes to bootstrap seed data (`services/commands/bootstrap/phases/seed_working_sections.py`) — see "Scope > Out of scope" for rationale.

## Scope

- In scope:
  - `models/tables/working_sections/working_section.py`: new `allows_shopify_product_modifications` column, same shape as `allows_batch_working` (`Boolean`, `nullable=False`, `default=False`, `server_default=text("false")`).
  - One new linear Alembic migration adding the column to `working_sections` only.
  - `domain/working_sections/serializers.py`: both `serialize_working_section_compact` and `serialize_working_section_full` gain the new field, mirroring the existing `allows_batch_working` field exactly.
  - Every caller of `serialize_working_section_compact` that currently passes `allows_batch_working` also passes the new field (three call sites, listed under "Implementation plan").
  - `services/commands/working_sections/requests/create_working_section_request.py` and `create_working_section.py`: new field on the request model, defaulted `False`, passed into the `WorkingSection(...)` constructor.
  - `services/commands/working_sections/requests/edit_working_section_request.py` and `edit_working_section.py`: new optional field on the edit request model, added to the "at least one updatable field" set, and applied via the same `model_fields_set` guard pattern as `allows_batch_working`.
  - `routers/api_v1/working_sections.py`: new field on both `WorkingSectionCreateBody` and `WorkingSectionEditBody` Pydantic request models.
  - Unit test updates: `tests/unit/test_working_section_serializers.py` (the existing `serialize_working_section_compact` call becomes a signature break unless updated — this is a required fix, not optional coverage).
- Out of scope:
  - `models/tables/tasks/task_step.py` and every `TaskStep.allows_batch_working` read/write site (`add_task_steps.py`, `create_task.py`, `transition_step_state.py`, `transition_step_state_batch.py`, `_step_transition_core.py`, `_user_working_record.py`, `get_user_last_active_step_record.py`). These implement task-step batch-completion enforcement, a distinct feature from the working-section-level Shopify flag this plan adds. `allows_batch_working` is denormalized onto `TaskStep` specifically because batch-completion is enforced at transition time per step; `allows_shopify_product_modifications` has no such per-step enforcement requirement today, so it is not propagated there.
  - `services/commands/bootstrap/phases/seed_working_sections.py`: this file sets `allows_batch_working` from a hardcoded `_SECTION_BATCH_MAP` keyed by section name. There is no equivalent Shopify-modification map supplied for this task, and the column's `False` default already gives every seeded section the correct value with no code change. Inventing a seed map here would be scope creep beyond what was asked.
  - Any Shopify command/service enforcing this flag (e.g., rejecting a Shopify product modification when the flag is `false`). Only requested: the column, its serialization, and its presence on create/edit.
- Assumptions:
  - "Every serialization where there is the serialization of `allows_batch_working`" means every serialization of the `WorkingSection` entity itself (the `working_sections` table's own fields), not every place a `TaskStep.allows_batch_working` value is serialized — those are a different column on a different table that happens to share a name for an unrelated purpose (see "Out of scope" above).
  - "Creation of the working section services" is read as the `create_working_section` command plus its request/router pair. `edit_working_section` is included alongside it (not just literally "creation") because the router's `PATCH` route and edit request already mirror every other `allows_batch_working` field 1:1, and shipping a flag that can be set at creation but never toggled afterward would be an inconsistent, easily-missed gap against the existing pattern this plan is asked to mirror.

## Clarifications required

None. Every file in scope was located and read directly; the pattern to mirror (`allows_batch_working` on `WorkingSection`) is unambiguous and fully precedented in the current codebase.

## Acceptance criteria

1. `alembic upgrade head` runs cleanly from the current single head (`ab12cd34ef56`) with no merge conflict, on a database that already has `26d4b7f0c3aa` applied — the new migration is the sole, linear next revision.
2. `working_sections.allows_shopify_product_modifications` exists, `NOT NULL`, `DEFAULT false`, on both `upgrade` and any pre-existing row.
3. `PUT /api/v1/working-sections` (create) accepts `allows_shopify_product_modifications: bool` (default `false`) and persists it.
4. `PATCH /api/v1/working-sections/{id}` (edit) accepts `allows_shopify_product_modifications: bool | null` and, when set, updates the row; omitting it leaves the existing value untouched (same `model_fields_set` semantics as every other optional edit field).
5. Every response shape that currently includes `"allows_batch_working"` for a `WorkingSection` also includes `"allows_shopify_product_modifications"` with the correct value: `serialize_working_section_compact`, `serialize_working_section_full`, and all three of their call sites (`list_users.py`, `get_worker_working_sections.py`, `list_working_section_steps.py`).
6. `TaskStep.allows_batch_working` and every task-step batch-transition file are untouched — `git diff` shows no changes under `models/tables/tasks/`, `services/commands/tasks/create_task.py`, or `services/commands/task_steps/`.
7. `pytest tests/unit/test_working_section_serializers.py` and the full working-section integration suite pass.

## Contracts and skills

### Contracts loaded

- `../architecture/01_architecture.md`: baseline layering (router → command/query → domain → model) this change must stay inside.
- `../architecture/04_context.md`: `ServiceContext`/`ctx.workspace_id` usage already present in every touched command/query — no new pattern introduced.
- `../architecture/05_errors.md`: no new error paths added by this plan; existing `NotFound`/`ConflictError`/`ValidationError` usage in `create_working_section.py`/`edit_working_section.py` is untouched.
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: governs the edits to `create_working_section.py` and `edit_working_section.py` (session.add/flush, `ctx.session.begin()`, `model_fields_set`-guarded partial update shape). Local companion's `maybe_begin`/subordinate-event rules confirmed not implicated — both commands already own a single top-level `ctx.session.begin()` block this plan adds lines inside of, not a new one.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: governs the edits to `list_users.py`, `get_worker_working_sections.py`, `list_working_section_steps.py` (offset pagination already in place, untouched by this plan — only the selected-column list changes).
- `../architecture/09_routers.md`: governs the two Pydantic body models in `routers/api_v1/working_sections.py`.
- `../architecture/21_naming_conventions.md`: `allows_shopify_product_modifications` follows the existing `allows_<verb>_<noun>` boolean-flag naming precedent set by `allows_batch_working`.
- `../architecture/40_identity.md`: no identity/client_id changes in this plan; loaded per core-contract policy only.
- `../architecture/41_user.md`: no user-model changes; loaded per core-contract policy only.
- `../architecture/42_event.md`: `create_working_section`/`edit_working_section` already dispatch `working_section:created`/`working_section:updated` workspace events via `build_workspace_event(section, ...)`. This plan changes no event-emission code — the new column rides along automatically since the event payload is built from the ORM row, not an explicit field list. Confirm this assumption by reading `build_workspace_event` before editing, per "File read intent" below (relational read: what does this existing function already do with a changed row).
- `../architecture/48_presence.md`: no presence-channel changes; loaded per core-contract policy only.

### Goal bundle: CRUD + realtime

- `../architecture/03_models.md`: governs the new `mapped_column` on `WorkingSection`.
- `../architecture/08_domain.md`: governs the `domain/working_sections/serializers.py` edits.
- `../architecture/11_infra_events.md`: confirms the `build_workspace_event` payload-from-row shape referenced above needs no edit.
- `../architecture/13_sockets.md`: confirms no socket-channel/payload allowlist elsewhere needs a matching field addition (check for any explicit working-section field allowlist before/after this change; if `13_sockets.md` documents one, it must be updated too — otherwise no socket change is needed).
- `../architecture/30_migrations.md`: governs the new migration file (linear, single `down_revision`, no merge revision).
- `../architecture/15_testing.md`: governs the required `test_working_section_serializers.py` fix and any new assertion added for the new field.

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin` / session-call-safety rules — confirmed not newly implicated (see above).
- `../architecture/07_queries_local.md`: offset-pagination override — confirmed not newly implicated (no pagination shape change, only an added selected column).

### File read intent — pattern vs. relational

- Reading `build_workspace_event` (in `services/infra/events/build_event.py`): relational read — confirming what fields the existing event payload already includes for a `WorkingSection` row, not learning a new pattern.
- Reading `13_sockets.md` for any explicit working-section field allowlist: relational read — confirming whether a hardcoded field list exists that would otherwise silently omit the new column from realtime payloads.
- No other implementation file outside this plan's explicit scope list should be opened. Every command/query/serializer/router file this plan touches was already read in full while drafting this plan; do not re-open sibling domain commands (e.g. other `services/commands/<domain>/create_*.py` files) to "check the pattern" — `06_commands.md` already defines it, and `create_working_section.py` in this plan's scope is itself the working, precedented example.

### Skill selection

- Primary skill: none required beyond the contracts above — this is a same-shape, same-file extension of an existing, fully precedented pattern (`allows_batch_working`), not new architecture.
- Router trigger terms: none of the trigger-expansion-map terms (worker, retry, replay, observability, ci, deterministic testing, rate limit, timeout, cache, bulk insert, multipart, search) apply.
- Excluded alternatives: "Worker-driven backend", "Replayable async runtime", and "CI-validated runtime" goal bundles — none apply; this plan adds no background job, no replay concern, and no CI/deployment change.

## Implementation plan

1. **Model** — `beyo_manager/models/tables/working_sections/working_section.py`: add, immediately after the existing `allows_batch_working` column (after line 25, before `created_at`):
   ```python
   allows_shopify_product_modifications: Mapped[bool] = mapped_column(
       Boolean,
       nullable=False,
       default=False,
       server_default=text("false"),
   )
   ```

2. **Migration** — new file `app/migrations/versions/<new_revision>_add_allows_shopify_product_modifications_to_working_sections.py`:
   - Confirm the current single head is still `ab12cd34ef56` (`alembic heads`) immediately before generating the revision id, to avoid racing any other in-flight migration.
   - `down_revision = "ab12cd34ef56"`.
   - Pick a new, unique 12-character lowercase-hex `revision` id (grep `migrations/versions/*.py` for `revision: str = "<id>"` to confirm no collision — do not reuse or guess an id that collides).
   - `upgrade()`: single `op.add_column("working_sections", sa.Column("allows_shopify_product_modifications", sa.Boolean(), nullable=False, server_default=sa.text("false")))` — same shape as `26d4b7f0c3aa`'s `working_sections` column add, minus the `task_steps` half (out of scope here).
   - `downgrade()`: single `op.drop_column("working_sections", "allows_shopify_product_modifications")`.
   - No data migration/backfill needed — `server_default` handles existing rows.

3. **Domain serializers** — `beyo_manager/domain/working_sections/serializers.py`:
   - `serialize_working_section_compact(...)`: add parameter `allows_shopify_product_modifications: bool` after `allows_batch_working: bool`, and add `"allows_shopify_product_modifications": allows_shopify_product_modifications,` to the returned dict, immediately after the `allows_batch_working` key.
   - `serialize_working_section_full(...)`: add `"allows_shopify_product_modifications": section.allows_shopify_product_modifications,` immediately after the `"allows_batch_working": section.allows_batch_working,` line.

4. **Compact-serializer call sites** — update all three to pass the new value, matching the added parameter:
   - `beyo_manager/services/queries/users/list_users.py`: add `WorkingSection.allows_shopify_product_modifications` to the `select(...)` column list (after `WorkingSection.allows_batch_working`), and add `sec_row.allows_shopify_product_modifications` to the `serialize_working_section_compact(...)` call.
   - `beyo_manager/services/queries/working_sections/get_worker_working_sections.py`: `sections` is already a full `WorkingSection` ORM row (`select(WorkingSection)...scalars().all()`), so no SELECT change is needed — just add `section.allows_shopify_product_modifications` to the `serialize_working_section_compact(...)` call.
   - `beyo_manager/services/queries/working_sections/list_working_section_steps.py`: add `WorkingSection.allows_shopify_product_modifications.label("ws_allows_shopify_product_modifications")` to the `select(...)` column list (after the `ws_allows_batch_working` label), and add `allows_shopify_product_modifications=row.ws_allows_shopify_product_modifications` to the `serialize_working_section_compact(...)` call.

5. **Create path**:
   - `beyo_manager/services/commands/working_sections/requests/create_working_section_request.py`: add `allows_shopify_product_modifications: bool = False` after `allows_batch_working: bool = False`.
   - `beyo_manager/services/commands/working_sections/create_working_section.py`: add `allows_shopify_product_modifications=request.allows_shopify_product_modifications,` to the `WorkingSection(...)` constructor call, after `allows_batch_working=request.allows_batch_working,`.

6. **Edit path**:
   - `beyo_manager/services/commands/working_sections/requests/edit_working_section_request.py`: add `allows_shopify_product_modifications: bool | None = None` after `allows_batch_working: bool | None = None`; add `"allows_shopify_product_modifications"` to the `updatable` set in `at_least_one_updatable_field`; extend the `ValueError` message to mention the new field alongside the others.
   - `beyo_manager/services/commands/working_sections/edit_working_section.py`: add, after the existing `allows_batch_working` block:
     ```python
     if "allows_shopify_product_modifications" in request.model_fields_set:
         section.allows_shopify_product_modifications = request.allows_shopify_product_modifications
     ```

7. **Router request bodies** — `beyo_manager/routers/api_v1/working_sections.py`:
   - `WorkingSectionCreateBody`: add `allows_shopify_product_modifications: bool = False` after `allows_batch_working: bool = False`.
   - `WorkingSectionEditBody`: add `allows_shopify_product_modifications: bool | None = None` after `allows_batch_working: bool | None = None`.

8. **Event/socket sanity check** (no code change expected): read `build_workspace_event` in `services/infra/events/build_event.py` and check `13_sockets.md` for any explicit working-section field allowlist. If either hardcodes a field list that excludes new columns by name, update that list; if both build payloads generically from the ORM row (the expected case, matching `26d4b7f0c3aa`'s precedent of `allows_batch_working` needing no such edit), no change is needed here — record which it was in the review log.

9. **Tests**:
   - `tests/unit/test_working_section_serializers.py`: update `test_serialize_working_section_compact_includes_allows_batch_working` to pass `allows_shopify_product_modifications=False` (or add a new dedicated test) so the call matches the new signature; assert the new key is present in the result with the expected value.
   - Add one integration-level round-trip check (create with `allows_shopify_product_modifications=True`, then read it back via `GET /{id}` or `GET ""`) in the existing working-section integration test file(s) that already cover `allows_batch_working` create/edit round-trips, mirroring the existing assertions at the lines already identified (e.g. `tests/integration/services/commands/working_sections/test_batch_working_section_integration.py` patterns around lines 100, 155, 237, 259) — new assertions only, no existing assertion needs to change since none of them do whole-dict equality.

## Risks and mitigations

- Risk: Positional-argument breakage — `serialize_working_section_compact` is called positionally in `get_worker_working_sections.py` and `list_users.py`. Adding the new parameter in the wrong position silently shifts arguments instead of failing loudly.
  Mitigation: Add the new parameter last in the signature (after `allows_batch_working`) and pass it as the last positional/keyword argument at every call site, matching the order shown in step 3-4 above; run the full working-section test suite after the change to catch any mismatch.
- Risk: Scope drift onto `TaskStep.allows_batch_working` — the shared substring `allows_` and `_working` across `WorkingSection.allows_batch_working` and `TaskStep.allows_batch_working` makes it easy to over-grep and touch task-step transition files that were never in scope.
  Mitigation: Acceptance criterion 6 explicitly checks `git diff` excludes `models/tables/tasks/`, `create_task.py`, and `services/commands/task_steps/`.
- Risk: Migration revision id collision or non-linear chain if another migration lands on `ab12cd34ef56` concurrently.
  Mitigation: Re-run `alembic heads` immediately before writing the migration file to confirm `ab12cd34ef56` is still the sole head; if not, rebase `down_revision` onto the new actual head before finalizing.

## Validation plan

- `alembic heads`: expect exactly one head, the new revision, both before and after this plan's migration is authored (single-head chain preserved).
- `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` against a scratch/test database: expect clean apply and clean rollback with no error.
- `pytest tests/unit/test_working_section_serializers.py -q`: expect pass.
- `pytest tests/integration/services/commands/working_sections/ -q`: expect pass (existing `allows_batch_working` assertions untouched, new field assertions added per step 9 pass).
- `pytest tests/unit/test_working_section_serializers.py tests/integration/services/queries/working_sections/ tests/integration/services/commands/bootstrap/test_seed_working_sections_integration.py -q`: expect pass (bootstrap seed test should be unaffected since no seed-file code changes).
- Manual/API sanity: `PUT` a working section with `allows_shopify_product_modifications: true`, then `GET` it back (both list and single-item routes) and confirm the field round-trips; `PATCH` it to `false` and confirm the update applies.

## Review log

- `2026-07-09` `Claude`: Initial plan drafted from direct inspection of all `allows_batch_working` call sites; scoped to `WorkingSection`-level serialization/creation/edit only, explicitly excluding the unrelated `TaskStep.allows_batch_working` denormalization and bootstrap seed data.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `Codex`
