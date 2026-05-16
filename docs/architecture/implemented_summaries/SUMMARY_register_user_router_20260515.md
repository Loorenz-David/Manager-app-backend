# Register User Router Implementation - Summary

Plan ID: PLAN_register_user_router_20260515  
Status: Completed  
Completion Date: 2026-05-15  
Owner Agent: GitHub Copilot

## Overview

Implemented an admin-protected `POST /api/v1/auth/register` endpoint that allows an authenticated admin to create a new user in their workspace, atomically inserting the user, workspace membership, and (for WORKER roles) optional working section memberships in a single transaction.

## Delivered Changes

### New files

- `app/beyo_manager/services/commands/users/__init__.py`
- `app/beyo_manager/services/commands/users/requests/__init__.py`
- `app/beyo_manager/services/commands/users/requests/register_user_request.py`
- `app/beyo_manager/domain/users/validators.py`
- `app/beyo_manager/domain/users/serializers.py`
- `app/beyo_manager/services/commands/users/register_user.py`

### Edited files

- `app/beyo_manager/routers/api_v1/auth.py`
  - Added `require_roles` and `ADMIN` imports.
  - Added `register_user` command import.
  - Added `RegisterUserBody` Pydantic model.
  - Added `@router.post("/register")` handler guarded by `require_roles([ADMIN])`.

## Behavior and Contract Compliance

- **Role guard**: `require_roles([ADMIN])` — unauthenticated or non-admin requests rejected before command runs.
- **WorkspaceRole resolution**: Role is resolved scoped to `ctx.workspace_id`; cross-workspace lookup returns `NotFound`.
- **WORKER restriction**: `working_section_ids` can only be provided when the resolved role is WORKER. Any other role returns `ValidationError`.
- **Atomicity**: `User`, `WorkspaceMembership`, and all `WorkingSectionMembership` rows are inserted inside one `async with ctx.session.begin()` block. A `NotFound` on any section ID rolls back the entire transaction — no partial commit.
- **Password policy**: Minimum 8 characters, enforced via `validate_password_policy` before the transaction. Password hashed with `bcrypt` before `session.add(user)` — plaintext never persisted.
- **Uniqueness**: Global email uniqueness and global username uniqueness checked inside transaction; both raise `ConflictError` on collision.
- **Serializer**: `serialize_user_profile(user)` in `domain/users/serializers.py` — excludes `password` and all sensitive internal fields.
- **Response shape**: `{"user": serialize_user_profile(user)}` wrapped by `build_ok`.

## Validation Results

### Static validation

- No errors across all 7 touched files.

### Live API validation (all against `localhost:8000`)

| # | Scenario | Result | HTTP |
|---|---|---|---|
| 1 | Register WORKER (no sections) | 200 + user object | ✅ |
| 2 | Sign-in as newly registered user | 200 + access_token | ✅ |
| 3 | Register WORKER + valid section | 200 + DB row confirmed | ✅ |
| 4 | Non-WORKER + sections | ValidationError | ✅ |
| 5 | WORKER + invalid section (rollback) | NotFound, user NOT in DB | ✅ |
| 6 | Duplicate email | ConflictError | ✅ |
| 7 | Duplicate username | ConflictError | ✅ |
| 8 | Password < 8 chars | ValidationError | ✅ |
| 9 | No token | 403 Not authenticated | ✅ |
| 10 | Non-admin token | 403 role access denied | ✅ |
