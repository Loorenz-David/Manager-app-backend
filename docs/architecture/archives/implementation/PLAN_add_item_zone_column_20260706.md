# PLAN_add_item_zone_column_20260706

## Metadata

- Plan ID: `PLAN_add_item_zone_column_20260706`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T00:00:00Z`
- Last updated at (UTC): `2026-07-06T17:09:20Z`
- Related issue/ticket: `N/A`
- Intention plan: `N/A`

## Goal and intent

- Goal: Add a new nullable string column `item_zone` to the `Item` model, mirroring the existing `item_position` column everywhere it is written (create / update / find-or-create / task-embedded item input / batch) and everywhere it is serialized. Then generate and apply the Alembic migration.
- Business/user intent: Items need a second free-text location descriptor (`item_zone`) alongside `item_position`, editable through the same flows and visible in the same API responses.
- Non-goals:
  - No new endpoint, command, or serializer is created — `item_zone` is added to the **existing** ones that already carry `item_position`.
  - No batch endpoint dedicated to `item_zone` (the existing batch endpoint is `batch_update_item_positions`, scoped to positions; see Clarifications — default is to leave it position-only).
  - No search/filter (`ilike`) support for `item_zone` (the `item_position` `ilike` query filters are out of scope; see Clarifications).
  - No enum, no index, no uniqueness on `item_zone`.
  - No history/event semantics beyond what the existing update flow already emits.

## Scope

- In scope (add `item_zone: str | None`, nullable, `String(255)`, mirroring `item_position` exactly):
  1. Model: `models/tables/items/item.py` — add the column.
  2. Command request models (pydantic): `services/commands/items/requests/__init__.py`
     - `CreateItemRequest`, `UpdateItemRequest`, `FindOrCreateItemRequest` — add `item_zone: str | None = None`.
  3. Task-embedded item inputs: `services/commands/tasks/requests/__init__.py` `FindOrCreateItemInput` — add `item_zone: str | None = None`.
  4. Command write logic:
     - `services/commands/items/create_item.py` — add `item_zone=request.item_zone` to the `Item(...)` constructor.
     - `services/commands/items/find_or_create_item.py` — add `"item_zone"` to `_DIRECT_FIELDS` (drives the update branch) **and** `item_zone=request.item_zone` in the `Item(...)` constructor (create branch).
     - `services/commands/items/update_item.py` — add `"item_zone"` to `_DIRECT_FIELDS`.
  5. Router request bodies: `routers/api_v1/items.py` — `_CreateItemBody`, `_UpdateItemBody`, `_FindOrCreateItemBody`; and `routers/api_v1/tasks.py` — `_TaskItemInputBody`. Add `item_zone: str | None = None`.
  6. Serializers: `domain/items/serializers.py` `_serialize_item_base` and `domain/tasks/serializers.py` (the item serializer at ~line 105) — add `"item_zone": item.item_zone`.
  7. Migration: autogenerate + review + `alembic upgrade head`.
- Out of scope:
  - `batch_update_item_positions` command / `_BatchUpdateItemPositionsBody` / `ItemPositionEntry` — leave position-only (Clarification #1).
  - `item_position` `ilike` search filters in `services/queries/**` (task_search, upholstery_*, items, seat_tasks_*) — no `item_zone` filter added (Clarification #2).
  - Frontend.
- Assumptions:
  - `item_zone` semantics = free-text, same shape/constraints as `item_position` (`String(255)`, nullable, no validation).
  - Task create/update forwards item fields via `request.item.model_dump(exclude_unset=True)` into `find_or_create_item` (confirmed in `create_task.py:163-167`), so adding `item_zone` to `FindOrCreateItemInput` + `FindOrCreateItemRequest` + `find_or_create_item` is sufficient — no explicit field mapping edit needed in `create_task.py`.
  - `update_task.py` does not write item fields (it references `item_location`, unrelated), so no change there.

## Clarifications required

- [ ] **Batch endpoint**: Should `item_zone` also be batch-updatable via the existing `batch_update_item_positions` flow (which would mean renaming/extending it), or stay position-only? — Default assumption: **stay position-only**, `item_zone` is edited via create/update/find-or-create only. Blocks whether `batch_update_item_positions.py` + `ItemPositionEntry` + `_BatchUpdateItemPositionsBody` + `_ItemPositionEntry` are touched.
- [ ] **Search/filter**: Should `item_zone` be searchable (`ilike`) in the same queries where `item_position` is (`task_search.py`, `upholstery_*`, `items.py` query, `seat_tasks_pending_upholstery.py`)? — Default assumption: **no**. Blocks whether contract `55` (string search) is loaded and those query files are edited.

> Both default assumptions keep the change to "mirror `item_position` on the single-item write/serialize paths." If either answer is "yes," expand Scope and reload the noted contracts before coding.

## Acceptance criteria

1. `Item` has a nullable `item_zone` column, `String(255)`, no index/constraint/default, positioned like `item_position`.
2. Creating an item (via `PUT /items`, via task create, via find-or-create) with `item_zone` persists it; omitting it stores `NULL`.
3. Updating an item (via `PATCH`/update route) with `item_zone` present writes it; omitting the key leaves the existing value unchanged (present-key semantics via `model_fields_set`, identical to `item_position`).
4. Every API response that currently includes `item_position` also includes `item_zone` with the stored value (`domain/items/serializers.py` and `domain/tasks/serializers.py`).
5. A new Alembic migration exists in `app/migrations/versions/` adding only the `item_zone` column, generated via `--autogenerate` and reviewed; `alembic upgrade head` applies cleanly.
6. No behavior change to `item_position` anywhere.

## Contracts and skills

Resolution per `task_system/backend_contract_goal_mapping_guide.md`. Contracts live in `backend/architecture/` (the guide's `../architecture/` relative to `task_system/`).

### Contracts loaded

Core (always):
- `architecture/01_architecture.md` — layering baseline.
- `architecture/04_context.md` — `ServiceContext` usage in commands.
- `architecture/05_errors.md` — error-raising conventions (no new errors expected).
- `architecture/06_commands.md` + `architecture/06_commands_local.md` — command structure, `maybe_begin`, session/event rules (edits touch create/update/find-or-create commands).
- `architecture/09_routers.md` — router request-body wiring (adding a field to existing bodies).
- `architecture/21_naming_conventions.md` — column/field naming (`item_zone` snake_case, mirrors `item_position`).

Primary goal bundle — **CRUD + realtime** (this is a model+CRUD change):
- `architecture/03_models.md` — how to declare the `mapped_column` (nullable String).
- `architecture/30_migrations.md` — autogenerate → review → `upgrade head` (see Implementation step 8).
- `architecture/46_serialization.md` + `architecture/46_serialization_local.md` — how to add a field to existing serializers.

### Local extensions loaded

- `architecture/06_commands_local.md` — `maybe_begin` transaction utility + subordinate-command event rule (baseline: `06_commands.md`).
- `architecture/46_serialization_local.md` — app-specific serializer deltas (baseline: `46_serialization.md`).

Read order / applied precedence: canonical first, then `_local.md`; local overrides baseline only for this app.

### Excluded contracts

- `architecture/07_queries.md` (+local) — no query/read-model change (search filters are out of scope per Clarification #2).
- `architecture/08_domain.md`, `11_infra_events.md`, `13_sockets.md` — no new enum, event, or socket; the existing `item:updated` event in `update_item` is unchanged and needs no contract work.
- `architecture/15_testing.md` — load only if adding tests (recommended but not required by the request).
- Trigger-map `55` (string search) — excluded unless Clarification #2 is answered "yes."

### File read intent — pattern vs. relational

Relational reads already performed during planning (understanding what exists — permitted): `item.py`, both serializers, `create_item.py`, `update_item.py`, `find_or_create_item.py`, the item request models in `services/commands/items/requests/__init__.py` and `services/commands/tasks/requests/__init__.py`, the router bodies in `items.py`/`tasks.py`, and `create_task.py:163-167`. These established exact field names, ordering, and the `model_dump` passthrough.

Prohibited (pattern reads): do **not** open other commands/routers/serializers to "learn the shape" — `03_models.md`, `06_commands.md`, `09_routers.md`, `46_serialization.md` already define it.

### Skill selection

- Primary skill: `N/A` — mechanical field addition mirroring an existing column.
- Router trigger terms: `model column, serializer field, alembic migration`.
- Excluded alternatives: none.

## Implementation plan

1. `models/tables/items/item.py`: add, directly under the `item_position` line (43):
   `item_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)`
2. `services/commands/items/requests/__init__.py`: add `item_zone: str | None = None` to `CreateItemRequest`, `UpdateItemRequest`, and `FindOrCreateItemRequest` (place next to `item_position` in each).
3. `services/commands/tasks/requests/__init__.py`: add `item_zone: str | None = None` to `FindOrCreateItemInput` (next to `item_position`, line ~39).
4. `services/commands/items/update_item.py`: add `"item_zone"` to `_DIRECT_FIELDS`.
5. `services/commands/items/find_or_create_item.py`: add `"item_zone"` to `_DIRECT_FIELDS` **and** `item_zone=request.item_zone` to the `Item(...)` constructor (create branch, next to `item_position=`).
6. `services/commands/items/create_item.py`: add `item_zone=request.item_zone` to the `Item(...)` constructor (next to `item_position=`).
7. Routers — add `item_zone: str | None = None`:
   - `routers/api_v1/items.py`: `_CreateItemBody`, `_UpdateItemBody`, `_FindOrCreateItemBody`.
   - `routers/api_v1/tasks.py`: `_TaskItemInputBody`.
8. Serializers — add `"item_zone": item.item_zone`:
   - `domain/items/serializers.py` → `_serialize_item_base` (next to line 106).
   - `domain/tasks/serializers.py` → the item serializer (next to line 105).
9. Migration (per `30_migrations.md`, run from `app/`):
   - `APP_ENV=development alembic revision --autogenerate -m "add_item_zone_to_items"`
   - Review the generated file in `app/migrations/versions/`: it must contain exactly one `op.add_column('items', sa.Column('item_zone', sa.String(length=255), nullable=True))` and its reverse `op.drop_column`. Remove any unrelated autogenerated ops (drift), keeping only the `item_zone` add.
   - `APP_ENV=development alembic upgrade head`
10. Verify no remaining write/serialize path references `item_position` without a sibling `item_zone` (grep check in Validation).

## Risks and mitigations

- Risk: Autogenerate picks up unrelated model drift and emits extra `op.*` calls.
  Mitigation: Review the generated migration and strip everything except the `item_zone` add/drop before `upgrade head` (Acceptance #5). Never hand-write the column SQL — edit the generated file only.
- Risk: Missing one of the several write paths (e.g. `find_or_create_item` has *two* touch points — the `_DIRECT_FIELDS` set for updates and the constructor for creates).
  Mitigation: Explicit per-file checklist in steps 2-8; final grep in Validation compares `item_zone` occurrences against `item_position` occurrences.
- Risk: Task-create path silently drops `item_zone`.
  Mitigation: Confirmed `create_task.py` forwards via `model_dump(exclude_unset=True)`; adding the field to `FindOrCreateItemInput` + `FindOrCreateItemRequest` + `find_or_create_item` is sufficient — no `create_task.py` edit. Covered by Acceptance #2 (task-create case).
- Risk: Scope creep into batch/search.
  Mitigation: Both gated behind Clarifications with explicit "no" defaults; do not touch `batch_update_item_positions` or query `ilike` filters unless answered otherwise.

## Validation plan

- `alembic upgrade head` (from `app/`): applies cleanly; `alembic current` shows the new head.
- Static: repo linter on all changed files; no unused imports; app imports without error (`python -c "import beyo_manager"` or equivalent).
- Grep parity check (from `app/`): `grep -rn "item_position" beyo_manager --include=*.py` vs `grep -rn "item_zone" beyo_manager --include=*.py` — every **write** and **serialize** site with `item_position` (model, 3 item request models, `FindOrCreateItemInput`, 4 router bodies, `create_item`, `find_or_create_item` ×2, `update_item` `_DIRECT_FIELDS`, both serializers) has a matching `item_zone`. Query `ilike` sites intentionally have no `item_zone` (Clarification #2).
- Functional smoke (optional, recommended): `PUT /items` with `item_zone` → GET the item → response contains the value; `PATCH` update changing only `item_zone` → other fields unchanged; task-create with an embedded item carrying `item_zone` → persisted.
- (If tests are added) unit tests for create/update/find-or-create round-tripping `item_zone` and serializer output — per `15_testing.md`.

## Review log

- `2026-07-06` `owner`: drafted from a full trace of every `item_position` reference; identified the `_DIRECT_FIELDS` passthrough pattern (update paths) and explicit-constructor pattern (create paths) as the two write shapes to mirror.
- `2026-07-06` `codex`: implemented the `item_zone` field across model, request, router, command, serializer, and migration paths; reviewed autogenerate output to remove unrelated drift; applied migration `03cfb5308256`; wrote summary and archive record.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
