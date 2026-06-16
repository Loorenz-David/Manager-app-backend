# SUMMARY_PLAN_create_upholstery_order_20260616

## Metadata

- Summary ID: `SUMMARY_PLAN_create_upholstery_order_20260616`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-16T13:34:05Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_order_20260616.md`
- Related debug plan (optional): —

## What was implemented

- Added `CreateUpholsteryOrderRequest` and `parse_create_upholstery_order_request` to the upholstery request module with creation-state, positive-amount, and non-negative-price validation.
- Added the new `create_upholstery_order` command to create an `UpholsteryOrder`, append its initial `UpholsteryOrderHistoryRecord`, and gate inventory allocation side effects to the `ORDERED` creation state only.
- Added the `PUT /api/v1/upholstery-orders` router and registered it in API v1.
- Implemented requirement allocation ordering as requested: explicit priority item-upholstery IDs first, then earliest task deadline, then oldest requirement creation time.

## Files changed

- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added the create-order request model and parser.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py`: added the new create-order command and requirement allocation helper.
- `backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: added the new create-order endpoint.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: registered the upholstery-orders router.
- `backend/docs/architecture/under_construction/implementation/PLAN_create_upholstery_order_20260616.md`: updated lifecycle metadata before archival.

## Contract adherence

- `backend/architecture/06_commands.md`: kept validation in the request parser, owned the transaction in the command, and dispatched events after commit.
- `backend/architecture/09_routers.md`: kept the router thin and delegated orchestration to `run_service`.
- `backend/skills/_shared/quality_gate.md`: kept business logic out of the router and preserved workspace-scoped reads and writes.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py backend/app/beyo_manager/services/commands/upholstery/create_upholstery_order.py backend/app/beyo_manager/routers/api_v1/upholstery_orders.py backend/app/beyo_manager/routers/api_v1/__init__.py`: passed.
- `cd backend/app && .venv/bin/python -c "from beyo_manager.services.commands.upholstery.requests import CreateUpholsteryOrderRequest, parse_create_upholstery_order_request; from beyo_manager.services.commands.upholstery.create_upholstery_order import create_upholstery_order; from beyo_manager.routers.api_v1.upholstery_orders import router; print(CreateUpholsteryOrderRequest.__name__, callable(parse_create_upholstery_order_request), create_upholstery_order.__name__, len(router.routes))"`: passed and printed `CreateUpholsteryOrderRequest True create_upholstery_order 1`.
- `PYTHONPATH=backend/app backend/app/.venv/bin/python -c "from fastapi import FastAPI; from beyo_manager.routers.api_v1 import register_v1_routers; app = FastAPI(); register_v1_routers(app)"`: blocked by missing local settings (`jwt_secret_key`, `database_url`) in this shell environment.

## Known gaps or deferred items

- No live HTTP or database-backed integration test was run in this task.
- Alembic migration work remains out of scope for this plan.
- The linked intention reference is a planning-table document, not a lifecycle intention plan with a linked-implementations table, so no intention-plan progress table was updated here.

## Handoff notes (if needed)

- Future order state-transition commands must own the delayed `ORDERED` side effects for orders created in `draft`, `pending`, or `approved` state.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_create_upholstery_order_20260616.md`
