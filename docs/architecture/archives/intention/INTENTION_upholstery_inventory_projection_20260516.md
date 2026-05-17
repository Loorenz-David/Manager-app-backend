# INTENTION_upholstery_inventory_projection_20260516

## Metadata

- Intention ID: `INTENTION_upholstery_inventory_projection_20260516`
- Status: `active`
- Owner: `David Loorenz`
- Created at (UTC): `2026-05-16T12:00:00Z`
- Last updated at (UTC): `2026-05-16T12:00:00Z`

## Goal

Provide a complete set of composable inventory mutation commands that any service can call to keep the `upholstery_inventory` projection accurate and its `inventory_condition` always deterministically consistent with the actual stock state — without duplicating projection logic or bypassing the aggregate.

## Why this matters

`upholstery_inventory` is the operational aggregate that workspace managers and production workflows use to understand how much of each upholstery material is available, in use, needed, or on order. If any service modifies stock or need fields directly (bypassing these commands), the aggregate diverges and condition evaluation (`AVAILABLE` / `LOW_STOCK` / `OUT_OF_STOCK`) produces incorrect results — creating false procurement triggers or hiding actual shortages. Centralizing all mutations in a small command set guarantees the aggregate stays replay-compatible and deterministic.

## Success criteria

1. A command `check_and_inject_need` exists that evaluates whether a given quantity can be covered by the current inventory, optionally records the need in the aggregate, and returns a result struct — without requiring callers to read inventory directly.
2. A command `consume_to_in_use` exists that moves a quantity from `current_stored_amount_meters` to `current_amount_in_use_meters` in a single inline operation, raising a typed domain error if stored stock is insufficient.
3. A command `finish_in_use` exists that moves a quantity from `current_amount_in_use_meters` to the correct total fields (`total_upholstery_used_inventory_meters` or `total_upholstery_used_surplus_meters` depending on source), raising a typed error if the recorded in-use amount is less than the completion quantity.
4. A command `add_ordered` exists that records an ordered quantity in `current_amount_ordered_meters`.
5. A command `confirm_ordered_to_stock` exists that moves a quantity from `current_amount_ordered_meters` to `current_stored_amount_meters`, raising a typed error if the ordered amount is insufficient, and re-evaluates `inventory_condition` afterward.
6. A command `add_stored_surplus` exists that increments both `current_stored_amount_meters` and `total_upholstery_surplus_meters` by a surplus (offcut) quantity and re-evaluates `inventory_condition` — used when leftover pieces from other rolls are committed to fulfill a requirement.
7. `inventory_condition` re-evaluation is a pure function applied inline after every mutating command; the same inputs always produce the same condition outcome (AVAILABLE / LOW_STOCK / OUT_OF_STOCK), derived solely from `current_stored_amount_meters`, `current_amount_in_need_meters`, and `low_stock_threshold_meters` on the inventory row — no external policy lookup.
8. A command `complete_available_direct` exists that applies the combined consume + finish effect atomically for requirements transitioning directly from `AVAILABLE` to `COMPLETED`, with a guard against insufficient stored stock.
9. All commands are importable and callable by Intention 1 commands and any other service; no direct `upholstery_inventory` field writes exist outside this command set.

## Scope boundary

- **In scope:**
  - All mutation commands on `upholstery_inventory` rows (need, stored, in-use, ordered, totals, condition)
  - `inventory_condition` evaluation logic (pure function) respecting threshold policy precedence
  - Inline (same-transaction) updates — no background tasks for inventory mutations
  - `low_stock_threshold_meters` column on `upholstery_inventory` for condition evaluation (no separate policy table)
  - CRUD read endpoints for `UpholsteryInventory` (including `low_stock_threshold_meters` field)
  - CRUD create/update/soft-delete for `UpholsteryInventory`

- **Out of scope:**
  - `upholstery_inventory_history_records` (deferred — `latest_projection_history_id` FK is not yet active)
  - Warehouse movement logs, physical stock location tracking
  - Procurement order placement (setting `current_amount_ordered_meters` is tracked here; the external order is out of scope)
  - Notification or event emission on condition change (future concern)
  - Replay from history (deferred until history table exists)

- **Non-goals:**
  - Authoritative accounting valuation (`projected_inventory_value_minor` is planning-only)
  - Multi-warehouse or location-specific stock segmentation (deferred per README)
  - Reservation/lock engine
  - Workspace-level or time-bounded threshold policies (`UpholsteryInventoryThresholdPolicy` table is removed — threshold is a single nullable column per inventory row)

## Required migrations

Before any command in this intention can be implemented:

1. **Add column** `low_stock_threshold_meters NUMERIC(14,3) NULL CHECK (low_stock_threshold_meters > 0)` to `upholstery_inventory`.
2. **Drop table** `upholstery_inventory_threshold_policies` (and its DB enums: `threshold_policy_scope_enum`, `sourcing_escalation_policy_enum`, `inventory_warning_tier_enum`).
3. **Delete model file** `backend/app/beyo_manager/models/tables/upholstery/upholstery_inventory_threshold_policy.py`.
4. **Enums already removed** from `domain/upholstery/enums.py`: `ThresholdPolicyScopeEnum`, `SourcingEscalationPolicyEnum`, `InventoryWarningTierEnum`.

