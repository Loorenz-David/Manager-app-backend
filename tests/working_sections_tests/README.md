# Working Sections CRUD Test Suite

Comprehensive test suite for the working sections endpoints, including create, read, list, edit, delete, and cycle detection.

## Usage

```bash
bash tests/working_sections_tests/test_working_sections.sh <email> <password>
```

## Examples

### Test with bootstrap admin credentials
```bash
bash tests/working_sections_tests/test_working_sections.sh admin@beyo.dev Admin1234!
```

### Test with any authenticated user
```bash
bash tests/working_sections_tests/test_working_sections.sh user@example.com UserPassword123!
```

## Prerequisites

- API server running on `http://localhost:8000` (or set `BASE_URL` env var)
- User exists and credentials are correct
- User has required role permissions (admin or manager for write operations)

## Test Coverage

The test script validates:

1. **Authentication** — Sign in with provided email/password
2. **Create** (PUT /api/v1/working-sections) — Create working section with optional dependencies
3. **Read** (GET /api/v1/working-sections/{id}) — Retrieve section with full payload (name, image, dependencies, etc.)
4. **List** (GET /api/v1/working-sections) — List sections with pagination (limit/offset)
5. **Edit** (PATCH /api/v1/working-sections/{id}) — Update section name, image, dependencies
6. **Delete** (DELETE /api/v1/working-sections/{id}) — Soft-delete section (excluded from future queries)
7. **Cycle Detection** — Verify 409 response when attempting circular dependencies
8. **Soft-Delete Behavior** — Verify deleted sections don't appear in list and return 404 on get

## Test Workflow

1. Creates `test_section_1_<timestamp>` (no dependencies)
2. Creates `test_section_2_<timestamp>` depending on section 1
3. Retrieves section 1 and verifies full payload
4. Retrieves section 2 and verifies dependency linkage
5. Lists all sections and counts
6. Edits section 1 (rename + image update)
7. Attempts circular dependency (expects 409)
8. Deletes section 1 (soft-delete)
9. Verifies deletion behavior (excluded from list, 404 on get)

## Environment Variables

- `BASE_URL` — API base URL (default: `http://localhost:8000`)

## Exit Codes

- `0` — All tests passed
- `1` — Authentication failed or a test failed

## Notes

- Each test run uses a unique timestamp suffix to ensure section name uniqueness
- Soft-delete means sections remain in the database but are excluded from normal queries
- Cycle detection prevents circular dependency chains
- Tests require write permissions (admin/manager role)
