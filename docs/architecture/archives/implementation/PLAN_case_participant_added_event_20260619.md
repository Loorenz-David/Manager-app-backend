# PLAN_case_participant_added_event_20260619

## Metadata

- Plan ID: `PLAN_case_participant_added_event_20260619`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T11:15:10Z`
- Related issue/ticket: none
- Intention plan: none

## Goal and intent

- Goal: Emit a targeted per-participant `UserEvent` (`case:participant-added`) whenever a user is added to a case — at creation and via `add_participant` — carrying that user's current unread count for the case, so frontend badge counters update immediately without a polling round-trip.
- Business/user intent: Case banners showing unread message count and "cases I'm in" lists must update in real time when a case is created or a participant is added. Currently only a workspace broadcast (`case:created`) fires on creation, and the `case:participant-added` workspace broadcast from `add_participant` carries no unread state. Users who are participants never receive a signal telling them their unread count for the new case.
- Non-goals: Bumping unread count on new message send (deferred). Changes to `remove_participant`. Frontend handler implementation.

## Scope

- In scope:
  - `create_case.py`: append one `UserEvent` (`case:participant-added`) per participant to the dispatch batch, with `unread_count` derived from whether an initial message was written.
  - `add_participant.py`: query `CaseConversation.last_message_seq` inside the transaction; append one `UserEvent` (`case:participant-added`) per newly added participant after commit. Keep the existing workspace broadcast.
  - Both handoff catalog copies: correct `case:participant-added` — it is a `UserEvent`, not a workspace event — add `unread_count: number` to the payload, update the `ServerToClientEvents` type block and handler matrix row.
- Out of scope:
  - Bumping unread count on `send_message` / new conversation message.
  - `remove_participant` — no per-user unread signal needed on removal.
  - Frontend handler code.
- Assumptions:
  - `CaseEvent.PARTICIPANT_ADDED = "case:participant-added"` is already defined in `beyo_manager/domain/cases/events.py` — no new enum value needed.
  - `participant_ids` in `create_case` is a Python list of plain strings built before the transaction commits and remains available afterward.
  - `participant.user_id` on `CaseParticipant` objects in `add_participant` is a Python attribute set before session.add_all — accessible after commit without lazy load.
  - A case always has at least one `CaseConversation` created at case-creation time; `func.sum(last_message_seq)` handles single and multi-conversation cases correctly (same pattern as `get_unread_counts.py`).

## Clarifications required

*(none — proposal confirmed by user)*

## Acceptance criteria

1. When `create_case` is called with participants and no initial message, each participant receives a `case:participant-added` socket event on their `user:{id}` room with `{ client_id: <case_id>, unread_count: 0 }`.
2. When `create_case` is called with an initial message, the creator receives `unread_count: 0`; every other participant receives `unread_count: 1`.
3. When `add_participant` adds new participants to an existing case, each newly added user receives `case:participant-added` on their `user:{id}` room with `{ client_id: <case_id>, unread_count: N }` where N equals the current total `last_message_seq` across the case's conversations (i.e. all messages they haven't read yet).
4. The existing `case:created` workspace broadcast in `create_case` and the existing `case:participant-added` workspace broadcast in `add_participant` are preserved unchanged.
5. Both handoff catalog copies have `case:participant-added` documented as a `UserEvent` with `{ client_id: string; unread_count: number }` payload and corrected handler guidance.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/contracts/11_infra_events.md`: `UserEvent` dispatch pattern — build with `build_user_event`, dispatch AFTER the transaction block closes.
- `backend/docs/architecture/contracts/06_commands.md`: `begin` transaction boundaries — DB reads for side-effect data (like `total_unread`) must happen inside the `async with` block.
- `backend/docs/architecture/contracts/56_realtime_layer.md`: payload shape rule `{ client_id, ...extra }` and `UserEvent` routing to `user:{id}` room only.
- `backend/docs/architecture/contracts/23_documentation.md`: both living handoff copies must be updated together.

### Local extensions loaded

*(none)*

### File read intent — pattern vs. relational

Permitted reads before editing:
- `beyo_manager/domain/cases/events.py` — confirm `CaseEvent.PARTICIPANT_ADDED` string value
- `beyo_manager/services/infra/events/build_event.py` — confirm `build_user_event` signature
- `beyo_manager/models/tables/cases/case_conversation.py` — confirm `last_message_seq` column name
- Both handoff catalog files — locate exact anchor lines for each insertion