## Command catalogue

### Condition evaluation — shared pure function

`evaluate_condition(stored, in_need, low_stock_threshold_meters) -> UpholsteryInventoryConditionEnum`

Called at the end of every mutating command. No external policy lookup — all inputs come from the `upholstery_inventory` row itself.

1. `net_available = current_stored_amount_meters - current_amount_in_need_meters`
2. If `net_available <= 0`: → `OUT_OF_STOCK`.
3. If `low_stock_threshold_meters` is not null and `net_available < low_stock_threshold_meters`: → `LOW_STOCK`.
4. Otherwise: → `AVAILABLE`.

**Reversal rule:** condition returns to `AVAILABLE` as soon as `net_available >= low_stock_threshold_meters` (or threshold is null). No hysteresis — the same threshold value is used for both downward and upward transitions.

---

### CMD-1 — check_and_inject_need

**Purpose:** Determine if a quantity of a given upholstery can be sourced from current inventory. Optionally records the need in the aggregate (primary use: during requirement creation).

**Inputs:** `upholstery_id: str`, `quantity: Decimal`, `inject: bool = True`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory` for (`workspace_id`, `upholstery_id`). If none exists, create a new row with all quantity fields initialised to `0` (`current_stored_amount_meters = 0`, `current_amount_in_need_meters = 0`, `current_amount_in_use_meters = 0`, `current_amount_ordered_meters = 0`, all totals = `0`), `inventory_condition = AVAILABLE`, `low_stock_threshold_meters = null`.
2. If `inject=True`:
   - `current_amount_in_need_meters += quantity`
   - Flush (not commit — caller commits).
3. Calculate: `net = current_stored_amount_meters - current_amount_in_need_meters`.
4. Evaluate and update `inventory_condition` if `inject=True`.
5. Return: `{ inventory_id: str, sufficient: bool (net >= 0), condition: UpholsteryInventoryConditionEnum }`.

**Denied when:** nothing — this command always returns a result (even when `sufficient=False`). The caller decides how to respond to the result.

**Note:** When `inject=False`, this is a pure projection read — no writes occur, no flush. Used for planning/preview.

---

### CMD-2 — consume_to_in_use

**Purpose:** Move a quantity from stored inventory to in-use when material is pulled for production.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory` by `client_id`.
2. Calculate `new_stored = current_stored_amount_meters - quantity`.
3. **Guard:** if `new_stored < 0` → raise `ValidationError("Not enough upholstery in inventory to start production — please add more stock before marking in-use")`.
4. `current_stored_amount_meters = new_stored`
5. `current_amount_in_use_meters += quantity`
6. `current_amount_in_need_meters -= quantity` (requirement is no longer a "need" — it is now active)
7. Flush (caller commits).

**Note:** No condition re-evaluation — `net = stored − in_need` is unchanged by this command (both decrease equally), so `inventory_condition` cannot change.

**Note on in_need decrement (confirmed):** When material moves from need → in-use, the need is fulfilled — `current_amount_in_need_meters` decreases, `current_stored_amount_meters` decreases, and `current_amount_in_use_meters` increases. Both sides balance: stored − need and in_use + need remain consistent.

---

### CMD-3 — finish_in_use

**Purpose:** Record the consumption of in-use material at end of production. Handles cap-to-zero on underflow and routes to correct total fields.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `source: ItemUpholsteryRequirementSourceEnum`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory`.
2. `new_in_use = current_amount_in_use_meters - quantity`
3. **Guard:** if `new_in_use < 0` → raise `ValidationError("Inventory inconsistency: completion quantity exceeds recorded in-use amount")`. This should never occur in normal flow — the `quantity` passed is always the individual `ItemUpholsteryRequirement.amount_meters` for that specific instance, which is the same value CMD-2 consumed for that instance. An `ItemUpholstery` with split requirements calls this command once per instance, not once for the total.
4. `current_amount_in_use_meters = new_in_use`
5. `total_upholstery_used_meters += quantity`
6. If `source == INVENTORY`: `total_upholstery_used_inventory_meters += quantity`
7. If `source == SURPLUS`: `total_upholstery_used_surplus_meters += quantity`
8. Flush (caller commits).

**Note:** No condition re-evaluation — `finish_in_use` decrements `current_amount_in_use_meters` only; neither `current_stored_amount_meters` nor `current_amount_in_need_meters` changes, so `net = stored − in_need` is unchanged and `inventory_condition` cannot change.

---

### CMD-4 — add_ordered

**Purpose:** Record that an external supplier order for upholstery has been placed.

**Caller:** The external order system — NOT Intention 1. `current_amount_ordered_meters` is owned by the external ordering flow. Intention 1 CMD-4 (mark requirements ordered) runs separately after this and does not call this command.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory`.
2. `current_amount_ordered_meters += quantity`
3. No condition re-evaluation (ordered stock is not yet stored; condition is unchanged).
4. Flush (caller commits).

---

