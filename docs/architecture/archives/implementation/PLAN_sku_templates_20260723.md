# PLAN_sku_templates_20260723

## Metadata

- Plan ID: `PLAN_sku_templates_20260723`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-23T00:00:00Z`
- Last updated at (UTC): `2026-07-23T08:10:00Z`
- Related issue/ticket: `<id_or_link>`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_sku_templates_20260723.md`

## Goal and intent

- Goal: Add a `sku_templates` table and its command/query/router surface so the frontend can, per task type, fetch a configured SKU **prefix** plus the **next scalar number**, build a `prefix<sep><padded-number>` string on the item form, and atomically **reserve** the next number so two users never build the same SKU.
- Business/user intent: The `items.sku` column stays a free string. Users want a fast, predictable way to generate the next SKU for a given task type (e.g. `pre_order`) without hand-typing sequential numbers. A workspace configures one prefix per task type; the frontend reads it and composes the SKU.
- Non-goals:
  - No change to `items.sku` (remains a nullable free string).
  - No backfill/derivation of the counter from existing `items.sku` values (SKU is free-form and unreliable as a source of truth).
  - No enforcement that a created item's SKU actually matches the reserved value — the template is an aid, not a constraint.
  - No auto-advance of the counter inside the item-create command.

## Scope

- In scope:
  - New model `SkuTemplate` (`app/beyo_manager/models/tables/sku_templates/sku_template.py`), registered in `models/__init__.py`.
  - Alembic migration creating the table + reusing the existing `task_type` enum.
  - Commands: `create_sku_template`, `update_sku_template`, `reserve_sku_scalar` (atomic increment).
  - Queries: `list_sku_templates`, `get_sku_template_by_task_type` (the primary "give me the last sku for task_type=X" read).
  - Serializer + SKU formatting helper.
  - Self-contained router at `/api/v1/sku-templates`.
  - Domain event enum + realtime dispatch on create/update/reserve.
  - **Bootstrap phase** `seed_sku_templates` that seeds the default `pre_order` template (prefix `PRE_ORDER`), wired into `bootstrap_app`.
- Out of scope: frontend work; changes to `Item`; migrating historical SKUs.
- Assumptions (confirmed with product owner):
  1. **One prefix per (workspace, task_type)** → unique constraint `(workspace_id, task_type)`. The by-task-type query returns that single row.
  2. **Atomic reserve command** advances the counter (`UPDATE ... SET last_scalar = last_scalar + 1 ... RETURNING`), preventing duplicate numbers under concurrency.
  3. **Format is prefix + separator + zero-padded width** — the template stores `prefix`, `separator`, `pad_width`; the backend returns a fully formatted preview plus the raw parts.

## Clarifications required

All resolved with the product owner (2026-07-23):

- [x] `reserve_sku_scalar` **emits** a lightweight `SCALAR_RESERVED` realtime event (payload: `client_id` + new `last_scalar`) so other clients' "next number" preview stays fresh.
- [x] Roles: create/update = `[ADMIN, MANAGER]`; read + reserve = `[ADMIN, MANAGER, WORKER, SELLER]`. (Verify `SELLER`/`WORKER` constants exist in `routers/utils/roles` before wiring.)
- [x] `create_sku_template` is a **strict create** — raises `ConflictError` (409) if a non-deleted template already exists for the `(workspace_id, task_type)`; edits go through `PATCH /{client_id}` (`update_sku_template`).
- [x] **Bootstrap only** for prod — no paired Alembic data migration. Existing workspaces get the default `PRE_ORDER` template via `seed_sku_templates` on the next `bootstrap_app` run.

## Acceptance criteria

1. `GET /api/v1/sku-templates/by-task-type/{task_type}` returns `{ client_id, task_type, prefix, separator, pad_width, last_scalar, next_scalar, next_sku_preview }` where `next_scalar == last_scalar + 1` and `next_sku_preview == f"{prefix}{separator}{str(next_scalar).zfill(pad_width)}"`. Returns `404` when no template is configured for that task type.
2. `POST /api/v1/sku-templates` creates exactly one template per `(workspace_id, task_type)`; a second create for the same task type returns a conflict error.
3. `POST /api/v1/sku-templates/by-task-type/{task_type}/reserve` atomically increments `last_scalar` and returns the reserved scalar + formatted SKU; two concurrent reserve calls return two **distinct** consecutive scalars (no duplicates, no gaps under normal commit).
4. `PATCH /api/v1/sku-templates/{client_id}` updates `prefix`/`separator`/`pad_width` (and optionally corrects `last_scalar`) without breaking the unique key.
5. All reads are scoped to `ctx.workspace_id` and exclude soft-deleted rows; no cross-workspace leakage.
6. Alembic `upgrade head` then `downgrade -1` round-trips cleanly; `client_id_prefix_map.md` contains the new `skt` prefix.