Prohibited (pattern reads):
- Reading another command to understand `session.add` / `flush` / error-raising — covered by `06_commands.md`
- Reading the socket handler to understand routing — covered by `56_realtime_layer.md`

### Skill selection

- Primary skill: command writer pattern (`06_commands.md`)
- Excluded alternatives: none

## Implementation plan

### Step 1 — `create_case.py`: add per-participant UserEvents

File: `backend/app/beyo_manager/services/commands/cases/create_case.py`

**1a. Import change**

Locate the exact line:
```python
from beyo_manager.services.infra.events.build_event import build_conversation_event
```
Replace with:
```python
from beyo_manager.services.infra.events.build_event import build_conversation_event, build_user_event
```

The `build_workspace_event` import is on a separate line — leave it untouched.

**1b. Dispatch block change**

Locate the exact block (starts at the line after `async with ctx.session.begin():` closes):
```python
    event = build_workspace_event(case, CaseEvent.CREATED, workspace_id=ctx.workspace_id)
    events = [event]
    if initial_message is not None and initial_message_seq is not None:
        events.append(
            build_conversation_event(
                initial_message,
                ConversationMessageEvent.CREATED,
                conversation_id=conversation.client_id,
                workspace_id=ctx.workspace_id,
                extra=conversation_message_extra(initial_message_seq),
            )
        )
    await dispatch(events)
```

Replace with:
```python
    event = build_workspace_event(case, CaseEvent.CREATED, workspace_id=ctx.workspace_id)
    events = [event]
    if initial_message is not None and initial_message_seq is not None:
        events.append(
            build_conversation_event(
                initial_message,
                ConversationMessageEvent.CREATED,
                conversation_id=conversation.client_id,
                workspace_id=ctx.workspace_id,
                extra=conversation_message_extra(initial_message_seq),
            )
        )
    has_initial_message = initial_message is not None
    for uid in participant_ids:
        unread_count = 1 if (has_initial_message and uid != ctx.user_id) else 0
        events.append(
            build_user_event(
                user_id=uid,
                event_name=CaseEvent.PARTICIPANT_ADDED,
                client_id=case.client_id,
                extra={"unread_count": unread_count},
            )
        )
    await dispatch(events)
```

`participant_ids` is a Python list of strings already in scope at this point (built at line 106). `case.client_id` is the PK — accessible after commit.

---

### Step 2 — `add_participant.py`: query unread count and add per-user UserEvents

File: `backend/app/beyo_manager/services/commands/cases/add_participant.py`

**2a. Import changes**

Locate:
```python
from sqlalchemy import select, update
```
Replace with:
```python
from sqlalchemy import func, select, update
```

After the existing `CaseParticipant` import line, add:
```python
from beyo_manager.models.tables.cases.case_conversation import CaseConversation
```

Locate:
```python
from beyo_manager.services.infra.events.build_event import build_workspace_event
```
Replace with:
```python
from beyo_manager.services.infra.events.build_event import build_user_event, build_workspace_event
```

**2b. Transaction block change**

The current body of `async with ctx.session.begin():` ends with:
```python
        if added:
            await ctx.session.execute(update(Case).where(Case.client_id == case.client_id).values(participants_count=Case.participants_count + len(added)))
```

Replace that block with:
```python
        total_unread = 0
        if added:
            await ctx.session.execute(update(Case).where(Case.client_id == case.client_id).values(participants_count=Case.participants_count + len(added)))
            conv_result = await ctx.session.execute(
                select(func.coalesce(func.sum(CaseConversation.last_message_seq), 0))
                .where(CaseConversation.case_id == case.client_id)
            )
            total_unread = conv_result.scalar_one()
```

`total_unread` is a plain integer — it survives session expiry after commit.

**2c. Dispatch block change**

Locate:
```python
    if added:
        event = build_workspace_event(case, CaseEvent.PARTICIPANT_ADDED, workspace_id=ctx.workspace_id)
        await dispatch([event])
```

Replace with:
```python
    if added:
        events = [build_workspace_event(case, CaseEvent.PARTICIPANT_ADDED, workspace_id=ctx.workspace_id)]
        for participant in added:
            events.append(
                build_user_event(
                    user_id=participant.user_id,
                    event_name=CaseEvent.PARTICIPANT_ADDED,
                    client_id=case.client_id,
                    extra={"unread_count": total_unread},
                )
            )
        await dispatch(events)
```

`participant.user_id` is a Python string set directly on the object before `session.add_all` — accessible after commit. `case.client_id` is the PK.

