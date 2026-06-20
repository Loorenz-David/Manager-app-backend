# PLAN_pin_notification_batch_20260620

## Metadata

- Plan ID: `PLAN_pin_notification_batch_20260620`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Last updated at (UTC): `2026-06-20T13:06:16Z`
- Related issue/ticket: _none_
- Intention plan: _none_

## Goal and intent

- Goal: Extend the `NotificationPin` model with `major_entity_type` + `major_client_entity_id` ownership columns, replace the single-item pin/unpin endpoints with batch versions, add a new batch edit endpoint for updating conditions and `fire_once`, and add a `GET /pins` query endpoint.
- Business/user intent: A frontend action (e.g., opening a task) creates several pins at once — one per task step, one per item upholstery, one for the task itself. Sending them as a batch in a single request is more efficient than N serial requests. Storing the controlling entity on each pin makes cleanup trivial (one DELETE by major entity instead of collecting entity IDs via joins). Client-side optimistic IDs let the frontend reference new pins immediately before the round-trip completes.
- Non-goals: No changes to pin condition evaluation or `fire_once` firing logic. No changes to `resolve_pinned_subscribers`. No new entity types or condition types. Frontend implementation is out of scope.

## Scope

- In scope:
  - Add `major_entity_type` (String 64, nullable) and `major_client_entity_id` (String 128, nullable) columns to `NotificationPin` with a composite index.
  - Add reversible Alembic migration.
  - Replace `POST /pins` with a batch create/upsert endpoint that accepts a list of pin items, each carrying a caller-supplied `client_id`.
  - Replace `DELETE /pins` with a batch delete endpoint where each list item targets either by pin `client_id` or by `(major_entity_type, major_client_entity_id)`.
  - Add `PATCH /pins` endpoint for batch-editing `conditions` and `fire_once` on existing pins.
  - Update request parsers in `requests.py`.
  - Remove the stale `PinBody` model from the router (the simple one with only `entity_type` + `entity_client_id`).
  - Add `GET /pins` query endpoint filtered by `entity_client_ids` or `major_client_entity_ids` (comma-separated query params).
  - Add `domain/notifications/serializers.py` with `serialize_pin_full`.
  - Add `services/queries/notifications/list_pins.py`.
  - Note: the `pin_cleanup.py` helper planned in `PLAN_pin_notification_conditions_corrections_20260620` (Step 6) must be implemented using the `major_client_entity_id` column (see Step 8 below), superseding the multi-join approach described in that plan.

- Out of scope:
  - Condition evaluation or `fire_once` firing logic changes.
  - `resolve_pinned_subscribers` changes.
  - Frontend UI.
  - Any auth or role changes.

- Assumptions:
  - `major_entity_type` and `major_client_entity_id` are always provided together or both omitted. One without the other is a validation error.
  - A caller-supplied `client_id` must begin with the `npin_` prefix. Length must be ≤ 64 characters.
  - Batch create is upsert: if a pin already exists for `(user_id, entity_type, entity_client_id)`, its `conditions`, `fire_once`, `major_entity_type`, and `major_client_entity_id` are overwritten (last-write-wins). The existing `client_id` (PK) is preserved.
  - Batch edit silently skips items whose `client_id` is not found or does not belong to the requesting user (no error, idempotent).
  - Batch delete is also idempotent — no error if a targeted pin does not exist.

## Clarifications required

_None — all design decisions confirmed during the planning conversation._

## Acceptance criteria

