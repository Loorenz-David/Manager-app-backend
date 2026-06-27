# PLAN_batch_update_item_positions_20260625

## Metadata

- Plan ID: `PLAN_batch_update_item_positions_20260625`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-25T00:00:00Z`
- Last updated at (UTC): `2026-06-25T20:40:12Z`
- Related issue/ticket: `—`
- Intention plan: `—`

## Goal and intent

- Goal: Add a dedicated `PATCH /api/v1/items/positions` endpoint that accepts a list of `{client_id, item_position}` pairs and updates `item_position` on all matching items in a single transaction.
- Business/user intent: Warehouse staff need to reassign the physical location of many items at once (e.g. moving a shelf-full from "A-03" to "B-07"). Using the existing single-item PATCH would require N sequential calls; this endpoint removes that friction.
- Non-goals: Does not update any field other than `item_position`. Does not create, delete, or reorder items. Does not change `item_state`.

## Scope

- In scope:
  - New request model `BatchUpdateItemPositionsRequest` (+ nested `ItemPositionEntry`) in `services/commands/items/requests/__init__.py`
  - New parse function `parse_batch_update_item_positions_request` in the same file
  - New command service `batch_update_item_positions` at `services/commands/items/batch_update_item_positions.py`
  - New route `PATCH /positions` wired into `routers/api_v1/items.py`
- Out of scope:
  - Migrations (no schema change; `item_position` already exists as `String(255) nullable`)
  - Changes to the existing `PATCH /{client_id}` route or `update_item` service
- Assumptions:
  - `item_position` is a free-form string label (e.g. `"A-03"`); no uniqueness constraint exists.
  - A partial failure (one `client_id` not found in the workspace) must abort the entire batch — no partial writes.
  - Maximum list size is capped at 200 entries (mirrors the `limit` cap used in `list_items`).
  - Roles allowed: `ADMIN`, `MANAGER` (same as the existing patch route).

## Clarifications required

_None — all unknowns are resolved by the assumptions above and the existing `update_item` pattern._

## Acceptance criteria

1. `PATCH /api/v1/items/positions` with a valid list returns `200` and `{"data": {"updated_ids": ["itm_...", ...]}}`.
2. If any `client_id` in the list does not exist (or is deleted) within the workspace, the endpoint returns `404` and no item is modified.
3. An empty `entries` list is rejected with `422`.
4. A list exceeding 200 entries is rejected with `422`.
5. A `WORKER` JWT receives `403`.
6. Each updated item gets a history record (same shape as `update_item` produces for `item_position`).
7. Each updated item fires an `item:updated` workspace event.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/06_commands.md`: command shape, `maybe_begin`, error-raising, history record pattern
- `backend/docs/architecture/09_routers.md`: handler wiring, `ServiceContext`, `run_service`, `build_ok`/`build_err`
- `backend/docs/architecture/46_serialization.md`: request model + parse-function conventions

### Local extensions loaded

_None_

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** → reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading `update_item.py` to understand `session.add / flush / error-raising` shape → `06_commands.md`
- Reading `items.py` router to understand handler wiring → `09_routers.md`
- Reading existing request models to understand output shape → `46_serialization.md`

Permitted (relational reads — understanding what exists):
- Reading `app/beyo_manager/models/tables/items/item.py` to verify `item_position` field name and type ✓ (already done — `String(255) nullable`)
- Reading `app/beyo_manager/services/commands/items/requests/__init__.py` to see where to append new models ✓ (already done)
- Reading `app/beyo_manager/routers/api_v1/items.py` to see mount point and import list ✓ (already done)

### Skill selection

- Primary skill: command-service creation + router wiring
- Router trigger terms: `batch`, `positions`, `item_position`
- Excluded alternatives: `update_item` extension — adding bulk logic to the single-item service would violate single-responsibility and complicate the transaction boundary.

## Implementation plan

### Step 1 — Add request models and parse function to `requests/__init__.py`

File: `app/beyo_manager/services/commands/items/requests/__init__.py`

Append at the bottom of the existing models block (after `FindOrCreateItemRequest`):

```python
class ItemPositionEntry(BaseModel):
    client_id: str
    item_position: str | None = None


class BatchUpdateItemPositionsRequest(BaseModel):
    entries: list[ItemPositionEntry]

    @field_validator("entries")
    @classmethod
    def entries_must_not_be_empty(cls, v: list[ItemPositionEntry]) -> list[ItemPositionEntry]:
        if not v:
            raise ValueError("entries must contain at least one item.")
        if len(v) > 200:
            raise ValueError("entries must not exceed 200 items.")
        return v
```

