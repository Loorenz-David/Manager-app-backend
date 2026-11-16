# PLAN_edit_upholstery_order_amount_20261116

## Metadata

- Plan ID: `PLAN_edit_upholstery_order_amount_20261116`
- Status: `implemented` (2026-11-16, uncommitted) — owner approved C1–C5 as proposed
- Created at (UTC): `2026-11-16`
- Related: PRE-ORDER 29 incident fix (`settle_finished_task_upholstery`, same uncommitted tree)
- Repos touched: backend (`backend/app`), frontend (`managers-app`, `packages/realtime`)

## Goal and intent

- **Goal:** a manager can change the ordered amount (meters) of an existing upholstery
  order, and every requirement / inventory number follows as if the order had been
  placed with the new amount.
- **User intent:** today an order is frozen once created. A typo (15 m instead of 1.5 m)
  or a supplier delivering a different length leaves the inventory's "ordered" total and
  the items' `ordered` / `needs_ordering` states wrong, with no way to fix it in the app.
- **Non-goals:**
  - Changing *which* fabric was ordered (see C1).
  - Editing price, supplier, or the expected-receive date (they can join the same
    endpoint later).
  - Cancelling an order (a separate, already-missing command).

## Clarifications required

- [x] **C1 — "change the ordered upholstery" means the amount, not the fabric.** The plan
  assumes the input edits `order_amount_meters`. Switching an order to a different fabric
  is a different operation: move ordered meters between two inventories and re-allocate
  both. Confirm.
- [x] **C2 — Which order states are editable.** Proposed: `ordered` and
  `partially_received`. `received`, `cancelled` and `failed` are refused (the order is
  closed). `draft`, `pending` and `approved` aren't counted in inventory today, so for
  them only the field changes, with no recalculation.
- [x] **C3 — Lowering to exactly what was already received.** For a `partially_received`
  order, setting the amount equal to `received_amount_meters` closes it. Proposed: allow
  it, and the order becomes `received`. Lowering below the received amount is always
  refused.
- [x] **C4 — Notify on demotion?** Creating an order notifies "Requirements ordered" for
  newly covered items. When a decrease pushes items back to `needs_ordering`, proposed:
  send a mirror notification ("Order reduced: N item(s) need ordering again") to the same
  targets.
- [x] **C5 — Priority on increase.** Create and receive accept
  `priority_item_upholstery_ids`. Proposed: the edit doesn't (the input sheet has no item
  picker), so extra meters go to the earliest-due `needs_ordering` items, the same
  default order create uses.

## How the existing system works (what this plan builds on)

- `ItemUpholsteryRequirement.state = ordered` is **pooled per inventory**, not tied to an
  order: no requirement references an `upholstery_orders` row. Coverage is
  `inventory.current_amount_ordered_meters` + stored.
- **Allocation invariant** (`_pooled_requirement_allocation.calculate_pooled_requirement_pool`,
  mode `"ordered"`):
  `sum(ORDERED) ≤ stored + ordered − sum(AVAILABLE)`.
  - `create_upholstery_order._allocate_requirements` promotes `needs_ordering → ordered`
    while that holds: priority ids first, then earliest `ready_by_at`, skip-and-continue.
- **Reverse direction already exists for stored stock**:
  `set_current_stored_amount_inventory` runs *demote then re-promote* inside one
  transaction:
  - `_demote_available_requirements` demotes latest-due first (`_demotion_sort_key`);
  - `_promote_forward_requirements` re-promotes;
  - a `RequirementStateTracker` records the net transitions on the ledger.
- `receive_upholstery_order` moves meters ordered → stored (`confirm_ordered_to_stock`)
  and caps the cumulative received amount at `order_amount_meters`.

The edit is the ordered-side twin of `set_current_stored_amount_inventory`.

## Design

### Backend

