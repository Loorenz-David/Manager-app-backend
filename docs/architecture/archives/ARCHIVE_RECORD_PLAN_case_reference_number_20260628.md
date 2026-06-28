# ARCHIVE_RECORD_PLAN_case_reference_number_20260628

## Metadata

- Archive ID: `ARCHIVE_RECORD_PLAN_case_reference_number_20260628`
- Archived at (UTC): `2026-06-28T07:44:17Z`
- Archive owner agent: `codex`

## Source references

- Plan: `backend/docs/architecture/archives/implementation/PLAN_case_reference_number_20260628.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_case_reference_number_20260628.md`
- Debug chain (optional): none

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `yes`

## Final notes

- Cases now store a global sequential `scalar_id` and a human-readable `reference_number`.
- New case creation serializes allocation with a PostgreSQL advisory lock to avoid duplicate scalar ids under concurrency.
- Existing cases are backfilled in migration order with `N-####` reference numbers and the new columns are indexed.

## Follow-up links

- Next plan (optional): none
- Related handoff (optional): none
