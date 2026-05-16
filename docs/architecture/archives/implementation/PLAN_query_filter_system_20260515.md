# PLAN_query_filter_system_20260515

## Metadata

- Plan ID: `PLAN_query_filter_system_20260515`
- Status: `under_construction`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_query_filter_system_20260515.md`

## Goal and intent

- Goal: Create the `apply_string_filter` utility function that list queries use to apply case-insensitive partial string search (`q`) across declared ORM columns, with optional column scoping via `string_filters`.
- Business/user intent: Eliminate ad-hoc inline `.ilike` filter patterns by providing a single, tested, reusable utility that any query author or agent can call. Makes filter behavior consistent and discoverable via contract 55.
- Non-goals: Refactoring existing list queries to use this utility (separate per-domain plans); date filter utility (per-query, no shared function); enum/status filters; full-text search.

## Scope

- In scope:
  - `services/queries/utils/__init__.py` (package marker)
  - `services/queries/utils/string_filter.py` (`apply_string_filter` function)

- Out of scope:
  - Calling `apply_string_filter` from any existing query — this plan delivers the utility only
  - Any router, model, migration, or serializer changes
  - Date filter utility (each query implements its own inline block per contract 55)

- Assumptions:
  - SQLAlchemy `Select` and `InstrumentedAttribute` types are available in the existing dependency set
  - No database migration required — pure Python utility

## Clarifications required

None — all design decisions resolved in intention alignment.

## Acceptance criteria

1. `backend/app/beyo_manager/services/queries/utils/__init__.py` exists and is importable.
2. `apply_string_filter` is importable from `beyo_manager.services.queries.utils.string_filter`.
3. Called with `q=None` → returns `stmt` unchanged.
4. Called with `q=""` (empty string) → returns `stmt` unchanged.
5. Called with `q="foo"`, `string_filters=None` → applies `OR(col.ilike("%foo%"))` across all keys in `allowed_columns`.
6. Called with `q="foo"`, `string_filters="username,email"` → applies ILIKE only against `username` and `email` columns.
7. Called with `q="foo"`, `string_filters="nonexistent"` → returns `stmt` unchanged (invalid column silently ignored).
8. Function signature matches contract 55 exactly: `(stmt: Select, q: str | None, string_filters: str | None, allowed_columns: dict[str, InstrumentedAttribute]) -> Select`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries.md`: query layer structure and SQLAlchemy patterns
- `backend/architecture/07_queries_local.md`: app-local query overrides (offset pagination)
- `backend/architecture/55_query_filters_local.md`: **primary contract** — exact utility signature and behavior being implemented

### Local extensions loaded

- `backend/architecture/07_queries_local.md`: overrides cursor pagination with offset — does not affect this utility

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead. Contract 55 contains the exact implementation.
- **What exists** → reading is legitimate.

Prohibited (pattern reads — contract 55 already covers these):
- Reading another query file to understand ILIKE usage → contract 55 defines it
- Reading any existing filter or utility for the function shape → contract 55 defines the exact signature

Permitted (relational reads):
- Reading `__init__.py` files to verify import paths
- Reading `services/context.py` if the utility needs to reference `ServiceContext` (it does not — it takes `Select` directly)

### Skill selection

- Primary skill: not applicable — utility-only plan, no router or command scaffolding needed
- Excluded alternatives: command skill (no writes), router skill (no HTTP layer)

## Implementation plan

### File manifest

| Action | File | Notes |
|--------|------|-------|
| CREATE | `backend/app/beyo_manager/services/queries/utils/__init__.py` | Empty package marker |
| CREATE | `backend/app/beyo_manager/services/queries/utils/string_filter.py` | `apply_string_filter` function |

### Step 1 — Create `utils/__init__.py`

Empty file. No imports.

**Target content:**
```python
```

*(empty file — package marker only)*

---

### Step 2 — Create `utils/string_filter.py`

Implement `apply_string_filter` exactly as specified in contract 55.

**Target content:**
```python
from sqlalchemy import Select, or_
from sqlalchemy.orm import InstrumentedAttribute


def apply_string_filter(
    stmt: Select,
    q: str | None,
    string_filters: str | None,
    allowed_columns: dict[str, InstrumentedAttribute],
) -> Select:
    if not q:
        return stmt
    if string_filters:
        column_names = [c.strip() for c in string_filters.split(",") if c.strip()]
    else:
        column_names = list(allowed_columns.keys())
    valid = [allowed_columns[col] for col in column_names if col in allowed_columns]
    if not valid:
        return stmt
    return stmt.where(or_(*[col.ilike(f"%{q}%") for col in valid]))
```

**Do not add:**
- Module-level docstrings
- Inline comments explaining the logic (contract 55 is the documentation)
- Any imports beyond `Select`, `or_`, and `InstrumentedAttribute`

## Risks and mitigations

- Risk: Future callers pass mutable state as `allowed_columns` and modify it after calling.
  Mitigation: `allowed_columns` is used read-only inside the function; no mutation occurs.

- Risk: Copilot adds extra parameters or default fallbacks not in the contract signature.
  Mitigation: Acceptance criterion 8 requires the signature to match contract 55 exactly.

## Validation plan

- `python -c "from beyo_manager.services.queries.utils.string_filter import apply_string_filter; print('OK')"`: must print `OK` without error
- `python -m pytest backend/app/tests/ -k "string_filter" -v` (if tests exist): must pass

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David`
