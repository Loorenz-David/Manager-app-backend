# Users Domain — Table Guide

## Tables in this folder

| File | Table | Prefix | Purpose |
|---|---|---|---|
| `user_work_profile.py` | `user_work_profiles` | `uwp` | Per-user, per-workspace compensation profile |
| `user_shift_state_record.py` | `user_shift_state_records` | `uss` | Full history of shift state transitions per user |

> The `users` table itself lives at `models/tables/users/user.py` (bootstrap). These two tables extend it with operational worker data without modifying the core identity table.

---

## Boundary rules

**`users` is global identity only.** Do not add operational state to it. These tables exist to keep compensation and shift lifecycle separate from authentication identity.

Forbidden on `users`:
- salary / compensation
- shift state
- working section assignment (lives in `working_section_memberships`)
- role assignment (lives in `workspace_memberships.workspace_role_id`)
- websocket presence / runtime online state

---

## `user_work_profiles` — key rules for commands

- **One row per `(user_id, workspace_id)`.** UNIQUE constraint enforced. If a user leaves and is rehired, update the existing row — do not insert a second row.
- **Snapshot before mutating.** When salary changes, the command must snapshot the previous values before overwriting. Historical compensation truth must not be derived from the current mutable row.
- **`created_by_id` is never null** for normal operations. All compensation creation must be actor-attributed.
- **`updated_by_id` is required** on every update command (nullable only at creation time).
- **Currency is workspace-scoped**, not stored on this table. The workspace determines the currency for compensation values stored here.
- `Numeric(12,4)` — never `Float` for salary fields. Values are retrieved as Python `Decimal`.

---

## `user_shift_state_records` — key rules for commands

### State machine

```
STARTED_SHIFT -> WORKING
WORKING       -> IN_PAUSE
IN_PAUSE      -> WORKING
WORKING       -> ENDED_SHIFT
```

All other transitions are illegal. **Transition enforcement is exclusively in the domain layer** — no DB triggers or ORM validators.

### Active row rule

- Active shift = row where `exited_at IS NULL`.
- Enforced via partial unique index `uix_user_shift_state_records_active` on `(user_id, workspace_id) WHERE exited_at IS NULL`.
- **Before inserting a new state row, `exited_at` must be set on the current open row** within the same transaction.
- Only command-layer transition services may mutate these rows. Direct ORM mutation is forbidden.

### Read pattern for active shift

```python
SELECT * FROM user_shift_state_records
WHERE user_id = ? AND workspace_id = ? AND exited_at IS NULL
```

### Durability

- Do not hard-delete rows. `exited_at` / `changed_by_id` track the full lifecycle.
- All timestamps are UTC. Frontend is responsible for timezone localization.

---

## Deferred

- Websocket presence and runtime online tracking belong to a future realtime presence system.
- Language normalization is deferred (languages stored as JSONB on `users`).
