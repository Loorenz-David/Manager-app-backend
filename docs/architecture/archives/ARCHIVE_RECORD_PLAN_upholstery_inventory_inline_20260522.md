# ARCHIVE_RECORD_PLAN_upholstery_inventory_inline_20260522

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_upholstery_inventory_inline_20260522`
- Archived at (UTC): `2026-05-22T15:50:50Z`
- Archive owner agent: `Copilot`

## Source references

- Plan: `backend/docs/architecture/under_construction/implementation/PLAN_upholstery_inventory_inline_20260522.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_inline_20260522.md`
- Debug chain (optional): _none_

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `yes`

## Final notes

- `GET /api/v1/upholsteries` and `GET /api/v1/upholsteries/{client_id}` now inline `current_stored_amount_meters` and `inventory_condition` in the upholstery payload.
- Inventory loading is done in one additional query per list page and one query for single-get, both scoped by workspace and active rows.
- Null-safe behavior is preserved for missing inventory rows and null stored-meter values.

## Follow-up links

- Next plan (optional): _none_
- Related handoff (optional): _none_
