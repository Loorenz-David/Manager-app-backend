# ARCHIVE_RECORD_PLAN_internal_upholstery_without_requirement_20260617

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_internal_upholstery_without_requirement_20260617`
- Archived at (UTC): `2026-06-17T13:10:16Z`
- Archive owner agent: `codex`

## Source references

- Plan: `backend/docs/architecture/under_construction/implementation/PLAN_internal_upholstery_without_requirement_20260617.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_internal_upholstery_without_requirement_20260617.md`
- Debug chain (optional):
  - `—`

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `partial`

## Final notes

- Internal `ItemUpholstery` rows can now be created without a selected catalog upholstery when positive `amount_meters` is provided; requirement creation is deferred until selection is completed later.
- Existing upholstery swap behavior remains intact for already-linked requirements, while first-link activation now uses a separate path that does not attempt old inventory rollback.
- Pending seat-task upholstery discovery now treats deferred internal upholsteries as `missing_selection`, preventing them from disappearing from manager-facing work queues.

## Follow-up links

- Next plan (optional): `—`
- Related handoff (optional): `—`
