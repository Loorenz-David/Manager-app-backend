# 55 — Query Filter System (local-only contract)

> Local-only — no canonical counterpart. Governs all list query filter conventions for this app.
> See: [[INTENTION_query_filter_system_20260515]]

---

## Purpose

Define a consistent, reusable filter system for list queries:

- Free-text string search via `q` (case-insensitive partial match)
- Column scoping via `string_filters`
- Date range filter naming convention

All list queries that accept user-driven search or filtering **must** follow this contract.

---

## Filter types

### 1. String search — `q`

| Property | Value |
|----------|-------|
| Param name | `q` |
| Type | `str \| None` |
| Match strategy | Case-insensitive partial match (`ILIKE '%value%'`) |
| Applied via | `apply_string_filter` utility (see below) |
| Validated at | Router layer — `max_length=200` |

If `q` is `None` or empty string, the statement is returned unchanged.

---

### 2. Column scope — `string_filters`

| Property | Value |
|----------|-------|
| Param name | `string_filters` |
| Type | `str \| None` |
| Format | Comma-separated column names: `"username,email"` |
| Absent behavior | Apply `q` against **all** columns in `allowed_columns` |
| Invalid names | Silently ignored — no error raised |

Parsing: split on `,`, strip whitespace, drop empty strings.

---

### 3. Date range filters

Each query declares which date fields it supports. No shared utility — implement inline.

**Naming convention:**

| Param | Meaning | SQL equivalent |
|-------|---------|----------------|
| `{field}_before` | Exclusive upper bound | `field < value` |
| `{field}_after` | Inclusive lower bound | `field >= value` |

**Examples:** `created_at_before=2025-01-01`, `created_at_after=2024-01-01`

**Format:** ISO 8601 date (`YYYY-MM-DD`) or datetime (`YYYY-MM-DDTHH:MM:SSZ`). Parse with `date.fromisoformat()` or `datetime.fromisoformat()`.

---

## Shared utility: `apply_string_filter`

### File location

```
backend/app/beyo_manager/services/queries/utils/string_filter.py
```

### Signature and implementation

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

### Rules

- Never call outside of a query function — it is a filter helper, not a service.
- `allowed_columns` is defined **per query** as a module-level constant. It is never shared globally.
- Do **not** include `password`, hash fields, or internal identifiers in `allowed_columns`.
- Do **not** apply to a subquery or CTE result — only to a live `select()` statement that will be executed directly.

---

## Usage pattern — list query

```python
from sqlalchemy import select

from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_STRING_COLUMNS = {
    "username": User.username,
    "email": User.email,
    "phone_number": User.phone_number,
}


async def list_users(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")

    stmt = select(User).where(
        User.workspace_id == ctx.workspace_id,
        User.is_deleted.is_(False),
    )
    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)

    # Optional date range filters (per-query)
    if created_after := ctx.query_params.get("created_at_after"):
        from datetime import date
        stmt = stmt.where(User.created_at >= date.fromisoformat(created_after))
    if created_before := ctx.query_params.get("created_at_before"):
        from datetime import date
        stmt = stmt.where(User.created_at < date.fromisoformat(created_before))

    stmt = stmt.order_by(User.created_at.asc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "users": [serialize_user(u) for u in page],
        "users_pagination": {"has_more": has_more, "limit": limit, "offset": offset},
    }
```

---

## Joined table columns

`allowed_columns` may include columns from joined tables. The utility treats all `InstrumentedAttribute` values identically — it does not distinguish primary table columns from joined table columns.

**Constraint**: any join required by a column in `allowed_columns` must be present in the base statement **before** `apply_string_filter` is called. The utility appends a `WHERE` clause; it does not add joins.

```python
from beyo_manager.models.tables.workspaces.workspace_role import WorkspaceRole
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership

_ALLOWED_STRING_COLUMNS = {
    "username": User.username,
    "email": User.email,
    "role_name": WorkspaceRole.name,   # column from joined table
}


async def list_users(ctx: ServiceContext) -> dict:
    ...
    stmt = (
        select(User)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.client_id)
        .join(WorkspaceRole, WorkspaceRole.client_id == WorkspaceMembership.workspace_role_id)
        .where(
            User.workspace_id == ctx.workspace_id,
            WorkspaceMembership.workspace_id == ctx.workspace_id,
            WorkspaceMembership.is_active.is_(True),
        )
    )
    # JOIN is in place — safe to reference WorkspaceRole.name in the WHERE clause
    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_STRING_COLUMNS)
    ...
```

**When the join is optional (expensive and not always needed):**

If a joined column is only relevant when the user explicitly requests it via `string_filters`, keep the join out of the base statement and conditionally add it:

```python
_PRIMARY_COLUMNS = {"username": User.username, "email": User.email}
_JOINED_COLUMNS = {"role_name": WorkspaceRole.name}
_ALL_COLUMNS = {**_PRIMARY_COLUMNS, **_JOINED_COLUMNS}

async def list_users(ctx: ServiceContext) -> dict:
    ...
    requested = (
        [c.strip() for c in string_filters.split(",") if c.strip()]
        if string_filters
        else list(_ALL_COLUMNS.keys())
    )
    needs_role_join = any(col in _JOINED_COLUMNS for col in requested)

    stmt = select(User).where(User.workspace_id == ctx.workspace_id, ...)
    if needs_role_join:
        stmt = stmt.join(WorkspaceMembership, ...).join(WorkspaceRole, ...)

    stmt = apply_string_filter(stmt, q, string_filters, _ALL_COLUMNS)
    ...
```

Use the conditional join pattern only when the join is genuinely expensive and the joined column is an optional search target. Otherwise, always join upfront for simplicity.

---

## Router pattern

```python
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.services.context import ServiceContext


@router.get("")
async def list_users_route(
    claims: dict = Depends(require_roles([...])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    string_filters: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "string_filters": string_filters,
        },
        identity=claims,
        session=session,
    )
    ...
```

For endpoints that also expose date range filters, add them to the router signature and pass them in `query_params`:

```python
created_at_after: str | None = Query(None),
created_at_before: str | None = Query(None),
```

---

## Security rules

| Rule | Rationale |
|------|-----------|
| Validate `q` length at the router layer (`max_length=200`) | Prevents oversized inputs from reaching the DB |
| Never include `password`, hash, or secret fields in `allowed_columns` | Prevents credential leakage via search |
| SQLAlchemy parameterizes the ILIKE value | No raw string interpolation — SQL injection is not a risk |

---

## Performance notes

- `ILIKE` on unindexed `varchar` columns performs a sequential scan. Acceptable for workspace-scoped tables with moderate row counts.
- For high-volume tables, add a `pg_trgm` GIN index on the frequently searched columns to accelerate ILIKE queries.
- `apply_string_filter` applies an `OR` across all valid columns. Wider column sets → more work per row. Keep `allowed_columns` limited to the columns that are genuinely useful for search.

---

## Completion gate

A list query with `q` / `string_filters` support is **INCOMPLETE** if any of the following are true:

- [ ] `apply_string_filter` is not used — inline `.ilike` calls appear in the query body instead
- [ ] `allowed_columns` includes `password` or any credential/secret field
- [ ] `q` is not validated for length at the router layer (`max_length=200`)
- [ ] `string_filters` is parsed inline instead of being passed to `apply_string_filter`
- [ ] Date range filter params do not follow the `{field}_before` / `{field}_after` naming convention
- [ ] `q` or `string_filters` are missing from the `query_params` dict passed to `ServiceContext`
- [ ] A column from a joined table is in `allowed_columns` but the required JOIN is not in the statement before `apply_string_filter` is called
