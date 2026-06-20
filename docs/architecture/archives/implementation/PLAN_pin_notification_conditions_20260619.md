# PLAN_pin_notification_conditions_20260619

## Metadata

- Plan ID: `PLAN_pin_notification_conditions_20260619`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T20:15:42Z`
- Related issue/ticket: —

## Goal and intent

- Goal: Extend the polymorphic `NotificationPin` system so a pin can carry **conditions** — reusable, registry-driven attribute predicates that decide whether a given event on the pinned entity actually notifies the user. Ship the `state` condition; design the registry so future condition types (e.g. `time`) drop in without schema changes.
- Business/user intent: A user pinning an entity today receives *every* notification for it. They want to narrow it — e.g. "notify me about this task step only when it reaches `completed` or `paused`," or "notify me about this upholstery requirement only when it becomes `ordered`." This makes pins useful instead of noisy.
- Non-goals:
  - The `time` condition (and any non-`state` condition) — designed for, but **not implemented** here. It exists only as the proof that the registry is extensible.
  - Wildcard / workspace-scoped pins (`entity_client_id IS NULL`) and entity-ancestry resolution (pin a working section → receive its steps' events). Scope stays the entity target, exactly as today. See [Risks](#risks-and-mitigations).
  - Any change to the `CREATE_NOTIFICATIONS` / `SEND_PUSH_NOTIFICATION` workers — they stay dumb fan-outs over an already-resolved `user_ids` list.

## Scope

- In scope:
  - `NotificationPin` model: add nullable `conditions` JSONB column (`NULL` = match all → every existing pin is backward-compatible) and a non-nullable `fire_once` boolean column (default `False` → permanent pin, every existing pin is unaffected).
  - Alembic migration adding the column.
  - New domain module `domain/notifications/pin_conditions.py`: the condition-type registry, `validate_pin_conditions(entity_type, conditions)`, and the matcher `pin_conditions_match(conditions, event_facts) -> bool`.
  - New domain helper `domain/notifications/pinned_subscribers.py`: `resolve_pinned_subscribers(session, entity_type, entity_client_id, event_facts) -> set[str]` — the single, condition-aware pin source used by every call site.
  - `pin_notification` command + a `parse_pin_notification_request`: accept optional `conditions` and optional `fire_once` flag, validate them, and **update** both fields on re-pin (idempotent on identity, last-write-wins on conditions and `fire_once`).
  - Route the three existing pin sources through `resolve_pinned_subscribers`, each supplying `event_facts`:
    - `services/commands/task_steps/transition_step_state.py` (inline `task_step` pin query, lines 334–343)
    - `services/commands/tasks/_notification_helpers.py` (`_resolve_task_audience`, pin source)
    - `services/commands/items/_notification_helpers.py` (`_resolve_upholstery_audience`, pin source)
  - Extend `EntityType` with `TASK`, `TASK_STEP`, `ITEM_UPHOLSTERY` so the pin `entity_type` validates against the enum per the 47 contract (these are currently stored as raw strings — a pre-existing drift).
  - **Relocate audience resolvers to the domain layer per contract 47**: create `domain/task_steps/notification_targets.py`, `domain/tasks/notification_targets.py`, and `domain/items/notification_targets.py`. Wire all existing command call sites to the new domain modules. Delete the now-redundant `services/commands/tasks/_notification_helpers.py` and `services/commands/items/_notification_helpers.py`.
- Out of scope:
  - Frontend UI for composing conditions.
- Assumptions:
  - A single notification-triggering operation transitions its target entity to **one** state, so one `event_facts` dict per resolver call is sufficient (confirmed: `mark_requirements_*`, `transition_step_state`, task terminal commands each target one state).
  - `conditions` applies to **pins only**. Unconditional sources in the audience resolvers (active managers, `task.created_by_id`) must keep firing regardless — conditions never filter them.

## Clarifications required

- [x] Does the user pin specific entities or broad categories? — **resolved in design discussion**: specific entities only. No wildcard/ancestry. Scope = entity target.
- [x] Should `time` be implemented? — **resolved**: no, it is an extensibility example only.
- [ ] Re-pinning the same entity with new conditions — confirm desired semantics is **overwrite** the prior conditions (this plan assumes last-write-wins). Blocks safe implementation because the alternative (reject duplicate / merge) changes the command's conflict handling.

## Acceptance criteria

1. A pin created with `conditions = [{"type": "state", "op": "in", "value": ["completed", "paused"]}]` on a `task_step` causes a notification **only** when that step transitions into `completed` or `paused`; transitions into other states produce no notification for that user.
2. A pin with `conditions = NULL` (or omitted) behaves exactly as today — notifies on every event. Every pre-existing row is unaffected.
3. `pin_notification` rejects, with a `ValidationError`, conditions whose `type` is unknown, whose `op` is unsupported, or whose `value` contains a state not in the target entity's state enum (e.g. `paused` on an `item_upholstery` pin).
4. Unconditional audience sources (active managers, task creator) still receive notifications on the relevant task commands regardless of any pin conditions.
5. Re-pinning an entity with different conditions overwrites the stored conditions (subject to the open clarification).
6. The condition matcher and registry live in `domain/notifications/` and contain **no** SQL or command logic; the matcher is a pure function unit-tested in isolation.
7. Adding a hypothetical second condition type requires only a new registry entry + the emitting command supplying its fact key — no migration, no model change. Demonstrated by a `time`-shaped registry stub test (config-validation only, evaluation may `raise NotImplementedError`).
8. All three notification audience resolvers live in `domain/<entity>/notification_targets.py` per contract 47. `services/commands/tasks/_notification_helpers.py` and `services/commands/items/_notification_helpers.py` are deleted; no command imports from them.
9. A pin created with `fire_once = True` is deleted from `notification_pins` within the same transaction that enqueues `CREATE_NOTIFICATIONS` — confirmed by querying the table after the command returns.
10. A pin created with `fire_once = False` (default) is **not** deleted after firing — it persists and fires again on the next matching event.
11. `unpin_notification` still hard-deletes any pin regardless of `fire_once` value — no change to its behavior.

## Contracts and skills

Resolution per `backend/task_system/backend_contract_goal_mapping_guide.md`, document-only protocol. Canonical contracts read from `backend/architecture/` (the set carrying `_local` companions).

### Contracts loaded

Core (always):
- `01_architecture.md`: layer boundaries (domain vs. service vs. model).
- `04_context.md`: `ServiceContext` shape — `user_id`, `workspace_id`, `incoming_data`.
- `05_errors.md`: `ValidationError` for rejected conditions.
- `06_commands.md` + `06_commands_local.md`: command structure; `maybe_begin` transaction utility; subordinate-command event rule; `CREATE_NOTIFICATIONS` queued **after** commit.
- `07_queries.md` + `07_queries_local.md`: query/session-read conventions used by the resolver helper.
- `09_routers.md`: handler wiring for the unchanged `POST /notifications/pins` route (request body gains `conditions`).
- `21_naming_conventions.md`: module/function naming (`parse_*_request`, `resolve_*`).
- `40_identity.md`, `41_user.md`: `user.client_id` is the unit returned by resolvers.
- `42_event.md` + `42_event_local.md`: confirms the notification path is `UserEvent`-based and unchanged by this work.
- `48_presence.md` + `48_presence_local.md`: `EntityType` enum is the authority for pin `entity_type`; presence/`exclude_viewing` unchanged.

Primary domain contract (trigger: "notifications"):
- `47_notifications.md`: **central**. `NotificationPin` model, the `notification_targets.py` resolver pattern (pins are one independent `set[str]` source unioned via `asyncio.gather`), `pin_notification` validates `entity_type` against `EntityType`, commands never write inline target queries, `CREATE_NOTIFICATIONS` is the only notification-row entry point.

Goal bundle (CRUD + realtime → relevant subset):
- `03_models.md`: adding the `conditions` column to `NotificationPin`.
- `08_domain.md`: the condition registry, matcher, and validator are pure domain logic.
- `30_migrations.md`: nullable-column migration procedure.
- `15_testing.md`: matcher/validator unit tests, resolver integration tests.

### Local extensions loaded

- `06_commands_local.md`: `maybe_begin`, session-call safety, subordinate-command event rule.
- `07_queries_local.md`: offset pagination (not exercised here; loaded per always-both rule).
- `42_event_local.md`, `48_presence_local.md`: read; no deltas affecting this work.
- `47_notifications_local.md`: present but an **empty stub** — no local notification deltas. This plan adds nothing to it; the `conditions` field is a canonical-shaped extension. If conditions should become a documented app field, record it here in a follow-up (see Risks).

### Excluded contracts

- `11_infra_events.md`, `13_sockets.md`, `56_realtime_layer.md`: no socket/event-shape change — notification delivery path is untouched.
- `16_background_jobs.md`, `51_worker_runtime.md`, `12_infra_redis.md`: workers and presence/Redis unchanged; resolution is command-side.
- `28_roles_permissions.md`: no role/permission change; manager source query is reused verbatim.

### File read intent — pattern vs. relational

- Permitted (relational, already done): `notification_pin.py`, the three audience resolvers, `transition_step_state.py`, `pin_notification.py`, `create_notifications.py`, `EntityType`, `TaskStepStateEnum` / `ItemUpholsteryRequirementStateEnum` / `TaskStateEnum` — to learn exact field names, current pin queries, and state values.
- Prohibited (pattern reads — use contracts): another command's session/flush/error shape → `06_commands.md`; another resolver's structure → `47_notifications.md`; serializer shape → `46_serialization.md`.

### Skill selection

- Primary skill: backend command + domain modification (model → migration → domain → command → resolver wiring).
- Router trigger terms: notification, pin, condition, state, registry, audience.
- Excluded alternatives: worker/job skills — workers are not touched.

## Implementation plan

### Step 1 — Extend `EntityType`
File: `domain/presence/enums.py`. Add `TASK = "task"`, `TASK_STEP = "task_step"`, `ITEM_UPHOLSTERY = "item_upholstery"` (values must equal the strings the pins already store, so existing rows keep validating). This makes `pin_notification`'s contract-mandated `EntityType` validation real for these domains.

### Step 2 — Model columns
File: `models/tables/notifications/notification_pin.py`. Add two columns:
```python
from sqlalchemy import JSON, Boolean

conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
fire_once:  Mapped[bool]         = mapped_column(Boolean, nullable=False, default=False, server_default="false")
```
Use the JSON/JSONB type consistent with other JSON columns in the codebase (verify which the project uses — relational read of an existing JSON column). `conditions = NULL` = match all (unconditional). `fire_once = False` = permanent pin. The existing `uq_notification_pin_user_entity` unique constraint is unchanged — identity is still `(user_id, entity_type, entity_client_id)`; both new fields are mutable payload, not identity.

### Step 3 — Migration
Per `30_migrations.md`: autogenerate, then hand-verify it contains exactly two `add_column` statements on `notification_pins`:
```python
sa.Column('conditions', sa.JSON(), nullable=True)
sa.Column('fire_once',  sa.Boolean(), nullable=False, server_default='false')
```
Downgrade: two matching `drop_column` calls. No backfill — `conditions` is nullable; `fire_once` gets its `server_default` of `false` applied to all existing rows by Postgres on `ALTER TABLE`.

### Step 4 — Condition registry + matcher + validator
New file: `domain/notifications/pin_conditions.py`. Pure domain, no SQL.

- `PIN_ENTITY_STATE_ENUMS: dict[str, type[Enum]]` mapping `EntityType.TASK_STEP → TaskStepStateEnum`, `EntityType.ITEM_UPHOLSTERY → ItemUpholsteryRequirementStateEnum`, `EntityType.TASK → TaskStateEnum`.
- A condition-type handler structure. Each handler declares: the `event_facts` key it reads, the supported ops, and `validate(entity_type, cond)` + `evaluate(cond, facts) -> bool`.
  - `state` handler: reads `facts["state"]`; ops `in`, `eq`, `not_in`; validates every `value` member is a legal value of the entity's state enum.
  - `time` handler: **registered but stubbed** — `validate` accepts a documented shape; `evaluate` may `raise NotImplementedError`. Exists to lock the extension surface (AC 7).
- `PIN_CONDITION_REGISTRY: dict[str, Handler]` keyed by condition `type`.
- `validate_pin_conditions(entity_type: str, conditions: list[dict] | None) -> None`: `None`/`[]` ⇒ ok; else each cond must have a known `type`, a supported `op`, and pass the handler's `validate`. Raise `ValidationError` otherwise.
- `pin_conditions_match(conditions: list[dict] | None, event_facts: dict) -> bool`: `None`/`[]` ⇒ `True`; else **all** conditions must pass (AND semantics — single match mode for now; a `match: any` toggle is a future extension, not built).

### Step 5 — Condition-aware pin source
New file: `domain/notifications/pinned_subscribers.py`:
```python
async def resolve_pinned_subscribers(
    session, entity_type: str, entity_client_id: str, event_facts: dict,
) -> set[str]:
    rows = (await session.execute(
        select(
            NotificationPin.client_id,
            NotificationPin.user_id,
            NotificationPin.conditions,
            NotificationPin.fire_once,
        ).where(
            NotificationPin.entity_type == entity_type,
            NotificationPin.entity_client_id == entity_client_id,
        )
    )).all()

    matched_user_ids: set[str] = set()
    fire_once_pin_ids: list[str] = []

    for pin_id, user_id, conditions, fire_once in rows:
        if pin_conditions_match(conditions, event_facts):
            matched_user_ids.add(user_id)
            if fire_once:
                fire_once_pin_ids.append(pin_id)

    if fire_once_pin_ids:
        await session.execute(
            delete(NotificationPin).where(
                NotificationPin.client_id.in_(fire_once_pin_ids)
            )
        )
        # No explicit flush needed — the enclosing command transaction will flush
        # and commit atomically, so the DELETE and the CREATE_NOTIFICATIONS enqueue
        # land in the same commit. The pin is gone before the worker runs.

    return matched_user_ids