1. `NotificationPin` model has `major_entity_type` and `major_client_entity_id` columns, both nullable, with a composite index.
2. Alembic migration applies and reverts cleanly.
3. `POST /pins` accepts a JSON array. Each item carries `client_id`, `entity_type`, `entity_client_id`, optional `major_entity_type` + `major_client_entity_id` (co-required), optional `conditions`, optional `fire_once`. Response is a list of `{client_id}` for each created or updated pin.
4. `DELETE /pins` accepts a JSON array. Each item targets either by `client_id` (pin PK) or by `major_entity_type` + `major_client_entity_id`. The delete is scoped to the requesting user. Response is `{}`.
5. `PATCH /pins` accepts a JSON array of `{client_id, conditions, fire_once}`. Updates only pins belonging to the requesting user. Response is `{}`.
6. `GET /pins` accepts one of `entity_client_ids` or `major_client_entity_ids` as a comma-separated query param (exactly one required). Returns `{"pins": [...]}` where each item is serialized via `serialize_pin_full` and includes a nested `user` object.
7. All write endpoints use `maybe_begin` for transaction boundaries.
8. `py_compile` passes on all new and changed modules.
9. Existing `test_pin_conditions.py` and `test_transition_step_state.py` continue to pass.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md`: model columns use `mapped_column`; no business logic in models.
- `backend/architecture/06_commands.md`: all writes inside `maybe_begin`; no `session.commit()` inside command body.
- `backend/architecture/09_routers.md`: router defines body model, calls `_run(command, body.model_dump(), ...)`.
- `backend/architecture/30_migrations.md`: reversible Alembic migration per schema change.
- `backend/architecture/46_serialization.md`: serializers live in `domain/<domain>/serializers.py`; named `serialize_<resource>_<view>`; services may call domain serializers.
- `backend/architecture/47_notifications_local.md`: pin identity is `(user_id, entity_type, entity_client_id)`; last-write-wins re-pin.

### Local extensions loaded

- `backend/architecture/47_notifications_local.md`: conditions JSONB, fire_once bool.

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- `notification_pin.py` — exact column names and types before adding columns.
- `notifications.py` (router) — current route paths and body models before replacement.
- `pin_notification.py` — current upsert logic before rewrite.
- `unpin_notification.py` — current delete logic before rewrite.
- `requests.py` — current parser shapes before extension.
- `maybe_begin` — transaction utility signature (already read, confirmed).
- `domain/users/serializers.py` — `serialize_user_working_section_member` signature and return shape.
- `services/queries/notifications/list_notifications.py` — existing query service structure for reference.

Prohibited (pattern reads — contract already covers these):
- Reading another command to understand `session.add` / `flush` / error-raising shape → `06_commands.md`.
- Reading another router to understand handler wiring → `09_routers.md`.

### Skill selection

- Primary skill: _no specialized skill required_
- Router trigger terms: `pin_notification`, `unpin_notification`, `batch`, `major_entity`
- Excluded alternatives: _none_

## Implementation plan

### Step 1 — Add model columns and composite index

**File:** `backend/app/beyo_manager/models/tables/notifications/notification_pin.py`

Add two nullable columns after `fire_once`:

```python
major_entity_type:      Mapped[str | None] = mapped_column(String(64),  nullable=True, index=False)
major_client_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=False)
```

Add a composite index to `__table_args__` alongside the existing `UniqueConstraint`:

```python
Index(
    "ix_notification_pins_major_entity",
    "major_entity_type",
    "major_client_entity_id",
),
```

Add the `Index` import from `sqlalchemy`.

---

### Step 2 — Alembic migration

**New file:** `backend/app/migrations/versions/<revision>_add_notification_pin_major_entity.py`

The migration must:

`upgrade`:
```sql
ALTER TABLE notification_pins ADD COLUMN major_entity_type VARCHAR(64);
ALTER TABLE notification_pins ADD COLUMN major_client_entity_id VARCHAR(128);
CREATE INDEX ix_notification_pins_major_entity
    ON notification_pins (major_entity_type, major_client_entity_id);
```

`downgrade`:
```sql
DROP INDEX ix_notification_pins_major_entity;
ALTER TABLE notification_pins DROP COLUMN major_client_entity_id;
ALTER TABLE notification_pins DROP COLUMN major_entity_type;
```

---

### Step 3 — Update `requests.py` with all three batch request shapes

**File:** `backend/app/beyo_manager/services/commands/notifications/requests.py`

Replace the existing `PinNotificationRequest` and `parse_pin_notification_request` with the following. Keep the existing `PinNotificationRequest` **only** if it is referenced elsewhere; otherwise remove it.

#### Batch create item

```python
class PinNotificationItem(BaseModel):
    client_id:              str
    entity_type:            str
    entity_client_id:       str
    major_entity_type:      str | None = None
    major_client_entity_id: str | None = None
    conditions:             list[dict[str, object]] | None = None
    fire_once:              bool = False

    @field_validator("client_id")
    @classmethod
    def client_id_must_have_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("npin_") or len(value) > 64:
            raise ValueError("client_id must begin with 'npin_' and be ≤ 64 characters.")
        return value

    @field_validator("entity_type", "entity_client_id")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank.")
        return value

    @model_validator(mode="after")
    def major_entity_fields_co_required(self) -> "PinNotificationItem":
        has_type = self.major_entity_type is not None
        has_id   = self.major_client_entity_id is not None
        if has_type != has_id:
            raise ValueError(
                "major_entity_type and major_client_entity_id must both be provided or both omitted."
            )
        return self
