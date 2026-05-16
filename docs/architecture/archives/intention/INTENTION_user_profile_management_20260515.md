# INTENTION_user_profile_management_20260515

## Metadata

- Intention ID: `INTENTION_user_profile_management_20260515`
- Status: `achieved`
- Owner: `David`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T23:59:00Z`

## Goal

Expose user profile read and write endpoints for all roles (self-service) and for admin/manager roles (workspace user management and listing), covering identity fields, profile picture, and work profile salary data.

## Why this matters

Users need to manage their own profile data (email, phone, password, picture) without admin intervention. Admins and managers need a single interface to view, update, and deactivate workspace members, including sensitive work profile fields (salary). A paginated user list with role and section membership data enables workspace-level user management dashboards.

## Success criteria

1. Any authenticated user can GET their own profile (username, email, phone_number, profile_picture) via a self-service endpoint.
2. Any authenticated user can UPDATE their own profile fields (email, phone_number, profile_picture) and change their password (requires current password verification).
3. Admin/manager can GET any workspace member's profile including work profile salary fields (salary_per_hour_before_tax, salary_per_hour_after_tax).
4. Admin/manager can UPDATE any workspace member's identity fields and salary fields in a single operation.
5. Admin/manager can DEACTIVATE a user (set `WorkspaceMembership.is_active = False`); this action is workspace-scoped and does not affect other workspaces.
6. Admin/manager can GET a paginated list of **active** workspace members with: username, email, role (name + role_id), profile_picture, and working sections (id, name, image).
7. All endpoints enforce workspace-scoping and role-based access control. Non-admin users cannot access or modify other users' data.

## Scope boundary

- In scope:
  - Self-service profile GET and UPDATE (email, phone_number, password, profile_picture)
  - Admin/manager user profile GET and UPDATE (identity fields + salary)
  - Admin/manager user deactivation (workspace membership deactivation)
  - Paginated active users list with role and working section membership data
  - Lightweight working section serializer (id, name, image) for the list endpoint

- Out of scope:
  - User re-activation (reversing deactivation)
  - Profile picture file upload — client sends URL only; storage is handled externally
  - Cross-workspace user transfer or visibility
  - Hard deletion of the `User` row
  - Removal of the `WorkspaceMembership` row (only `is_active` flag changes)

- Non-goals:
  - Password reset flow (already exists via `auth.py`)
  - User invitation or registration (covered by `PLAN_register_user_work_profile_20260515`)
  - Email verification on change

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_user_self_service_profile_20260515` | `backend/docs/architecture/archives/implementation/PLAN_user_self_service_profile_20260515.md` | `completed` | Self-service GET/UPDATE own profile (all roles) |
| `PLAN_user_admin_management_20260515` | `backend/docs/architecture/archives/implementation/PLAN_user_admin_management_20260515.md` | `completed` | Admin/manager GET/UPDATE/deactivate any user + paginated active users list |

## Progress notes

- `2026-05-15`: Intention created. Goal-intent alignment completed with David. Delete = deactivate membership (is_active=False). Image update = URL string only. Two implementation plans proposed.
- `2026-05-15`: Both implementation plans written. Users list scope expanded to include `q` string search (username/email/phone_number via `apply_string_filter`) and `role` / `working_sections` FK filters. `PLAN_user_admin_management_20260515` depends on `PLAN_user_self_service_profile_20260515` being implemented first.
- `2026-05-15`: `PLAN_user_self_service_profile_20260515` implemented, summarized, and archived. Added `/api/v1/users/me`, `/api/v1/users/me/password`, and router registration. Static diagnostics clean; import validation passed (`OK_SELF_SERVICE`).
- `2026-05-15`: `PLAN_user_admin_management_20260515` implemented, summarized, and archived. Added workspace-scoped users list/get/update/deactivate endpoints plus compact serializers. Static diagnostics clean; import validation passed (`OK_ADMIN_USERS`, `OK_USERS_CONTRACT`).
- `2026-05-15`: Live HTTP validation passed on `http://localhost:8000`. Verified self-service profile read/update/password rotation, active-users list pagination, role filter, working-section filter, admin user update, workspace deactivation, and `404` after deactivation. Temporary validation user was deactivated and the seeded admin password was restored.

## Open questions

- None — all blocking decisions resolved during alignment.

## Lifecycle transition

- Current status: `achieved`
- Next status: `archived`
- Transition trigger: Archive the intention when no further follow-up plans are needed for this feature set.
