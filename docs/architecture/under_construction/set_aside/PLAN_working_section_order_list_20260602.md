# PLAN_working_section_order_list_20260602

## Metadata

- Plan ID: `PLAN_working_section_order_list_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T12:44:57Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add a nullable `order_list` integer field to `WorkingSection`, expose it through serializers, allow it to be set on creation and update, and use it as the primary sort key in all listing queries.
- Business/user intent: Provide a visual ordering number that clients can use to sort working sections in a list view, independent of the dependency graph. Sections with no value assigned fall to the end of the list.
- Non-goals: Enforcing uniqueness of `order_list` within a workspace; automatic re-ordering of other sections when the value changes.

## Scope

- In scope:
  - Add `order_list: Mapped[int | None]` column to the `WorkingSection` model (nullable `Integer`).
  - Generate and review an Alembic migration for the new column.
  - Add `order_list` to `WorkingSectionCreateRequest` (optional, defaults to `None`).
  - Add `order_list` to `WorkingSectionEditRequest` (optional, patch-style).
  - Pass `order_list` to the `WorkingSection` constructor in `create_working_section`.
  - Handle `order_list` in the patch block of `edit_working_section`.
  - Update `serialize_working_section_compact` to include `order_list`.
  - Update `serialize_working_section_full` to include `order_list`.
  - Add `order_list` to the `updatable` set in the edit-request `model_validator` so the guard accepts it as a valid lone field.
  - Sort both listing queries by `order_list ASC NULLS LAST` as the primary key, keeping the existing secondary sort as tiebreaker.

- Out of scope:
  - Query/filter by `order_list`.
  - Uniqueness constraint on `order_list`.
  - Auto-reindex other sections.
  - Any router-layer or socket-layer changes beyond what already exists.

- Assumptions:
  - `order_list` values are purely cosmetic integers supplied by the client; no server-side enforcement of ordering invariants is needed.
  - The existing event (`working_section:updated`) fired in `edit_working_section` is sufficient to propagate the change; no new event type is required.
  - The column sits between `image` and `created_at` in the model declaration (natural read order, matching insert order of related fields).

## Clarifications required

_None — scope is fully defined._

## Acceptance criteria

1. `WorkingSection` ORM model has `order_list` as a nullable `Integer` column with no server-side default.
2. `POST /working-sections` accepts `order_list` (integer or null) and persists it.
3. `PATCH /working-sections` accepts `order_list` alone as the only changed field without triggering the "at least one field" guard.
4. `serialize_working_section_compact` output includes `"order_list": <int|null>`.
5. `serialize_working_section_full` output includes `"order_list": <int|null>`.
6. Alembic migration applies cleanly (`alembic upgrade head`) and downgrades cleanly (`alembic downgrade -1`).
7. Existing sections not touched by the migration have `order_list = NULL`.
8. `GET /working-sections` returns sections ordered by `order_list ASC NULLS LAST, created_at ASC` — sections with a set value appear before those without.
9. `GET /worker/working-sections` returns sections ordered by `order_list ASC NULLS LAST, name ASC`.

## Contracts and skills

### Contracts loaded

- `../../../architecture/01_architecture.md`: baseline
- `../../../architecture/03_models.md`: column definition pattern
- `../../../architecture/06_commands.md`: command mutation pattern
- `../../../architecture/06_commands_local.md`: `maybe_begin`, session call safety
- `../../../architecture/07_queries.md`: query structure and ordering pattern
- `../../../architecture/07_queries_local.md`: offset pagination override
- `../../../architecture/21_naming_conventions.md`: snake_case field naming
- `../../../architecture/30_migrations.md`: Alembic autogenerate workflow
- `../../../architecture/40_identity.md`: identity mixin baseline
- `../../../architecture/46_serialization.md`: serializer output shape
- `../../../architecture/46_serialization_local.md`: app-specific serializer delta (if present)

### Local extensions loaded

- `../../../architecture/06_commands_local.md`: `maybe_begin` transaction utility, session call safety rules, subordinate-command event rule
- `../../../architecture/07_queries_local.md`: offset pagination replaces cursor pagination

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `07_queries.md`, `46_serialization.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add` / `flush` / error-raising shape → `06_commands.md`
- Reading another query to understand handler wiring or ordering → `07_queries.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `working_section.py` for exact field names and column types
- Reading `list_working_sections.py` and `get_worker_working_sections.py` to see the current `.order_by()` expressions being replaced
- Reading `create_working_section_request.py` and `edit_working_section_request.py` to understand the existing field set and validator structure
- Reading `serializers.py` to see current signatures and all output keys before adding `order_list`

