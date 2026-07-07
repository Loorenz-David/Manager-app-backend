# SUMMARY_PLAN_location_tracker_outbound_integration_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_location_tracker_outbound_integration_20260706`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T17:56:24Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_location_tracker_outbound_integration_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Added the `services/infra/location_tracker/` adapter package with a credential-injected HTTP client, constants, dataclass models, and a raw-response mapper.
- Added config/env wiring for `LOCATION_TRACKER_API_KEY`, `LOCATION_TRACKER_BASE_URL`, and `LOCATION_TRACKER_TIMEOUT_SECONDS`.
- Added the new execution task type `location_tracker_push_locations`, its payload dataclass, queue routing, worker handler registration, and the handler that reuses the shared location-tracker client.
- Added the outbound PATCH command that validates the request body, normalizes item targets and usernames, and enqueues a `queue:tasks` execution task with `max_try=3`.
- Added the synchronous GET query that validates `item_identity`, calls the external service, and returns mapped location records through the normal API response wrapper.
- Added the dedicated `/api/v1/location-tracker` router and registered it in the API v1 router bundle.
- Added focused tests for command enqueueing, request validation, query mapping, and worker error propagation.

## Files changed

- `backend/app/beyo_manager/config.py`: added location-tracker settings.
- `backend/app/beyo_manager/domain/execution/enums.py`, `backend/app/beyo_manager/domain/execution/payloads/location_tracker_push.py`: added the new execution task type and payload.
- `backend/app/beyo_manager/services/infra/location_tracker/*`: added the adapter client, constants, models, mapper, and factory.
- `backend/app/beyo_manager/services/commands/location_tracker/*`, `backend/app/beyo_manager/services/queries/location_tracker/*`, `backend/app/beyo_manager/services/tasks/location_tracker/*`: added the command, query, request models, and worker handler.
- `backend/app/beyo_manager/routers/api_v1/location_tracker.py`, `backend/app/beyo_manager/routers/api_v1/__init__.py`: added and registered the router.
- `backend/app/beyo_manager/services/infra/execution/task_router.py`, `backend/app/beyo_manager/services/infra/execution/worker_base.py`, `backend/app/beyo_manager/workers/tasks_worker.py`: wired the new task into routing and worker handling.
- `backend/.env.example`, `backend/.env`: added the new location-tracker environment keys.
- `backend/tests/tasks/test_location_tracker.py`: added the focused validation and handler tests.

## Contract adherence

- `backend/architecture/06_commands.md` and `06_commands_local.md`: the PATCH path stays command-owned and enqueues inside `maybe_begin(...)`.
- `backend/architecture/07_queries.md` and `07_queries_local.md`: the GET path is a read-only query service.
- `backend/architecture/09_routers.md`: routing remains thin; orchestration stays in services.
- `backend/architecture/16_background_jobs.md` and `51_worker_runtime.md`: the outbound push now uses the existing execution task pipeline and worker queue.
- `backend/architecture/19_integrations.md`: the adapter keeps transport details in infra and receives credentials via constructor injection.

## Validation evidence

- `python3 -m py_compile ...` on all touched Python modules: passed.
- `pytest tests/tasks/test_location_tracker.py`: could not run because `pytest` is not installed in this environment.
- Manual import smoke: blocked by missing runtime dependencies (`fastapi` is not installed in this environment).

## Known gaps or deferred items

- I did not run the new tests under a populated app virtualenv, so behavioral coverage remains statically verified only in this turn.
- The implementation follows the default assumptions from the plan for request-body entries and GET failure behavior.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_location_tracker_outbound_integration_20260706.md`