```
This is the one place pins are read for notification purposes. Fire-once deletion happens here because:
1. The session is the command's write session — deletion is safe within the transaction.
2. The `CREATE_NOTIFICATIONS` task is enqueued in the same commit, so "pin deleted" and "notification queued" are atomic.
3. The public return type stays `set[str]` — the 47 resolver contract is unchanged.

**Fire-once delivery guarantee:** the pin is deleted at "notification enqueued," not at "notification delivered to device." If the VAPID push subsequently fails, the pin is already gone. This is intentional — `fire_once` means "stop watching after this event fires," not "guarantee delivery before deletion." Document this clearly in `47_notifications_local.md`.

### Step 6 — `pin_notification` command + request parser
- New `parse_pin_notification_request` (in a `notifications/requests.py`, matching the `parse_*_request` convention): fields `entity_type: str`, `entity_client_id: str`, `conditions: list[dict] | None = None`, `fire_once: bool = False`.
- In `pin_notification`: validate `entity_type` against `EntityType` (now real), call `validate_pin_conditions(entity_type, conditions)`, then upsert. On the existing-row branch, **set `pin.conditions = conditions` and `pin.fire_once = fire_once`** (last-write-wins on both — subject to the open clarification) instead of the current no-op. Return shape unchanged: `{"pin": {"client_id": ...}}`.

### Step 7 — Create domain `notification_targets.py` modules
Per contract 47 each domain owns a single `notification_targets.py` module in `domain/<entity>/`. Each public resolver unions independent `set[str]` sources via `asyncio.gather` and returns the union minus `actor_id`. Sources passed as private functions.

**`domain/task_steps/notification_targets.py`**
```python
async def resolve_task_step_notification_targets(
    session, step_client_id: str, actor_id: str, event_facts: dict,
) -> set[str]:
    sources = await asyncio.gather(
        _get_pinned_subscribers(session, step_client_id, event_facts),
    )
    targets = set().union(*sources)
    targets.discard(actor_id)
    return targets

