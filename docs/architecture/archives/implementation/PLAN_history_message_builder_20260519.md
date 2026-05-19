# PLAN_history_message_builder_20260519

## Metadata

- Plan ID: `PLAN_history_message_builder_20260519`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-19T00:00:00Z`
- Last updated at (UTC): `2026-05-19T06:20:00Z`
- Related issue/ticket: `history-record-system`
- Intention plan: _none — utility extension of the history record infrastructure_

---

## Goal and intent

- **Goal:** Implement a pure Python message builder utility at `services/commands/history/message_builder.py` that produces consistent, human-readable `description` strings for the three history record change types (`CREATED`, `UPDATED`, `DELETED`).
- **Business/user intent:** Every history record displayed on the frontend should read naturally ("David updated the description on Item", "David deleted multiple Notes from Item"). Writing these strings ad-hoc inside individual commands would produce inconsistent phrasing. A shared builder enforces a uniform voice across all callers.
- **Non-goals:** No DB access, no SQLAlchemy, no models, no migration. No i18n or localisation support. No automatic pluralisation logic — callers supply the correct word form. No validation of field names, targets, or usernames — the builder is a pure formatting utility.

---

## Prerequisite

`username_snapshot` column was added to the `HistoryRecord` model and session helper outside the original plan. Verify that a migration for this column exists before deploying. The utility itself is pure Python and has no runtime dependency on the migration.

---

## Scope

- **In scope:**
  - NEW `beyo_manager/services/commands/history/message_builder.py` — three public functions and one private helper.
- **Out of scope:** Modifying `_create_history_record_in_session`, the model, the router, or any existing command. Automatic word pluralisation. Caller-side wiring (hooking commands to emit history records — that is the follow-up plan).
- **Assumptions:**
  - Callers pass `ctx.username` as the `username` argument. `ctx.username` reads from the JWT identity (`identity.get("username", "")`). An empty string or `None` falls back to `"Someone"` inside the builder.
  - Callers are responsible for passing the correct word form of `target` — singular when `plural=False`, plural form when `plural=True`. The builder makes no English pluralisation assumptions.
  - Field names are raw column/attribute names (e.g. `"amount_meters"`, `"state"`). The builder converts underscores to spaces for display.
  - All three functions return a `str` that fits within `String(512)` — the `description` column limit. The truncation logic for `build_update_message` keeps output well within this bound.

---

## Clarifications required

_None._

---

## Acceptance criteria

1. `build_update_message("David", ["description"], "Item")` → `"David updated the description on Item"`
2. `build_update_message("David", ["description", "price", "width"], "Item")` → `"David updated description, price, width on Item"`
3. `build_update_message("David", ["description", "price", "width", "height"], "Item")` → `"David updated description, price, width ... on Item"`
4. `build_update_message("David", ["amount_meters"], "Item Upholstery")` → `"David updated the amount meters on Item Upholstery"`
5. `build_delete_message("David", "Note", "Item", plural=False)` → `"David deleted a Note from Item"`
6. `build_delete_message("David", "Notes", "Item", plural=True)` → `"David deleted multiple Notes from Item"`
7. `build_create_message("David", "Note", "Item", plural=False)` → `"David added a Note to Item"`
8. `build_create_message("David", "Issues", "Item", plural=True)` → `"David added multiple Issues to Item"`
9. Any function called with `username=None` or `username=""` uses `"Someone"` as the actor.
10. `build_update_message("David", [], "Item")` returns a non-crashing fallback: `"David updated Item"`.

---

## Contracts and skills

### Contracts loaded

- `backend/architecture/21_naming_conventions.md`: module naming, file location inside `services/commands/history/`

### Local extensions loaded

_None — this utility has no framework dependencies._

### File read intent — pattern vs. relational

Permitted relational reads (understanding what exists):

| File | What to extract |
|---|---|
| `services/commands/history/_create_history_record_in_session.py` | Confirm the `description` and `username_snapshot` parameter names to document correct call-site wiring |
| `services/context.py` | Confirm `ctx.username` is the correct accessor for the caller's display name |

Prohibited (no pattern reads needed — this file contains no framework patterns):
- Do not read any other command, router, or model to understand how to write this file.

---

## Implementation plan

### Step 1 — Create `services/commands/history/message_builder.py`

This is the only file created by this plan.

```python
_MAX_FIELDS_SHOWN = 3