1. **Command** `services/commands/upholstery/update_upholstery_order_amount.py`
   (`update_upholstery_order_amount(ctx)`), in one transaction. In order:
   1. **Validate the request.** `order_amount_meters > 0`, 3 decimal places.
   2. **Lock the order.** Load it `FOR UPDATE`; 404 if missing, deleted or in another
      workspace. Then lock the inventory with `load_inventory_for_update`. That's the
      same order→inventory sequence receive should use (see 6).
   3. **Check the state.** Refuse closed states (C2). If
      `new < received_amount_meters`, refuse (422): "Can't be less than the
      X m already received".
   4. **No-op check.** If `new == order_amount_meters`, return `{}` without writing,
      the same as the stored-amount command.
   5. **Apply the change.** Compute `delta = new − old` and set `order_amount_meters`.
      If `new == received` → state `received` and stamp `received_at` (C3).
   6. **Counted states only** (`ordered` / `partially_received`):
      - **Inventory mutation** `adjust_ordered(session, ws, inv_id, delta, *, movement)`
        in `_inventory_mutations.py`. It adds `delta` to
        `current_amount_ordered_meters`, refuses a result below 0, and writes the
        ledger row with the new movement type `ORDER_AMOUNT_CHANGED`.
        - The `_inventory_mutations` AST guard requires every quantity write to go
          through these helpers. That's why it's a helper, not inline.
      - **Recalculate requirements** (new `_reallocate_after_ordered_change` in the
        same module, mirroring the stored-amount command):
        1. Load `ORDERED` and `NEEDS_ORDERING` candidates for the inventory, plus a
           `RequirementStateTracker`.
        2. **Demote:**
           `deficit = sum(ORDERED) − (stored + new_ordered − sum(AVAILABLE))`.
           While `deficit > 0`, demote `ordered → needs_ordering` latest-due first,
           reusing `_demotion_sort_key`; move it to `_pooled_requirement_allocation.py`
           so both commands share it. Clear `ordered_at`.
        3. **Re-promote:** run the create path's allocation (lift
           `_allocate_requirements` from `create_upholstery_order.py` into
           `_pooled_requirement_allocation.py` and import it from both) with no priority
           ids. After a decrease this can still promote a *smaller* item that now fits
           (skip-and-continue). After an increase it covers new items.
        4. **Ledger:** `record_requirement_transitions` (net transitions only) plus
           `allocation_details` on the parent ledger row, exactly as
           `set_current_stored_amount_inventory` does.
   7. **Order history row.** Write an `UpholsteryOrderHistoryRecord` (state +
      `snapshot_order_amount_meters`), like create and receive do.
   8. **Post-commit events.**
      - `upholstery:order-updated` `{client_id, state, order_amount_meters}`.
      - `item:upholstery-requirement-state-changed` with
        `{ids, new_state: "ordered"}` and `{ids, new_state: "needs_ordering"}`.
      - Notifications per C4.
   9. **Return** `{client_id, state, order_amount_meters, received_amount_meters}`, so the
      frontend can patch its cache without a refetch.
2. **Enums**
   - `InventoryMovementTypeEnum.ORDER_AMOUNT_CHANGED = "order_amount_changed"`. It's a
     Postgres enum, so it needs an Alembic migration:
     `ALTER TYPE upholstery_inventory_movement_type_enum ADD VALUE 'order_amount_changed'`.
     Labels are lowercase values.
   - `InventoryMovementTriggerEnum.ORDER_AMOUNT_CHANGED = "order_amount_changed"`. It's a
     plain string, so no migration.
3. **Request parser** `parse_update_upholstery_order_amount_request` in
   `services/commands/upholstery/requests`. It takes `client_id` (from the path) and
   `order_amount_meters: Decimal (> 0)`.
4. **Route** `PATCH /api/v1/upholstery-orders/{client_id}/amount`, body
   `{order_amount_meters}`, roles ADMIN and MANAGER (same as create and receive), through
   `run_service`. The path-scoped `PATCH` matches the inventory routes
   (`PATCH /upholstery-inventories/{id}/current-stored-amount`).
5. **Order list serializer.** No change needed: it already returns
   `order_amount_meters` / `received_amount_meters`. Re-check once the state can flip to
   `received` through this path.
6. **Fix a race this exposes in `receive_upholstery_order`.** It loads the order with
   `session.get`, without a lock. A concurrent edit could lower the amount after the
   receive's cap check, letting received exceed ordered. Change it to `FOR UPDATE` with
   `populate_existing`, and keep the order→inventory lock order in both commands.

### Frontend (managers-app, `features/upholstery-ordering`)

7. **Header ⋮ button.** Edit the `DetailPage` header in `pages/DetailSlidePages.tsx`: in
   `mode === "order"` only, add an `aria-label="Order actions"` icon button
   (`EllipsisVertical`, size-10, like Back) at the right of the header row. Hide it when
   the live order is in a closed state (C2).
8. **Actions sheet** `UPHOLSTERY_ORDER_ACTIONS_SHEET_ID`, page
   `pages/OrderActionsSheetPage.tsx`. A copy of the
   `upholstery-inventory/pages/InventoryDetailActionsSheetPage.tsx` pattern: title
   "Order actions", one button "Change ordered amount" that closes this sheet and opens
   the amount sheet. Register it in `surfaces.ts` as `surface: "sheet"`.