async def _get_pinned_subscribers(session, step_client_id, event_facts) -> set[str]:
    return await resolve_pinned_subscribers(
        session, EntityType.TASK_STEP, step_client_id, event_facts,
    )
```
Task steps have no unconditional manager source today — only pins. Keep it symmetric with the 47 pattern for future extension.

**`domain/tasks/notification_targets.py`**
Replaces `services/commands/tasks/_notification_helpers._resolve_task_audience`. Three sources unioned:
1. `_get_managers(session, workspace_id)` — active manager-role workspace members (unconditional).
2. `_get_task_creator(task_created_by_id)` — returns `{task_created_by_id}` if set, else `set()` (unconditional).
3. `_get_pinned_subscribers(session, task_client_id, event_facts)` — conditional via `resolve_pinned_subscribers`.

```python
async def resolve_task_notification_targets(
    session, workspace_id: str, task_client_id: str,
    task_created_by_id: str | None, actor_id: str, event_facts: dict,
) -> set[str]:
    sources = await asyncio.gather(
        _get_managers(session, workspace_id),
        _get_task_creator(task_created_by_id),
        _get_pinned_subscribers(session, task_client_id, event_facts),
    )
    targets = set().union(*sources)
    targets.discard(actor_id)
    return targets
```

**`domain/items/notification_targets.py`**
Replaces `services/commands/items/_notification_helpers._resolve_upholstery_audience`. Two sources:
1. `_get_managers(session, workspace_id)` — unconditional.
2. For each upholstery id: `resolve_pinned_subscribers(session, EntityType.ITEM_UPHOLSTERY, uph_id, event_facts)` — unioned across all ids.

```python
async def resolve_upholstery_notification_targets(
    session, workspace_id: str, item_upholstery_ids: list[str],
    actor_id: str, event_facts: dict,
) -> set[str]:
    pin_sources = [
        _get_pinned_subscribers(session, uph_id, event_facts)
        for uph_id in item_upholstery_ids
    ]
    sources = await asyncio.gather(
        _get_managers(session, workspace_id),
        *pin_sources,
    )
    targets = set().union(*sources)
    targets.discard(actor_id)
    return targets
