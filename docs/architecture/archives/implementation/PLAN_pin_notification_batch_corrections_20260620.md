# PLAN_pin_notification_batch_corrections_20260620

## Metadata

- Plan ID: `PLAN_pin_notification_batch_corrections_20260620`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-20T00:00:00Z`
- Last updated at (UTC): `2026-06-20T13:24:23Z`
- Related issue/ticket: post-implementation review of `SUMMARY_PLAN_pin_notification_batch_20260620`
- Intention plan: _none_

## Goal and intent

- Goal: Apply four corrections identified in the post-implementation review of `PLAN_pin_notification_batch_20260620`: a broken `build_err` call, a None-crash in `list_pins`, a misleading validation error message in `UnpinItem`, and missing unit tests for the batch endpoints.
- Business/user intent: The batch pin endpoints are functionally correct for the happy path but carry two bugs that can surface under real usage and one message that will confuse frontend developers during integration. The test gap means regressions will not be caught automatically.
- Non-goals: No schema changes. No new features. No changes to condition evaluation, fire_once logic, or cleanup helpers.

## Scope

- In scope:
  - Fix `build_err(ValidationError(...))` → `build_err("...")` in `list_pins_route` and remove the now-unused `ValidationError` import from the router.
  - Fix `list_pins` else-branch to guard against `major_client_entity_ids` being `None`.
  - Rewrite `UnpinItem.exactly_one_targeting_mode` with three explicit, distinct error messages.
  - Add unit tests for `pin_notification`, `unpin_notification`, `edit_pin_notification`, and `list_pins`.

- Out of scope:
  - Any change to the request/response shape.
  - Any migration or schema change.
  - Any change to the handoff document.

- Assumptions:
  - The existing test files live under `backend/app/tests/unit/`.
  - The test for `pin_notification` can use an in-memory SQLite session or the existing async session fixture already used by `test_transition_step_state.py`.

## Clarifications required

_None._

## Acceptance criteria

1. `list_pins_route` calls `build_err` with a plain string, not a `ValidationError` instance.
2. `from beyo_manager.errors.validation import ValidationError` is removed from `notifications.py`.
3. `list_pins` returns `{"pins": []}` when both incoming params are `None` instead of crashing with a SQLAlchemy error.
4. `UnpinItem.exactly_one_targeting_mode` raises three distinct, clearly worded `ValueError`s: one for a partial major pair, one for both targeting modes provided, one for neither provided.
5. New unit tests cover the following cases and all pass:
   - `pin_notification`: new pin created, re-pin overwrites fields, duplicate pair in one batch raises `ValidationError`.
   - `unpin_notification`: delete by `client_id`, delete by `major_entity`, empty list is no-op.
   - `edit_pin_notification`: updates conditions and `fire_once`, missing pin is skipped, invalid condition raises `ValidationError`.
   - `list_pins`: filters by `entity_client_ids`, filters by `major_client_entity_ids`, both None returns empty list.
6. `py_compile` passes on all changed files.
7. All pre-existing tests continue to pass.

## Contracts and skills

### Contracts loaded

- `backend/architecture/09_routers.md`: router error responses use `build_err` with string messages; error handling flows through `run_service`.
- `backend/architecture/06_commands.md`: commands use `maybe_begin`; no direct session management in routers.

### Local extensions loaded

- _none_

### File read intent — pattern vs. relational

Permitted (relational reads — understanding what exists):
- `routers/api_v1/notifications.py` — confirm exact line of the broken `build_err` call before editing.
- `services/queries/notifications/list_pins.py` — confirm the else-branch before editing.
- `services/commands/notifications/requests.py` — confirm `UnpinItem` validator before rewriting.
- `tests/unit/domain/notifications/test_pin_conditions.py` — confirm fixture and import pattern before adding new test files.

Prohibited (pattern reads):
- Reading another command to understand `session.add` / flush shape → `06_commands.md`.
- Reading another router to understand handler wiring → `09_routers.md`.

### Skill selection

- Primary skill: _no specialized skill required_
- Router trigger terms: `build_err`, `list_pins`, `UnpinItem`, `batch`, `pin`
- Excluded alternatives: _none_

## Implementation plan

### Step 1 — Fix `build_err` call in `list_pins_route`

**File:** `backend/app/beyo_manager/routers/api_v1/notifications.py`

**Change A** — replace the broken `build_err` call:

```python
# Before
return build_err(ValidationError("Provide exactly one of entity_client_ids or major_client_entity_ids."))

# After
return build_err("Provide exactly one of entity_client_ids or major_client_entity_ids.")
```

**Change B** — remove the now-unused import:

```python
# Remove this line entirely
from beyo_manager.errors.validation import ValidationError
```

---

### Step 2 — Guard `list_pins` against None IN clause

**File:** `backend/app/beyo_manager/services/queries/notifications/list_pins.py`

Replace the `if/else` filter block with an `if/elif/else` guard:

```python
# Before
if entity_client_ids:
    stmt = stmt.where(NotificationPin.entity_client_id.in_(entity_client_ids))
else:
    stmt = stmt.where(NotificationPin.major_client_entity_id.in_(major_client_entity_ids))

# After
if entity_client_ids:
    stmt = stmt.where(NotificationPin.entity_client_id.in_(entity_client_ids))
elif major_client_entity_ids:
    stmt = stmt.where(NotificationPin.major_client_entity_id.in_(major_client_entity_ids))