9. **Amount sheet** `UPHOLSTERY_ORDER_AMOUNT_SHEET_ID`, page
   `pages/OrderAmountSheetPage.tsx`. A copy of
   `upholstery-inventory/pages/StoredAmountSheetPage.tsx`:
   - It shows the fabric (image + name), "Ordered X m · received Y m", and a decimal input
     prefilled with the current amount, inside a `FloatingKeyboardBar`.
   - Client-side validation: `> 0`, `≥ received`, `≠ current`. Use
     `normalizeNonNegativeDecimalString` and send the value as a 3-dp string, the same way
     stored amount does.
   - When the new value is lower, show a hint: "Some items may go back to needs
     ordering".
10. **API and action**
    - `updateUpholsteryOrderAmount()` in `api/fetch-upholstery-ordering.ts`, with zod
      request and response schemas in `types.ts`.
    - `actions/use-update-upholstery-order-amount.ts`: on success, patch every
      `ordersLists()` cache entry for the order (`order_amount_meters`, `state`). Because
      `useLiveOrder` reads that cache, the header updates at once. On settled, invalidate
      the same key set `use-receive-upholstery-order.ts` invalidates (ordering, item
      upholstery, picker lists, pending-seat counts, inventory lists).
11. **Realtime**
    - Add `"upholstery:order-updated"` to `packages/realtime/src/lib/socket-types.ts`.
    - Handle it in `upholstery-inventory/socket-events.ts` (invalidate inventory details,
      as for created and received).
    - Also invalidate `upholsteryOrderingKeys.all`, so a second manager's open list
      refreshes. Today no ordering socket handler exists; the list relies on its own
      mutations.
12. **Inventory history label.** Add `order_amount_changed` (movement and trigger) to
    `upholstery-inventory/lib/inventory-history.ts`, e.g. "Order changed: +2.000 m" /
    "Order changed: −1.500 m".

## Acceptance criteria

1. **Increase:** an `ordered` order of 1.5 m, with 3 m of `needs_ordering` waiting and no
   stock, is raised to 4.5 m.
   - Inventory `ordered` goes 1.5 → 4.5.
   - The 3 m of `needs_ordering` becomes `ordered`, earliest due first.
   - The fabric leaves the shortage list once
     `need − stored − ordered ≤ 0`.
2. **Decrease:** 4.5 m → 1.5 m with three `ordered` requirements (1.5 m each).
   - Inventory `ordered` = 1.5.
   - Exactly the two latest-due requirements return to `needs_ordering`, with
     `ordered_at` cleared, and the fabric reappears in the shortage list with 3 m to order.
3. **Skip-and-continue:** a decrease that frees no room for a 3 m item, but does for a
   1 m item, promotes the 1 m item.
4. **Received floor:** with 2 m received, editing to < 2 m is refused (422, nothing
   written). Editing to exactly 2 m makes the order `received` (if C3 is accepted).
5. **Closed orders:** `received` / `cancelled` / `failed` orders are refused (409).
   `draft` / `pending` / `approved` change only the field; inventory is untouched.
6. **No-op:** the same amount returns success and writes no ledger, history or event.
7. **Ledger:** one `order_amount_changed` parent row with the signed delta, plus
   requirement-transition child rows for exactly the net state changes.
8. **Order history:** one `UpholsteryOrderHistoryRecord` with the new snapshot amount.
9. **Concurrency:** receive and edit on the same order serialize (both lock the order row
   first). Received never exceeds ordered.
10. **UI flow:**
    - The ⋮ button shows on an editable order's detail page and is hidden on a closed one.
    - ⋮ → "Change ordered amount" → amount sheet prefilled with the current value.
    - Invalid values disable Save with a message.
    - On save, both sheets close and the header ("X m ordered • Y m remaining") updates
      without a reload.
11. **Realtime:** a second manager sees the order list and the inventory detail update
    after an `upholstery:order-updated` event.

## Tests

- **Backend integration**
  - File:
    `tests/integration/services/commands/upholstery/test_update_upholstery_order_amount_integration.py`.
  - One test per acceptance criterion 1–8 (fixtures as in
    `test_set_current_stored_amount_inventory_integration.py`).
  - A concurrency test in the style of the existing FOR UPDATE race tests for criterion 9.
