# PLAN_maybe_begin_transaction_utility_20260517

## Metadata

- Plan ID: `PLAN_maybe_begin_transaction_utility_20260517`
- Status: `summarized`
- Owner agent: `Claude Sonnet 4.6`
- Created at (UTC): `2026-05-17T12:00:00Z`
- Last updated at (UTC): `2026-05-17T12:00:00Z`
- Related issue/ticket: `—`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_item_crud_and_issues_20260517.md`

## Goal and intent

- **Goal:** Introduce a `maybe_begin` async context manager and apply it to every command in `services/commands/items/` so that each command can be called both as a standalone operation (opening its own transaction) and as a subordinate within a parent command that already holds an open transaction.
- **Business/user intent:** Higher-level commands (e.g., a future task-creation command that creates an item, its issues, and its upholstery in one atomic unit) must be able to call item-level commands inline without triggering a nested `session.begin()`, which raises `InvalidRequestError` in SQLAlchemy 2.x. The item-level commands must remain usable from standalone routers without any change to callers.
- **Non-goals:** Adding `maybe_begin` to commands outside `services/commands/items/`. Changing business logic inside any command. Changing router behaviour. Changing return shapes of any command.

## Commit and flush semantics — read this before touching any command

This section is the authoritative answer to "who commits and when." It must be understood before implementing Step 3.

### Two modes, one utility — exact behavior at block exit

```
┌──────────────────────────────────────────────────────────────────────┐
│  OWNER MODE  (session.in_transaction() is False on entry)            │
│                                                                      │
│  async with maybe_begin(ctx.session):   ← opens session.begin()     │
│      ctx.session.add(record)                                         │
│      await ctx.session.flush()          ← pushes to DB, no commit   │
│                                         ← block exits normally       │
│                         ↓ SQLAlchemy auto-calls session.commit() ↓   │
│                         ← COMMIT fires here, once, on block exit     │
│                                                                      │
│  On exception inside block → SQLAlchemy auto-calls session.rollback()│
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  SUBORDINATE MODE  (session.in_transaction() is True on entry)       │
│                                                                      │
│  async with maybe_begin(ctx.session):   ← no session.begin() called │
│      ctx.session.add(record)                                         │
│      await ctx.session.flush()          ← pushes to DB, no commit   │
│                                         ← block exits normally       │
│                         ↓ NOTHING HAPPENS ↓                          │
│                         ← NO commit, NO rollback                     │
│                         ← transaction stays open, owned by parent    │
│                                                                      │
│  On exception inside block → exception propagates to parent;         │
│  the parent's maybe_begin (owner mode) triggers the rollback.        │
└──────────────────────────────────────────────────────────────────────┘
```

### The single commit point

When a parent command opens a transaction (owner mode) and calls a subordinate command (subordinate mode) inline, the commit chain is:

```
parent: async with maybe_begin(ctx.session):  ← opens transaction
    # ... parent logic ...
    await _child_helper(ctx.session, ...)     ← subordinate adds rows, flushes
    # ... more parent logic ...
                                              ← parent block exits normally
                      ↓ ONE commit here ↓
              ALL flushes from ALL subordinate helpers committed together