---

### Step 3 — Both handoff catalog copies: correct and extend `case:participant-added`

Apply identical changes to both files:
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`
- `frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`

**3a. Cases section header correction**

Locate the exact line:
```
All case events are workspace-scoped. `client_id` refers to the case.
```
Replace with:
```
Most case events are workspace-scoped. `client_id` refers to the case. Exception: `case:participant-added` is a `UserEvent` — it is emitted only to each participant's own `user:{id}` room, not broadcast to the workspace.
```

**3b. `case:participant-added` entry in the Cases code block**

Locate the exact lines:
```
// A user was added to the case's participant list
'case:participant-added': (payload: { client_id: string }) => void;
```
Replace with:
```
// Sent to each newly added participant on their user:{id} room only (UserEvent, not workspace-scoped).
// unread_count: total messages in the case they have not yet read at the time of addition.
'case:participant-added': (payload: { client_id: string; unread_count: number }) => void;
```

**3c. `ServerToClientEvents` type block**

Locate the exact line:
```
  'case:participant-added':    (payload: { client_id: string }) => void;
```
Replace with:
```
  'case:participant-added':    (payload: { client_id: string; unread_count: number }) => void;
```

**3d. Handler responsibility matrix**

Locate the exact row:
```
| `case:participant-added` | `features/cases/socket-events.ts` | Invalidate case detail |
```
Replace with:
```
| `case:participant-added` | `features/cases/socket-events.ts` | Add case to "my cases" list; set unread badge for this case to `payload.unread_count` |
```

---

## Risks and mitigations

- Risk: `participant_ids` in `create_case` is empty (edge case — creator added but immediately removed from `participant_ids`).
  Mitigation: The `for uid in participant_ids:` loop produces zero iterations on an empty list — no guard needed, no error.

- Risk: `case.client_id` accessed after `ctx.session.begin()` commits may be expired.
  Mitigation: `client_id` is the primary key; SQLAlchemy retains PKs in the identity map after expiry. This is the same access pattern already used by `build_workspace_event(case, CaseEvent.CREATED, ...)` which runs after the block in both files today.

- Risk: `participant.user_id` on `CaseParticipant` objects in `add_participant` is expired after commit.
  Mitigation: `user_id` is set as a Python keyword argument in `CaseParticipant(case_id=..., user_id=user_id)` before `session.add_all`. SQLAlchemy holds it in `__dict__` until flush; after commit it may be expired but it's not a lazy-loaded relationship — it's a scalar column. In async context, accessing a scalar column on an expired object triggers a lazy refresh which fails. To be safe: store `[(p.user_id, p.client_id) for p in added]` before the `async with` block closes (while still inside the session), then iterate that plain list during dispatch.

  **Revised approach for Step 2b** — inside the transaction block, before `async with` closes, capture the needed data:
  ```python
          added_info = [(p.user_id, p.client_id) for p in added]
  ```
  Then in Step 2c, iterate `added_info` instead of `added`:
  ```python
      if added:
          events = [build_workspace_event(case, CaseEvent.PARTICIPANT_ADDED, workspace_id=ctx.workspace_id)]
          for user_id, participant_client_id in added_info:
              events.append(
                  build_user_event(
                      user_id=user_id,
                      event_name=CaseEvent.PARTICIPANT_ADDED,
                      client_id=case.client_id,
                      extra={"unread_count": total_unread},
                  )
              )
          await dispatch(events)
  ```
  Note: `participant_client_id` is available but not needed here — `case.client_id` is the `client_id` for this event since it identifies the case. `participant_client_id` (the CaseParticipant PK) is not included in the payload.

  Add this capture line inside the `async with` block, after `ctx.session.add_all(added)` and before the closing dedent:
  ```python
          added_info = [(p.user_id,) for p in added]
  ```
  (Only `user_id` is needed; tuples of one element are fine or use a plain list of strings: `added_user_ids = [p.user_id for p in added]`)

  Simplest form: capture `added_user_ids = [p.user_id for p in added]` inside the transaction block while `added` is still fully loaded.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/add_participant.py`: must pass with no output.
- `rg -n "case:participant-added\|unread_count" backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/add_participant.py`: must match in both files.
- `rg -n "unread_count" backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: must match in both catalog copies.
- `rg -n "UserEvent\|user:{id}\|user_id room" backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: must confirm the cases section now describes `case:participant-added` as user-scoped.

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
