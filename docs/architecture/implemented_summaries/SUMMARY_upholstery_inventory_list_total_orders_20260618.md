# SUMMARY_upholstery_inventory_list_total_orders_20260618

## Metadata

- Summary ID: `SUMMARY_upholstery_inventory_list_total_orders_20260618`
- Status: `implemented`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T13:07:31Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_list_total_orders_20260618.md`
- Related debug plan (optional): none

## What was implemented

- Added `total_orders` to each item returned by `list_upholstery_inventories`.
- Counted active upholstery orders with one extra grouped query scoped to the page's inventory IDs.
- Extended the partial inventory serializer to emit `total_orders`, normalizing zero to `null`.

## Files changed

- `backend/app/beyo_manager/services/queries/upholstery/list_upholstery_inventories.py`: added active-state constant and grouped active-order count query.
- `backend/app/beyo_manager/domain/upholstery/serializers.py`: extended `serialize_upholstery_inventory_partial(..., total_orders=...)`.
- `backend/app/tests/unit/services/queries/upholstery/test_list_upholstery_inventories.py`: added query coverage for aggregated counts and empty-page fast path.
- `backend/app/tests/unit/test_upholstery_serializers.py`: added `total_orders` serializer assertions and aligned fixtures with the current upholstery serializer contract.

## Contract adherence

- Existing list query shape was preserved: inventory page query stays intact and `total_orders` is resolved in one additional grouped query rather than per-row lookups.
- `serialize_upholstery_inventory` was left unchanged; only the list-view partial serializer was extended, matching the plan scope.

## Validation evidence

- `/bin/zsh -lc 'cd backend/app && PYTHONPATH=. .venv/bin/pytest tests/unit/test_upholstery_serializers.py tests/unit/services/queries/upholstery/test_list_upholstery_inventories.py'`: passed, `6 passed`.

## Known gaps or deferred items

- The active order-state set is encoded locally in the list query. If business rules later exclude `DRAFT` or redefine “active”, only that constant needs to change.

## Handoff notes (if needed)

- None.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_list_total_orders_20260618.md`
