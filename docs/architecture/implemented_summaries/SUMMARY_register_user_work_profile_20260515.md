# Register User Work Profile Implementation - Summary

Plan ID: PLAN_register_user_work_profile_20260515  
Status: Completed  
Completion Date: 2026-05-15  
Owner Agent: GitHub Copilot

## Overview

Extended the existing admin-protected `POST /api/v1/auth/register` flow to always create a `UserWorkProfile` and `UserLifetimeStats` row in the same transaction as user creation. Added optional salary inputs for registration and nested `work_profile` serialization in the response.

## Delivered Changes

### Edited files

- app/beyo_manager/services/commands/users/requests/register_user_request.py
  - Added optional salary fields: `salary_per_hour_before_tax`, `salary_per_hour_after_tax`.
  - Added non-negative validator for both salary fields.
- app/beyo_manager/services/commands/users/register_user.py
  - Added creation of `UserWorkProfile` on every register call.
  - Added creation of `UserLifetimeStats` on every register call.
  - Kept all writes inside one transaction for rollback safety.
  - Returned nested `work_profile` via serializer.
- app/beyo_manager/routers/api_v1/auth.py
  - Added salary fields to `RegisterUserBody`.
- app/beyo_manager/domain/users/serializers.py
  - Added `serialize_user_work_profile`.
  - Extended `serialize_user_profile(..., work_profile=None)`.
  - Ensured salary values serialize as fixed-scale 4-decimal strings (`25.5000`).
- app/beyo_manager/services/commands/bootstrap/phases/seed_admin_user.py
  - Added idempotent seeding for `UserWorkProfile` and `UserLifetimeStats`.
  - Ensured `admin_user` exists in both branches for snapshot username usage.

## Behavior and Contract Compliance

- `register` now always creates:
  - `users` row
  - `workspace_memberships` row
  - `user_work_profiles` row
  - `user_lifetime_stats` row
  - plus optional `working_section_memberships` rows
- Salary values are optional and non-negative.
- Negative salary is rejected before DB writes.
- Response now includes:
  - `user.work_profile.salary_per_hour_before_tax`
  - `user.work_profile.salary_per_hour_after_tax`
- Atomicity preserved: invalid working section still rolls back all inserted rows.

## Validation Results

### Static validation

- No diagnostics in all touched files.

### Live API + DB validation

Executed against `localhost:8000` and Postgres (`localhost:5433`):

1. Register without salary (`wp_nosalary_1`)  
   - HTTP 200  
   - `user_work_profiles`: row exists, both salaries `NULL`  
   - `user_lifetime_stats`: row exists
2. Register with salary (`wp_salary_1`)  
   - HTTP 200  
   - DB values: `25.5000` and `20.1000`  
   - Response work_profile formatting corrected to fixed-scale (`wp_salary_2` check)
3. Register with negative salary (`wp_negative_1`)  
   - HTTP 422  
   - Validation error returned  
   - user not persisted
4. Register with valid `working_section_ids` (`wp_worker_section_1`)  
   - HTTP 200  
   - `working_section_memberships`, `user_work_profiles`, `user_lifetime_stats` all created
5. Register with invalid `working_section_ids` (`wp_bad_section_1`)  
   - HTTP 404  
   - rollback confirmed: no user/work_profile/lifetime rows persisted
6. Existing conflict behavior regression check
   - duplicate email still returns HTTP 409

### Bootstrap seed validation

- Verified admin initially lacked profile/lifetime rows in current DB snapshot.
- After seed-path execution, admin rows present:
  - `user_work_profiles`: 1
  - `user_lifetime_stats`: 1
- Re-run remained idempotent (counts unchanged).

## Acceptance Criteria Status

- AC-1 through AC-8: Met.

## Related Artifacts

- Archived implementation plan:
  - backend/docs/architecture/archives/implementation/PLAN_register_user_work_profile_20260515.md
- Archive record:
  - backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_register_user_work_profile_20260515.md
- Intention plan:
  - backend/docs/architecture/under_construction/intention/users.md
