# ARCHIVE_PLAN_seat_tasks_pending_upholstery_corrections_20260615_1226

**Status:** IMPLEMENTED

**Date Archived:** 2026-06-15 (UTC)

**Original Plan:** `backend/docs/architecture/archives/implementation/PLAN_seat_tasks_pending_upholstery_corrections_20260615.md`

**Implementation Summary:** `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_seat_tasks_pending_upholstery_corrections_20260615.md`

---

## What Was Implemented

Applied three targeted corrections to the pending seat-tasks upholstery list implementation:

- removed the redundant `_seat_task_subquery` helper
- removed the matching redundant outer-query `IN` filter
- aligned the in-memory role comparison with the existing task query convention
- exposed `order_by` on the router and passed it through to the query layer

## Validation

- `python3 -m py_compile backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`
- `rg -n "_seat_task_subquery" backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py`
- `rg -n "ti\\.role ==" backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py`

## Known Gaps

- No live request was executed against the endpoint in this correction slice.
