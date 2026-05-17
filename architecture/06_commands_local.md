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

All composable commands replace `ctx.session.begin()` with `maybe_begin` from
`beyo_manager.services.commands.utils.transaction`:

```python
from beyo_manager.services.commands.utils.transaction import maybe_begin

async def create_record(ctx: ServiceContext) -> dict:
    request = parse_create_record_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        record = Record(workspace_id=ctx.workspace_id, ...)
        ctx.session.add(record)
        await ctx.session.flush()   # only when client_id is needed immediately

    return {"client_id": record.client_id}
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

### What each session call does inside a `maybe_begin` block

| Call | Effect | Safe in subordinate mode? |
|------|--------|--------------------------|
| `ctx.session.add(obj)` | Stages ORM object — no DB write yet | ✅ Yes |
| `await ctx.session.flush()` | Pushes staged objects to DB within the open transaction; makes DB-generated values (e.g. `client_id`) available; does NOT commit | ✅ Yes |
| `await ctx.session.commit()` | **FORBIDDEN inside `maybe_begin`** — prematurely closes the parent's transaction in subordinate mode | ❌ Never |
| `await ctx.session.rollback()` | **FORBIDDEN inside `maybe_begin`** — exception propagation triggers rollback automatically | ❌ Never |

### Event emission rule

Events must only be dispatched after the owning commit fires. Subordinate
commands must NOT dispatch events — they collect `pending_events` and return
them to the parent, which dispatches after its own block exits:

```python
# Parent command (owner)
pending_events = []

async with maybe_begin(ctx.session):
    pending_events += await _child_helper(ctx.session, ...)

event_bus.dispatch(pending_events)   # after commit — never inside begin()
```

For commands with no event emission (most item lifecycle commands), no special
handling is needed.

### Invariants

1. One `maybe_begin` block per command function — never nest two in the same body.
2. Never add `await session.commit()` or `await session.rollback()` manually
   inside a `maybe_begin` block.
3. `await session.flush()` is the only explicit session operation permitted
   inside the block beyond `session.add()` and `session.execute()`.
4. `maybe_begin` must be imported from
   `beyo_manager.services.commands.utils.transaction` — not re-implemented inline.

### Which commands use `maybe_begin`

All commands in `services/commands/items/` use `maybe_begin`. Commands in other
domains continue to use `ctx.session.begin()` until a higher-level command
requires composition across those commands — at which point they are refactored
to `maybe_begin` in a dedicated plan.

Commands that are never embedded by a parent (e.g., auth, bootstrap) retain
`ctx.session.begin()` and are explicitly excluded from this extension.
