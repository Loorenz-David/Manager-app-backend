# ARCHIVE_PLAN_seat_tasks_pending_upholstery_20260615_1215

**Status:** IMPLEMENTED

**Date Archived:** 2026-06-15 (UTC)

**Original Plan:** `backend/docs/architecture/archives/implementation/PLAN_seat_tasks_pending_upholstery_20260615.md`

**Implementation Summary:** `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_seat_tasks_pending_upholstery_20260615.md`

---

## What Was Implemented

Added two read-only endpoints on `/api/v1/item-upholsteries` for seat tasks that are blocked on upholstery data entry:

- `GET /pending-seat-tasks`: paginated task list with `q`, `missing_selection`, and `missing_quantity` filters, returning the existing `tasks_pagination` structure.
- `GET /pending-seat-tasks/counts`: lightweight global counts for tasks missing upholstery selection vs missing upholstery quantity.

## Key Delivery Notes

- Query-layer filtering stays workspace-scoped and read-only.
- Route declaration order keeps both static endpoints ahead of wildcard `/{client_id}` paths.
- Seat-category matching is case-insensitive to avoid snapshot casing drift.
- The list endpoint reuses the existing task ordering helper and task-card payload structure.

## Validation

- `python3 -m py_compile backend/app/beyo_manager/services/queries/items/seat_tasks_pending_upholstery.py backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`

## Known Gaps

- Automated API/integration coverage for these new endpoints was not added in this slice.
