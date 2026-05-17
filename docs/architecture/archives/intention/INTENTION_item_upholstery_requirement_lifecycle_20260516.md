# INTENTION_item_upholstery_requirement_lifecycle_20260516

## Metadata

- Intention ID: `INTENTION_item_upholstery_requirement_lifecycle_20260516`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-16T12:00:00Z`
- Last updated at (UTC): `2026-05-16T12:00:00Z`

## Goal

Enable upholstery requirements for items to be created, tracked, and transitioned through their full lifecycle — from availability assignment or needs-ordering at creation, through in-use and completion — as composable leaf commands that higher-level task commands can orchestrate safely.

## Why this matters

Each item being upholstered must be linked to a specific material requirement that tracks whether material is available from inventory, needs ordering, is being consumed in production, or has been used. Without reliable lifecycle tracking at this level, production managers cannot know the material status of individual items, and automated workflows (scheduling, procurement triggers, delivery sequencing) cannot be built on top. The commands defined here are the atomic unit that task-level orchestration will compose into larger flows.

## Success criteria

1. A single command atomically creates `ItemUpholstery` + its initial `ItemUpholsteryRequirement`, calling the inventory availability check — assigning `AVAILABLE` or `NEEDS_ORDERING` state correctly based on the result, and setting `active_requirement_id` on the `ItemUpholstery`.
2. A command transitions a requirement from `AVAILABLE`/`NEEDS_ORDERING` to `IN_USE`, calling the inventory consume command inline; the operation is denied if inventory stock is insufficient.
3. A command transitions a requirement from `IN_USE` to `COMPLETED`, calling the inventory finish-in-use command inline; surplus overflow is handled correctly.
4. A command allocates a given `ordered_quantity` across `NEEDS_ORDERING` requirements using skip-and-continue (priority list → oldest-first remainder), marking only those that fit as `ORDERED`, with no inventory mutation.
5. A command recalculates and resolves ORDERED/NEEDS_ORDERING requirements for a given upholstery after stock arrives, applying priority-based allocation in deterministic order (priority list > ORDERED > NEEDS_ORDERING, sorted by date within each tier), and returning the list of items updated to AVAILABLE and those still unresolved.
6. A command applies workspace surplus (offcut material not yet in inventory) to a `NEEDS_ORDERING` or `ORDERED` requirement, splitting or converting it correctly, and adding the surplus amount to `current_stored_amount_meters`.
7. A command `set_quantity` (CMD-7) transitions a `MISSING_QUANTITY` requirement to `AVAILABLE` or `NEEDS_ORDERING` once the quantity is provided, running the inventory check inline.
8. A command `complete_requirement_instance` (CMD-8) completes a single identified `IN_USE` requirement independently, allowing partial completion without blocking on other requirements of the same `ItemUpholstery`.
9. A command `reallocate_available_stock` (CMD-9) moves donor requirements from `AVAILABLE` back to `NEEDS_ORDERING` and runs the skip-and-continue allocation algorithm to give priority items first access to the freed pool — with no inventory field mutations.
10. All commands are callable independently from higher-level task commands; no item state (`ItemStateEnum`) transitions are performed directly — those are the responsibility of higher-level orchestrators.

## Scope boundary

- **In scope:**
  - `ItemUpholstery` create command (atomic with initial requirement creation)
  - `ItemUpholsteryRequirement` state machine: MISSING_QUANTITY → AVAILABLE ↔ NEEDS_ORDERING → ORDERED → IN_USE → COMPLETED / FAILED (AVAILABLE → NEEDS_ORDERING via CMD-9 only)
  - Maintaining `active_requirement_id` on `ItemUpholstery` across requirement history
  - All inventory mutations delegated to `INTENTION_upholstery_inventory_projection_20260516` commands (no direct `upholstery_inventory` writes)
  - Priority-based allocation algorithm when resolving requirements after stock arrival
  - Surplus application command (splits or converts source to SURPLUS)
  - CRUD read endpoints for `ItemUpholstery` and `ItemUpholsteryRequirement`

- **Out of scope:**
  - `Item` state transitions (`ItemStateEnum`: PENDING / STALL / FIXING / READY) — these are driven by higher-level task commands, not this intention
  - Procurement / order placement (upholstery ordering is external; `ORDERED` state is set by these commands, but the order itself is out of scope)
  - `upholstery_inventory` direct writes — all delegated to Intention 2 commands
  - Notification or event emission on state change (future concern)
  - Multi-upholstery batch creation (one `ItemUpholstery` per command call)

- **Non-goals:**
  - Replacing the task command orchestration layer — this intention delivers leaf commands only
  - Warehouse movement logs or physical stock tracking
  - Accounting valuation of upholstery costs

## Command catalogue

### Intention 2 dependency

All commands that mutate inventory state call commands from `INTENTION_upholstery_inventory_projection_20260516`. These are always inline (same transaction). The dependency is unidirectional: Intention 1 → Intention 2.

---

### CMD-1 — Create ItemUpholstery (atomic with initial requirement)

**Inputs:** `item_id`, `upholstery_id` (nullable — can be custom), `name` (nullable), `code` (nullable), `amount_meters`, `source` (`INTERNAL` | `CUSTOMER`), `time_to_fix_in_seconds` (nullable), `workspace_id`, `created_by_id`

**Behavior:**

**Branch A — quantity provided** (`amount_meters` is not null and > 0):
1. Create `ItemUpholstery` row.
2. Call **Intention 2 / CMD-1** `check_and_inject_need(upholstery_id, amount_meters, inject=True)`.
   - Returns `{ inventory_id, sufficient: bool, condition }`.
3. Create `ItemUpholsteryRequirement` with:
   - `source = INVENTORY` (initial default)
   - `state = AVAILABLE` if `sufficient`, else `NEEDS_ORDERING`
   - `upholstery_inventory_id` = returned `inventory_id` (if upholstery_id is not null)
   - `amount_meters` = same as `ItemUpholstery.amount_meters`
4. Set `item_upholstery.active_requirement_id` to the new requirement.
5. Flush and commit.

**Branch B — no quantity** (`amount_meters` is null or 0 — 0 is coerced to null):
1. Create `ItemUpholstery` row (with `amount_meters = null`).
2. Create `ItemUpholsteryRequirement` with:
   - `source = INVENTORY`
   - `state = MISSING_QUANTITY`
   - `amount_meters = null`
   - `upholstery_inventory_id = null` (inventory not touched until quantity is known)
3. Set `item_upholstery.active_requirement_id` to the new requirement.
4. Flush and commit.
5. **No inventory commands called.** `current_amount_in_need_meters` is not modified.

**Denied when:**
- `item_id` does not belong to the workspace.
- `upholstery_id` is null AND `source` is not `CUSTOMER` — a non-catalog upholstery is only valid for customer-supplied material. Any other source requires a catalog `upholstery_id` for inventory tracking.
- `upholstery_id` is provided but no `UpholsteryInventory` row exists for it (Branch A only).

**Note (source=CUSTOMER):** When `source=CUSTOMER`, the item's upholstery material is customer-owned. The requirement is still created (to track the need), but **no inventory commands are called** — inventory is never touched for customer-source items. The customer requirement follows an independent path deferred to a future expansion of the customer table. CMD-6 (surplus) does not apply to this path.

---

### CMD-2 — Mark Requirements In-Use

**Inputs:** `item_upholstery_id`, `workspace_id`, `updated_by_id`

**Behavior:**
1. Load ALL requirements for `item_upholstery_id` with state `AVAILABLE`.
2. Guard: at least one `AVAILABLE` requirement must exist.
3. For each `AVAILABLE` requirement:
   - If `upholstery_inventory_id` is not null (INTERNAL/SURPLUS source):
     - Call **Intention 2 / CMD-2** `consume_to_in_use(upholstery_inventory_id, amount_meters)`.
       - Denied (raised) if inventory stored is insufficient.
   - If `upholstery_inventory_id` is null (CUSTOMER source): skip inventory commands.
   - Update requirement state → `IN_USE`, set `in_use_at`.
4. Commit.

**Denied when:** no `AVAILABLE` requirements exist for the item_upholstery; or inventory stored amount is insufficient for any non-customer requirement being transitioned.

**Note on multiple requirements:** An item_upholstery can have multiple `AVAILABLE` requirements at the same time (e.g., one SURPLUS + one INVENTORY after CMD-6 Case A resolves and CMD-5 later fulfills the INVENTORY portion). CMD-2 transitions all of them to `IN_USE` in a single call — the user starting work on an item moves all available material into active production.

---

### CMD-3 — Mark Requirements Completed (natural complete-all)

**Inputs:** `item_upholstery_id`, `workspace_id`, `updated_by_id`

**Behavior:**
1. Load ALL requirements for `item_upholstery_id` with state `IN_USE` or `AVAILABLE`.
2. Guard: at least one `IN_USE` or `AVAILABLE` requirement must exist.
3. For each `IN_USE` requirement:
   - If `upholstery_inventory_id` is not null: call **Intention 2 / CMD-3** `finish_in_use(upholstery_inventory_id, amount_meters, source)`.
   - If `upholstery_inventory_id` is null (CUSTOMER source): skip inventory commands.
   - Update state → `COMPLETED`, set `completed_at`.
4. For each `AVAILABLE` requirement (direct complete — skips the in-use step):
   - If `upholstery_inventory_id` is not null: call **Intention 2 / CMD-7** `complete_available_direct(upholstery_inventory_id, amount_meters, source)`.
   - If `upholstery_inventory_id` is null (CUSTOMER source): skip inventory commands.
   - Update state → `COMPLETED`, set `completed_at`.
5. Commit.

**Denied when:** no `IN_USE` or `AVAILABLE` requirements exist.

**Note on mixed states:** The typical mixed case is: SURPLUS instance is `IN_USE` (user started work with it via CMD-2), INVENTORY instance is `AVAILABLE` (stock arrived and CMD-5 resolved it, but CMD-2 was not called again for it). CMD-3 closes both in one call — IN_USE via the normal finish path, AVAILABLE via the direct path.

**Note on already COMPLETED:** Requirements already `COMPLETED` (e.g., the SURPLUS portion completed via CMD-8 before the INVENTORY portion became available) are silently skipped.

---

### CMD-4 — Mark Requirements Ordered (pool-based, priority-aware)

**Context:** Called after the external order system has already placed a supplier order and called Intention 2 `add_ordered` with the total ordered quantity. This command allocates that quantity to specific requirements by marking them `ORDERED`. It does NOT touch any inventory fields.

**Inputs:** `upholstery_id: str`, `ordered_quantity: Decimal`, `priority_item_upholstery_ids: list[str]` (optional, defaults to empty), `workspace_id`, `updated_by_id`

**Behavior:**
1. Load all active requirements for `upholstery_id` in the workspace with state `NEEDS_ORDERING`.
2. Sort into two tiers:
   - **Tier 1** — items in `priority_item_upholstery_ids`, in the order provided (skipped if not `NEEDS_ORDERING`).
   - **Tier 2** — remaining `NEEDS_ORDERING` requirements, sorted by `created_at ASC` (oldest first).
3. Set `running_pool = ordered_quantity`.
4. Iterate all candidates in tier order using skip-and-continue:
   - If `running_pool - candidate.amount_meters >= 0`: mark → `ORDERED`, set `ordered_at = now()`, `running_pool -= candidate.amount_meters`.
   - If `running_pool - candidate.amount_meters < 0`: skip — leave at `NEEDS_ORDERING`, continue to next candidate.
5. No inventory mutation.
6. Commit.
7. Return: `{ ordered: [item_upholstery_ids], unordered: [item_upholstery_ids] }`.

**Denied when:** `upholstery_id` not found in workspace; `ordered_quantity <= 0`.

**Allocation behaviour:** Same skip-and-continue as CMD-5 and CMD-9. A large item that doesn't fit the remaining pool is skipped — smaller items later in the tier still get evaluated and marked `ORDERED` if they fit. Priority list gets first access to the pool.

---

### CMD-5 — Resolve Requirements After Stock Arrival (priority allocation)

**Inputs:** `upholstery_id`, `priority_item_upholstery_ids: list[str]` (ordered list), `workspace_id`, `updated_by_id`

**Behavior:**

> **Note:** This command assumes `INTENTION_upholstery_inventory_projection / CMD-5` (`confirm_ordered_to_stock`) has already been called separately, updating `current_stored_amount_meters` before this command runs. The caller (task command) is responsible for sequencing: `confirm_ordered_to_stock` first, then this command.

1. Load all active requirements for the given `upholstery_id` where state is `ORDERED` or `NEEDS_ORDERING` (non-deleted, correct workspace).
2. Sort into three tiers:
   - **Tier 1** — items in `priority_item_upholstery_ids`, in the order provided.
   - **Tier 2** — remaining items with state `ORDERED`, sorted by `ordered_at ASC` (oldest first).
   - **Tier 3** — remaining items with state `NEEDS_ORDERING`, sorted by `created_at ASC` (oldest first).
3. Load `UpholsteryInventory` for this upholstery.
4. Calculate running pool:
   - `total_need_of_all_candidates = SUM(requirement.amount_meters for all candidates)`
   - `running_pool = current_stored_amount_meters - (current_amount_in_need_meters - total_need_of_all_candidates)`
   - This removes all candidates' existing contribution from the need, then lets us re-allocate cleanly.
5. Iterate all candidates in tier order (all candidates are evaluated — do not stop early):
   - If `running_pool - candidate.amount_meters >= 0`:
     - Mark candidate → `AVAILABLE`; `running_pool -= candidate.amount_meters`.
   - If `running_pool - candidate.amount_meters < 0`:
     - Skip candidate — leave at current state (`ORDERED` or `NEEDS_ORDERING`); `running_pool` unchanged.
     - Continue to next candidate.
6. Commit.
7. Return: `{ resolved: [item_upholstery_ids], unresolved: [item_upholstery_ids] }`.

**Note on inventory fields:** CMD-5 does not modify any `upholstery_inventory` fields directly. `current_amount_in_need_meters` does not change when items move from NEEDS_ORDERING/ORDERED to AVAILABLE — in_need is only decremented when material physically moves to IN_USE (CMD-2). Condition was already re-evaluated by `confirm_ordered_to_stock` (Intention 2 CMD-5) before this command ran.

**Allocation behaviour:** Skip-and-continue. A candidate that cannot fit does not block subsequent candidates — smaller requirements later in the priority order are still evaluated and marked AVAILABLE if the remaining pool covers them. Priority ordering determines who gets first access to the pool, not who blocks the rest.

---

### CMD-6 — Apply Surplus to Requirement

Surplus = leftover/offcut pieces from other upholstery rolls that the workspace has in its possession but are not yet recorded in the upholstery inventory. Applying surplus commits those offcuts to a specific requirement and adds them to stored inventory.

**Inputs:** `item_upholstery_id`, `surplus_amount_meters: Decimal`, `workspace_id`, `updated_by_id`

**State guard:** The active requirement must be in state `NEEDS_ORDERING` or `ORDERED`. Surplus cannot be applied to requirements in any other state.

**Surplus amount guard:** `surplus_amount_meters` must be ≤ the active requirement's `amount_meters`. No over-application allowed.

**Note on ORDERED requirements:** When the requirement is `ORDERED`, it means an external order was placed for this material. Applying surplus means that order (or part of it) is no longer needed. `current_amount_ordered_meters` must be decremented accordingly. This requires a `reduce_ordered` command in Intention 2 — flagged as an open question below pending confirmation of the desired behavior.

**Behavior:**

**Case A — surplus covers full need** (`surplus_amount_meters == requirement.amount_meters`):
1. Call **Intention 2 / CMD-6** `add_stored_surplus(upholstery_inventory_id, surplus_amount_meters)`.
   - Increments `current_stored_amount_meters` by the surplus amount; re-evaluates condition.
2. Update existing requirement: `source → SURPLUS`, `state → AVAILABLE`.
3. Commit.

**Case B — surplus partially covers** (`surplus_amount_meters < requirement.amount_meters`):
1. Call **Intention 2 / CMD-6** `add_stored_surplus(upholstery_inventory_id, surplus_amount_meters)`.
   - Increments `current_stored_amount_meters` by the surplus amount; re-evaluates condition.
2. Create a new requirement (`source = SURPLUS`, `amount_meters = surplus_amount_meters`, `state = AVAILABLE`, `upholstery_inventory_id` = same as the INVENTORY requirement — same inventory row, same upholstery).
3. Update existing (INVENTORY) requirement: `amount_meters -= surplus_amount_meters`.
4. `active_requirement_id` remains pointing to the INVENTORY requirement (it still represents the outstanding inventory need).
5. Commit.

**Flow after CMD-6:** The surplus is now in `current_stored_amount_meters`. When CMD-2 (in-use) runs for the SURPLUS requirement, the normal consume flow applies — stored decreases, in_use increases, in_need decreases. CMD-3 (complete) then routes it to `total_upholstery_used_surplus_meters` via the `source` field.

**Customer-source path:** CMD-6 does not apply to `source=CUSTOMER` items — customer material is never tracked in workspace inventory. That path is deferred.

**Case B flow after creation:** The SURPLUS requirement is immediately `AVAILABLE` — CMD-2 will pick it up and the user can start working with the item. The INVENTORY requirement remains `NEEDS_ORDERING` and is driven forward by CMD-5 (stock allocation) when stock arrives, or CMD-4 (mark ordered) if an order is placed. CMD-2 and CMD-3 always operate on ALL requirements of the target state, so when the INVENTORY portion eventually becomes `AVAILABLE`, CMD-2 will include it in the next in-use transition.

---

---

### CMD-7 — Set Quantity on Missing-Quantity Requirement

**Purpose:** Resolve a `MISSING_QUANTITY` requirement once the user provides the upholstery amount. Runs the inventory check and transitions the requirement to `AVAILABLE` or `NEEDS_ORDERING`.

**Inputs:** `item_upholstery_id`, `amount_meters: Decimal`, `workspace_id`, `updated_by_id`

**Guards:**
- Active requirement must be in state `MISSING_QUANTITY`.
- `amount_meters` must be > 0 (passing 0 is rejected — use a non-zero quantity or leave the requirement in `MISSING_QUANTITY`).

**Behavior:**
1. Load `ItemUpholstery` + active requirement.
2. Update `ItemUpholstery.amount_meters = amount_meters`.
3. Call **Intention 2 / CMD-1** `check_and_inject_need(upholstery_id, amount_meters, inject=True)`.
   - Returns `{ inventory_id, sufficient: bool, condition }`.
4. Update requirement:
   - `amount_meters = amount_meters`
   - `upholstery_inventory_id` = returned `inventory_id`
   - `state = AVAILABLE` if `sufficient`, else `NEEDS_ORDERING`
5. Commit.

**Note:** This command is the only valid transition out of `MISSING_QUANTITY`. A requirement in `MISSING_QUANTITY` cannot be moved to IN_USE or any other state without first resolving the quantity via this command.

---

### CMD-8 — Complete a Specific Requirement Instance

**Purpose:** Complete a single identified requirement that is `IN_USE`, without touching any other requirements on the same `ItemUpholstery`. Allows the user to close out a partial requirement (e.g., the SURPLUS portion) independently while the INVENTORY portion is still pending.

**Inputs:** `item_upholstery_requirement_id: str`, `workspace_id`, `updated_by_id`

**Guards:**
- Requirement must belong to the workspace.
- Requirement state must be `IN_USE`.

**Behavior:**
1. Load `ItemUpholsteryRequirement` by `client_id`.
2. If `upholstery_inventory_id` is not null: call **Intention 2 / CMD-3** `finish_in_use(upholstery_inventory_id, amount_meters, source)`.
3. Update state → `COMPLETED`, set `completed_at`.
4. Commit.

**Note:** This command targets a single requirement by its own ID — not `item_upholstery_id`. The remaining requirements on the same `ItemUpholstery` are unaffected.

---

### CMD-9 — Reallocate Available Stock (priority reorder)

**Purpose:** Reassign virtual stock from lower-priority items currently `AVAILABLE` to higher-priority items currently `NEEDS_ORDERING` or `ORDERED`. The donor items return to `NEEDS_ORDERING`; the priority items are re-evaluated with the freed pool. This is the only command that transitions requirements from `AVAILABLE` back to `NEEDS_ORDERING`.

**Inputs:** `upholstery_id: str`, `priority_item_upholstery_ids: list[str]`, `donor_item_upholstery_ids: list[str]`, `workspace_id`, `updated_by_id`

**Guards:**
- All donor items must have an active requirement in state `AVAILABLE`.
- All priority items must have an active requirement in state `NEEDS_ORDERING` or `ORDERED`.
- `donor_item_upholstery_ids` and `priority_item_upholstery_ids` must not overlap.

**Behavior:**
1. Load donor requirements (state `AVAILABLE`); validate all pass the guard.
2. Move all donor requirements → `NEEDS_ORDERING`. No inventory changes — `current_amount_in_need_meters` is unchanged (donors' amounts were already recorded; moving back to NEEDS_ORDERING is a state-only change).
3. Run the same skip-and-continue allocation algorithm as CMD-5, sorting ALL current `NEEDS_ORDERING` and `ORDERED` requirements for `upholstery_id` into tiers:
   - **Tier 1** — `priority_item_upholstery_ids`, in the order provided.
   - **Tier 2** — remaining `ORDERED`, sorted by `ordered_at ASC`.
   - **Tier 3** — remaining `NEEDS_ORDERING` (including donors), sorted by `created_at ASC`.
4. Calculate running pool using the same formula as CMD-5:
   - `total_need_of_all_candidates = SUM(requirement.amount_meters for all candidates)`
   - `running_pool = current_stored_amount_meters - (current_amount_in_need_meters - total_need_of_all_candidates)`
5. Allocate candidates (skip-and-continue); mark fitting candidates → `AVAILABLE`.
6. **No inventory field mutations.** `current_amount_in_need_meters` and `current_stored_amount_meters` are unchanged throughout. No condition re-evaluation needed (stored and in_need are unchanged).
7. Commit.
8. Return: `{ reallocated_to: [item_ids marked AVAILABLE], returned_to_needs_ordering: [donor ids that did not fit] }`.

**Note:** Donors that end up fitting in the re-allocation (because their turn comes up in Tier 3 and pool permits) will be marked `AVAILABLE` again. Only donors that cannot be covered by the remaining pool stay at `NEEDS_ORDERING`.

---

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| PLAN_item_upholstery_requirement_lifecycle_20260516 | backend/docs/architecture/archives/implementation/PLAN_item_upholstery_requirement_lifecycle_20260516.md | IMPLEMENTED | Complete item upholstery lifecycle with 9 leaf commands, allocation algorithm, CRUD operations, and router |

## Progress notes

- `2026-05-16`: Intention created from rough notes + model analysis. Commands specified at behavioral level. Alignment complete.
- `2026-05-16`: First implementation plan must be the migration making `item_upholstery_requirements.amount_meters` nullable — required before CMD-1 Branch B and CMD-7 can be implemented.

## Open questions

- **CMD-5 allocation behaviour — RESOLVED**: Skip-and-continue. When a candidate cannot fit the remaining pool, it is skipped and the next candidate is evaluated. Priority order determines who gets first access; it does not block subsequent items from fitting.
- **CMD-6 Case B — active_requirement_id — RESOLVED**: `active_requirement_id` stays on the INVENTORY requirement. The SURPLUS requirement is supplementary (tracks the offcut portion). Downstream commands (CMD-2, CMD-3) are called per-requirement, not per-item.
- **CMD-6 inventory field — RESOLVED**: Surplus = workspace offcuts (not customer-owned). CMD-6 calls `add_stored_surplus` which **increments** `current_stored_amount_meters`. The need is decremented later via CMD-2 (normal consume flow), not at surplus application time.
- **MISSING_QUANTITY — amount_meters storage — RESOLVED**: Stored as `null`. Passing `0` in any input is treated as null (coerced before writing). `item_upholstery_requirements.amount_meters` is currently `nullable=False` — a migration is required to make it nullable before CMD-1 Branch B can be implemented.
- **CMD-1 null upholstery_id — RESOLVED**: Null `upholstery_id` is only valid when `source = CUSTOMER`. Any other source with a null `upholstery_id` raises a validation error — catalog tracking is required for non-customer material.
- **CMD-6 on ORDERED requirements — RESOLVED**: No `reduce_ordered` needed. `current_amount_ordered_meters` is owned by the external order system — it is incremented when a supplier order is placed (Intention 2 `add_ordered` called externally) and decremented when stock arrives (`confirm_ordered_to_stock`). Requirement state (`ORDERED`) is a separate tracking concern. Applying surplus to an ORDERED requirement only affects the requirement and `current_stored_amount_meters` — the external order is managed independently.
- **FAILED state**: Enum value kept for future use. No scenario identified yet — no command will cover this transition until a concrete use case is defined.
- **Source=CUSTOMER creation flow — RESOLVED**: CMD-1 creates the requirement but does NOT call any inventory commands. Inventory is never touched for customer-source items. CMD-2 also skips inventory when `upholstery_inventory_id` is null.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: all success criteria met — all commands implemented, covered by integration tests, and callable by a higher-level task command stub
