# PLAN_case_reference_number_20260628

## Metadata

- Plan ID: `PLAN_case_reference_number_20260628`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-28T00:00:00Z`
- Last updated at (UTC): `2026-06-28T07:44:17Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/improving_note_system.txt`

## Goal and intent

- Goal: Add `scalar_id` and `reference_number` columns to the `cases` table, compute them on case creation, and expose them in case serializations.
- Business/user intent: Give each case a short human-readable reference number (e.g., `tsk-0023`) that surfaces in the UI and can be used for support lookups.
- Non-goals: Updating existing read queries to filter/sort by `reference_number`; changing the event schema emitted on `CaseEvent.CREATED`.

## Scope

- In scope:
  - `Case` model: new `scalar_id` (Integer, indexed, not-null) and `reference_number` (String(32), indexed, not-null) columns.
  - Alembic migration: add both columns nullable, backfill existing rows, then apply NOT NULL constraints and indexes.
  - `create_case` command: acquire a global advisory lock, compute `scalar_id` via `coalesce(max, 0) + 1`, derive `reference_number`, and write both fields.
  - `serialize_case` and `serialize_case_list_item`: expose `scalar_id` and `reference_number`.
- Out of scope:
  - Filtering/searching cases by `reference_number`.
  - Updating `update_case` or any other mutation to change `reference_number`.
  - Adding `reference_number` to event payloads or socket frames.
- Assumptions:
  - `scalar_id` is global (not workspace-scoped); `Case` has no `workspace_id` column.
  - The `entity_client_id` index prefix (e.g., `tsk` from `tsk-abc123`) is the intended "index" for the reference number. If no case link exists, the index is `N`.
  - Existing cases without a scalar_id should be backfilled in the migration ordered by `created_at` ascending; they all receive reference_number prefix `N` since link data is not reliably available at migration time.

## Clarifications required

- [ ] Should the backfill for existing cases use `N` as the prefix (safest, no join needed) or attempt to join `case_links` for each row? — this affects migration complexity and whether the initial reference numbers are meaningful.
- [ ] Is `scalar_id` truly global, or should it be scoped per-workspace in the future? — if workspace-scoped is likely, it's better to add a `workspace_id` column to `cases` now or reserve it; otherwise the advisory lock will become a global bottleneck.

## Acceptance criteria

1. A newly created case with no entity link has `scalar_id = N` (where N is the next integer) and `reference_number = "N-000N"` (zero-padded to ≥4 digits).
2. A newly created case linked to entity `tsk-abc123` has `reference_number = "tsk-000N"`.
3. Both `scalar_id` and `reference_number` appear in the responses of `serialize_case` and `serialize_case_list_item`.
4. Concurrent case creation does not produce duplicate `scalar_id` values (advisory lock test).
5. The migration runs cleanly on a non-empty `cases` table (backfill + NOT NULL).

## Contracts and skills

### Contracts loaded

- `../architecture/01_architecture.md`: overall system layering rules
- `../architecture/04_context.md`: `ServiceContext` usage
- `../architecture/05_errors.md`: `ValidationError` / `ConflictError` patterns
- `../architecture/06_commands.md`: command structure, session.add/flush, error-raising shape
- `../architecture/06_commands_local.md`: `maybe_begin` utility and session call safety rules
- `../architecture/07_queries.md`: select/scalar patterns
- `../architecture/07_queries_local.md`: offset pagination override
- `../architecture/09_routers.md`: no new router, but loaded for completeness
- `../architecture/21_naming_conventions.md`: column and file naming
- `../architecture/40_identity.md`: client_id / IdentityMixin patterns
- `../architecture/41_user.md`: user identity in commands
- `../architecture/42_event.md`: event dispatch (no new event, but existing `CaseEvent.CREATED` still fires)
- `../architecture/48_presence.md`: no changes, loaded as core
- `../architecture/03_models.md`: SQLAlchemy model column declarations
- `../architecture/30_migrations.md`: Alembic migration authoring rules
- `../architecture/46_serialization.md`: serializer shape and output conventions

### Local extensions loaded

- `../architecture/06_commands_local.md`: `maybe_begin` transaction utility, session call safety rules, subordinate-command event rule

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand session.add / flush / error-raising shape → `06_commands.md`
- Reading another serializer to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- `app/beyo_manager/models/tables/cases/case.py` — exact existing field names and types
- `app/beyo_manager/services/commands/cases/create_case.py` — where to inject scalar_id logic
- `app/beyo_manager/domain/cases/serializers.py` — which serializer functions to extend
- `app/beyo_manager/models/tables/tasks/task.py` — reference for `task_scalar_id` pattern (advisory lock + coalesce/max)
- `app/beyo_manager/services/commands/tasks/create_task.py` — reference for advisory lock + scalar_id assignment pattern (lines 59–68)

### Skill selection

- Primary skill: `../architecture/06_commands.md` (command mutation)
- Router trigger terms: none (no new endpoint)
- Excluded alternatives: `09_routers.md` — no new route added

## Implementation plan

### Step 1 — Model: add `scalar_id` and `reference_number` to `Case`

File: `app/beyo_manager/models/tables/cases/case.py`

Add two columns after `messages_count`:

```python
scalar_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
reference_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
```

No server default; values are always written by the command before flush.

### Step 2 — Migration: add columns, backfill, enforce NOT NULL

Generate a new Alembic revision. File name pattern: `<hash>_add_scalar_id_reference_number_to_cases.py`

**upgrade:**

```sql
-- 1. Add columns as nullable (no server default needed; we backfill immediately)
ALTER TABLE cases ADD COLUMN scalar_id INTEGER;
ALTER TABLE cases ADD COLUMN reference_number VARCHAR(32);