### CMD-5 — confirm_ordered_to_stock

**Purpose:** Record that ordered stock has arrived — moves it from ordered to stored and re-evaluates condition.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory`.
2. `new_ordered = current_amount_ordered_meters - quantity`
3. **Guard:** if `new_ordered < 0` → raise `ValidationError("Confirmed quantity exceeds the recorded ordered amount — verify the stock quantity before confirming")`.
4. `current_amount_ordered_meters = new_ordered`
5. `current_stored_amount_meters += quantity`
6. Evaluate and update `inventory_condition`.
7. Flush (caller commits).

**Note:** This command is typically called by a higher-level "confirm order received" task command, which then calls `INTENTION_1 / CMD-5` (`resolve_requirements_after_stock`) to re-allocate pending requirements.

---

### CMD-7 — complete_available_direct

**Purpose:** Apply the combined consume + finish effect in a single step when a requirement transitions directly from `AVAILABLE` to `COMPLETED` (skipping `IN_USE`). Used by Intention 1 / CMD-3 for `AVAILABLE` requirements in the natural complete-all flow.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `source: ItemUpholsteryRequirementSourceEnum`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory`.
2. `new_stored = current_stored_amount_meters - quantity`
3. **Guard:** if `new_stored < 0` → raise `ValidationError("Not enough upholstery in stored inventory to complete directly — stock may have changed since availability was confirmed")`.
4. `current_stored_amount_meters = new_stored`
5. `current_amount_in_need_meters -= quantity` (cap to 0 if underflow — guards against edge cases)
6. `total_upholstery_used_meters += quantity`
7. If `source == INVENTORY`: `total_upholstery_used_inventory_meters += quantity`
8. If `source == SURPLUS`: `total_upholstery_used_surplus_meters += quantity`
9. Flush (caller commits).

**Note:** No condition re-evaluation — `stored` decreases by `quantity` and `in_need` decreases by `quantity`, so `net = stored − in_need` is unchanged and `inventory_condition` cannot change. `current_amount_in_use_meters` is never modified by this command.

---

### CMD-6 — add_stored_surplus

**Purpose:** Add leftover/offcut material (surplus from other upholstery rolls) to stored inventory when it is committed to fulfill a requirement. This is workspace-owned material that was not yet tracked in inventory.

**Inputs:** `upholstery_inventory_id: str`, `quantity: Decimal`, `workspace_id: str`

**Behavior:**
1. Load `UpholsteryInventory`.
2. `current_stored_amount_meters += quantity`
3. `total_upholstery_surplus_meters += quantity`
4. Evaluate and update `inventory_condition` (more stored may change condition from OUT_OF_STOCK to AVAILABLE or LOW_STOCK).
5. Flush (caller commits).

**Note:** This command does NOT modify `current_amount_in_need_meters`. The need remains recorded — it will be decremented normally when the requirement transitions to IN_USE via CMD-2. The net effect after CMD-6 + CMD-2: stored increases then decreases (net zero), in_use increases, need decreases. The surplus is source-tracked at the requirement level (`source = SURPLUS`) so CMD-3 routes it to `total_upholstery_used_surplus_meters` at completion.

**Customer-source path:** When `ItemUpholstery.source = CUSTOMER`, the customer provides their own material. This is an entirely separate path — inventory commands are never called for customer-source items in this intention. That path is deferred to a future expansion of the customer table.

---

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| PLAN_upholstery_inventory_projection_20260516 | backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_projection_20260516.md | IMPLEMENTED | Complete inventory projection layer with migrations, domain logic, mutation helpers, CRUD commands, and router |

## Progress notes

- `2026-05-16`: Intention created from rough notes + model analysis. All 6 commands specified at behavioral level. Condition evaluation function defined. Awaiting review before implementation plan.

## Open questions

- **in_need on consume (CMD-2) — RESOLVED:** Confirmed: CMD-2 decrements `current_amount_in_need_meters`, decrements `current_stored_amount_meters`, and increments `current_amount_in_use_meters`. Both sides balance. A requirement must be AVAILABLE before transitioning to IN_USE (CMD-1 checks availability first), so in_need was already correctly incremented at requirement creation time.
- **Condition when threshold is null — RESOLVED:** `low_stock_threshold_meters = null` means only `AVAILABLE` or `OUT_OF_STOCK` are possible — `LOW_STOCK` is never triggered. This is the default state for newly created inventory rows.
- **CMD-5 caller sequencing:** CMD-5 (`confirm_ordered_to_stock`) must run before `INTENTION_1 / CMD-5` (resolve requirements). Enforcing this sequencing is the responsibility of the task command layer. Document the required call order explicitly in the task command when implemented.
- **`total_upholstery_used_meters` invariant — RESOLVED:** `total_used = used_inventory + used_surplus` always holds. The cap-to-zero overflow scenario was invalid — CMD-3 always receives the same quantity CMD-2 consumed, so underflow cannot occur in normal flow. The guard in CMD-3 now raises on negative rather than capping.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: all success criteria met — all 6 commands implemented, condition evaluation is a pure function, and all commands are covered by integration tests with deterministic assertions