## Contracts and skills

### Read order (baseline → local delta)

Per the contract-mapping guide's document-only protocol, load canonical first, then `*_local.md` if present; local overrides baseline for this app only.

### Contracts loaded

Core (always):
- `../architecture/01_architecture.md`: overall layering (model → command/query → router).
- `../architecture/04_context.md`: `ServiceContext` shape (`session`, `workspace_id`, `user_id`, `incoming_data`, `query_params`, `identity`).
- `../architecture/05_errors.md`: domain errors (`ConflictError`, `NotFound`, `ValidationError`) raised inside services; `run_service` is the single catch boundary.
- `../architecture/06_commands.md` + `../architecture/06_commands_local.md`: command signature `async def verb_noun(ctx) -> dict`; local adds `maybe_begin` transaction utility, session-call safety, subordinate-command event rule.
- `../architecture/07_queries.md` + `../architecture/07_queries_local.md`: query signature; **local overrides cursor pagination with offset** (use `limit+1` sentinel + `offset`).
- `../architecture/09_routers.md`: handler skeleton, `require_roles`, `get_db`, `run_service`, `build_ok`/`build_err`.
- `../architecture/21_naming_conventions.md`: table/column/file/endpoint naming.
- `../architecture/40_identity.md`: `IdentityMixin` / `client_id` / `CLIENT_ID_PREFIX` / `generate_id`.
- `../architecture/41_user.md` (+ `_local` if present): `created_by_id`/`updated_by_id` sourcing from `ctx.user_id`.
- `../architecture/42_event.md`: `build_workspace_event` + `dispatch` after commit.
- `../architecture/48_presence.md`, `../architecture/46_serialization.md`: serializer contract (expose `client_id`, enums as `.value`, datetimes as `.isoformat()`).

Added from guide — **CRUD + realtime** bundle (this is a new table with realtime sync):
- `../architecture/03_models.md`: SQLAlchemy model conventions (columns, `__table_args__`, enum via `configure_sa_enum_values`).
- `../architecture/08_domain.md`: where enums/serializers/formatting live.
- `../architecture/11_infra_events.md`: event infra.
- `../architecture/13_sockets.md`: realtime dispatch surface.
- `../architecture/30_migrations.md`: nullable-first, trim autogenerate drift, enum `create_type` handling.
- `../architecture/15_testing.md`: test layout for command/query/router.

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin(ctx.session)` wraps writes; dispatch events only **after** the transaction commits.
- `../architecture/07_queries_local.md`: offset pagination (not cursor).
- Load any `40_identity_local.md` / `42_event_local.md` if they exist in the folder before coding.

### File read intent — pattern vs. relational

Reads already performed (relational — "what exists", permitted):
- `app/beyo_manager/models/tables/items/item.py` — exact item columns/indexes (SKU stays free string).
- `app/beyo_manager/domain/tasks/enums.py` — `TaskTypeEnum = {RETURN, PRE_ORDER, INTERNAL}` (reused, not redefined).
- `app/beyo_manager/models/__init__.py`, `models/base/identity.py`, `client_id_prefix_map.md` — registration + identity mechanics + free prefix.
- Reference-only (canonical shapes, do not copy blindly): `item_category.py`, `create_pause_reason.py`, `item_categories.py` (query), `item_categories.py` (router), `ad5da5b32355_create_pause_reasons_table.py` (migration).

Do **not** re-open other commands/queries/routers/serializers to relearn structure — `06/07/09/46` already define it.

### Skill selection

- Primary skill: contract-driven implementation (no code-generation skill required).
- Router trigger terms: `crud`, `realtime`, `migration`.
- Excluded alternatives: background-jobs / replayability contracts — no async worker, retry, or replay involved.

## Data model

Table `sku_templates` — `class SkuTemplate(IdentityMixin, Base)`, `CLIENT_ID_PREFIX = "skt"` (verified free in `client_id_prefix_map.md`).

| Column | Type | Notes |
|---|---|---|
| `client_id` | `String(64)` PK | from `IdentityMixin`, `skt_<ULID>` |
| `workspace_id` | `String(64)` FK→`workspaces.client_id` `ondelete=RESTRICT` | `nullable=False`, `index=True` |
| `task_type` | `SAEnum(TaskTypeEnum, name="business_task_type_enum", create_type=False)` | `nullable=False`; reuse the existing business task enum; do not create a new PG enum or drop it on downgrade. |
| `prefix` | `String(32)` | `nullable=False`; user-chosen |
| `separator` | `String(8)` | `nullable=False`, default `"-"` |
| `pad_width` | `Integer` | `nullable=False`, default `4`; `0` = no padding |
| `last_scalar` | `Integer` | `nullable=False`, default `0`; highest **reserved** number. `next = last_scalar + 1` |
| audit | — | `created_at`, `created_by_id`, `updated_at`, `updated_by_id`, `is_deleted`, `deleted_at`, `deleted_by_id` — declared explicitly (no audit mixin), mirroring `item_category.py` |

`__table_args__`:
- `UniqueConstraint("workspace_id", "task_type", name="uq_sku_templates_workspace_task_type")` — enforces one prefix per task type. Consider a partial unique index excluding soft-deleted rows (mirror the item partial-unique pattern) if templates can be soft-deleted and re-created: `Index("uix_sku_templates_workspace_task_type", "workspace_id", "task_type", unique=True, postgresql_where=text("is_deleted = false"))`. **Pick one** and document why.

Implementation choice: the plain unique constraint is used because this scope has no delete/recreate command; it enforces the confirmed one-template-per-key rule even if a row is later soft-deleted.

Formatting helper (`app/beyo_manager/domain/sku_templates/formatting.py`):
```python
def format_sku(prefix: str, separator: str, pad_width: int, scalar: int) -> str:
    return f"{prefix}{separator}{str(scalar).zfill(pad_width)}"