### Skill selection

- Primary skill: `06_commands.md` — field patch pattern (`model_fields_set` guard)
- Router trigger terms: n/a (no router changes)
- Excluded alternatives: `13_sockets.md` — no new event type required; `09_routers.md` — no handler changes

## Implementation plan

1. **Model** — In `beyo_manager/models/tables/working_sections/working_section.py`, add `Integer` to the existing `sqlalchemy` import. Insert the column after `image`:
   ```python
   order_list: Mapped[int | None] = mapped_column(Integer, nullable=True)
   ```

2. **Migration** — From `backend/app/` run:
   ```bash
   alembic revision --autogenerate -m "add_order_list_to_working_sections"
   ```
   Review the generated file; confirm it adds a nullable `Integer` column with no server default and no NOT NULL constraint. Apply with `alembic upgrade head`.

3. **Create request** — In `beyo_manager/services/commands/working_sections/requests/create_working_section_request.py`, add to `WorkingSectionCreateRequest`:
   ```python
   order_list: int | None = None
   ```

4. **Edit request** — In `beyo_manager/services/commands/working_sections/requests/edit_working_section_request.py`:
   - Add `order_list: int | None = None` to `WorkingSectionEditRequest`.
   - Add `"order_list"` to the `updatable` set inside `at_least_one_updatable_field`.
   - Update the error message string to include `order_list` in the field list.

5. **Create command** — In `beyo_manager/services/commands/working_sections/create_working_section.py`, add `order_list=request.order_list` to the `WorkingSection(...)` constructor.

6. **Edit command** — In `beyo_manager/services/commands/working_sections/edit_working_section.py`, add after the `image` patch block:
   ```python
   if "order_list" in request.model_fields_set:
       section.order_list = request.order_list
   ```

7. **Serializers** — In `beyo_manager/domain/working_sections/serializers.py`:
   - `serialize_working_section_compact`: add `order_list: int | None` as the last positional parameter (after `image`); add `"order_list": order_list` to the return dict.
   - `serialize_working_section_full`: add `"order_list": section.order_list` to the return dict.

8. **Call-site audit** — `grep -r "serialize_working_section_compact"` across the codebase; update every caller to pass `order_list` sourced from the ORM object or row available at that call-site.

9. **Query sort — list_working_sections** — In `beyo_manager/services/queries/working_sections/list_working_sections.py`, replace:
   ```python
   .order_by(WorkingSection.created_at.asc())
   ```
   with:
   ```python
   .order_by(WorkingSection.order_list.asc().nulls_last(), WorkingSection.created_at.asc())
   ```
   No new imports needed — `nulls_last()` is a method on the column expression.

10. **Query sort — get_worker_working_sections** — In `beyo_manager/services/queries/working_sections/get_worker_working_sections.py`, replace:
    ```python
    .order_by(WorkingSection.name.asc())
    ```
    with:
    ```python
    .order_by(WorkingSection.order_list.asc().nulls_last(), WorkingSection.name.asc())
    ```

## Risks and mitigations

- Risk: `serialize_working_section_compact` is called with positional args at call-sites — adding a new parameter shifts the positional order.
  Mitigation: Add `order_list` as the last positional parameter (after `image`) so existing positional callers break at parse time rather than silently passing the wrong value; audit all callers in step 8.

- Risk: The edit-request model validator error message becomes stale (doesn't list `order_list`).
  Mitigation: Update the message string in the same edit (step 4).

- Risk: Migration autogenerate misses the column if the model import path is not in `env.py` target metadata.
  Mitigation: `working_section.py` is already imported by the existing initial migration, so its table is known; no `env.py` change is needed.

## Validation plan

- `alembic upgrade head`: exits 0, no errors.
- `alembic downgrade -1`: exits 0, column removed cleanly.
- `grep "order_list" backend/app/beyo_manager/models/tables/working_sections/working_section.py`: returns the column line.
- Manual POST with `{"order_list": 3, ...}`: persisted value returned in full serialization.
- Manual POST without `order_list`: field is `null` in response.
- Manual PATCH with only `{"client_id": "...", "order_list": 5}`: accepted, no validation error.
- Manual PATCH with `{"client_id": "...", "order_list": null}`: accepted, resets to null.
- `GET /working-sections` with mixed sections (some with `order_list`, some without): numbered ones appear first in ascending order, nulls at the end sorted by `created_at`.
- `GET /worker/working-sections` same ordering behaviour with `name` as tiebreaker for nulls.

## Review log

_No entries yet._

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `copilot`