```

Add parser:
```python
def parse_pin_notification_batch_request(data: list) -> list[PinNotificationItem]:
    items = []
    for i, raw in enumerate(data):
        try:
            items.append(PinNotificationItem.model_validate(raw))
        except PydanticValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(loc) for loc in first_error["loc"])
            raise ValidationError(f"items[{i}].{field}: {first_error['msg']}") from exc
    return items
```

#### Batch delete item

```python
class UnpinItem(BaseModel):
    client_id:              str | None = None
    major_entity_type:      str | None = None
    major_client_entity_id: str | None = None

    @model_validator(mode="after")
    def exactly_one_targeting_mode(self) -> "UnpinItem":
        by_client_id    = self.client_id is not None
        by_major_entity = (
            self.major_entity_type is not None
            and self.major_client_entity_id is not None
        )
        if by_client_id == by_major_entity:
            raise ValueError(
                "Provide either client_id OR both major_entity_type + major_client_entity_id, not both or neither."
            )
        return self
```

Add parser:
```python
def parse_unpin_batch_request(data: list) -> list[UnpinItem]:
    items = []
    for i, raw in enumerate(data):
        try:
            items.append(UnpinItem.model_validate(raw))
        except PydanticValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(loc) for loc in first_error["loc"])
            raise ValidationError(f"items[{i}].{field}: {first_error['msg']}") from exc
    return items
```

#### Batch edit item

```python
class EditPinItem(BaseModel):
    client_id:  str
    conditions: list[dict[str, object]] | None = None
    fire_once:  bool = False

    @field_validator("client_id")
    @classmethod
    def client_id_must_have_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("npin_"):
            raise ValueError("client_id must begin with 'npin_'.")
        return value
```

Add parser:
```python
def parse_edit_pin_batch_request(data: list) -> list[EditPinItem]:
    items = []
    for i, raw in enumerate(data):
        try:
            items.append(EditPinItem.model_validate(raw))
        except PydanticValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(loc) for loc in first_error["loc"])
            raise ValidationError(f"items[{i}].{field}: {first_error['msg']}") from exc
    return items