```

### Step 8 — Wire call sites to domain resolvers; delete old helpers
Each command imports from the domain module instead of the helper. Each passes the concrete `event_facts` dict carrying the state the operation produces.

**`transition_step_state.py` (lines 334–357):** replace the inline `NotificationPin` query and `user_ids` assembly with:
```python
step_pin_user_ids = list(await resolve_task_step_notification_targets(
    ctx.session, step.client_id, ctx.user_id, {"state": request.new_state.value},
))
```
Feed `step_pin_user_ids` (unchanged name) into the existing `CREATE_NOTIFICATIONS` enqueue block.

**`cancel_task.py`, `fail_task.py`, `resolve_task.py`:** replace `await _resolve_task_audience(session, workspace_id, task.client_id, task.created_by_id, ctx.user_id)` with:
```python
notify_ids = list(await resolve_task_notification_targets(
    ctx.session, ctx.workspace_id, task.client_id,
    task.created_by_id, ctx.user_id,
    {"state": task.state.value},   # task.state already set to terminal value before this call
))
```

**`mark_requirements_ordered.py`, `mark_requirements_completed.py`, `mark_requirements_in_use.py`, `receive_upholstery_order.py`, `resolve_requirements_after_stock.py`, `create_upholstery_order.py`:** replace `await _resolve_upholstery_audience(session, workspace_id, upholstery_ids, actor_id)` with:
```python
notify_ids = list(await resolve_upholstery_notification_targets(
    ctx.session, ctx.workspace_id, upholstery_ids, ctx.user_id,
    {"state": "<target_state_value>"},   # concrete value differs per command
))
```

**Delete:**
- `services/commands/tasks/_notification_helpers.py`
- `services/commands/items/_notification_helpers.py`

`assign_worker_to_step.py` is **not touched** — it sends `task_step_assigned` directly to the assigned worker's user_id, not through any pin/audience resolver.

### Step 9 — Tests
- Unit: `pin_conditions_match` truth table (NULL, empty, single `in`, `eq`, `not_in`, multi-AND, miss); `validate_pin_conditions` rejects unknown type/op and cross-entity illegal state (`paused` on upholstery); `time` stub validates shape but `evaluate` raises.
- Unit: each domain `notification_targets` resolver — mock session, assert unconditional sources (managers, creator) always appear regardless of conditions; assert conditioned pin only appears when condition matches.
- Integration: pin a step with `state in [completed, paused]`; drive a `working` transition → no notification; drive `completed` → notification. Re-pin with new conditions → row updated. Manager still notified on a conditioned task pin.
- Deletion check: `grep -r "_notification_helpers"` in `services/commands/` returns empty — no stale imports.

## Risks and mitigations

- Risk: Six commands import `_resolve_upholstery_audience` and three import `_resolve_task_audience`; missing any import when deleting the helpers will cause a runtime `ImportError`.
  Mitigation: Step 8 ends with a `grep -r "_notification_helpers"` sweep; CI import checks catch any missed reference before merge.
- Risk: `EntityType` previously excluded `task`/`task_step`/`item_upholstery`, so `pin_notification` was not truly validating them.
  Mitigation: Step 1 adds them with values equal to the stored strings — existing rows keep validating; no data migration.
- Risk: A conditioned pin could silently swallow notifications if a command forgets to pass `state` in `event_facts` (missing key → `state` handler sees `None` → no match).
  Mitigation: `state` handler treats a missing fact key as a hard mismatch **and** the registry exposes the required fact keys; add a test asserting each wired call site supplies them. Consider logging at debug when a referenced fact key is absent.
- Risk: `fire_once` pin is deleted at "enqueued," not at "delivered." If the VAPID push worker subsequently fails (stale subscription, network error), the user never receives the push and cannot re-subscribe because the pin is gone.
  Mitigation: This is a documented trade-off, not a bug — `fire_once` means "stop watching after this event fires." The `Notification` DB row is still created, so the user sees it in-app on next load via `list_notifications`. Document the semantic in `47_notifications_local.md` so the API contract is explicit to callers.
- Risk: A fire-once pin on an entity that fires multiple rapid events in the same millisecond could be matched by two concurrent command transactions, causing a double-delete (which is harmless) but also a double-notification.
  Mitigation: The `uq_notification_pin_user_entity` unique constraint on the table serialises upserts; concurrent deletes of the same row are idempotent in Postgres. Double-notification is possible only under extreme concurrency and is acceptable for the current use case. If it becomes a problem, a DB-level advisory lock or a `DELETE ... RETURNING` pattern can prevent it.
- Risk: Re-pin semantics (overwrite vs. reject) is unconfirmed.
  Mitigation: Open clarification gates Step 6's conflict branch; default assumption (overwrite) documented in AC 5.
- Risk: `47_notifications_local.md` is an empty stub; adding `conditions` is a canonical-shaped extension not yet documented as a local delta.
  Mitigation: After approval, record the `conditions` field and the condition-registry decision in `47_notifications_local.md` per the local-extension protocol (canonical stays unmodified).

## Validation plan

- `alembic upgrade head` then `downgrade -1`: column adds and drops cleanly; no other diff.
- `pytest` on the new domain unit tests: matcher + validator truth tables pass; `time` stub raises on evaluate.
- Integration test described in Step 8: conditioned step pin notifies on `completed`/`paused` only; unconditional manager source unaffected.
- Manual: pin a step with `{"type":"state","op":"in","value":["completed"]}`, complete it → in-app + VAPID push arrives; pause a *different* unconditioned pinned step → still arrives; transition the conditioned step to `working` → no push.
- Regression: existing pins (NULL conditions) on a case still notify on `case:message` exactly as before.
- Fire-once integration: create a `fire_once=True` pin on a step, trigger a matching transition, query `notification_pins` → row is gone; trigger again → no notification (pin was removed).
- Fire-once negative: create a `fire_once=False` pin, trigger twice → two notifications, pin still present after both.
- `grep -r "_notification_helpers" backend/app/beyo_manager/services/commands/` → zero results; files deleted and no stale imports.
- `grep -r "notification_targets" backend/app/beyo_manager/domain/` → three modules present (`task_steps/`, `tasks/`, `items/`).

## Review log

- `2026-06-19` user: design agreed — scope = entity target (no ancestry/wildcard); conditions = reusable registry-driven predicates; `state` shipped, `time` as extensibility example.
- `2026-06-19` user: fold audience-resolver relocation into this plan — `_notification_helpers.py` files to be deleted, domain `notification_targets.py` modules to be created per contract 47.
- `2026-06-19` user: add `fire_once` support — `fire_once` boolean column on `NotificationPin`; pin self-deletes within the same transaction when conditions match and `fire_once=True`; deletion is at enqueue-time not delivery-time (documented trade-off).

## Lifecycle transition

- Current state: `archived`
- Next state: _none_
- Transition owner: `codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_pin_notification_conditions_20260619.md`
- Archive record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_pin_notification_conditions_20260619.md`