```

There is exactly one commit for the entire chain. It fires when the outermost owner-mode `maybe_begin` block exits. Subordinate commands contribute their writes via `flush()` — they are committed by the parent, not by themselves.

### What `flush()` does vs. what `commit()` does

| Operation | What it does | Safe in subordinate mode? |
|-----------|-------------|--------------------------|
| `await session.flush()` | Pushes pending ORM objects to the DB within the open transaction; makes DB-generated values (e.g. `client_id`) available for the same session to read; does NOT commit | ✅ Yes — does not close the transaction |
| `await session.commit()` | Writes all pending changes permanently and closes the transaction | ❌ Never call manually inside `maybe_begin` |
| `await session.rollback()` | Discards all pending changes and closes the transaction | ❌ Never call manually inside `maybe_begin` |

### Absolute rules for Copilot

1. **Never add `await session.commit()` inside a `maybe_begin` block.** The context manager handles commit in owner mode. In subordinate mode, calling `commit()` would prematurely close the parent's transaction.
2. **Never add `await session.rollback()` inside a `maybe_begin` block.** Exception propagation triggers rollback automatically in owner mode.
3. **`await session.flush()` is the only explicit session call permitted inside the block** — and only when the command needs a DB-generated value immediately (e.g., `client_id` after `session.add()`).
4. **Existing `flush()` calls in the 9 target files are correct and must not be removed.** They are needed to obtain `client_id` before linking related rows.

---

## Scope

- **In scope:**
  1. New file `backend/app/beyo_manager/services/commands/utils/__init__.py` (empty, makes `utils` a package)
  2. New file `backend/app/beyo_manager/services/commands/utils/transaction.py` containing `maybe_begin`
  3. New file `backend/architecture/06_commands_local.md` — local companion contract documenting the propagation-aware transaction pattern for this app
  4. Replacing every `async with ctx.session.begin():` in the 9 files listed below with `async with maybe_begin(ctx.session):`

- **Out of scope:**
  - Any command outside `services/commands/items/`
  - Extracting session-level helpers from `create_item_upholstery.py` (that refactor is part of `PLAN_item_crud_and_issues_20260517`)
  - Tests, migrations, model changes, router changes
  - Any upholstery commands in `services/commands/upholstery/`

- **Assumptions:**
  - SQLAlchemy 2.x `AsyncSession.in_transaction()` returns `True` when `session.begin()` has been called and the transaction is still open. This is verified by the SQLAlchemy 2.x async session API.
  - All 9 target files use `async with ctx.session.begin():` as their only transaction control statement — no nested `begin()` calls exist inside any single command. (Verified by reading the files before coding.)
  - The `services/commands/utils/` directory does not yet exist. The plan creates it.

## Clarifications required

None — all questions resolved in the intention plan.

## Acceptance criteria

1. `backend/app/beyo_manager/services/commands/utils/transaction.py` exists and exports `maybe_begin`.
2. `backend/architecture/06_commands_local.md` exists and formally documents the `maybe_begin` pattern as the app-local transaction contract extension.
3. All 9 command files in `services/commands/items/` import and use `maybe_begin` in place of `ctx.session.begin()`.
4. No command file contains a bare `async with ctx.session.begin():` call after the refactor (grep confirms zero occurrences).
5. All existing item-upholstery endpoints remain callable and return the same shapes as before the refactor — confirmed by running the server and hitting one GET and one POST endpoint from each file.
6. No Python import errors on server start.

## Contracts and skills

### Contracts loaded

Read order:

- `backend/architecture/01_architecture.md` (baseline) — layer rules, folder structure, naming conventions
- `backend/architecture/04_context.md` (baseline) — `ServiceContext` shape; confirms `ctx.session` is `AsyncSession`
- `backend/architecture/05_errors.md` (baseline) — error hierarchy; no change here but needed for context
- `backend/architecture/06_commands.md` (baseline) — canonical transaction pattern (`async with ctx.session.begin()`); the section "If the caller already holds an open transaction" is the explicit acknowledgment that this plan formalises
- `backend/architecture/21_naming_conventions.md` (baseline) — file naming rules; confirms private helpers prefix `_`; confirms no file named `utils.py` (directory named `utils/` with a meaningfully-named file inside is acceptable, matching existing `services/queries/utils/string_filter.py`)

Applied precedence:
- `06_commands_local.md` (created by this plan) will override the canonical default after this plan completes. During implementation, the canonical rule is still the active baseline — the local companion documents the approved extension.

No local companion exists for `06_commands.md` prior to this plan. Creating it is step 1.

### Local extensions loaded

- None pre-exist. `06_commands_local.md` is created as step 1 of this plan.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

**Permitted (relational reads — what exists):**
- Reading each of the 9 target command files to find every `async with ctx.session.begin():` occurrence and confirm no nested `begin()` calls exist — required before applying the mechanical replacement
- Reading `services/commands/items/requests/__init__.py` to verify import paths are unchanged
- Reading `services/commands/items/__init__.py` to verify no import of a utility is needed there

**Prohibited (pattern reads — contract already covers these):**
- Reading any command outside the 9 targets to learn the `session.begin()` / `flush()` pattern — `06_commands.md` already defines it
- Reading any router to understand handler wiring — `09_routers.md` covers it
- Reading any serializer to understand output shape — not in scope

### Skill selection

- Primary skill: `06_commands.md` — transaction boundary rules
- No router trigger terms apply (no new endpoints)
- Excluded: `09_routers.md`, `08_domain.md`, `30_migrations.md` — not needed for a utility extraction + mechanical refactor

---

## Implementation plan

### Step 1 — Create local contract companion `06_commands_local.md`

Create `backend/architecture/06_commands_local.md` with the following content:

```markdown
# Command Contract — Local Extensions
> Extends: 06_commands.md

## Transaction propagation pattern (`maybe_begin`)

### Context

The canonical contract specifies that commands own their own transaction via
`async with ctx.session.begin()` and explicitly forbids nesting `begin()` inside
another `begin()`. Higher-level commands that compose multiple leaf commands in
one atomic unit need the leaf commands to join an existing transaction instead of
opening a new one.