```

Required imports to add: `model_validator` from `pydantic`.

---

### Step 4 — Rewrite `pin_notification.py` (batch create / upsert)

**File:** `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`

Full rewrite. Logic:

1. Parse `ctx.incoming_data["items"]` via `parse_pin_notification_batch_request`.
2. Validate each item's `entity_type` against `EntityType` enum — raise `ValidationError` for unknown values.
3. Validate each item's `conditions` via `validate_pin_conditions(entity_type.value, item.conditions)`.
4. Steps 2–3 happen **before** any DB call (fast-fail without touching the session).
5. Inside `maybe_begin`:
   a. Build a set of `(entity_type, entity_client_id)` pairs from all items.
   b. Select existing pins for `user_id = ctx.user_id` AND `(entity_type, entity_client_id) IN (...)` using a tuple comparison:
      ```python
      select(NotificationPin).where(
          NotificationPin.user_id == ctx.user_id,
          tuple_(NotificationPin.entity_type, NotificationPin.entity_client_id).in_(pairs),
      )
      ```
   c. Build a `dict` keyed by `(entity_type, entity_client_id)` → existing `NotificationPin`.
   d. For each item:
      - If existing pin found: update `conditions`, `fire_once`, `major_entity_type`, `major_client_entity_id` on the ORM object.
      - If no existing pin: create `NotificationPin(client_id=item.client_id, user_id=ctx.user_id, ...)` and call `ctx.session.add(pin)`.
   e. `await ctx.session.flush()` to ensure PKs are available.
6. Return `{"pins": [{"client_id": pin_client_id} for each item in order]}`.
   - For re-pins, return the existing pin's client_id (not the caller-supplied one, since the PK was already set).
   - Track this by mapping item → resolved_client_id during step 5d.

Imports needed: `tuple_` from `sqlalchemy`, `maybe_begin`, `parse_pin_notification_batch_request`, `validate_pin_conditions`, `EntityType`, `ValidationError`, `NotificationPin`.

---

### Step 5 — Rewrite `unpin_notification.py` (batch delete)

**File:** `backend/app/beyo_manager/services/commands/notifications/unpin_notification.py`

Full rewrite. Logic:

1. Parse `ctx.incoming_data["items"]` via `parse_unpin_batch_request`.
2. Partition items into two lists:
   - `by_client_ids`: items where `client_id` is set.
   - `by_major_entities`: items where `major_entity_type` + `major_client_entity_id` are set.
3. Inside `maybe_begin`:
   a. If `by_client_ids`:
      ```python
      await session.execute(
          delete(NotificationPin).where(
              NotificationPin.user_id.in_([ctx.user_id]),  # scoped to requesting user
              NotificationPin.client_id.in_([item.client_id for item in by_client_ids]),
          )
      )
      ```
      Actually scope with `NotificationPin.user_id == ctx.user_id` (single value):
      ```python
      await session.execute(
          delete(NotificationPin).where(
              NotificationPin.user_id == ctx.user_id,
              NotificationPin.client_id.in_([item.client_id for item in by_client_ids]),
          )
      )
      ```
   b. If `by_major_entities`, group by `major_entity_type` to minimise queries. For each unique `major_entity_type`:
      ```python
      await session.execute(
          delete(NotificationPin).where(
              NotificationPin.user_id == ctx.user_id,
              NotificationPin.major_entity_type == major_entity_type,
              NotificationPin.major_client_entity_id.in_(
                  [item.major_client_entity_id for item in group]
              ),
          )
      )
      ```
4. Return `{}`.

Imports needed: `delete` from `sqlalchemy`, `maybe_begin`, `parse_unpin_batch_request`, `NotificationPin`.

---

### Step 6 — Create `edit_pin_notification.py` (batch edit)

**New file:** `backend/app/beyo_manager/services/commands/notifications/edit_pin_notification.py`

Logic:

1. Parse `ctx.incoming_data["items"]` via `parse_edit_pin_batch_request`.
2. Collect all `client_id`s.
3. Inside `maybe_begin`:
   a. Fetch all matching pins in one query:
      ```python
      select(NotificationPin).where(
          NotificationPin.user_id == ctx.user_id,
          NotificationPin.client_id.in_(client_ids),
      )
      ```
   b. Build a `dict` keyed by `client_id` → `NotificationPin`.
   c. For each edit item:
      - If pin not found in the dict: skip (idempotent — pin may already be deleted).
      - Validate `item.conditions` against `pin.entity_type` via `validate_pin_conditions(pin.entity_type, item.conditions)` — raise `ValidationError` on first invalid item.
      - Set `pin.conditions = item.conditions` and `pin.fire_once = item.fire_once`.
4. Return `{}`.

Imports needed: `select` from `sqlalchemy`, `maybe_begin`, `parse_edit_pin_batch_request`, `validate_pin_conditions`, `ValidationError`, `NotificationPin`.

---

### Step 7 — Update router

**File:** `backend/app/beyo_manager/routers/api_v1/notifications.py`

Changes:

1. Remove the old `PinBody` class.
2. Add inline body models for the three pin endpoints:

```python
class PinCreateItem(BaseModel):
    client_id:              str
    entity_type:            str
    entity_client_id:       str
    major_entity_type:      str | None = None
    major_client_entity_id: str | None = None
    conditions:             list[dict] | None = None
    fire_once:              bool = False


class UnpinItem(BaseModel):
    client_id:              str | None = None
    major_entity_type:      str | None = None
    major_client_entity_id: str | None = None


class EditPinItem(BaseModel):
    client_id:  str
    conditions: list[dict] | None = None
    fire_once:  bool = False