- **Backend unit**
  - The demotion deficit math: boundary where the deficit is exactly 0, and a single
    requirement bigger than the deficit.
  - `adjust_ordered` refuses to go negative.
- **Router:** auth roles and the 422 body shape.
- **Mutation checks before review:**
  - With the demote step removed, criterion 2 must fail.
  - With the receive lock removed, criterion 9 must fail.
- **Frontend (vitest)**
  - Amount sheet validation (≤ 0, < received, unchanged).
  - Cache patch in the action hook.
  - ⋮ visibility by order state.
  - Inventory-history label.
- **Regression:** the full backend suite, diffing failure IDs against the checked-in
  23-failure baseline, plus the managers-app test suite.

## Rollout

1. Run the migration (`ALTER TYPE ... ADD VALUE`). It's additive and safe to apply before
   the code.
2. Deploy the backend, then the frontend. The ⋮ only appears with the new frontend, and an
   old frontend never calls the new route.
3. No data backfill: existing orders become editable as they are.
4. Verify on prod with `prod-db`, read-only:
   - the first edit's ledger row and requirement transitions;
   - `inventory.current_amount_ordered_meters` equals the sum of the outstanding amounts
     (`order_amount − received`) over that inventory's `ordered` and
     `partially_received` orders.

## Files

| Area | File | Change |
|---|---|---|
| backend | `services/commands/upholstery/update_upholstery_order_amount.py` | new command |
| backend | `services/commands/upholstery/_inventory_mutations.py` | `adjust_ordered` |
| backend | `services/commands/upholstery/_pooled_requirement_allocation.py` | shared `demotion_sort_key`, lifted `allocate_needs_ordering` |
| backend | `services/commands/upholstery/create_upholstery_order.py` | import the lifted allocator (no behaviour change) |
| backend | `services/commands/upholstery/set_current_stored_amount_inventory.py` | import the shared sort key (no behaviour change) |
| backend | `services/commands/upholstery/receive_upholstery_order.py` | lock the order `FOR UPDATE` |
| backend | `services/commands/upholstery/requests/` | request parser |
| backend | `routers/api_v1/upholstery_orders.py` | `PATCH /{client_id}/amount` |
| backend | `domain/upholstery/enums.py` + `migrations/versions/<new>.py` | movement type + trigger |
| frontend | `features/upholstery-ordering/pages/DetailSlidePages.tsx` | ⋮ button in order mode |
| frontend | `features/upholstery-ordering/pages/OrderActionsSheetPage.tsx` | new |
| frontend | `features/upholstery-ordering/pages/OrderAmountSheetPage.tsx` | new |
| frontend | `features/upholstery-ordering/surfaces.ts` | two sheet registrations |
| frontend | `features/upholstery-ordering/api/fetch-upholstery-ordering.ts`, `types.ts` | client + schemas |
| frontend | `features/upholstery-ordering/actions/use-update-upholstery-order-amount.ts` | new |
| frontend | `packages/realtime/src/lib/socket-types.ts`, `features/upholstery-inventory/socket-events.ts` | `upholstery:order-updated` |
| frontend | `features/upholstery-inventory/lib/inventory-history.ts` | label |

## Implementation notes (2026-11-16)

- Built as designed. Shared helpers now live in `_pooled_requirement_allocation.py`:
  `allocate_needs_ordering_to_ordered` (lifted unchanged from create) and
  `demotion_sort_key` (lifted from the stored-amount command).
- The demotion deficit is `-calculate_pooled_requirement_pool(inventory, NEEDS_ORDERING,
  "ordered")`, the same pool the re-promotion allocates from.
- **Receive race confirmed and fixed.** Without `FOR UPDATE`, receive checked the cap
  against a stale amount, then blocked only on its own UPDATE, so it could write past a
  cap that had just been lowered. The test
  `test_edit_and_receive_read_the_order_under_its_row_lock` fails with either lock
  removed.
- **Live ordering screens** (owner request, same day): a new
  `features/upholstery-ordering/socket-events.ts`, registered in `app/socket-registry.ts`
  (`composeSocketHandlers` merges it with the inventory handlers for shared events).
  Mapping:
  - order created / received / updated, fabric renamed, inventory deleted → all ordering
    keys;
  - `upholstery:inventory-updated` → shortage keys;
  - requirement state changed → shortage keys + order items.

  All use `refetchType: "active"`. This also makes order create/receive live on other
  devices, which they weren't before.
- Migration `e3b5c7d9f1a2` (enum value) must be applied before deploying the backend.