else:
    return {"pins": []}
```

---

### Step 3 — Rewrite `UnpinItem.exactly_one_targeting_mode`

**File:** `backend/app/beyo_manager/services/commands/notifications/requests.py`

Replace the entire `exactly_one_targeting_mode` method body with three explicit, distinct checks. Remove the `has_major_field` variable:

```python
@model_validator(mode="after")
def exactly_one_targeting_mode(self) -> "UnpinItem":
    partial_major = (self.major_entity_type is None) != (self.major_client_entity_id is None)
    if partial_major:
        raise ValueError(
            "major_entity_type and major_client_entity_id must both be provided together."
        )
    by_client_id = self.client_id is not None
    by_major     = self.major_entity_type is not None
    if by_client_id and by_major:
        raise ValueError(
            "Provide either client_id or major entity targeting, not both."
        )
    if not by_client_id and not by_major:
        raise ValueError(
            "Provide either client_id or both major_entity_type + major_client_entity_id."
        )
    return self
```

The `has_major_field` variable and the two merged `raise ValueError` calls are replaced by three separate checks covering: incomplete pair, both modes, neither mode.

---

### Step 4 — Write unit tests for the batch endpoints

**New file:** `backend/app/tests/unit/services/commands/notifications/test_pin_notification_batch.py`

Use the same async session fixture and import pattern as `test_transition_step_state.py`. Tests must be async and use `pytest.mark.asyncio`.

Cover the following cases:

#### `pin_notification`

- **New pin created**: send a valid single-item batch; assert one `NotificationPin` row exists with the caller-supplied `client_id`, correct `entity_type`, `entity_client_id`, `major_entity_type`, `major_client_entity_id`.
- **Re-pin overwrites fields**: insert a pin directly, then call `pin_notification` with the same `(entity_type, entity_client_id)` and different `conditions` / `fire_once`; assert the existing row is updated and the response returns the original `client_id` (not the new caller-supplied one).
- **Duplicate pair in one batch raises `ValidationError`**: send two items with the same `(entity_type, entity_client_id)` in a single request; assert `ValidationError` is raised before any DB write.

#### `unpin_notification`

- **Delete by `client_id`**: insert a pin, call `unpin_notification` with `[{"client_id": pin.client_id}]`; assert the row is gone.
- **Delete by `major_entity`**: insert two pins with `major_entity_type="task"` and `major_client_entity_id="tsk_test"`, call `unpin_notification` with `[{"major_entity_type": "task", "major_client_entity_id": "tsk_test"}]`; assert both rows are gone.
- **Empty list is no-op**: call `unpin_notification` with `[]`; assert no error and no DB change.

#### `edit_pin_notification`

- **Updates conditions and `fire_once`**: insert a pin with `conditions=None, fire_once=False`; call `edit_pin_notification` with new conditions and `fire_once=True`; assert the row reflects the new values.
- **Missing pin is skipped**: call `edit_pin_notification` with a `client_id` that does not exist; assert no error, returns `{}`.
- **Invalid condition raises `ValidationError`**: insert a pin with `entity_type="task_step"`; call `edit_pin_notification` with `conditions=[{"type": "state", "op": "in", "value": ["not_a_real_state"]}]`; assert `ValidationError` is raised.

#### `list_pins`

- **Filters by `entity_client_ids`**: insert two pins with different `entity_client_id`s; call `list_pins` with one of them; assert only one pin is returned.
- **Filters by `major_client_entity_ids`**: insert two pins sharing `major_client_entity_id="tsk_x"`; call `list_pins` with `major_client_entity_ids=["tsk_x"]`; assert both are returned.
- **Both params None returns empty list**: call `list_pins` with both params `None`; assert `{"pins": []}` with no crash.

---

## Risks and mitigations

- Risk: The async session fixture may not auto-create the `notification_pins` table if tests use SQLite instead of Postgres (JSONB columns are Postgres-specific).
  Mitigation: Use the same test DB setup as the existing notification tests. If SQLite is used, mock the JSONB column as JSON.

- Risk: `NotificationPin` requires a `User` row for the FK on `user_id`. Tests must insert a stub user or use the existing user fixture.
  Mitigation: Reuse the user fixture from `test_transition_step_state.py` or create a minimal stub directly in the test.

## Validation plan

- `py_compile` on all changed files:
  - `backend/app/beyo_manager/routers/api_v1/notifications.py`
  - `backend/app/beyo_manager/services/queries/notifications/list_pins.py`
  - `backend/app/beyo_manager/services/commands/notifications/requests.py`
  - `backend/app/tests/unit/services/commands/notifications/test_pin_notification_batch.py`
- `pytest tests/unit/domain/notifications/test_pin_conditions.py tests/unit/services/commands/task_steps/test_transition_step_state.py`: all pre-existing tests pass.
- `pytest tests/unit/services/commands/notifications/test_pin_notification_batch.py`: all new tests pass.
- `rg -n "ValidationError" backend/app/beyo_manager/routers/api_v1/notifications.py`: zero results.

## Review log

- `2026-06-20` `claude-sonnet-4-6`: Post-implementation review of `PLAN_pin_notification_batch_20260620`. Identified 2 bugs, 1 DX issue, 1 test gap.

## Lifecycle transition

- Current state: `archived`
- Next state: `_none_`
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_batch_corrections_20260620.md`
- Archive record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_batch_corrections_20260620.md`
