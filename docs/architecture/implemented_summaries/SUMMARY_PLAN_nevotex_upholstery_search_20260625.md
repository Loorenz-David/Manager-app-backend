# SUMMARY_PLAN_nevotex_upholstery_search_20260625

## Metadata

- Summary ID: `SUMMARY_PLAN_nevotex_upholstery_search_20260625`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-25T09:38:21Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_nevotex_upholstery_search_20260625.md`
- Related debug plan (optional): —

## What was implemented

- Added a new Nevotex-backed external upholstery search flow with an async `httpx` client, response-shape validation, and a pure normalizer that maps Nevotex products into the existing upholstery card shape.
- Added `GET /api/v1/upholsteries/external/nevotex` with required `q` validation, external-result limit capping, and standard `run_service` error handling for `502` failures.
- Extended `serialize_upholstery` so all database-backed upholstery responses now include `origin: "database"`.
- Added focused unit coverage for Nevotex candidate normalization and the new serializer `origin` field.

## Files changed

- `backend/app/beyo_manager/errors/__init__.py`: exported the shared error surface, including the new external-service error.
- `backend/app/beyo_manager/errors/external_service.py`: added `ExternalServiceError` with HTTP `502`.
- `backend/app/beyo_manager/services/infra/nevotex/client.py`: added the Nevotex search adapter with timeout, non-200, invalid-JSON, and missing-`Product` handling.
- `backend/app/beyo_manager/services/infra/nevotex/normalizer.py`: added the Nevotex product normalizer and image URL absolutization.
- `backend/app/beyo_manager/services/queries/upholstery/list_nevotex_upholsteries.py`: added the read-only external search query service.
- `backend/app/beyo_manager/routers/api_v1/upholsteries.py`: added `GET /external/nevotex` ahead of the wildcard `/{client_id}` routes.
- `backend/app/beyo_manager/domain/upholstery/serializers.py`: added `origin: "database"` to serialized upholstery results.
- `backend/app/tests/unit/services/infra/nevotex/test_normalizer.py`: added normalizer unit tests.
- `backend/app/tests/unit/test_upholstery_serializers.py`: added coverage for the new serializer origin field.
- `backend/docs/architecture/under_construction/implementation/PLAN_nevotex_upholstery_search_20260625.md`: updated lifecycle metadata and closure notes before archival.

## Contract adherence

- `backend/architecture/05_errors.md`: added a dedicated domain error subclass instead of raising generic exceptions across the service boundary.
- `backend/architecture/09_routers.md`: kept the new route handler thin and declared the static `/external/nevotex` path before `/{client_id}`.
- `backend/architecture/19_integrations.md`: isolated the external API call in an infra adapter with an explicit timeout and graceful failure mapping.
- `backend/architecture/46_serialization.md`: kept normalization/serialization pure and free of DB access.
- `backend/architecture/55_query_filters_local.md`: enforced `q` naming and router-layer `max_length=200` validation.

## Validation evidence

- `./.venv/bin/python -m pytest tests/unit/services/infra/nevotex/test_normalizer.py tests/unit/test_upholstery_serializers.py`: passed (`10 passed`).
- `./.venv/bin/python -m py_compile beyo_manager/errors/__init__.py beyo_manager/errors/external_service.py beyo_manager/services/infra/nevotex/__init__.py beyo_manager/services/infra/nevotex/client.py beyo_manager/services/infra/nevotex/normalizer.py beyo_manager/services/queries/upholstery/list_nevotex_upholsteries.py beyo_manager/routers/api_v1/upholsteries.py beyo_manager/domain/upholstery/serializers.py`: passed.

## Known gaps or deferred items

- No live Nevotex HTTP smoke call was run in this task, so the new adapter was validated by static checks and unit coverage only.
- Category derivation for Nevotex candidates remains deferred exactly as scoped in the plan.

## Handoff notes (if needed)

- Frontend consumers can now distinguish database and Nevotex candidates via the `origin` field without any change to the existing upholstery list response envelope.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_nevotex_upholstery_search_20260625.md`
