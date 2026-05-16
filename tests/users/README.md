# Test User Credentials

This directory documents the seeded test users available for API testing across all test suites.

## Seeded Users

All users below are created by the bootstrap identity script (`backend/tests/bootstrap_tests/01_seed_identity.sh`).

### Admin User

- **Email:** `admin@beyo.dev`
- **Password:** `Admin1234!`
- **Client ID:** (auto-generated on first bootstrap)
- **Workspace:** (auto-generated on first bootstrap)
- **Role:** Admin
- **Workspace Role:** Admin
- **Use cases:**
  - All endpoint testing (full CRUD)
  - Role-gated route validation
  - Privileged operations (admin scope)
- **Token scope:** Use `app_scope=admin` for all routes requiring admin or manager roles

### Test Admin User

- **Email:** `user_test@test.local`
- **Password:** `Test1234!`
- **Client ID:** `usr_user_test`
- **Workspace:** `ws_workspace_test`
- **Role:** Admin
- **Workspace Role:** Admin
- **Use cases:**
  - Alternative admin credential for parallel test execution
  - Isolated identity testing
- **Token scope:** Use `app_scope=admin` for all routes requiring admin or manager roles

### Worker User

- **Email:** (not seeded with email; access via client_id)
- **Client ID:** `usr_worker_test`
- **Username:** `worker_test`
- **Workspace:** (same as admin, via workspace membership)
- **Role:** Worker
- **Workspace Role:** Worker
- **Use cases:**
  - Worker-only assignment validation
  - Role-based read access (working sections)
  - Membership feature testing
- **Token scope:** To authenticate this user, first bootstrap the identity, then query the database:
  ```bash
  PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d beyo_manager -At -c \
    "SELECT wm.user_id FROM public.workspace_memberships wm \
     JOIN public.workspace_roles wr ON wr.client_id = wm.workspace_role_id \
     JOIN public.roles r ON r.client_id = wr.role_id \
     WHERE wm.is_active = true AND r.name = 'worker' LIMIT 1;"
  ```
  - The query returns `usr_worker_test` (or another worker user_id if created)

## Sign-In Pattern

All sign-in requests use the `/api/v1/auth/sign-in` endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/auth/sign-in \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "<email>",
    "password": "<password>",
    "app_scope": "<scope>"
  }'
```

### App Scope Values

- `app_scope=admin`: Full admin/management endpoints. Required for route role checks against ADMIN/MANAGER roles.
- `app_scope=workspace`: Workspace-specific operations. Some routes return 403 with workspace scope (e.g., membership endpoints).

### Token Extraction (jq)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/sign-in \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@beyo.dev","password":"Admin1234!","app_scope":"admin"}' \
  | jq -r '.data.access_token')
```

### Bearer Token Usage

```bash
curl -X GET http://localhost:8000/api/v1/working-sections \
  -H "Authorization: Bearer $TOKEN"
```

## Typical Test Flow

1. Start backend server (see `backend/app/run.py`)
2. Run bootstrap identity script (idempotent):
   ```bash
   bash backend/tests/bootstrap_tests/01_seed_identity.sh
   ```
3. Sign in as admin:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/sign-in \
     -H 'Content-Type: application/json' \
     -d '{"email":"admin@beyo.dev","password":"Admin1234!","app_scope":"admin"}' \
     | jq -r '.data.access_token')
   ```
4. Call endpoints with Bearer token:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/working-sections
   ```

## User Management Integration Test

Run the user-management shell test from the backend root:

```bash
bash tests/users/test_user_management.sh user_test@test.local Test1234!
```

The script covers:

- self-service `GET /api/v1/users/me`
- self-service `PATCH /api/v1/users/me`
- self-service password rotation and restore
- admin `POST /api/v1/auth/register` using `role_name`
- admin `GET /api/v1/users`
- admin `GET /api/v1/users/{user_client_id}`
- admin `PATCH /api/v1/users/{user_client_id}`
- admin `PATCH /api/v1/users/{user_client_id}/deactivate`
- users-list filtering by `role`, `q`, and `working_sections`

The script creates a temporary working section and temporary worker user, then cleans them up at the end.

## Adding New Test Users

To add new test users to the seeded set:

1. Add user creation SQL to `backend/tests/bootstrap_tests/01_seed_identity.sh`
2. Document the new credentials here with use cases
3. Create workspace membership rows (link to workspace roles) if role-based access is needed
4. Commit changes to git so all test scripts share the same identity baseline

## Known Limitations

- **Worker user email:** `usr_worker_test` has no email field; it cannot sign in via email/password. Use admin credentials to call membership endpoints on its behalf, or add email to the seed script if direct worker auth is needed.
- **Password complexity:** All test passwords follow simple patterns. Do not use in production.
- **Single workspace:** All seeded users are in a single workspace. Multi-workspace testing requires additional seed records.
- **Soft-delete recovery:** Deleted users/roles cannot be recovered via API; recreate via seed script or database.

## References

- Bootstrap script: `backend/tests/bootstrap_tests/01_seed_identity.sh`
- Auth endpoint: `backend/app/beyo_manager/routers/api_v1/auth.py`
- JWT claim structure: `backend/app/beyo_manager/routers/utils/jwt_dep.py`
- Role gating: `backend/app/beyo_manager/routers/utils/roles.py`