```

## API surface (self-contained router `/api/v1/sku-templates`)

- `GET /api/v1/sku-templates` → `list_sku_templates` (all templates for workspace; offset pagination).
- `GET /api/v1/sku-templates/by-task-type/{task_type}` → `get_sku_template_by_task_type` — **the primary read**; returns the template + `next_scalar` + `next_sku_preview`; `404` if none.
- `POST /api/v1/sku-templates` → `create_sku_template` (body: `task_type`, `prefix`, `separator?`, `pad_width?`, `initial_scalar?`); conflict if one already exists for that task type.
- `PATCH /api/v1/sku-templates/{client_id}` → `update_sku_template` (any of `prefix`, `separator`, `pad_width`, `last_scalar`).
- `POST /api/v1/sku-templates/by-task-type/{task_type}/reserve` → `reserve_sku_scalar` — atomic; returns `{ reserved_scalar, sku, task_type, client_id }`.

Serialized shape (`serialize_sku_template`, `app/beyo_manager/domain/sku_templates/serializers.py`):
```json
{
  "client_id": "skt_...",
  "workspace_id": "wsp_...",
  "task_type": "pre_order",
  "prefix": "PRE",
  "separator": "-",
  "pad_width": 4,
  "last_scalar": 6,
  "next_scalar": 7,
  "next_sku_preview": "PRE-0007",
  "created_at": "…", "created_by_id": "usr_…", "updated_at": null
}
```

## Implementation plan

1. **Model** — create `app/beyo_manager/models/tables/sku_templates/__init__.py` and `sku_template.py` per the Data model table above (mirror `item_category.py`'s enum/audit/`__table_args__` shape; `SAEnum = configure_sa_enum_values(SAEnum)`). Reuse `TaskTypeEnum` from `beyo_manager.domain.tasks.enums`.
2. **Register model** — add `from beyo_manager.models.tables.sku_templates import sku_template  # noqa: F401` to `app/beyo_manager/models/__init__.py`, after `workspaces` and the tasks/task_type-defining model (dependency order).
3. **Prefix map** — add a `skt` row to `app/beyo_manager/models/tables/client_id_prefix_map.md` (and the models `README.md` table if it enumerates tables).
4. **Domain layer** — `app/beyo_manager/domain/sku_templates/`: `formatting.py` (`format_sku`), `serializers.py` (`serialize_sku_template`, computing `next_scalar`/`next_sku_preview`), `events.py` (`SkuTemplateEvent` enum: `CREATED`, `UPDATED`, `SCALAR_RESERVED`).
5. **Request models** — `app/beyo_manager/services/commands/sku_templates/requests/`: Pydantic `BaseModel`s with `@field_validator` (trim/upper `prefix`, `pad_width >= 0`, `separator` length ≤ 8, `task_type` ∈ enum), each wrapped by a `parse_*_request(ctx.incoming_data)` that converts `PydanticValidationError` → domain `ValidationError`.
6. **Commands** (`app/beyo_manager/services/commands/sku_templates/`), each `async def (ctx) -> dict`, writes wrapped in `async with maybe_begin(ctx.session)`, events dispatched after commit:
   - `create_sku_template.py` — parse request; `select` existing `(workspace_id, task_type, is_deleted==False)` → raise `ConflictError` if found; construct row with `workspace_id=ctx.workspace_id`, `created_by_id=ctx.user_id`, `last_scalar=initial_scalar or 0`; `add` + `flush`; emit `SkuTemplateEvent.CREATED`.
   - `update_sku_template.py` — load by `client_id` + workspace scope (`NotFound` if missing); apply provided fields; set `updated_by_id`; emit `UPDATED`.
   - `reserve_sku_scalar.py` — **atomic increment**:
     ```python
     stmt = (
         update(SkuTemplate)
         .where(
             SkuTemplate.workspace_id == ctx.workspace_id,
             SkuTemplate.task_type == task_type,
             SkuTemplate.is_deleted.is_(False),
         )
         .values(last_scalar=SkuTemplate.last_scalar + 1, updated_by_id=ctx.user_id)
         .returning(SkuTemplate.client_id, SkuTemplate.last_scalar, SkuTemplate.prefix,
                    SkuTemplate.separator, SkuTemplate.pad_width)
     )
     row = (await ctx.session.execute(stmt)).one_or_none()
     if row is None:
         raise NotFound(...)
     reserved = row.last_scalar
     sku = format_sku(row.prefix, row.separator, row.pad_width, reserved)
     ```
     Emit `SCALAR_RESERVED` (pending clarification). Return `{ "client_id": ..., "task_type": ..., "reserved_scalar": reserved, "sku": sku }`. The single `UPDATE ... RETURNING` is row-atomic, so concurrent reservers serialize on the row lock and receive distinct consecutive scalars.
