# PLAN_step_dependency_working_sections_20260602

## Metadata

- Plan ID: `PLAN_step_dependency_working_sections_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T14:22:56Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Extend `list_working_section_steps` to return, per step, one entry per active dependency — each entry containing the compact working-section object of the prerequisite step's section **plus the current state of that prerequisite step**.
- Business/user intent: Workers can see which sections are blocking them and how far along each blocker is (`pending`, `working`, `completed`, etc.), without opening the step detail. The `total_dependencies` / `completed_dependencies` counters already exist as aggregate signals; this adds the per-dependency identity and live state.
- Non-goals: Computing dependency counts (already denormalized on `TaskStep`). Changing the dependency graph itself. Any new endpoints.

## Scope

- In scope:
  - Add one batch JOIN query inside `list_working_section_steps` that resolves `TaskStepDependency` → prerequisite `TaskStep` → `WorkingSection` for all steps in the current page, selecting all active dependency edges (`removed_at IS NULL`) regardless of the prerequisite step's state.
  - Include `PrerequisiteStep.state` in the SELECT so each entry carries the current state of its prerequisite step.
  - Build a `dep_ws_map: dict[str, list[dict]]` keyed by `dependent_step_id`.
  - Each entry in the list has shape `{ "working_section": serialize_working_section_compact(...), "prerequisite_step_state": <state_value> }`.
  - Add `"dependency_working_sections": [...]` to each step payload entry.
  - Import `TaskStepDependency` into the query file.
  - Import `serialize_working_section_compact` into the query file.

- Out of scope:
  - Changes to `serialize_working_section_compact` signature (already accepts `client_id, name, image, order_list`).
  - Changes to any router, command, migration, or socket.
  - Filtering or sorting by dependency working sections.
  - Returning dependency working sections in any other query service.

- Assumptions:
  - All active dependency edges are returned (`TaskStepDependency.removed_at IS NULL`), regardless of the prerequisite step's state — including terminal states. The frontend uses the per-entry `prerequisite_step_state` to decide rendering (e.g., strikethrough for completed, warning icon for failed).
  - One entry is emitted per dependency link (not per unique working section). Two prerequisite steps in the same working section at different states yield two separate entries.
  - Only non-deleted prerequisite steps are included (`TaskStep.is_deleted = false`).
  - Only non-deleted working sections are included (`WorkingSection.is_deleted = false`).
  - All `WorkingSection` rows needed are within `ctx.workspace_id` — the join through `TaskStep.workspace_id` enforces this without an extra filter.
  - The `working_section_name_snapshot` on `TaskStep` is NOT used in place of the live `WorkingSection` row, because `serialize_working_section_compact` also requires `image` and `order_list`, which are not snapshotted.
  - Result order within the list per step is stable by `ws.order_list ASC NULLS LAST, ws.client_id ASC` so entries appear in section display order.

## Clarifications required

_None — scope is fully defined._

## Acceptance criteria

1. Each item in `steps_pagination.items` includes a `"dependency_working_sections"` key.
2. For a step with no active dependency edges the value is `[]`.
3. For a step with N active dependency edges the value contains N objects, each shaped:
   ```json
   {
     "working_section": { "client_id": "...", "name": "...", "image": "...", "order_list": 1 },
     "prerequisite_step_state": "pending"
   }
   ```
4. Removed dependency edges (`removed_at IS NOT NULL`) are excluded.
5. Deleted prerequisite steps (`is_deleted = true`) are excluded from the join — their entry is omitted.
6. Deleted working sections (`is_deleted = true`) are excluded from the join — their entry is omitted.
7. All states of the prerequisite step are included (`pending`, `working`, `paused`, `completed`, `skipped`, etc.) — no state filter applied.
8. Two prerequisite steps in the same working section produce two separate entries (one per dependency link).
9. The feature does not add a per-step query loop — exactly one new SQL query is issued per page, regardless of step count.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline
- `../../../architecture/07_queries.md`: query structure, batch-load pattern
- `../../../architecture/07_queries_local.md`: offset pagination, no cursor
- `../../../architecture/21_naming_conventions.md`: snake_case field naming
- `../../../architecture/24_multi_tenancy.md`: workspace_id scoping on every query
- `../../../architecture/25_soft_delete.md`: is_deleted / removed_at filter rules
- `../../../architecture/46_serialization.md`: serializer output shape
- `../../../architecture/46_serialization_local.md`: app-specific serializer delta

### Local extensions loaded

- `../../../architecture/07_queries_local.md`: offset pagination replaces cursor pagination

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`07_queries.md`, `46_serialization.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another query service to understand the batch-load / map pattern → `07_queries.md`
- Reading another serializer to understand output key shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `list_working_section_steps.py` to understand the existing query structure, import block, and payload assembly loop
- Reading `task_step_dependency.py` for exact column names (`dependent_step_id`, `prerequisite_step_id`, `removed_at`)
- Reading `working_section.py` for exact field names (`client_id`, `name`, `image`, `order_list`, `is_deleted`)
- Reading `domain/working_sections/serializers.py` to confirm the current `serialize_working_section_compact` signature