### `maybe_begin` — approved local extension

A shared async context manager `maybe_begin` replaces `ctx.session.begin()` in
all composable commands:

```python
# backend/app/beyo_manager/services/commands/utils/transaction.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def maybe_begin(session: AsyncSession):
    """Join the active transaction if one exists; open a new one otherwise."""
    if session.in_transaction():
        yield          # subordinate mode — flush is allowed; commit is the caller's
    else:
        async with session.begin():
            yield      # owner mode — commits on normal exit, rolls back on exception
```

### Usage rule

Every composable item command replaces:

```python
async with ctx.session.begin():
    ...
```

with:

```python
from beyo_manager.services.commands.utils.transaction import maybe_begin

async with maybe_begin(ctx.session):
    ...
```

### Commit semantics — exact behavior per mode

**Owner mode** (`session.in_transaction()` is `False` on entry):
- `maybe_begin` opens `session.begin()` internally.
- On normal block exit: SQLAlchemy automatically calls `session.commit()` —
  all flushes and ORM additions inside the block are committed.
- On exception: SQLAlchemy automatically calls `session.rollback()`.
- Behaviour is identical to the canonical `ctx.session.begin()`.

**Subordinate mode** (`session.in_transaction()` is `True` on entry):
- `maybe_begin` calls neither `session.begin()` nor any commit or rollback.
- The block body runs inside the parent's already-open transaction.
- On normal block exit: **nothing happens** — no commit, no rollback.
  The transaction stays open, owned by the parent.
- On exception: the exception propagates up to the parent's `maybe_begin`
  (owner mode), which triggers `session.rollback()` on its exit.
- The parent's owner-mode `maybe_begin` is the **single commit point** for
  the entire call chain — all flushes from all subordinates are committed
  together when the parent's block exits normally.

### What each session operation does inside a `maybe_begin` block

| Call | Effect | Safe in subordinate mode? |
|------|--------|--------------------------|
| `ctx.session.add(obj)` | Stages ORM object — no DB write yet | ✅ Yes |
| `await ctx.session.flush()` | Pushes staged objects to DB within the open transaction; makes DB-generated values (e.g. `client_id`) available; does NOT commit | ✅ Yes |
| `await ctx.session.commit()` | ❌ **FORBIDDEN inside `maybe_begin`** — in subordinate mode this prematurely closes the parent's transaction; in owner mode it is redundant and bypasses the context manager's rollback guard | ❌ Never |
| `await ctx.session.rollback()` | ❌ **FORBIDDEN inside `maybe_begin`** — exception propagation triggers rollback automatically | ❌ Never |

### Event emission rule

Events must only be dispatched after the owning commit. Commands that emit
events must collect them in a `pending_events` list inside the `maybe_begin`
block and dispatch **after** the block exits, guarded as follows:

```python
pending_events = []

async with maybe_begin(ctx.session):
    # writes and flushes
    pending_events.append(build_event(...))

# Only reached after commit (owner) or after parent block continues (subordinate).
# In subordinate mode this code still runs, but the parent will dispatch its own
# events after its own commit — subordinate commands should NOT emit events.
# Pattern: subordinate commands return pending_events to the parent instead of
# dispatching them directly.
```

For the 9 commands refactored in this plan: none emit events. No change needed.

### Invariants

- One `maybe_begin` block per command function — never nest two in the same body.
- Never add `await session.commit()` or `await session.rollback()` manually
  inside a `maybe_begin` block.
- `await session.flush()` is the only explicit session operation permitted
  inside the block beyond `session.add()` / `session.execute()`.

### Which commands must use `maybe_begin`

All commands in `services/commands/items/` use `maybe_begin`. Commands in other
domains continue to use `ctx.session.begin()` until a higher-level command
requires composition across those commands — at which point they are refactored
to `maybe_begin` in a dedicated plan.

Commands that are **never** embedded by a parent (e.g., auth, bootstrap) retain
`ctx.session.begin()` and are explicitly excluded from this extension.
```

---

### Step 2 — Create `services/commands/utils/` package

Create two files:

**`backend/app/beyo_manager/services/commands/utils/__init__.py`**
```python
```
*(empty — makes the directory a Python package)*

**`backend/app/beyo_manager/services/commands/utils/transaction.py`**
```python
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def maybe_begin(session: AsyncSession):
    """Join the active transaction if one exists; open a new one otherwise.

    Owner mode  (no active transaction): opens session.begin(); commits on normal
                exit; rolls back on exception — identical to ctx.session.begin().
    Subordinate (active transaction open): yields immediately; flush is valid;
                commit and rollback are the caller's responsibility.
    """
    if session.in_transaction():
        yield
    else:
        async with session.begin():
            yield
