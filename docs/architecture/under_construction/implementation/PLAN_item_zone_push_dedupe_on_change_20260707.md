# PLAN_item_zone_push_dedupe_on_change_20260707

## Metadata

- Plan ID: `PLAN_item_zone_push_dedupe_on_change_20260707`
- Status: `under_construction`
- Owner agent: `claude`
- Created at (UTC): `2026-07-07T00:00:00Z`
- Last updated at (UTC): `2026-07-07T00:00:00Z`
- Related issue/ticket: `N/A`
- Corrects: `PLAN_item_zone_location_sync_side_effect_20260706` (already implemented) — review findings: #2 (push fires when unchanged), #4 (double item load), #5 (trigger-condition consistency), #6 (no audit on enqueue).

## Goal and intent

- Goal: Apply the accepted review corrections to the item-zone → location-tracker side effect:
  1. **Dedupe (#2):** enqueue a push only when `item_zone` actually **changes** to a non-empty value on the item update paths (create paths already represent a change from nothing).
  2. **Avoid double load (#4):** let `_update_item_in_session` accept an already-loaded `Item` so post-handling does not re-query the primary item.
  3. **Trigger consistency (#5):** normalize all four call-site guards to reason about the stripped zone value.
  4. **Audit (#6):** write one audit record when a push is enqueued, mirroring the email-enqueue audit pattern.
- Business/user intent: fewer redundant outbound PATCH calls / execution tasks, one less redundant DB query per post-handling completion, consistent trigger logic, and an audit trail for outbound zone pushes.
- Non-goals:
  - No change to accepted note #1 (post-handling depending on a live task instance) or #3 (the item `history` record from reusing `_update_item_in_session`).
  - No change to the payload shape, job type, worker, client, socket/domain events, or DB schema/migration.

## Scope

- In scope:
  1. `services/commands/items/update_item.py` (`_update_item_in_session`): old-vs-new zone gate on enqueue; add optional pre-loaded `item` parameter.
  2. `services/commands/items/find_or_create_item.py`: update branch old-vs-new gate; normalize create-branch guard.
  3. `services/commands/items/create_item.py`: normalize create guard.
  4. `services/commands/task_post_handling/complete_task_post_handling.py`: pass the already-loaded `primary_item` into `_update_item_in_session` (uses #2's optional param).
  5. `services/commands/location_tracker/enqueue_item_zone_push.py`: write an audit record after a successful enqueue.
  6. Tests.
- Out of scope: the helper's skip logic, the client, the payload, the worker, and any create-path *enqueue trigger* semantics (create still enqueues for a new non-empty zone).
- Assumptions:
  - Zone comparison is normalized: `(value or "").strip()`; whitespace-only differences are not changes.
  - `_load_primary_item` already filters `workspace_id` + `is_deleted`, so an item it returns is safe to pass into the core without re-validation.

## Clarifications required

- [x] Change detection — RESOLVED: compare old vs new (requester).
- [x] Notes #1 and #3 — RESOLVED: accepted as intended; no code change.
- [x] Notes #4, #5, #6 — RESOLVED: include all (requester: "add also the minor / optional").

## Acceptance criteria

1. **Dedupe:** in `_update_item_in_session`, the old zone is captured **before** the `_DIRECT_FIELDS` setattr loop; the push is enqueued **iff** `"item_zone" in request.model_fields_set` **and** `normalized(new_zone) != normalized(old_zone)`. Same gate in `find_or_create_item`'s update branch on `existing`.
2. Updating an item with the **same** (or whitespace-only-different) `item_zone` enqueues **no** task; changing it to a different non-empty value enqueues exactly one. Create paths still enqueue for a new non-empty zone.
3. **No double load:** `_update_item_in_session` accepts an optional `item: Item | None = None`; when provided it uses it and skips the `SELECT`. `update_item(ctx)` calls it without the arg (loads as today); `complete_task_post_handling` passes the `primary_item` it already loaded. Post-handling performs **one** item `SELECT` total (in `_load_primary_item`).
4. **Consistency:** the create-path guards in `create_item.py` and `find_or_create_item.py` are `if (item.item_zone or "").strip():`, matching the normalized comparison used on the update paths.
5. **Audit:** on a successful enqueue, `enqueue_item_zone_location_push` writes one audit entry via `write_audit(...)` in the same transaction — `event="location_tracker.item_zone_push_enqueued"`, `resource_type="item"`, `resource_client_id=item.client_id`, `actor_user_id=requested_by_user_id`, `workspace_id=item.workspace_id`, `detail={position, article_number, sku, task_client_id}`. No audit is written on the skip paths (no zone / no target).
6. **Event/update behavior unchanged:** a no-op `item_zone` update still runs the normal update (`updated_at`, history, returns `item:updated`); only the enqueue (and now the audit) are gated on an actual change.
7. Existing tests pass; new tests cover: no-change → no enqueue/no audit; changed → one enqueue + one audit; post-handling passes the loaded item and does not re-query; unchanged effective zone in post-handling → no enqueue.

## Contracts and skills

Resolution per `task_system/backend_contract_goal_mapping_guide.md`. Contracts in `backend/architecture/`.

### Contracts loaded

- `architecture/01_architecture.md`: layering.
- `architecture/04_context.md`: `ServiceContext`/session threading into `write_audit`.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: command structure, `maybe_begin`, subordinate event rule (the core still returns events; the enqueue/audit are gated). Unchanged contract, confirmed intact.
- `architecture/16_background_jobs.md`: the gated `create_instant_task` enqueue.
- `architecture/36_audit_log.md`: the `write_audit` call for the outbound push (mirrors `email.batch_send_enqueued`).
- `architecture/21_naming_conventions.md`: variable/event naming (`location_tracker.item_zone_push_enqueued`).
- `architecture/15_testing.md`: unit tests.

### Local extensions loaded

- `architecture/06_commands_local.md` — `maybe_begin` + subordinate event rule (baseline `06_commands.md`). Loaded to confirm the event-return contract stays intact and `write_audit` runs inside the owning transaction (never commits itself).

### Excluded contracts

- `03_models`, `30_migrations`, `46_serialization`, `11_infra_events`, `13_sockets`, `19_integrations` — no schema, serializer, event-shape, socket, or transport change.

### File read intent — pattern vs. relational

Relational reads already performed: `update_item.py`, `find_or_create_item.py`, `create_item.py`, `complete_task_post_handling.py`, `enqueue_item_zone_push.py`, and `services/infra/audit/write_audit.py` (audit signature, transaction semantics, precedent `email.batch_send_enqueued`). No pattern reads needed.

### Skill selection

- Primary skill: `N/A` (small, localized command edits).
- Router trigger terms: `enqueue gate, change detection, audit log, item_zone`.

## Implementation plan

1. `enqueue_item_zone_push.py`: capture the returned task and add an audit write after `create_instant_task`:
   ```python
   task = await create_instant_task(session=session, task_type=TaskType.LOCATION_TRACKER_PUSH_LOCATIONS, payload=..., max_try=3)
   await write_audit(
       session=session,
       event="location_tracker.item_zone_push_enqueued",
       workspace_id=item.workspace_id,
       actor_user_id=requested_by_user_id,
       resource_type="item",
       resource_client_id=item.client_id,
       detail={"position": zone, "article_number": item.article_number, "sku": item.sku, "task_client_id": task.client_id},
   )
   return True
   ```
   (Skip paths return `False` without auditing.)
2. `update_item.py` → `_update_item_in_session`:
   - Add optional param `item: Item | None = None`. If `None`, run the existing `SELECT` (+ `NotFound`); if provided, use it directly.
   - Capture `old_item_zone = (item.item_zone or "").strip()` **before** the `_DIRECT_FIELDS` loop.
   - After mutation: `new_item_zone = (item.item_zone or "").strip()`; enqueue only `if "item_zone" in request.model_fields_set and new_item_zone != old_item_zone:`.
   - `update_item(ctx)` wrapper unchanged (calls the core without `item=`).
3. `find_or_create_item.py`:
   - Update branch: capture `old_item_zone = (existing.item_zone or "").strip()` before the `_DIRECT_FIELDS` loop; gate the enqueue on `"item_zone" in request.model_fields_set and (existing.item_zone or "").strip() != old_item_zone`.
   - Create branch: change guard to `if (item.item_zone or "").strip():`.
4. `create_item.py`: change guard to `if (item.item_zone or "").strip():`.
5. `complete_task_post_handling.py`: pass `item=primary_item` into `_update_item_in_session(...)` (remove the core's re-query for this path). No other change.
6. Tests (`tests/tasks/test_item_zone_location_sync.py`):
   - `_update_item_in_session`: same zone → helper not called; different zone → called once (existing).
   - `find_or_create_item` update branch: unchanged zone → no enqueue.
   - Helper: on enqueue, asserts `write_audit` called with the expected event/resource/detail; on skip, `write_audit` not called (monkeypatch `write_audit` + `create_instant_task`).
   - Post-handling: assert `_update_item_in_session` receives `item=primary_item` and that only `_load_primary_item` performs a SELECT for the item; unchanged effective zone → no enqueue (real core, monkeypatch only the helper).

## Risks and mitigations

- Risk: capturing old zone **after** the setattr loop → never enqueues.
  Mitigation: Acceptance #1 requires capture before the loop; changed-value test guards it.
- Risk: passing a stale/mismatched `item` into the core (client_id ≠ request.client_id).
  Mitigation: post-handling builds `UpdateItemRequest(client_id=primary_item.client_id, ...)`; the passed item and request client_id always match. Optionally assert equality in the core.
- Risk: `write_audit` inside the helper double-audits if the helper is somehow called twice.
  Mitigation: the dedupe gate ensures at most one enqueue per actual change; audit is one-per-enqueue by construction.
- Risk: audit write failing/raising aborts the item write.
  Mitigation: `write_audit` runs in the same transaction by design (consistent with `email.batch_send_enqueued`); a failure should roll back the whole unit — acceptable and consistent with existing audited enqueues.
- Risk: over-scoping into create-path enqueue semantics.
  Mitigation: create paths keep enqueuing for a new non-empty zone; only the guard expression is normalized (cosmetic).

## Validation plan

- `pytest tests/tasks/test_item_zone_location_sync.py`: all pass, including new no-enqueue/no-audit and audit-on-enqueue cases.
- Reasoning trace: update same zone → 0 tasks/0 audits; update different zone → 1 task/1 audit; new item with zone → 1 task/1 audit; post-handling unchanged effective zone → 0 tasks, completion + `item:updated` still emitted; post-handling with change → 1 SELECT for the item (no double load) + 1 task + 1 audit.
- Grep check: changes limited to the five listed files; helper/client/worker/job untouched otherwise.

## Review log

- `2026-07-07` `owner`: scoped to accepted review notes — #2 (dedupe), #4 (double load), #5 (guard consistency), #6 (audit). Notes #1 and #3 accepted as intended, no code change.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `claude`