```

3. Replace the `POST /pins` route:

```python
@router.post("/pins")
async def pin_route(
    body: list[PinCreateItem],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        pin_notification,
        {"items": [item.model_dump() for item in body]},
        claims,
        session,
    )
```

4. Replace the `DELETE /pins` route:

```python
@router.delete("/pins")
async def unpin_route(
    body: list[UnpinItem],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        unpin_notification,
        {"items": [item.model_dump() for item in body]},
        claims,
        session,
    )
```

5. Add `PATCH /pins` route:

```python
@router.patch("/pins")
async def edit_pin_route(
    body: list[EditPinItem],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        edit_pin_notification,
        {"items": [item.model_dump() for item in body]},
        claims,
        session,
    )
```

6. Add import for `edit_pin_notification`.

---

### Step 8 — Note on `pin_cleanup.py` (supersedes corrections plan Step 6)

`PLAN_pin_notification_conditions_corrections_20260620` Step 6 describes `cleanup_task_pins` using a multi-join approach to collect entity IDs. **This approach is superseded.** Once `major_client_entity_id` is stored on every pin at creation time, the entire task-graph cleanup collapses to a single query:

```python
async def cleanup_task_pins(session: AsyncSession, task_client_id: str) -> None:
    await session.execute(
        delete(NotificationPin).where(
            NotificationPin.major_entity_type      == EntityType.TASK.value,
            NotificationPin.major_client_entity_id == task_client_id,
        )
    )
```

This must be implemented **after** this plan is complete and the migration is applied. Codex should implement the corrections plan's Step 6 using this approach, not the multi-join approach.

Step 7 of the corrections plan (wiring into `delete_task.py`) remains unchanged.

---

### Step 9 — Add `GET /pins` query endpoint

#### 9a — Serializer: `domain/notifications/serializers.py`

**New file:** `backend/app/beyo_manager/domain/notifications/serializers.py`

```python
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.users.user import User


def serialize_pin_full(pin: NotificationPin, user: User) -> dict:
    return {
        "client_id":              pin.client_id,
        "entity_type":            pin.entity_type,
        "entity_client_id":       pin.entity_client_id,
        "major_entity_type":      pin.major_entity_type,
        "major_client_entity_id": pin.major_client_entity_id,
        "conditions":             pin.conditions,
        "fire_once":              pin.fire_once,
        "pinned_at":              pin.pinned_at.isoformat(),
        "user":                   serialize_user_working_section_member(user),
    }
```

#### 9b — Query service: `services/queries/notifications/list_pins.py`

**New file:** `backend/app/beyo_manager/services/queries/notifications/list_pins.py`

Logic:

1. Read `entity_client_ids: list[str] | None` and `major_client_entity_ids: list[str] | None` from `ctx.incoming_data`.
2. Build a base query joining `NotificationPin` → `User` and filtering to `ctx.user_id`.
3. Apply exactly one filter branch:
   - If `entity_client_ids`: `WHERE entity_client_id IN (...)`.
   - If `major_client_entity_ids`: `WHERE major_client_entity_id IN (...)`.
4. Execute, unpack `(NotificationPin, User)` tuples, serialize each with `serialize_pin_full`.
5. Return `{"pins": [...]}`.

```python
from sqlalchemy import select

from beyo_manager.domain.notifications.serializers import serialize_pin_full
from beyo_manager.models.tables.notifications.notification_pin import NotificationPin
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext


async def list_pins(ctx: ServiceContext) -> dict:
    entity_client_ids        = ctx.incoming_data.get("entity_client_ids")
    major_client_entity_ids  = ctx.incoming_data.get("major_client_entity_ids")

    stmt = (
        select(NotificationPin, User)
        .join(User, NotificationPin.user_id == User.client_id)
        .where(NotificationPin.user_id == ctx.user_id)
    )

    if entity_client_ids:
        stmt = stmt.where(NotificationPin.entity_client_id.in_(entity_client_ids))
    else:
        stmt = stmt.where(NotificationPin.major_client_entity_id.in_(major_client_entity_ids))

    rows = (await ctx.session.execute(stmt)).all()
    return {"pins": [serialize_pin_full(pin, user) for pin, user in rows]}