```

---

### Step 3 — Refactor the 9 command files

For each file below, perform the mechanical replacement:

**Add import** (after existing imports, grouped with other `beyo_manager` imports):
```python
from beyo_manager.services.commands.utils.transaction import maybe_begin
```

**Replace** every occurrence of:
```python
async with ctx.session.begin():
```
with:
```python
async with maybe_begin(ctx.session):
```

No other changes to any file. Logic, guards, flush calls, return values — all unchanged.

#### Target files (9 total)

| # | File | Commands inside | `ctx.session.begin()` occurrences |
|---|------|----------------|----------------------------------|
| 1 | `services/commands/items/create_item_upholstery.py` | `create_item_upholstery` | 1 |
| 2 | `services/commands/items/update_and_delete_item_upholstery.py` | `update_item_upholstery`, `delete_item_upholstery` | 2 |
| 3 | `services/commands/items/mark_requirements_in_use.py` | `mark_requirements_in_use` | 1 |
| 4 | `services/commands/items/mark_requirements_completed.py` | `mark_requirements_completed` | 1 |
| 5 | `services/commands/items/mark_requirements_ordered.py` | `mark_requirements_ordered` | 1 |
| 6 | `services/commands/items/resolve_requirements_after_stock.py` | `resolve_requirements_after_stock` | 1 |
| 7 | `services/commands/items/apply_surplus_to_requirement.py` | `apply_surplus_to_requirement` | 1 |
| 8 | `services/commands/items/set_requirement_quantity.py` | `set_requirement_quantity` | 1 |
| 9 | `services/commands/items/complete_single_and_reallocate.py` | `complete_single_requirement`, `reallocate_stock` | 2 |

**Read each file before editing it** to confirm the exact occurrence count and that no nested `begin()` calls exist. If an actual count differs from the table above, stop and reconcile before continuing.

---

### Step 4 — Verify zero remaining occurrences

After all edits, run:

```bash
grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/items/
```

Expected output: **no matches**. If any remain, fix before proceeding.

---

### Step 5 — Confirm server imports cleanly

Start the server (or run `python -c "from beyo_manager import create_app; create_app()"` from `backend/app/`) and confirm no `ImportError` or `AttributeError` is raised.

---

## Risks and mitigations

- **Risk:** `session.in_transaction()` returns an unexpected value in the version of SQLAlchemy in use, causing double-begin or no-begin.
  **Mitigation:** Verify by checking `sqlalchemy.__version__` — `in_transaction()` on `AsyncSession` is stable since SQLAlchemy 2.0. If the project uses 1.4, the method name is `is_active` on the underlying sync session; the plan must be updated before applying.

- **Risk:** A command emits events after its block exits in subordinate mode, dispatching before the parent commits — events fired for writes that haven't landed yet.
  **Mitigation:** All 9 commands in scope currently have no event emission (confirmed by reading each file). The local contract companion explicitly documents the invariant for future commands. No runtime risk for this plan.

- **Risk:** A command in the 9 has a nested `begin()` call that was missed in the initial read, causing a double-enter after the refactor hides the outer `begin()` guard.
  **Mitigation:** Step 3 instructs the agent to read each file in full before editing. Step 4 grep catches stale `ctx.session.begin()` calls.

- **Risk:** `services/commands/utils/` directory naming conflicts with the naming convention ("never create `utils.py`").
  **Mitigation:** The convention prohibits a **file** named `utils.py`. A **directory** named `utils/` containing a file with a meaningful name (`transaction.py`) follows the same pattern already established by `services/queries/utils/string_filter.py`. The directory is a namespace; the file name states its purpose.

---

## Validation plan

- `grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/items/` → **zero matches**
- `grep -rn "maybe_begin" backend/app/beyo_manager/services/commands/items/` → **9 matches minimum** (one per file; files with 2 commands show 2 matches)
- Server starts without `ImportError`: `cd backend/app && .venv/bin/python -c "from beyo_manager import create_app; create_app()"`
- Existing standalone behaviour confirmed: start server, hit `PUT /api/v1/item-upholsteries` with a valid payload → returns same shape as before the refactor (transaction opens and commits in owner mode unchanged)
- Confirm `06_commands_local.md` exists at `backend/architecture/06_commands_local.md` and opens with `> Extends: 06_commands.md`

---

## Review log

*(to be filled as the plan is implemented)*

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `David Loorenz`