### Skill selection

- Primary skill: `07_queries.md` — batch-load and map-build pattern for list services
- Router trigger terms: n/a (no router changes)
- Excluded alternatives: `06_commands.md` — no mutations; `09_routers.md` — no handler changes; `30_migrations.md` — no schema changes

## Implementation plan

1. **Imports** — In `beyo_manager/services/queries/working_sections/list_working_section_steps.py`, add to the existing import block:
   ```python
   from beyo_manager.domain.working_sections.serializers import serialize_working_section_compact
   from beyo_manager.models.tables.tasks.task_step_dependency import TaskStepDependency
   ```

2. **Batch JOIN query** — After the `first_started_map` is built (after line 334) and before the `items_payload` assembly loop, add:
   ```python
   dep_ws_map: dict[str, list[dict]] = {}
   if page_ids:
       PrerequisiteStep = aliased(TaskStep)
       dep_rows_result = await ctx.session.execute(
           select(
               TaskStepDependency.dependent_step_id,
               PrerequisiteStep.state.label("prereq_state"),
               WorkingSection.client_id.label("ws_client_id"),
               WorkingSection.name.label("ws_name"),
               WorkingSection.image.label("ws_image"),
               WorkingSection.order_list.label("ws_order_list"),
           )
           .join(
               PrerequisiteStep,
               and_(
                   PrerequisiteStep.client_id == TaskStepDependency.prerequisite_step_id,
                   PrerequisiteStep.workspace_id == ctx.workspace_id,
                   PrerequisiteStep.is_deleted.is_(False),
               ),
           )
           .join(
               WorkingSection,
               and_(
                   WorkingSection.client_id == PrerequisiteStep.working_section_id,
                   WorkingSection.is_deleted.is_(False),
               ),
           )
           .where(
               TaskStepDependency.dependent_step_id.in_(page_ids),
               TaskStepDependency.removed_at.is_(None),
           )
           .order_by(
               WorkingSection.order_list.asc().nullslast(),
               WorkingSection.client_id.asc(),
           )
       )
       for row in dep_rows_result.all():
           dep_ws_map.setdefault(row.dependent_step_id, []).append(
               {
                   "working_section": serialize_working_section_compact(
                       client_id=row.ws_client_id,
                       name=row.ws_name,
                       image=row.ws_image,
                       order_list=row.ws_order_list,
                   ),
                   "prerequisite_step_state": row.prereq_state.value,
               }
           )
   ```

   Note: `TaskStep`, `WorkingSection`, and `aliased` are already imported in this file (check `sqlalchemy.orm` import). `TaskStepDependency` and `serialize_working_section_compact` are the two new imports from step 1. The alias `PrerequisiteStep` is declared inline to avoid the self-join conflict on `task_steps`. No state filter is applied — all active edges are returned so the frontend can render per-state UI (e.g., checkmark for `completed`, spinner for `working`).

3. **Payload assembly** — In the `items_payload.append(...)` block, add the new key after `"cases_summary"`:
   ```python
   "dependency_working_sections": dep_ws_map.get(step.client_id, []),
   ```

## Risks and mitigations

- Risk: `TaskStep` is used as a join target with an alias conflict — the file already uses `TaskStep` for the main step rows. The new JOIN targets `TaskStep` again (prerequisite steps), so SQLAlchemy needs an alias to avoid table ambiguity.
  Mitigation: `aliased(TaskStep)` is used and named `PrerequisiteStep` inline at the query site. `aliased` is already in `sqlalchemy.orm` which is already imported by the file; no new import needed for it.

- Risk: `order_list` on `WorkingSection` was added in `PLAN_working_section_order_list_20260602`. If the migration was not applied the column is missing at runtime.
  Mitigation: That plan is already archived (implemented). Confirm `WorkingSection.order_list` exists on the ORM model before implementing; if absent, run that migration first.

## Validation plan

- `GET /working-sections/<id>/steps` with a step that has 0 active dependency edges: `dependency_working_sections` is `[]`.
- `GET /working-sections/<id>/steps` with a step that has 2 active prerequisites in 2 different sections: `dependency_working_sections` has 2 entries, each shaped `{ "working_section": {...}, "prerequisite_step_state": "<state>" }`.
- `GET /working-sections/<id>/steps` with a step that has 2 active prerequisites in the **same** section (different steps): `dependency_working_sections` has 2 entries, both with the same `working_section.client_id` but potentially different `prerequisite_step_state`.
- `GET /working-sections/<id>/steps` with a prerequisite step in state `completed`: its entry is present with `"prerequisite_step_state": "completed"` (no state filter hides it).
- `GET /working-sections/<id>/steps` with a step whose only dependency has `removed_at` set: `dependency_working_sections` is `[]`.
- `GET /working-sections/<id>/steps` with a step whose prerequisite belongs to a deleted working section (`is_deleted = true`): that entry is omitted.
- SQL query count: exactly one new query issued per page call (verify via `echo=True` on the engine in a dev environment).

## Review log

- `2026-06-02T14:22:56Z` — Implemented in query layer, validated typecheck, summarized, and archived.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
