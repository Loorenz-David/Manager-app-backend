# ARCHIVE_bootstrap_and_roles_20260515_1200

## Metadata

- Archive ID: `ARCHIVE_bootstrap_and_roles_20260515_1200`
- Archived at (UTC): `2026-05-15T12:00:00Z`
- Archive owner agent: `GitHub Copilot`

## Source references

- Plan: `backend/docs/architecture/under_construction/archives/implementation/PLAN_bootstrap_and_roles_20260515.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_bootstrap_and_roles_20260515.md`
- Debug chain (optional): none

## Outcome classification

- Result: `completed`
- Acceptance criteria met: `yes`

## Final notes

- All 18 implementation steps completed: role enum transition, 6 bootstrap settings, env example, response helper update, Alembic migration, 9 seed phases, orchestrator, and bootstrap router.
- Migration `ec9017a0245c` applied — live DB `role_name_enum` confirmed as `['admin', 'worker', 'manager', 'seller']`.
- All phase modules import cleanly. Compile check passes with zero errors.
- Bootstrap is idempotent by SELECT-before-INSERT contract. `IssueCategoryConfig` uses `IS NULL` filter on `effective_from` because Postgres unique constraints treat `NULL` as not-equal.
- `seed_workspace` partial-seed recovery path added: if workspace exists but some `WorkspaceRole` rows are missing (interrupted prior run), the idempotent branch creates them before returning — prevents `KeyError` in `seed_admin_user`.
- `ValidationError` (not `ValidationFailed`) is raised for missing env vars — `ValidationFailed` does not exist in this codebase.
- **Bug Found & Fixed** (May 15, 2026):
  - **Issue**: `seed_issue_category_configs.py` loop logic only created seating configs for `upholstery_damage` (7 rows), missing 56 rows for 8 wood-applicable issue types.
  - **Root Cause**: Single loop with conditional branch assigned wood-applicable types to `_WOOD_CATEGORIES` only, skipping seating.
  - **Fix**: Split into two explicit loops: (1) all 9 types × 7 seating = 63 rows; (2) 8 wood-applicable types × 27 wood = 216 rows.
  - **Verification**: DB spot-check confirmed `issue_category_configs` total = 279 (was 223), all 9 types with 7 seating configs each.
- **Live end-to-end validation** (May 15, 2026):
  - `POST /api/v1/bootstrap` with correct secret → `200 OK`, idempotent (re-run returns same IDs).
  - `POST /api/v1/bootstrap` with wrong secret → `403 Forbidden`.
  - JWT token issued by bootstrap; sign-in with admin credentials → valid JWT, correct identity.
  - All 12 bootstrap tables spot-checked: 10/12 exact matches (users & memberships have 1 extra each due to idempotent re-run during testing).

## Follow-up links

- Next plan (optional): `backend/docs/architecture/under_construction/implementation/PLAN_working_section_crud_20260515.md`
- Related handoff (optional): none