Append the corresponding parse function (follow the existing `parse_*` pattern exactly):

```python
def parse_batch_update_item_positions_request(data: dict) -> BatchUpdateItemPositionsRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return BatchUpdateItemPositionsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

---

### Step 2 — Create the command service

File: `app/beyo_manager/services/commands/items/batch_update_item_positions.py`

```python
"""CMD: Batch-update item_position for a list of items in one transaction."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.history.message_builder import build_update_message
from beyo_manager.services.commands.items.requests import parse_batch_update_item_positions_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def batch_update_item_positions(ctx: ServiceContext) -> dict:
    """Update item_position for each entry. All-or-nothing: raises NotFound if any client_id is missing."""
    request = parse_batch_update_item_positions_request(ctx.incoming_data)
    client_ids = [e.client_id for e in request.entries]

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.client_id.in_(client_ids),
                Item.is_deleted.is_(False),
            )
        )
        items_by_id = {item.client_id: item for item in result.scalars().all()}

        missing = [cid for cid in client_ids if cid not in items_by_id]
        if missing:
            raise NotFound(f"Items not found: {', '.join(missing)}")

        username = ctx.identity.get("username")
        now = datetime.now(timezone.utc)

        for entry in request.entries:
            item = items_by_id[entry.client_id]
            item.item_position = entry.item_position
            item.updated_at = now
            item.updated_by_id = ctx.user_id

            await _create_history_record_in_session(
                session=ctx.session,
                entity_type=HistoryRecordEntityTypeEnum.ITEM,
                entity_client_id=item.client_id,
                change_type=HistoryRecordChangeTypeEnum.UPDATED,
                description=build_update_message(username, ["item_position"], "item"),
                field_name=None,
                from_value=None,
                to_value=None,
                created_by_id=ctx.user_id,
                username_snapshot=username,
            )

    await event_bus.dispatch([
        build_workspace_event(item, "item:updated")
        for item in items_by_id.values()
    ])
    return {"updated_ids": list(items_by_id.keys())}
```

---

### Step 3 — Wire the route in `routers/api_v1/items.py`

**3a. Add the import** at the top of the imports block, alongside the other command imports:

```python
from beyo_manager.services.commands.items.batch_update_item_positions import batch_update_item_positions
```

**3b. Add the router-local body model** (after `_BatchDeleteIssuesBody`, before the first `@router` decorator):

```python
class _ItemPositionEntry(BaseModel):
    client_id: str
    item_position: str | None = None


class _BatchUpdateItemPositionsBody(BaseModel):
    entries: list[_ItemPositionEntry]
```

**3c. Add the handler** — place it immediately before `route_update_item` (the existing `PATCH /{client_id}`) so that `PATCH /positions` is registered before the path parameter route and is matched correctly by FastAPI:

```python
@router.patch("/positions")
async def route_batch_update_item_positions(
    body: _BatchUpdateItemPositionsBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"entries": [e.model_dump() for e in body.entries]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(batch_update_item_positions, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

> **Important**: `PATCH /positions` must be registered **before** `PATCH /{client_id}` in the file. FastAPI evaluates routes in declaration order; if `/{client_id}` comes first, the literal `/positions` path would be captured by the path parameter.

---

### Step 4 — Write the frontend handoff document

After all files are created and validated, write the handoff document at:
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_batch_update_item_positions_20260625.md`

Use the template at `docs/handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`.

## Risks and mitigations

- Risk: `PATCH /positions` is shadowed by `PATCH /{client_id}` if route order is wrong.
  Mitigation: Step 3c explicitly places the `/positions` handler above the `/{client_id}` handler.

- Risk: Large batches (close to 200) generate 200 history records + 200 events in one request, creating latency.
  Mitigation: The 200-entry cap (matching `list_items`) bounds the worst case. Event dispatch is async and non-blocking.

- Risk: Duplicate `client_id` entries in a single request (same item updated twice).
  Mitigation: The service iterates `request.entries` in order; if the same `client_id` appears twice, the second write wins. This is predictable and consistent with how `update_item` handles re-submission.

## Validation plan

- `pytest app/tests/items/ -k position` (or equivalent): service unit test verifying all-or-nothing behavior on missing IDs.
- Manual `curl PATCH /api/v1/items/positions` with a valid list: expect `200` + `updated_ids`.
- Manual `curl PATCH /api/v1/items/positions` with one unknown `client_id`: expect `404`.
- Manual `curl PATCH /api/v1/items/positions` with empty `entries: []`: expect `422`.

## Review log

_—_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