7. **Queries** (`app/beyo_manager/services/queries/sku_templates/`):
   - `list_sku_templates.py` — filter `workspace_id == ctx.workspace_id`, `is_deleted.is_(False)`; `order_by(task_type)`; offset pagination (`limit+1` sentinel) per `07_queries_local.md`.
   - `get_sku_template_by_task_type.py` — validate `task_type`; `scalar_one_or_none()`; `NotFound` if absent; return `serialize_sku_template(row)` (serializer computes `next_scalar`/`next_sku_preview`).
8. **Router** — `app/beyo_manager/routers/api_v1/sku_templates.py`, self-contained `APIRouter(prefix="/api/v1/sku-templates", tags=["sku-templates"])`; handlers build `ServiceContext(...)` and go through `run_service` → `build_ok`/`build_err`; auth via `require_roles([...])` per the roles clarification (config vs. reserve/read split).
9. **Register router** — add `sku_templates` to `app/beyo_manager/routers/api_v1/__init__.py` (`app.include_router(sku_templates.router)` — self-contained style).
9a. **Bootstrap phase** — `app/beyo_manager/services/commands/bootstrap/phases/seed_sku_templates.py`, mirroring the idempotent shape of `seed_pause_reasons.py`:
   ```python
   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession

   from beyo_manager.domain.tasks.enums import TaskTypeEnum
   from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate

   # (task_type, prefix, separator, pad_width, initial_last_scalar)
   _SKU_TEMPLATES = (
       (TaskTypeEnum.PRE_ORDER, "PRE_ORDER", "-", 4, 0),
   )

   async def seed_sku_templates(session: AsyncSession, workspace_id: str) -> dict[str, str]:
       sku_template_ids: dict[str, str] = {}
       for task_type, prefix, separator, pad_width, initial_scalar in _SKU_TEMPLATES:
           existing = await session.scalar(
               select(SkuTemplate).where(
                   SkuTemplate.workspace_id == workspace_id,
                   SkuTemplate.task_type == task_type,
                   SkuTemplate.is_deleted.is_(False),
               )
           )
           if existing is not None:
               sku_template_ids[task_type.value] = existing.client_id
               continue
           template = SkuTemplate(
               workspace_id=workspace_id,
               task_type=task_type,
               prefix=prefix,
               separator=separator,
               pad_width=pad_width,
               last_scalar=initial_scalar,
               created_by_id=None,
           )
           session.add(template)
           await session.flush()
           sku_template_ids[task_type.value] = template.client_id
       return sku_template_ids
   ```
   Idempotency key is `(workspace_id, task_type)` — a rerun leaves an existing template (and its advanced `last_scalar`) untouched, never resetting the counter. Seed as a `tuple` so more task-type prefixes can be added later.
