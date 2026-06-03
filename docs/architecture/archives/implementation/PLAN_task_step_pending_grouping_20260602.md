# PLAN_task_step_pending_grouping_20260602

## Metadata

- Plan ID: `PLAN_task_step_pending_grouping_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T12:11:31Z`
- Related issue/ticket: `TBD`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_step_pending_grouping_20260602.md`

## Goal and intent

- Goal: Merge same-time pending task-step flow records into a single grouped flow record entry in task flow timeline output.
- Business/user intent: Reduce noisy timeline output when task creation (or other same-time events) produces multiple pending step state records, and show a human-readable grouped assignment summary by working section names.
- Non-goals:
  - Changing write-side behavior for task step creation or step state writes.
  - Adding database migrations.
  - Changing task history record creation behavior.

## Scope

- In scope:
  - Read-path grouping logic in task flow-record query pipeline.
  - Grouped flow-record serialization with a new record type.
  - Tests for grouping behavior, ordering, and pagination determinism.
- Out of scope:
  - Frontend design changes beyond minimal compatibility handling for new type.
  - Any schema or migration changes.
  - Changes to unrelated timeline endpoints.
- Assumptions:
  - Grouping key is `(created_at, created_by_id, pending state)` for step-state flow rows.
  - Grouping applies to rows visible in the returned page slice.
  - `working_section_name_snapshot` is available on joined task-step rows.

## Clarifications required

- [ ] Should grouped section names preserve original raw order, alphabetical order, or first-seen order only? — ordering choice affects deterministic UI snapshots and test expectations.
- [ ] Should grouped row `entity_client_id` be first step id, synthetic id, or omitted/null? — this blocks final contract shape and frontend click-through behavior.

## Acceptance criteria

1. For multiple pending step-state rows sharing the same grouping key in the returned page, response contains one grouped row with `type = "task_step_group"`.
2. Grouped description format is: `{username} assigned to working sections {name1, name2, ...}`.
3. Non-grouped step-state and history rows preserve current behavior and ordering.
4. Response remains reverse-chronological by created timestamp after grouping.
5. Pagination output remains deterministic for the same offset and data state.
6. Existing clients reading `history_record` and `task_step` rows continue to function.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: enforce layer boundaries and keep grouping in query/serialization layers.
- `backend/architecture/04_context.md`: maintain correct `ServiceContext` usage for query params and identity.
- `backend/architecture/05_errors.md`: preserve error semantics (no regression on missing task behavior).
- `backend/architecture/07_queries.md`: query-service composition and read-only behavior.
- `backend/architecture/07_queries_local.md`: pagination conventions and expected API shape.
- `backend/architecture/46_serialization.md`: serializer purity and stable output contracts.

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: local pagination details for offset + fixed limit handling.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another router to understand handler wiring → `09_routers.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading an existing endpoint to see what it currently returns
- Reading model files for exact field names and types
- Reading `__init__.py` files to verify import paths
- Reading related domain files to understand how existing logic connects

### Skill selection

- Primary skill: `backend/architecture/07_queries.md` + `backend/architecture/46_serialization.md`
- Router trigger terms: `task flow records`, `group pending`, `timeline grouping`
- Excluded alternatives: `command/write-path patterns` — excluded because this change is read-path only.

## Implementation plan

1. Define grouped flow-row contract:
   - Add grouped record shape and required fields.
   - Confirm fallback rules for username and working section name snapshots.

2. Implement grouping pass in flow query service:
   - In `task_flow_records` query path, add a post-pagination grouping step.
   - Group only consecutive step-state rows that are pending and share `(created_at, created_by_id)`.
   - Emit synthetic grouped row payload while preserving timeline ordering anchor.

3. Implement grouped serializer:
   - Add serializer helper for `task_step_group` rows.
   - Build grouped description with section name list and stable formatting.

4. Wire serialization branch:
   - Route grouped rows to grouped serializer.
   - Preserve existing serializers for `history_record` and single `task_step` rows.

5. Add or update backend tests:
   - Grouping happy path with 3+ pending rows.
   - Mixed history + step rows ordering.
   - Single pending row remains `task_step`.
   - Pagination boundary case with partial group visibility in page.

6. Validate manually with API calls:
   - Create task with multi-step payload.
   - Check flow-records response for grouped row type and description text.

## Risks and mitigations

- Risk: Grouping by timestamp can merge unrelated pending events if they share identical timestamp and actor.
  Mitigation: Restrict grouping to consecutive rows within page and pending state only; add regression tests.

- Risk: New row type can break frontend assumptions.
  Mitigation: Add frontend compatibility handling and API contract tests before rollout.

- Risk: Pagination semantics may surprise users around grouped boundaries.
  Mitigation: Document grouping as presentation-level aggregation and add deterministic pagination tests.

## Validation plan

- `backend tests for task flow records query`: grouped output appears only when criteria match.
- `manual API check for create task + flow records`: grouped description contains all expected working sections.
- `ordering check`: timeline remains descending by created timestamp.
- `pagination check`: stable results across repeated calls with same offset.

## Review log

- `2026-06-02` `copilot`: Initial implementation plan created from template for pending step flow grouping.

## Lifecycle transition

- Current state: `archived`
- Next state: `archived`
- Transition owner: `copilot`
