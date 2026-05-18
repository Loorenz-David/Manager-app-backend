# SUMMARY_customer_crud_20260517

## Metadata

- Summary ID: `SUMMARY_customer_crud_20260517`
- Status: `summarized`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Created at (UTC): `2026-05-17T21:10:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_customer_crud_20260517.md`

## What was implemented

- Added new customer command package with request parsing and normalization utilities.
- Implemented CMD-1 `create_customer` with required contact guard (`email` or `phone`).
- Implemented CMD-2 `update_customer` using `model_fields_set` semantics (omit vs explicit null).
- Implemented CMD-3 `delete_customer` as soft-delete only.
- Implemented CMD-4 `find_or_create_customer` matching by normalized email/phone with `was_created` return flag.
- Added customer serializers in domain layer for list/detail payloads, including linked item serialization via item serializer.
- Added customer queries:
  - QUERY-1 `list_customers` with offset pagination and `q` + `string_filters` via `apply_string_filter`.
  - QUERY-2 `get_customer` with linked items joined through `tasks -> task_items` and batched item issue counts.
- Added and registered `/api/v1/customers` router with route-order safety (`/find-or-create` before `/{client_id}`).
- Added formal bash test suite in `backend/tests/costumer` following working_sections shell-test style.

## Files changed

- `backend/app/beyo_manager/services/commands/customers/__init__.py`
- `backend/app/beyo_manager/services/commands/customers/requests/__init__.py`
- `backend/app/beyo_manager/services/commands/customers/create_customer.py`
- `backend/app/beyo_manager/services/commands/customers/update_customer.py`
- `backend/app/beyo_manager/services/commands/customers/delete_customer.py`
- `backend/app/beyo_manager/services/commands/customers/find_or_create_customer.py`
- `backend/app/beyo_manager/services/queries/customers/__init__.py`
- `backend/app/beyo_manager/services/queries/customers/customers.py`
- `backend/app/beyo_manager/domain/customers/serializers.py`
- `backend/app/beyo_manager/routers/api_v1/customers.py`
- `backend/app/beyo_manager/routers/api_v1/__init__.py`
- `backend/tests/costumer/test_costumer.sh`
- `backend/tests/costumer/README.md`

## Contract adherence

- `backend/architecture/06_commands_local.md`: all customer commands use `maybe_begin`, no manual commit/rollback.
- `backend/architecture/07_queries_local.md`: QUERY-1 uses offset pagination with `limit + 1` has_more detection.
- `backend/architecture/09_routers.md`: thin handlers, `run_service` pattern, static route declared before wildcard, PATCH uses `exclude_unset=True`.
- `backend/architecture/55_query_filters_local.md`: string filtering implemented via `apply_string_filter` with explicit allowed-column map.
- `backend/task_system/backend_contract_goal_mapping_guide.md`: selected minimal core + CRUD contract set, including local precedence.

## Validation evidence

- Import smoke:
  - `cd backend/app && ./.venv/bin/python -c "from beyo_manager import create_app; create_app(); print('OK')"`
  - Result: `OK`
- Command transaction rule check:
  - `rg -n "ctx\.session\.begin" backend/app/beyo_manager/services/commands/customers/`
  - Result: no matches
- Router registration check:
  - `rg -n "customers" backend/app/beyo_manager/routers/api_v1/__init__.py`
  - Result: import + include_router present
- Route ordering check:
  - `rg -n "find-or-create|/\{client_id\}" backend/app/beyo_manager/routers/api_v1/customers.py`
  - Result: `/find-or-create` appears before wildcard routes
- Formal endpoint suite:
  - `cd backend && bash tests/costumer/test_costumer.sh admin@beyo.dev Admin1234!`
  - Result: all steps passed (create/get/list/patch/find-or-create/delete)

## Known gaps or deferred items

- No dedicated test fixture setup for linked task-item chains was added; QUERY-2 linked items were validated for shape and compatibility, not expanded fixture scenarios.
- No migration work was required by this scope and none was added.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_customer_crud_20260517.md`
