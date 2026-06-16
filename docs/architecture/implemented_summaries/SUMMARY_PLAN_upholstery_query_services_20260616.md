# SUMMARY_PLAN_upholstery_query_services_20260616

## Metadata

- Summary ID: `SUMMARY_PLAN_upholstery_query_services_20260616`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-16T15:11:56Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_upholstery_query_services_20260616.md`
- Related debug plan (optional): —

## What was implemented

- Added `get_upholstery_order_needs_count`, `list_upholstery_order_needs`, and `get_upholstery_order_need_items` in a new `upholstery_order_needs.py` query module, including task/item text search, aggregated ordering-need totals, due-date ranking, and task page enrichment with `item_upholstery`.
- Added `get_upholstery_orders_count`, `list_upholstery_orders`, and `list_upholstery_order_items` in a new `upholstery_orders_query.py` module, including optional state filters, joined upholstery metadata, task search across impacted upholsteries, and the same task/item/image batch-load pattern used by the task query service.
- Added the new `GET /api/v1/upholstery-order-needs/count`, `GET /api/v1/upholstery-order-needs`, and `GET /api/v1/upholstery-order-needs/{upholstery_id}/items` router handlers.
- Extended `upholstery_orders.py` with `GET /count`, `GET /`, and `GET /items`, and registered the new `upholstery-order-needs` router in API v1.
- Added an Alembic migration that creates the three workspace-scoped indexes needed by the new upholstery query paths.

## Files changed

- `backend/app/beyo_manager/services/queries/upholstery/upholstery_order_needs.py`: added the new ordering-needs query services.
- `backend/app/beyo_manager/services/queries/upholstery/upholstery_orders_query.py`: added the new upholstery-order query services.
- `backend/app/beyo_manager/routers/api_v1/upholstery_order_needs.py`: added the new read-only upholstery-order-needs router.
- `backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: added the three read-only upholstery-order routes.
- `backend/app/beyo_manager/routers/api_v1/__init__.py`: registered the new router.
- `backend/app/migrations/versions/6787eabf4c32_add_upholstery_query_indexes.py`: added the three missing concurrent indexes.
- `backend/docs/architecture/under_construction/implementation/PLAN_upholstery_query_services_20260616.md`: updated lifecycle metadata and summary notes before archival.

## Contract adherence

- `backend/architecture/07_queries.md` and `backend/architecture/07_queries_local.md`: kept workspace-first filters, read-only service boundaries, and offset pagination with `limit + 1`.
- `backend/architecture/09_routers.md`: kept handlers thin and routed all work through `run_service`.
- `backend/architecture/30_migrations.md`: used an Alembic migration and the concurrent-index pattern for non-blocking index creation.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/services/queries/upholstery/upholstery_order_needs.py backend/app/beyo_manager/services/queries/upholstery/upholstery_orders_query.py backend/app/beyo_manager/routers/api_v1/upholstery_order_needs.py backend/app/beyo_manager/routers/api_v1/upholstery_orders.py backend/app/beyo_manager/routers/api_v1/__init__.py backend/app/migrations/versions/6787eabf4c32_add_upholstery_query_indexes.py`: passed.
- `rg -n "route_get_upholstery_order_needs_count|route_list_upholstery_order_needs|route_get_upholstery_order_need_items" backend/app/beyo_manager/routers/api_v1/upholstery_order_needs.py`: returned all three handlers.
- `rg -n "route_get_upholstery_orders_count|route_list_upholstery_orders|route_list_upholstery_order_items" backend/app/beyo_manager/routers/api_v1/upholstery_orders.py`: returned all three handlers.
- `rg -n "upholstery_order_needs" backend/app/beyo_manager/routers/api_v1/__init__.py`: returned the import and `include_router` registration.
- `PYTHONPATH=backend/app backend/app/.venv/bin/python -c "..."`: blocked by missing local settings (`jwt_secret_key`, `database_url`) during app config initialization, so no import-level runtime boot check was completed.

## Known gaps or deferred items

- No DB-backed integration query or live HTTP endpoint test was run in this task.
- The app-level import/bootstrap check is still blocked in this shell without required settings.

## Handoff notes (if needed)

- If query latency becomes a problem in production, the first place to inspect is the aggregate/order-by path in `list_upholstery_order_needs`, because it still traverses the task chain to produce ordering priority.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_upholstery_query_services_20260616.md`