-- 2. Backfill: assign sequential scalar_ids ordered by created_at, prefix = 'N'
WITH ranked AS (
    SELECT client_id,
           ROW_NUMBER() OVER (ORDER BY created_at ASC, client_id ASC) AS rn
    FROM cases
)
UPDATE cases
SET scalar_id       = ranked.rn,
    reference_number = 'N-' || LPAD(ranked.rn::text, 4, '0')
FROM ranked
WHERE cases.client_id = ranked.client_id;

-- 3. Enforce NOT NULL
ALTER TABLE cases ALTER COLUMN scalar_id SET NOT NULL;
ALTER TABLE cases ALTER COLUMN reference_number SET NOT NULL;

-- 4. Indexes
CREATE INDEX ix_cases_scalar_id ON cases (scalar_id);
CREATE INDEX ix_cases_reference_number ON cases (reference_number);
```

**downgrade:**

```sql
DROP INDEX IF EXISTS ix_cases_reference_number;
DROP INDEX IF EXISTS ix_cases_scalar_id;
ALTER TABLE cases DROP COLUMN reference_number;
ALTER TABLE cases DROP COLUMN scalar_id;
```

Use `op.execute(text(...))` for the backfill UPDATE inside the Alembic `upgrade()` function. Use `op.add_column`, `op.alter_column`, `op.create_index`, and `op.drop_column` for the structural changes.

### Step 3 — Command: compute and assign `scalar_id` + `reference_number` in `create_case`

File: `app/beyo_manager/services/commands/cases/create_case.py`

**Imports to add:**

```python
from sqlalchemy import func, select, text  # text already imported; add func if not already present
```

`func` is already imported. `text` is already imported (via SQLAlchemy). No new imports needed.

**Inside `async with ctx.session.begin():`**, before creating the `Case` instance, insert:

```python
await ctx.session.execute(
    text("SELECT pg_advisory_xact_lock(hashtext('cases_scalar_id'))")
)
scalar_id_result = await ctx.session.execute(
    select(func.coalesce(func.max(Case.scalar_id), 0) + 1)
)
case_scalar_id = scalar_id_result.scalar_one()

# Derive the reference index from entity_client_id prefix, fall back to 'N'
ref_index = entity_client_id.split("-")[0] if entity_client_id else "N"
reference_number = f"{ref_index}-{str(case_scalar_id).zfill(4)}"
```

**Pass both fields into the `Case(...)` constructor:**

```python
case = Case(
    **case_kwargs,
    created_by_id=ctx.user_id,
    updated_by_id=ctx.user_id,
    state=CaseStateEnum.OPEN,
    case_type_id=case_type_id,
    type_label=type_label,
    scalar_id=case_scalar_id,
    reference_number=reference_number,
)
```

**Advisory lock note:** `hashtext('cases_scalar_id')` is a constant string that produces a stable integer hash, serializing all case-creation transactions globally. This mirrors the `hashtext(:workspace_id)` pattern in `create_task` but without workspace scoping, since `Case` has no `workspace_id` column.

**`zfill(4)` logic:** `str(n).zfill(4)` zero-pads to 4 digits minimum and expands naturally beyond 4 digits for n ≥ 10000 — matching the stated format.

### Step 4 — Serializers: expose `scalar_id` and `reference_number`

File: `app/beyo_manager/domain/cases/serializers.py`

**`serialize_case`** — add to the `payload` dict:

```python
"scalar_id": case.scalar_id,
"reference_number": case.reference_number,
```

**`serialize_case_list_item`** — add to the `payload` dict:

```python
"scalar_id": case.scalar_id,
"reference_number": case.reference_number,
```

No signature changes required; both fields come directly off the `case` object.

## Risks and mitigations

- Risk: Global advisory lock on `hashtext('cases_scalar_id')` serializes all concurrent case creations.
  Mitigation: Acceptable at current scale; mirrors the existing task pattern. Flag for revisit if case creation volume grows significantly.

- Risk: Backfill UPDATE assigns `N-` prefix to all existing rows even those that had an entity link.
  Mitigation: Noted in clarifications. If accurate historical prefixes are required, the migration must join `case_links` — accepted as out of scope unless confirmed otherwise.

- Risk: `entity_client_id.split("-")[0]` assumes client_id format `{prefix}-{rest}`. If any entity_client_id lacks a `-`, `split("-")[0]` returns the whole string.
  Mitigation: All client_ids in this system are generated by `IdentityMixin` with a mandatory prefix and `-` separator, so this is safe. Add a guard comment at the call site for clarity.

## Validation plan

- `alembic upgrade head`: migration applies cleanly with no errors on both empty and non-empty `cases` tables.
- `alembic downgrade -1` then `alembic upgrade head`: round-trip succeeds.
- POST create case (no entity link): response body contains `scalar_id: 1`, `reference_number: "N-0001"`.
- POST create case (entity_client_id `tsk-abc`): response body contains `reference_number: "tsk-0002"`.
- POST two concurrent cases: no duplicate `scalar_id` values in DB.
- GET case list: `scalar_id` and `reference_number` present in each item.

## Review log

- `2026-06-28`: Implemented case scalar/reference-number support, added migration `d1e2f3a4b5c6`, validated upgrade/downgrade round-trip on the local test database, and wrote the summary/archive artifacts.

## Lifecycle transition

- Current state: `archived`
- Next state: none
- Transition owner: `codex`