```

Note: no `maybe_begin` — read-only queries run in the session's ambient transaction or autobegin mode. No explicit transaction management needed.

#### 9c — Router: add `GET /pins`

**File:** `backend/app/beyo_manager/routers/api_v1/notifications.py`

Add import for `list_pins`. Add route after the existing pin routes:

```python
@router.get("/pins")
async def list_pins_route(
    entity_client_ids:       str | None = None,
    major_client_entity_ids: str | None = None,
    claims:  dict         = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    has_entity  = bool(entity_client_ids)
    has_major   = bool(major_client_entity_ids)
    if has_entity == has_major:  # both provided or neither provided
        return build_err("Provide exactly one of entity_client_ids or major_client_entity_ids.")
    return await _run(
        list_pins,
        {
            "entity_client_ids":       entity_client_ids.split(",")       if entity_client_ids       else None,
            "major_client_entity_ids": major_client_entity_ids.split(",") if major_client_entity_ids else None,
        },
        claims,
        session,
    )
```

The comma-split and param validation happen entirely in the router before the service is called. The service receives clean `list[str] | None` values.

---

### Step 10 — Write frontend handoff document

After all implementation steps are verified and `py_compile` / migration / tests pass, create the handoff document at:

```
backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pin_notification_batch_20260620.md
```

Use the template at `backend/docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`.

The document must cover all four pin endpoints as distinct sections inside **Interface details**. For each endpoint, document:

- HTTP method + path
- Auth: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`
- Request shape (body or query params, with field types and constraints)
- Response shape (exact JSON structure with field types)
- Error cases (validation errors, targeting conflicts)

Endpoints to document:

| Method | Path | Service |
|--------|------|---------|
| `POST` | `/api/v1/notifications/pins` | `pin_notification` — batch create / upsert |
| `DELETE` | `/api/v1/notifications/pins` | `unpin_notification` — batch delete by pin id or major entity |
| `PATCH` | `/api/v1/notifications/pins` | `edit_pin_notification` — batch edit conditions + fire_once |
| `GET` | `/api/v1/notifications/pins` | `list_pins` — fetch pins by entity ids or major entity ids |

The document must include a **Reference: Entity types and state enums** section with the following content exactly as specified. Codex must not abbreviate or skip any values.

#### Entity types (`entity_type` / `major_entity_type`)

All values are from `EntityType(StrEnum)` in `domain/presence/enums.py`:

| `entity_type` value | Supports state condition | `major_entity_type` for cleanup |
|---------------------|-------------------------|----------------------------------|
| `task`              | yes                     | `task` (self)                    |
| `task_step`         | yes                     | `task`                           |
| `item_upholstery`   | yes                     | `task`                           |
| `case`              | no                      | `task`                           |
| `case_list`         | no                      | —                                |
| `conversation`      | no                      | —                                |
| `conversation_list` | no                      | —                                |

The only supported value for `major_entity_type` in the current task-driven design is `"task"`. The `major_client_entity_id` is the `client_id` of the controlling task.

#### State enum values per entity type

These are the only legal values for a `state` condition on each entity type.

**`task`**

| Value | Meaning |
|-------|---------|
| `pending` | Task created, not yet assigned |
| `assigned` | Task assigned to a worker |
| `working` | Task actively in progress |
| `stalled` | Task blocked or on hold |
| `ready` | Task ready for next action |
| `resolved` | Task successfully completed |
| `failed` | Task ended in failure |
| `cancelled` | Task cancelled |

**`task_step`**

| Value | Meaning |
|-------|---------|
| `pending` | Step not yet started |
| `working` | Step actively in progress |
| `paused` | Step paused mid-execution |
| `ended_shift` | Worker ended their shift mid-step |
| `blocked` | Step blocked by a dependency |
| `completed` | Step successfully completed |
| `skipped` | Step skipped intentionally |
| `failed` | Step ended in failure |
| `cancelled` | Step cancelled |

**`item_upholstery`**

| Value | Meaning |
|-------|---------|
| `missing_quantity` | Required quantity not yet available |
| `available` | Stock confirmed available |
| `needs_ordering` | Must be ordered externally |
| `ordered` | Purchase order placed |
| `in_use` | Currently being consumed in the task |
| `completed` | Requirement fulfilled |
| `failed` | Requirement could not be fulfilled |

#### Condition schema reference

```json
{
  "type": "state",
  "op": "eq" | "in" | "not_in",
  "value": "<string>"  // for "eq"
             | ["<string>", ...]  // for "in" and "not_in"
}
```

A pin with no conditions (`null` or `[]`) fires on every event for that entity.
Multiple conditions in the array are evaluated with AND semantics.

The **Frontend action required** section must list:
1. Replace any single-item pin/unpin calls with the batch list endpoints.
2. Generate and inject `client_id` values client-side using the `npin_` prefix before calling `POST /pins`.
3. Store `major_entity_type` + `major_client_entity_id` on each pin creation request to enable efficient batch delete and list queries later.
4. Use `PATCH /pins` to update conditions or `fire_once` on existing pins by their `client_id`.
5. Use `GET /pins?major_client_entity_ids=<id>` to hydrate pin state when opening a task view.

---

## Risks and mitigations

- Risk: Batch create contains duplicate `(entity_type, entity_client_id)` pairs within the same request (frontend bug). The SELECT-then-upsert loop would try to INSERT two rows with the same unique key, causing a DB constraint violation.
  Mitigation: Before the `maybe_begin` block, deduplicate items by `(entity_type, entity_client_id)` and raise `ValidationError` if duplicates are found.

- Risk: Caller-supplied `client_id` collides with an existing PK for a different user/entity row.
  Mitigation: The `client_id` PK constraint will raise a DB integrity error. This surfaces to the caller as a 500. The risk is extremely low given ULID entropy. No special handling required.

- Risk: Empty list body sent to any batch endpoint. 
  Mitigation: All three commands return immediately with the appropriate empty response (`{"pins": []}` / `{}`) when the parsed list is empty. No DB call is made.

- Risk: `edit_pin_notification` validates conditions against `entity_type` fetched from the DB, but the edit skips missing pins. If all pins are missing, no validation runs and the response is `{}` — silently accepted.
  Mitigation: Acceptable. The caller is responsible for sending valid `client_id`s. Idempotency is the intended behavior.

- Risk: `GET /pins` with a very large comma-separated list (e.g., hundreds of IDs) generates a large SQL `IN` clause.
  Mitigation: Acceptable for current scale. A pin list per task graph is bounded by the number of steps and items on a task — typically under 50 IDs. No pagination required at this stage.

## Validation plan

- `py_compile` on all changed and new modules:
  - `backend/app/beyo_manager/models/tables/notifications/notification_pin.py`
  - `backend/app/beyo_manager/services/commands/notifications/requests.py`
  - `backend/app/beyo_manager/services/commands/notifications/pin_notification.py`
  - `backend/app/beyo_manager/services/commands/notifications/unpin_notification.py`
  - `backend/app/beyo_manager/services/commands/notifications/edit_pin_notification.py`
  - `backend/app/beyo_manager/domain/notifications/serializers.py`
  - `backend/app/beyo_manager/services/queries/notifications/list_pins.py`
  - `backend/app/beyo_manager/routers/api_v1/notifications.py`
  - `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_pin_notification_batch_20260620.md`
- `.venv/bin/alembic heads`: single head.
- `.venv/bin/alembic upgrade head`: applies cleanly.
- `.venv/bin/alembic downgrade -1`: reverts cleanly.
- `.venv/bin/alembic upgrade head`: restores DB.
- `pytest tests/unit/domain/notifications/test_pin_conditions.py`: 7 tests pass.
- `pytest tests/unit/services/commands/task_steps/test_transition_step_state.py`: passes.
- `rg -n "ctx.session.begin()" backend/app/beyo_manager/services/commands/notifications/`: zero results.

## Review log

- `2026-06-20` `claude-sonnet-4-6`: Initial plan authored.
- `2026-06-20` `claude-sonnet-4-6`: Added Step 9 — `GET /pins` query endpoint with domain serializer.
- `2026-06-20` `claude-sonnet-4-6`: Added Step 10 — frontend handoff document to be authored by Codex after implementation is verified.

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_batch_20260620.md`
- Archive record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_batch_20260620.md`