def _actor(username: str | None) -> str:
    return username if username else "Someone"


def _fmt_field(field_name: str) -> str:
    return field_name.replace("_", " ")


def build_update_message(
    username: str | None,
    fields: list[str],
    target: str,
) -> str:
    """Build a human-readable description for a UPDATED history record.

    Single field:   "David updated the description on Item"
    2–3 fields:     "David updated description, price, width on Item"
    4+ fields:      "David updated description, price, width ... on Item"
    No fields:      "David updated Item"  (fallback — callers should always supply at least one field)
    """
    actor = _actor(username)
    if not fields:
        return f"{actor} updated {target}"
    fmt = [_fmt_field(f) for f in fields]
    if len(fmt) == 1:
        return f"{actor} updated the {fmt[0]} on {target}"
    shown = fmt[:_MAX_FIELDS_SHOWN]
    suffix = " ..." if len(fields) > _MAX_FIELDS_SHOWN else ""
    return f"{actor} updated {', '.join(shown)}{suffix} on {target}"


def build_delete_message(
    username: str | None,
    target: str,
    major_target: str,
    plural: bool = False,
) -> str:
    """Build a human-readable description for a DELETED history record.

    plural=False:  "David deleted a Note from Item"
    plural=True:   "David deleted multiple Notes from Item"

    The caller is responsible for passing the correct word form of `target`
    (singular when plural=False, plural form when plural=True).
    """
    actor = _actor(username)
    qualifier = "multiple" if plural else "a"
    return f"{actor} deleted {qualifier} {target} from {major_target}"


def build_create_message(
    username: str | None,
    target: str,
    major_target: str,
    plural: bool = False,
) -> str:
    """Build a human-readable description for a CREATED history record.

    plural=False:  "David added a Note to Item"
    plural=True:   "David added multiple Issues to Item"

    The caller is responsible for passing the correct word form of `target`
    (singular when plural=False, plural form when plural=True).
    """
    actor = _actor(username)
    qualifier = "multiple" if plural else "a"
    return f"{actor} added {qualifier} {target} to {major_target}"
```

**Import path for all callers:**
```python
from beyo_manager.services.commands.history.message_builder import (
    build_create_message,
    build_delete_message,
    build_update_message,
)
```

**Canonical call-site pattern inside any command:**
```python
# UPDATED example — inside update_item.py, after mutating item.description
description = build_update_message(ctx.username, ["description"], "Item")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM,
    entity_client_id=item.client_id,
    change_type=HistoryRecordChangeTypeEnum.UPDATED,
    description=description,
    field_name="description",
    from_value={"description": old_description},
    to_value={"description": item.description},
    created_by_id=ctx.user_id,
    username_snapshot=ctx.username,
)

# CREATED example — inside create_task_note.py
description = build_create_message(ctx.username, "Note", "Task")
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.TASK,
    entity_client_id=task.client_id,
    change_type=HistoryRecordChangeTypeEnum.CREATED,
    description=description,
    field_name=None,
    from_value=None,
    to_value={"note_id": note.client_id},
    created_by_id=ctx.user_id,
    username_snapshot=ctx.username,
)

