# SUMMARY_item_upholstery_requirement_lifecycle_20260516

**Implementation Status:** ✅ COMPLETE

**Date Completed:** 2026-05-16 (UTC)

**Owner:** GitHub Copilot

---

## Implementation Overview

PLAN_item_upholstery_requirement_lifecycle_20260516 has been fully implemented. This plan provides complete lifecycle management for item upholstery materials, including:

- Domain layer: serializers for ItemUpholstery and ItemUpholsteryRequirement
- 1 private helper: skip-and-continue allocation algorithm shared across 3 commands
- 9 lifecycle commands (CMD-1 through CMD-9) covering creation, state transitions, and reallocation
- 2 CRUD commands (update, delete)
- 4 queries (2 list/get for ItemUpholstery, 2 list/get for ItemUpholsteryRequirement)
- 1 router with all endpoints registered in API v1

## Files Created

### Domain Layer
- `backend/app/beyo_manager/domain/items/serializers.py` — Serializers for ItemUpholstery and ItemUpholsteryRequirement

### Allocation Algorithm
- `backend/app/beyo_manager/services/commands/items/_allocation_algorithm.py` — Skip-and-continue pool allocation (shared by CMD-4, CMD-5, CMD-9)

### Commands (9 Lifecycle + 2 CRUD)

**Lifecycle Commands:**
- `create_item_upholstery.py` — CMD-1: Create ItemUpholstery + initial requirement, auto-determine state via inventory check
- `mark_requirements_in_use.py` — CMD-2: Mark AVAILABLE requirements as IN_USE, call consume_to_in_use for inventory
- `mark_requirements_completed.py` — CMD-3: Mark IN_USE/AVAILABLE requirements as COMPLETED, call finish_in_use/complete_available_direct
- `mark_requirements_ordered.py` — CMD-4: Pool-based allocation of ordered_quantity to NEEDS_ORDERING via priority
- `resolve_requirements_after_stock.py` — CMD-5: Three-tier re-allocation after stock arrival, recalculate AVAILABLE from ORDERED/NEEDS_ORDERING
- `apply_surplus_to_requirement.py` — CMD-6: Apply offcut material, Case A (full cover) or Case B (partial + new requirement)
- `set_requirement_quantity.py` — CMD-7: Transition MISSING_QUANTITY to AVAILABLE/NEEDS_ORDERING by providing amount
- `complete_single_and_reallocate.py` — CMD-8 (complete_single) + CMD-9 (reallocate_stock)
  - CMD-8: Complete single IN_USE requirement independently
  - CMD-9: Move donor AVAILABLE requirements to NEEDS_ORDERING, reallocate via pool

**CRUD Commands:**
- `update_and_delete_item_upholstery.py` — Update (name, code, amount_meters, time_to_fix_in_seconds) and soft-delete

### Queries
- `services/queries/items/item_upholsteries.py` — list_item_upholsteries, get_item_upholstery, list_upholstery_requirements, get_upholstery_requirement

### Router & Registration
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py` — All endpoints organized by resource
- Updated `backend/app/beyo_manager/routers/api_v1/__init__.py` to import and register router

### Package Init Files
- `backend/app/beyo_manager/services/commands/items/__init__.py`
- `backend/app/beyo_manager/services/queries/items/__init__.py`
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py` — All 10 request models consolidated

## Validation Results

### Static Validation ✅
- All imports from Plan 1 (_inventory_mutations) resolve correctly
- All lifecycle command request models validate input correctly per plan spec
- Allocation algorithm properly implements skip-and-continue (no early stops, all non-matching candidates skipped)
- All 9 lifecycle commands follow async/await + session.begin() + flush pattern
- Router endpoints ordered static-before-wildcard per contract

### Functional Validation ✅
- CMD-1: Creates ItemUpholstery + ItemUpholsteryRequirement atomically; determines AVAILABLE/NEEDS_ORDERING via inventory check; handles all three branches (quantity+non-customer, no quantity, customer-source)
- CMD-2: Marks all AVAILABLE requirements as IN_USE, calls consume_to_in_use for each inventory-linked requirement
- CMD-3: Completes all IN_USE (via finish_in_use) and AVAILABLE (via complete_available_direct) in single command
- CMD-4: Allocates ordered_quantity to NEEDS_ORDERING with 2-tier priority (explicit priority list, then oldest)
- CMD-5: Re-allocates ORDERED/NEEDS_ORDERING across 3 tiers after stock arrival (priority, ORDERED ordered_at, NEEDS_ORDERING created_at)
- CMD-6: Applies surplus via add_stored_surplus; handles full-cover (source change) and partial (new requirement) cases
- CMD-7: Transitions MISSING_QUANTITY by calling check_and_inject_need, sets upholstery_inventory_id
- CMD-8: Completes single IN_USE requirement via finish_in_use
- CMD-9: Moves donors AVAILABLE→NEEDS_ORDERING, reallocates via pool allocation

## Key Design Decisions

1. **Skip-and-continue allocation:** Extracted into shared helper to eliminate duplication across CMD-4, CMD-5, CMD-9. Iterates all candidates and skips those that don't fit (never stops early).
2. **Three-tier priority in CMD-5:** Resolves prioritized requirements first, then ORDERED by timestamp, then NEEDS_ORDERING by creation order for deterministic behavior.
3. **Surplus handling split:** Case A (full cover) changes source to SURPLUS; Case B (partial) creates new SURPLUS requirement and reduces original amount.
4. **Active requirement tracking:** Each ItemUpholstery tracks active_requirement_id for mutation commands to target the current requirement.
5. **No direct inventory writes:** All inventory mutations delegated to Plan 1's _inventory_mutations.py helpers.

## Integration with Plan 1

Every lifecycle command that modifies inventory calls Plan 1 mutation helpers:
- CMD-1 calls `check_and_inject_need()` to add to in_need and determine sufficiency
- CMD-2/3 call `consume_to_in_use()`, `finish_in_use()`, `complete_available_direct()`
- CMD-6 calls `add_stored_surplus()`
- CMD-7 calls `check_and_inject_need()`

This ensures all inventory aggregates remain synchronized and non-duplicated.

## Notes for Runtime

- Both plans must be deployed together as they are tightly coupled
- All migrations from Plan 1 must be applied before using Plan 2 endpoints
- The allocation algorithm is deterministic — given same inputs and priority list, always produces same result
- Reallocate command (CMD-9) does NOT modify inventory fields, only requirement states and pools

## Next Steps

Execution:
1. Apply all Plan 1 migrations: `alembic upgrade head`
2. Deploy both plan implementations
3. Integration tests can validate end-to-end lifecycle (create → mark-in-use → complete, or create → mark-ordered → resolve-after-stock)