9b. **Wire the phase** — in `app/beyo_manager/services/commands/bootstrap/bootstrap_app.py`: add the import next to the other phase imports and call `await seed_sku_templates(ctx.session, workspace_result["workspace_id"])` inside the `async with ctx.session.begin():` block (after `seed_workspace`, since it needs `workspace_id`). Optionally surface `"sku_templates_seeded": list(sku_template_ids.keys())` in the returned dict, mirroring `pause_reasons_seeded`.
   - **Decided: bootstrap only** — no paired Alembic data migration. Existing prod workspaces receive the default on their next `bootstrap_app` run.
10. **Migration** — `APP_ENV=development alembic revision --autogenerate -m "create sku_templates table"` from `app/`; then hand-edit to: chain `down_revision`; use existing `task_type_enum` with `create_type=False` (verify enum already exists — do NOT recreate/drop a shared enum in `downgrade`); include the unique constraint/index; trim unrelated autogenerate drift. `upgrade` creates table; `downgrade` drops table + its own indexes only.
11. **Tests** (`15_testing.md` layout): command tests (create conflict, reserve monotonicity incl. a concurrent-reserve test asserting distinct scalars, update), query tests (by-task-type 404 + preview math, workspace isolation), router smoke tests (auth + happy path).

## Risks and mitigations

- Risk: Recreating or dropping the shared `task_type_enum` in the migration breaks the tasks table.
  Mitigation: `create_type=False`; verify the enum's exact PG name against the tasks migration; never `DROP TYPE` in `downgrade`.
- Risk: Concurrent reserves hand out duplicate scalars.
  Mitigation: single `UPDATE ... SET last_scalar = last_scalar + 1 ... RETURNING` (row-level lock); add a concurrency test.
- Risk: Duplicate templates per task type slipping past a plain unique constraint if soft-delete + recreate is allowed.
  Mitigation: decide unique-constraint vs. partial-unique-index up front (documented in Data model) and match the migration to it.
- Risk: `reserve` events flooding the socket channel.
  Mitigation: resolve the reserve-event clarification before wiring dispatch; keep the payload minimal.
- Risk: Pattern drift (reading unrelated commands to relearn structure).
  Mitigation: rely on `06/07/09/46`; only relational reads permitted.

## Validation plan

- `APP_ENV=development alembic upgrade head` then `alembic downgrade -1`: table created and dropped cleanly, shared `business_task_type_enum` untouched.
- `python scripts/apply_db_triggers.py` (if triggers apply to new tables): no error.
- `GET /api/v1/sku-templates/by-task-type/pre_order` after configuring `PRE`/`-`/`4` with `last_scalar=6` → `next_scalar=7`, `next_sku_preview="PRE-0007"`.
- Two rapid `POST .../by-task-type/pre_order/reserve` → distinct scalars `7` then `8`; `last_scalar` ends at `8`.
- Duplicate `POST /api/v1/sku-templates` for `pre_order` → conflict error.
- Run `bootstrap_app` on a fresh DB → a `pre_order` template with prefix `PRE_ORDER` exists (`GET .../by-task-type/pre_order` → `next_sku_preview="PRE_ORDER-0001"`). Re-run bootstrap → **no** duplicate and `last_scalar` unchanged (idempotent; counter not reset).
- Cross-workspace `GET`/reserve returns `404` for another workspace's task type.
- `pytest` for the new command/query/router tests: all green.

## Review log

- `2026-07-23` `owner`: initial plan drafted from confirmed decisions (one prefix per task type; atomic reserve; prefix+separator+pad_width).
- `2026-07-23` `codex`: implemented and validated. The repository's existing task enum is `business_task_type_enum` (not `task_type_enum`), so the migration reuses it with PostgreSQL `ENUM(create_type=False)` and never drops it. Focused SKU tests pass; the full suite retains 30 unrelated failures already present in the dirty worktree.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
