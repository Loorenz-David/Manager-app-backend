# PLAN_list_task_steps_corrections_20260620

## Metadata

- Plan ID: `PLAN_list_task_steps_corrections_20260620`
- Status: `under_construction`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Last updated at (UTC): `2026-06-20T00:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `—`
- Source review: post-implementation review of `SUMMARY_PLAN_list_task_steps_by_task_20260620`

## Goal and intent

- Goal: Apply the three targeted corrections identified in the post-implementation review of `list_task_steps`. No new behavior, no new files, no scope expansion.
- Business/user intent: Ensure the endpoint is consistent with every other list route in the file, that the serializer makes only true claims about nullability, and that the frontend handoff document accurately describes when fields can be `null`.
- Non-goals: Any change to query logic, pagination behavior, serializer fields, roles, or route path.

## Scope

- In scope:
  - `routers/api_v1/tasks.py` — add `ge=1` to the `limit` Query param on `route_list_task_steps`
  - `domain/task_steps/serializers.py` — remove the null guard on `created_at`
  - `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md` — update the two nullability notes in the field reference table
- Out of scope:
  - Query logic (`list_task_steps.py`) — no changes needed
  - Route path, roles, response shape, pagination behavior — all correct as-is
  - Any other router, serializer, or service file

## Clarifications required

_(none — all three corrections are fully specified below)_

## Acceptance criteria

1. `GET /tasks/{task_id}/steps?limit=0` returns `422 Unprocessable Entity` (FastAPI validation rejects it before the handler runs).
2. `GET /tasks/{task_id}/steps?limit=1` continues to work correctly.
3. `serialize_task_step_compact` no longer has a conditional branch on `step.created_at`; `closed_at` retains its guard.
4. The handoff field table for `working_section_name` mentions soft-deleted sections as a null source.
5. The handoff field table for `working_section_image` mentions soft-deleted sections as a null source alongside the "no image set" case.
6. No other lines in any of the three files are changed.

## Contracts and skills

### Contracts loaded

- `backend/architecture/07_queries_local.md`: completion gate — `limit: int = Query(50, le=200)` — local contract does not prescribe `ge=1` but existing routes in the same file uniformly use it; consistency is required
- `backend/architecture/09_routers.md`: router query param declaration pattern
- `backend/architecture/46_serialization.md` (if present) / `08_domain.md`: serializer must not assert nullability that the model does not support

### File read intent — pattern vs. relational

Permitted reads before making changes:
- `routers/api_v1/tasks.py` — to locate the exact line of the `limit` param in `route_list_task_steps` (relational: what exists)
- `domain/task_steps/serializers.py` — to locate the exact `created_at` line (relational: what exists)
- `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md` — to locate the two field table rows (relational: what exists)

Prohibited:
- Reading any other router to understand how to declare a Query param → `09_routers.md` covers it
- Reading any other serializer to understand isoformat usage → `07_queries.md` covers it

## Implementation plan

### Correction 1 — Add `ge=1` to `limit` in `routers/api_v1/tasks.py`

**Location:** the `route_list_task_steps` handler, `limit` Query param declaration.

Find:
```python
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
```

Replace with:
```python
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
```

Only this one line changes. Do not touch any other param or handler.

---

### Correction 2 — Remove null guard on `created_at` in `domain/task_steps/serializers.py`

**Location:** `serialize_task_step_compact`, the `created_at` key.

Find:
```python
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "closed_at": step.closed_at.isoformat() if step.closed_at else None,
```

Replace with:
```python
        "created_at": step.created_at.isoformat(),
        "closed_at": step.closed_at.isoformat() if step.closed_at else None,
```

`closed_at` is `Mapped[datetime | None]` in the model — its guard is correct and must remain. `created_at` is `Mapped[datetime]` non-nullable — the guard is removed.

---

### Correction 3 — Update nullability notes in the handoff doc

**Location:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_list_task_steps_by_task_20260620.md`, field reference table, rows for `working_section_name` and `working_section_image`.

Find:
```markdown
| `working_section_name` | `string` | Yes | Display name of the working section; `null` only on data integrity issue |
| `working_section_image` | `string` (URL) | Yes | Image URL for the working section; `null` if none set |
```

Replace with:
```markdown
| `working_section_name` | `string` | Yes | Display name of the working section; `null` when the section is soft-deleted or (rarely) on data integrity issue |
| `working_section_image` | `string` (URL) | Yes | Image URL for the working section; `null` if no image is set, or if the section is soft-deleted |
```

No other lines in the document change.

---

## Risks and mitigations

- Risk: Changing `Query(50, le=200)` to `Query(50, ge=1, le=200)` is a breaking change for any client currently passing `limit=0`.
  Mitigation: `limit=0` was never a valid documented value — the handoff doc specifies default `50`, max `200`. No client should rely on `limit=0` returning results. The change makes FastAPI reject it explicitly rather than silently returning a misleading response.

- Risk: Removing the `created_at` null guard causes a crash if a row somehow has `NULL` in a non-nullable column.
  Mitigation: The column is `nullable=False` in the model and has a server-side default. A `NULL` value would indicate a broken DB row that should surface as an error, not be silently swallowed. Removing the guard is the correct behavior per contract (`07_queries.md`: "Serializers use isoformat() for all datetime fields").

## Validation plan

- `GET /tasks/{valid_task_id}/steps?limit=0` → expect `422` (FastAPI rejects before handler).
- `GET /tasks/{valid_task_id}/steps?limit=1` → expect `200` with `steps_pagination.items` of length ≤ 1.
- `python3 -m compileall` on all three changed files: passes.
- `ruff check` on `serializers.py` and `tasks.py` router: no new errors.

## Review log

_(none yet)_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
