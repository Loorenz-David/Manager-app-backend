# PLAN_upholstery_history_name_20260602

## Metadata

- Plan ID: `PLAN_upholstery_history_name_20260602`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-06-02T00:00:00Z`
- Last updated at (UTC): `2026-06-02T12:14:54Z`
- Related issue/ticket: —

## Goal and intent

- Goal: Include the upholstery name in the `description` field of every `HistoryRecord` written for `ITEM_UPHOLSTERY` entity type.
- Business/user intent: Operators reading the task flow records can identify which upholstery was created, updated, or deleted at a glance — without having to cross-reference the entity id.
- Non-goals: Do not change descriptions for any other entity type (task, case, requirement, etc.). Do not change the message builder function signatures.

## Scope

- In scope:
  - `create_item_upholstery` — created record description
  - `update_item_upholstery` — updated record description
  - `delete_item_upholstery` — deleted record description
- Out of scope:
  - `message_builder.py` functions — no signature changes needed; the call sites will compose the target string
  - Any other history-producing commands
- Assumptions:
  - `ItemUpholstery.name` may be `None` (e.g. CUSTOMER-sourced upholstery with no name supplied). The description must degrade gracefully to the current wording when `name` is absent.

## File manifest

### Existing files to edit

| Path (relative to `backend/app/`) | Change summary |
|---|---|
| `beyo_manager/services/commands/items/create_item_upholstery.py` | Build `target` string from `request.name` before the `build_create_message` call; pass it as the `target` argument |
| `beyo_manager/services/commands/items/update_and_delete_item_upholstery.py` | Build `target` string from `iup.name` before each `build_update_message` and `build_delete_message` call; pass it as the `target` argument |

### New files to create

_None._

## Clarifications required

_None — name is available at every call site._

## Acceptance criteria

1. After `create_item_upholstery` runs with `name="Velvet Blue"`, the flow record description reads `"<actor> added a upholstery Velvet Blue to item"`.
2. After `update_item_upholstery` runs on an upholstery with `name="Velvet Blue"`, the description reads `"<actor> updated <fields> on upholstery Velvet Blue"`.
3. After `delete_item_upholstery` runs on an upholstery with `name="Velvet Blue"`, the description reads `"<actor> deleted a upholstery Velvet Blue from item"`.
4. When `name` is `None`, all three descriptions fall back to the current wording (no crash, no `None` literal in the string).

## Contracts and skills

### Contracts loaded

_None required._

### Local extensions loaded

_None required._

### Skill selection

_No special skill — straightforward call-site edit._

## Implementation plan

1. **`create_item_upholstery.py`** — Before the `_create_history_record_in_session` call (line ~171), derive the target:
   ```python
   upholstery_target = f"upholstery {request.name}" if request.name else "upholstery"
   ```
   Pass `upholstery_target` as the `target` argument to `build_create_message` instead of the hardcoded `"upholstery"`.

2. **`update_and_delete_item_upholstery.py` — update branch** — Before the `_create_history_record_in_session` call in `update_item_upholstery` (line ~192), derive the target:
   ```python
   upholstery_target = f"upholstery {iup.name}" if iup.name else "upholstery"
   ```
   Pass `upholstery_target` as the `target` argument to `build_update_message` instead of the hardcoded `"upholstery"`.

3. **`update_and_delete_item_upholstery.py` — delete branch** — Before the `_create_history_record_in_session` call in `delete_item_upholstery` (line ~237), derive the target:
   ```python
   upholstery_target = f"upholstery {iup.name}" if iup.name else "upholstery"
   ```
   Pass `upholstery_target` as the `target` argument to `build_delete_message` instead of the hardcoded `"upholstery"`.

## Risks and mitigations

- Risk: `name` is `None` for CUSTOMER-sourced upholsteries.
  Mitigation: The ternary `f"upholstery {name}" if name else "upholstery"` ensures no `None` literal appears in the description.

## Validation plan

- Manual smoke test: create an upholstery with a known name, update a field, then delete it, and call `GET /tasks/{id}/flow-records` — verify the three flow record descriptions each contain the upholstery name.
- Manual smoke test: repeat with a CUSTOMER-sourced upholstery where `name` is `None` — verify descriptions read the same as before this change.

## Review log

- `2026-06-02` `copilot`: Implemented upholstery name in item upholstery history descriptions and validated with typecheck.

## Lifecycle transition

- Current state: `archived`
- Next state: `archived`
- Transition owner: `david`
