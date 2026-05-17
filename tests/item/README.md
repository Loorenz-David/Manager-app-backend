# Item CRUD Test Suite

Comprehensive test suite for the item endpoints, including create, read, list, edit, delete, and related entity composition (issues, upholstery, requirements).

## Test Coverage

The suite validates 6 comprehensive test propositions:

1. **Happy Path**: Create item with embedded issues and upholstery, retrieve with composition, update, and delete
2. **Atomicity**: Failed related entity creation (e.g., invalid upholstery) rolls back entire item transaction
3. **Isolation**: Create and retrieve items without optional categories or upholstery
4. **Serializers**: Verify item_upholstery_requirements included in all API responses
5. **Query Filters**: Full-text search across 7 columns (article_number, sku, position, designer, issue_name, upholstery_name, upholstery_code)
6. **Soft-Delete & Reuse**: Soft-deleted items can be recreated with identical unique field values

## Prerequisites

- Backend server running (`make run` from `backend/app/`)
- Database accessible at `localhost:5433`
- Python venv configured in `backend/app/.venv/`
- httpx package installed: `pip install httpx`

## Usage

```bash
bash tests/item/test_item.sh [<email> <password>]
```

## Examples

### Test with bootstrap admin credentials (default)
```bash
bash tests/item/test_item.sh
```

### Test with explicit credentials
```bash
bash tests/item/test_item.sh admin@beyo.dev Admin1234!
```

### Test with custom user
```bash
bash tests/item/test_item.sh user@example.com UserPassword123!
```

## Output

The script produces detailed test output with color-coded status:

```
════════════════════════════════════════════════════════════════
TEST: Item CRUD Flow
════════════════════════════════════════════════════════════════

INFO   Authenticating...
OK     ✓ Authenticated as admin@beyo.dev

--- TEST 1: Happy Path ---
INFO   Creating item with issues and upholstery...
OK     ✓ Item created: itm_01KRTHE4MZM831YZVA22MG3DB4
INFO   Getting item...
OK     ✓ Item has composition
...

════════════════════════════════════════════════════════════════
OK     RESULTS: 6/6 passed
════════════════════════════════════════════════════════════════
```

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Troubleshooting

### Server connection refused
```bash
# Ensure server is running
cd backend/app
make run
```

### Authentication failed
- Verify credentials are correct and user exists in database
- Check `.env` file has `JWT_SECRET_KEY` configured

### httpx not installed
```bash
# Install from requirements
cd backend/app
pip install httpx
```

### Unique constraint violations
- Test data uses timestamps to ensure unique article_number/sku values
- If tests fail on create, ensure previous test data was cleaned up (soft-deleted items should not conflict)

## Implementation Notes

- Tests use timestamps in payload values to ensure uniqueness across runs
- Test item category ID: `itc_01KRP1PGHATQD9TH3F0HR93T3B` (hardcoded fixture)
- Test upholstery ID: `uph_test_velvet_001` (hardcoded fixture)
- All API calls include proper Authorization headers with Bearer token
- Request/response handling uses httpx Client with 10-second timeouts
