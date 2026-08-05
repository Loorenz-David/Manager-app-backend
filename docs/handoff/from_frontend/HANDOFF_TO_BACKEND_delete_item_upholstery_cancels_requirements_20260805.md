# HANDOFF_TO_BACKEND_delete_item_upholstery_cancels_requirements_20260805

## Metadata

- Handoff ID: `HANDOFF_TO_BACKEND_delete_item_upholstery_cancels_requirements_20260805`
- Created at (UTC): `2026-08-05T00:00:00Z`
- Owner agent: `claude-opus-5`
- Source frontend plan: `docs/architecture/under_construction/implementation/PLAN_item_can_have_upholstery_none_field_20260805.md`
- Related backend handoff: `docs/handoff/from_backend/HANDOFF_TO_FRONTEND_item_can_have_upholstery_flag_20260805.md`

## Request to backend

- **Required backend behavior:** `DELETE /api/v1/item-upholsteries/{client_id}` must cancel the row's
  unfinished `ItemUpholsteryRequirement`s — reversing their inventory projections — before soft-deleting
  the `ItemUpholstery`. Today it soft-deletes the link and leaves the requirements untouched, so their
  reserved meters are never returned to the inventory.
- **User-facing impact:** a manager who removes an upholstery from an item silently leaks inventory.
  The upholstery keeps counting as "in need" (or stays deducted as "in use") against its
  `UpholsteryInventory` forever, with no item or task left pointing at it. Ordering decisions made from
  those numbers over-order fabric.
- **Desired timeline:** before the frontend's new "None / No upholstery" control ships on
  `TaskDetailSlidePage` — removing an upholstery is the *required first step* of that flow, so this
  path is about to go from rarely used to routinely used.

## The gap

Three call sites end a requirement's life. Two of them cancel; the delete path does not.

| Path | Requirement handling | Location |
|---|---|---|
| Swap — `PATCH /api/v1/item-upholsteries/{id}` with a new `upholstery_id` | loads the active requirement, refuses if `COMPLETED` (`ConflictError`), calls `cancel_requirements_in_session`, then creates the replacement requirement | `services/commands/items/update_and_delete_item_upholstery.py:145-190` |
| Delete task | `cancel_unfinished_item_requirements_in_session` over the task's items | `services/commands/tasks/delete_task.py:16` |
| **Delete link — `DELETE /api/v1/item-upholsteries/{id}`** | **none** — sets `is_deleted/deleted_at/deleted_by_id`, writes a history record, dispatches `item:updated` + `item:upholstery-deleted`, returns | `services/commands/items/update_and_delete_item_upholstery.py:247-300` |

The swap path gets away with cancelling because it immediately re-creates a requirement for the new
upholstery. Delete has no such successor, so nothing reverses `adjust_need` /
`rollback_in_use_to_stored`.

### Concrete leak

1. Item has an `ItemUpholstery` whose active requirement is `ordered`, `amount_meters = 6.0`, against
   `upholstery_inventory_id = X`. `X.current_amount_in_need_meters` includes those 6.0 m.
2. Manager removes the upholstery from the item → `DELETE /api/v1/item-upholsteries/{id}` → 200.
3. The `ItemUpholstery` is soft-deleted. The requirement row stays `ordered` and is still referenced by
   `X`'s projections. `X` reports 6.0 m of demand that no item, task or person is waiting for, and
   `computeAvailableUpholsteryMeters` (frontend) subtracts it from what the picker shows as available.
4. Nothing in the product can ever clear it — the requirement is only reachable through the
   `ItemUpholstery` that no longer exists.

The `in_use` variant is worse: those meters were deducted from stored stock and never roll back.

## Expected backend deliverables

1. In `delete_item_upholstery` (`services/commands/items/update_and_delete_item_upholstery.py:247`),
   inside the same `maybe_begin(ctx.session)` block and **before** the soft delete, load the row's
   unfinished requirements and pass them to the existing
   `cancel_requirements_in_session(session=..., workspace_id=..., requirements=[...], actor_id=ctx.user_id, now=...)`.
   Reuse the helper — do not re-implement the inventory reversal; `cancel_requirements_in_session`
   already skips anything not in `UNFINISHED_REQUIREMENT_STATES` and handles the
   `DEMAND_REQUIREMENT_STATES` vs `IN_USE` split.
2. Decide and document the `COMPLETED` case (see clarification below).
3. Keep the response shape as-is (`{ }` inside the standard envelope) — the frontend does not read the
   body of this call.
4. Keep the dispatched events as-is (`item:updated`, `item:upholstery-deleted`). If cancelling a
   requirement normally emits its own event elsewhere, emit it here too so inventory screens refresh;
   otherwise the frontend will rely on `item:upholstery-deleted` alone (see socket note below).
5. Suggested test: create an item upholstery with an `ordered` requirement against an inventory row,
   record `current_amount_in_need_meters`, `DELETE` the link, assert the requirement is `failed` and the
   inventory need is back to its pre-requirement value. Repeat for `in_use` asserting
   `current_stored_amount_meters` is restored.

## Clarifications required

- [ ] **`COMPLETED` requirements.** The swap path raises
      `ConflictError("Cannot swap upholstery after requirement completion.")`. Should delete do the
      same (409, and the frontend keeps the field disabled as it already does for `completed`), or
      should it allow the delete and leave the completed requirement historically intact? Frontend
      preference: **409**, consistent with swap — a completed requirement means the fabric was
      physically consumed, and that record should not be detachable from the item.
- [ ] **Should the delete also be blocked (or warned) for `ordered`?** Cancelling an `ordered`
      requirement means fabric may already be on its way from a supplier. Backend's call — the frontend
      can surface a confirmation step if you want one, just say so and we'll add it.

## Interface expectations

- Endpoint: `DELETE /api/v1/item-upholsteries/{client_id}` — no signature change requested.
- Request shape: unchanged.
- Response shape: unchanged (`build_ok({})`).
- Error cases: existing `404 NotFound` when the link is missing; **possibly** a new `409 ConflictError`
  for the `COMPLETED` case, pending the clarification above. The frontend will treat any 4xx here as
  "removal refused" and leave the field on its current selection.
- Socket events: unchanged (`item:updated`, `item:upholstery-deleted`). Note the frontend already
  invalidates the pending-upholstery queue and item-upholstery queries from these.

## Frontend context

- **Why the frontend needs this:** the new `can_have_upholstery` control (backend handoff
  `HANDOFF_TO_FRONTEND_item_can_have_upholstery_flag_20260805.md`) renders a "None" option only while
  the item has no upholstery linked. Marking an item as "no upholstery" therefore *requires* removing
  the linked upholstery first — deliberately, so the inventory release happens before the flag flips.
  That release is the behavior this handoff asks for; without it the intended-clean flow is the one
  that leaks.
- **Blocked frontend work:** the detail-page half of
  `PLAN_item_can_have_upholstery_none_field_20260805.md` (clarification 6, step 13). The
  task-creation-form half is unaffected and can ship independently — no requirement exists at submit
  time there.
- This is a pre-existing bug, not a regression introduced by the flag work. It is only being surfaced
  now because the new flow makes deletion a routine action instead of a rare one.