# DELETED example — inside delete_item_issues.py, deleting multiple at once
description = build_delete_message(ctx.username, "Issues", "Item", plural=True)
await _create_history_record_in_session(
    session=ctx.session,
    entity_type=HistoryRecordEntityTypeEnum.ITEM,
    entity_client_id=item.client_id,
    change_type=HistoryRecordChangeTypeEnum.DELETED,
    description=description,
    field_name=None,
    from_value={"issue_count": len(deleted_ids)},
    to_value=None,
    created_by_id=ctx.user_id,
    username_snapshot=ctx.username,
)
```

**Note on `ctx.username`:** Use `ctx.username` (the `ServiceContext` property), not `ctx.identity.get("username")` directly. Both read the same JWT claim but `ctx.username` is the established accessor pattern.

---

## Critical implementation notes

### No framework imports

This file must import nothing from SQLAlchemy, FastAPI, or any beyo_manager module. It is a pure Python string-formatting module. Any import beyond the standard library is a contract violation.

### Underscore-to-space conversion applies only to field names

`_fmt_field` is applied only inside `build_update_message` on the `fields` list. `target` and `major_target` are caller-supplied display labels and must NOT be auto-formatted — callers pass them ready to display (e.g. `"Item Upholstery"`, `"Task"`, `"Note"`).

### Column length safety

The `description` column is `VARCHAR(512)`. The worst-case output from `build_update_message` with `_MAX_FIELDS_SHOWN=3` and field names up to 128 chars each is well under 512 chars. No truncation of the final string is needed.

### `_MAX_FIELDS_SHOWN` is module-level

Set to `3`. It is not a parameter — callers cannot override it. If the threshold ever needs changing, it changes in one place.

---

## Risks and mitigations

- **Risk:** Caller passes wrong plural form of `target` (e.g. passes `"Note"` when `plural=True`).
  **Mitigation:** The docstring explicitly states the caller's responsibility. The function itself is intentionally simple — it outputs what it receives. Consistent conventions will be established in the follow-up plan that hooks individual commands.

- **Risk:** `fields` is an empty list, producing a degraded message.
  **Mitigation:** The fallback `"David updated Item"` is non-crashing and acceptable. Commands that call this function should always have at least one changed field to pass.

- **Risk:** A very long target or major_target string pushes output over 512 chars.
  **Mitigation:** `target` and `major_target` are internal display labels derived from domain knowledge (e.g. `"Item Upholstery Requirement"` — 28 chars). In practice these are well within safe bounds.

---

## Validation plan

```python
# Run from backend/app:
# .venv/bin/python -c "
from beyo_manager.services.commands.history.message_builder import (
    build_update_message, build_delete_message, build_create_message,
)

# AC1 — single field with 'the'
assert build_update_message('David', ['description'], 'Item') == 'David updated the description on Item'

# AC2 — 3 fields, no truncation
assert build_update_message('David', ['description', 'price', 'width'], 'Item') == 'David updated description, price, width on Item'

# AC3 — 4 fields, truncated
assert build_update_message('David', ['description', 'price', 'width', 'height'], 'Item') == 'David updated description, price, width ... on Item'

# AC4 — underscore to space
assert build_update_message('David', ['amount_meters'], 'Item Upholstery') == 'David updated the amount meters on Item Upholstery'

# AC5 — delete singular
assert build_delete_message('David', 'Note', 'Item', plural=False) == 'David deleted a Note from Item'

# AC6 — delete plural
assert build_delete_message('David', 'Notes', 'Item', plural=True) == 'David deleted multiple Notes from Item'

# AC7 — create singular
assert build_create_message('David', 'Note', 'Item', plural=False) == 'David added a Note to Item'

# AC8 — create plural
assert build_create_message('David', 'Issues', 'Item', plural=True) == 'David added multiple Issues to Item'

# AC9 — None username
assert build_update_message(None, ['description'], 'Item') == 'Someone updated the description on Item'
assert build_delete_message('', 'Note', 'Item') == 'Someone deleted a Note from Item'

# AC10 — empty fields fallback
assert build_update_message('David', [], 'Item') == 'David updated Item'

print('All assertions passed.')
# "
```

---

## Review log

- Implemented `backend/app/beyo_manager/services/commands/history/message_builder.py` with `_actor`, `_fmt_field`, `build_update_message`, `build_delete_message`, and `build_create_message`.
- Validated all acceptance criteria with in-process assertions and py_compile.
- Wrote lifecycle artifacts:
    - `backend/docs/architecture/implemented_summaries/SUMMARY_history_message_builder_20260519.md`
    - `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_history_message_builder_20260519.md`

---

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `copilot`
