# Costumer CRUD Test Suite

Comprehensive shell-based test suite for the customers endpoints.

## Usage

```bash
bash tests/costumer/test_costumer.sh <email> <password>
```

## Example

```bash
bash tests/costumer/test_costumer.sh admin@beyo.dev Admin1234!
```

## What it validates

1. Authentication via sign-in endpoint
2. Create customer (`PUT /api/v1/customers`)
3. Get customer detail and response shape (`GET /api/v1/customers/{client_id}`)
4. List customers with `q` + `string_filters` and pagination payload
5. Partial update semantics on PATCH (unset fields remain unchanged)
6. Find-or-create existing customer path (`was_created=false`)
7. Find-or-create create new path (`was_created=true`)
8. Soft-delete customer and verify deleted resource returns 404

## Notes

- Script expects a running backend at `http://localhost:8000` (override with `BASE_URL`).
- Uses timestamped data to avoid collisions across runs.
- Exits with non-zero code on first failed assertion.
