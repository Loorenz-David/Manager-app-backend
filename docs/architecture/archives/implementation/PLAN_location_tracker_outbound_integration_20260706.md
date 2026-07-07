# PLAN_location_tracker_outbound_integration_20260706

## Metadata

- Plan ID: `PLAN_location_tracker_outbound_integration_20260706`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T00:00:00Z`
- Last updated at (UTC): `2026-07-06T17:56:24Z`
- Related issue/ticket: `N/A`
- Intention plan: `N/A`

## Goal and intent

- Goal: Create a new external integration, **location-tracker**, under `services/infra/`, starting with the **outbound** direction (this app → location-tracker). Deliver:
  1. An infra HTTP client (adapter) that authenticates with a Bearer API key and calls two location-tracker endpoints:
     - `PATCH manager-app/items/location` — push a list of item position changes.
     - `GET  manager-app/items/location` — query item locations by `q` and `item_identity`.
  2. The PATCH push runs as a **background job on the existing general worker** (`tasks_worker`, `queue:tasks`), retried up to 3 attempts via the execution-task `max_try` mechanism. The GET runs as a **synchronous query** (real-time read).
  3. A new `api_v1` router file dedicated to this integration exposing both operations to our own frontend (more endpoints — inbound — added later).
  4. Config + `.env` wiring for the API key and base URL.
- Business/user intent: Keep item positions in sync with, and searchable from, the external location-tracker system, behind a clean adapter so the rest of the app never imports the integration's transport details, and so the position push is durable and non-blocking.
- Non-goals:
  - **Inbound** direction (location-tracker → this app / webhooks). Explicitly future / out of scope (confirmed).
  - No DB model, table, or migration for location data — nothing about locations is persisted in our DB. (The only DB rows created are the standard `ExecutionTask` + `ExecutionPayload` for the background job.)
  - No new worker process — reuse the existing `tasks_worker` / `queue:tasks`.
  - No socket/domain event on success ("when ok it does nothing after").
  - No changes to the local `Item` model or existing item flows.

## Scope

- In scope:
  - `services/infra/location_tracker/` adapter package: `client.py`, `constants.py`, `mapper.py`, `models.py`, `__init__.py`, plus a `get_location_tracker_client()` factory that injects credentials from config.
  - New `TaskType.LOCATION_TRACKER_PUSH_LOCATIONS`, its payload dataclass, queue mapping, worker handler registration, and the handler itself.
  - Outbound PATCH command (enqueues the job) + outbound GET query (synchronous).
  - Request models (pydantic) + parse helpers for both operations.
  - New router `routers/api_v1/location_tracker.py` with a PATCH and a GET endpoint, registered in `routers/api_v1/__init__.py`.
  - Config: `LOCATION_TRACKER_API_KEY`, `LOCATION_TRACKER_BASE_URL`, `LOCATION_TRACKER_TIMEOUT_SECONDS` (default 10) in `config.py`; matching keys in `.env` and `.env.example`.
- Out of scope:
  - Inbound services, webhook receipt, signature verification.
  - Any DB persistence of location data.
  - Triggering the push automatically from `update_item` / `batch_update_item_positions` (this delivers the router-triggered path only).
  - A dedicated new worker or queue (reuse `queue:tasks`).
- Assumptions:
  - The location-tracker host/base URL is supplied via `LOCATION_TRACKER_BASE_URL`; relative paths (`manager-app/items/location`) are joined onto it.
  - Our new `api_v1` endpoints are protected by `require_roles([ADMIN, MANAGER, SELLER, WORKER])`; the Bearer API key authenticates **us → location-tracker** (outbound), not callers to us.
  - `item_identity`, when omitted, defaults to both `article_number` and `sku`; any value outside `{article_number, sku}` is a validation error.
  - `username` on a PATCH entry defaults to `ctx.identity.get("username")` when not supplied by the caller; it is resolved at enqueue time and stored in the job payload.

## Clarifications required

- [x] **Base URL** — RESOLVED: supplied via env var `LOCATION_TRACKER_BASE_URL`. Factory raises a clear config error if unset at runtime.
- [x] **Sync inline vs. background job for the PATCH push** — RESOLVED: **background job** on the existing `tasks_worker` (`queue:tasks`), retried via execution-task `max_try=3`. The infra client performs a single attempt and raises on failure; the worker owns retries/backoff.
- [x] **Router roles** — RESOLVED: `require_roles([ADMIN, MANAGER, SELLER, WORKER])`.
- [x] **API key placement** — RESOLVED: the requester will set the real key in `.env` at implementation time; `.env.example` ships empty.
- [x] **PATCH input source** — RESOLVED: the PATCH endpoint receives the full list of `{position, item_targets, username}` entries in the request body. This was implemented directly from the caller payload.
- [x] **GET failure behavior** — RESOLVED: outbound GET failures surface `ExternalServiceError` (502) to the frontend. The query does not degrade to an empty list.

## Acceptance criteria

1. `services/infra/location_tracker/client.py` exposes async methods to (a) PATCH a list of position-change objects and (b) GET item locations, each with an explicit timeout, sending `Authorization: Bearer <LOCATION_TRACKER_API_KEY>`, and raising `ExternalServiceError` on transport error / non-2xx. **Single attempt, no internal retry loop.** The client receives `api_key` and `base_url` via constructor injection — it never reads `settings`/`os.environ` internally (per `19_integrations.md`).
2. PATCH path: the router/command validates each entry (`position` mandatory; `item_targets` contains at least one of `article_number`/`sku`), defaults `username` from identity, and enqueues a `TaskType.LOCATION_TRACKER_PUSH_LOCATIONS` execution task via `create_instant_task(..., max_try=3)` inside an open transaction. The endpoint returns immediately (e.g. `{"enqueued": True, "task_client_id": ...}`).
3. The worker handler `handle_push_item_locations(raw_payload, task_client_id)` builds the client from the factory and calls `patch_item_locations(...)`. On 2xx it returns (task → COMPLETED, nothing further). On failure it raises; the worker increments `try_count` and reschedules with backoff until `max_try=3`, after which the task is FAIL. The handler is registered in `tasks_worker.HANDLER_MAP` and the type is mapped to `queue:tasks` in `task_router.QUEUE_MAP`.
4. GET path: a synchronous query service rejects `item_identity` values outside `{article_number, sku}`, forwards `q` and comma-joined `item_identity` to location-tracker, and returns a list of `{item_article_number, sku, item_position}` objects mapped via `mapper.py` (raw response never leaves the infra layer).
5. `routers/api_v1/location_tracker.py` defines a PATCH and a GET endpoint, both `require_roles([ADMIN, MANAGER, SELLER, WORKER])`, wired through `run_service` + `ServiceContext` + `build_ok/build_err`, registered in `routers/api_v1/__init__.py` under prefix `/api/v1/location-tracker`.
6. `config.py` defines `LOCATION_TRACKER_API_KEY`, `LOCATION_TRACKER_BASE_URL`, `LOCATION_TRACKER_TIMEOUT_SECONDS` (default 10); `.env` will hold the real key (set by requester); `.env.example` lists the keys empty/placeholder.
7. No DB **migration** is produced (no model change). App + worker import and start; OpenAPI shows the two new endpoints.
8. Tests (per `19_integrations.md`) monkeypatch the client — no test hits a real network; a test asserts the handler raising causes a job retry path (or, minimally, that the handler propagates the client error).

## Contracts and skills

Resolution per `task_system/backend_contract_goal_mapping_guide.md`. Contracts live in `backend/architecture/`.

### Contracts loaded

Selected — core (always):
- `architecture/01_architecture.md`: layering (infra / services / routers / tasks).
- `architecture/04_context.md`: `ServiceContext` (identity, query_params, incoming_data, session).
- `architecture/05_errors.md`: raising/surfacing `ExternalServiceError` + validation errors.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: the PATCH enqueue modeled as a command (`run_service`, `maybe_begin`, `create_instant_task` inside an open transaction per the factory's contract); local adds transaction/session rules.
- `architecture/07_queries.md` + `architecture/07_queries_local.md`: the GET modeled as a query service returning a list.
- `architecture/09_routers.md`: new router file, handler skeleton, `build_ok/build_err`, registration.
- `architecture/21_naming_conventions.md`: package/module/enum/env-var naming (`location_tracker`, `LOCATION_TRACKER_*`, `LOCATION_TRACKER_PUSH_LOCATIONS`).
- `architecture/40_identity.md`, `architecture/41_user.md`: deriving `username`/actor from identity for the PATCH `username` field and `requested_by_user_id`.

Added from guide — primary goal bundle: **External integration**
- `architecture/19_integrations.md`: **primary**. Adapter pattern (`services/infra/<integration>/client.py` + `mapper.py`), credential injection from config, explicit timeout, background-job delegation for external writes, mapper pattern (raw → domain), and integration test isolation.

Added from guide — trigger expansion: **background job / worker / retry** ("worker", "retry" → `16`, `12`, `51`)
- `architecture/16_background_jobs.md`: `create_instant_task`, payload, handler, `max_try` retry semantics — governs the PATCH job.
- `architecture/51_worker_runtime.md`: worker handler registration and runtime (`tasks_worker`, `queue:tasks`, handler signature `(raw_payload, task_client_id)`).
- `architecture/08_domain.md`: adding the new `TaskType` enum value and its payload dataclass (domain-owned).

Added — supporting:
- `architecture/28_roles_permissions.md`: `require_roles([...])` on the two endpoints.
- `architecture/15_testing.md`: test structure, combined with `19`'s monkeypatch isolation.
- `architecture/17_logging.md`: structured warning logs on outbound timeout/failure.

### Local extensions loaded

- `architecture/06_commands_local.md` — `maybe_begin` + session/event rules (baseline `06_commands.md`).
- `architecture/07_queries_local.md` — offset pagination override (baseline `07_queries.md`); external results are not DB-paginated, loaded per protocol.

Read order / precedence: canonical first, then `_local.md`; local overrides baseline for this app only.

### Excluded contracts

- `architecture/03_models.md`, `architecture/30_migrations.md` — no DB model or schema change (execution-task rows use existing tables).
- `architecture/46_serialization.md` (+local) — no ORM serialization; external→domain mapping uses `19`'s mapper; responses are plain dicts.
- `architecture/11_infra_events.md`, `architecture/13_sockets.md`, `architecture/42_event.md` (beyond baseline) — no domain/socket events emitted (success is silent by requirement).
- `architecture/12_infra_redis.md` — the job is enqueued through `create_instant_task` + the existing `QUEUE_MAP`; no direct Redis code is written, so loaded only if queue internals need inspection.
- `architecture/55` (string search) — `q` is forwarded to the external app; no local DB `ilike`.
- `architecture/02` (request timeout) — concerns inbound request middleware, not the outbound call timeout (covered by `19`).

### File read intent — pattern vs. relational

Relational reads already performed (understanding what exists — permitted): `services/infra/selfmade/client.py`, `services/infra/nevotex/client.py` (outbound httpx client shape, `ExternalServiceError`, timeout); `config.py` (`Field(alias=...)` pattern, `beyo_vintage_api_key`); `.env.example`; `routers/api_v1/__init__.py` (registration); `routers/api_v1/items.py` (`run_service`/`ServiceContext`/`query_params`); `errors/external_service.py`; `workers/tasks_worker.py` (`HANDLER_MAP`); `services/infra/execution/task_router.py` (`QUEUE_MAP`); `domain/execution/enums.py` (`TaskType`); `domain/execution/payloads/send_email_messages.py` (payload dataclass shape); `services/infra/execution/task_factory.py` (`create_instant_task(max_try=3)`); `services/infra/execution/worker_base.py` (handler signature + retry-on-exception); `services/tasks/emails/handle_send_email_messages.py` (handler precedent).

Prohibited (pattern reads): do not open further commands/queries/routers/handlers to "learn the shape" — `06/07/09/16/51` + `19` define it; the files above were read once as concrete precedents.

### Skill selection

- Primary skill: `N/A` (integration from contract `19` + background-job pattern `16/51` + existing precedents).
- Router trigger terms: `external integration, outbound HTTP, background job, worker, retry, api key`.
- Excluded alternatives: none.

## Implementation plan

**A. Config + env**
1. `config.py`: add
   - `location_tracker_api_key: str | None = Field(default=None, alias="LOCATION_TRACKER_API_KEY")`
   - `location_tracker_base_url: str | None = Field(default=None, alias="LOCATION_TRACKER_BASE_URL")`
   - `location_tracker_timeout_seconds: float = Field(default=10.0, alias="LOCATION_TRACKER_TIMEOUT_SECONDS")`
2. `.env`: add `LOCATION_TRACKER_API_KEY=` (requester fills real key) and `LOCATION_TRACKER_BASE_URL=<value>`.
3. `.env.example`: add `LOCATION_TRACKER_API_KEY=` and `LOCATION_TRACKER_BASE_URL=` (empty), grouped with the other integration keys.

**B. Infra adapter package** `services/infra/location_tracker/`
4. `models.py`: dataclasses — `ItemLocationTarget(article_number, sku)`, `ItemPositionChange(position, item_targets, username)`, `LocationItem(item_article_number, sku, item_position)`.
5. `constants.py`: `ITEMS_LOCATION_PATH = "manager-app/items/location"` and `bearer_headers(api_key)` → `{"Authorization": f"Bearer {api_key}", "Accept": "application/json"}`.
6. `client.py`: `class LocationTrackerClient(__init__(self, base_url, api_key, timeout_seconds))` (credentials injected). Methods:
   - `async patch_item_locations(self, changes: list[dict]) -> None`: single PATCH with the list body + Bearer headers + `httpx.Timeout`; on transport error / non-2xx raise `ExternalServiceError`; on 2xx return `None`. **No retry loop** (worker owns retries).
   - `async get_item_locations(self, q: str, item_identity: list[str]) -> list[dict]`: GET with params `{"q": q, "item_identity": ",".join(item_identity)}`; timeout; raise `ExternalServiceError` on error/non-200; return parsed JSON list.
7. `mapper.py`: `map_location_items(raw: list[dict]) -> list[LocationItem]`.
8. `__init__.py`: `get_location_tracker_client() -> LocationTrackerClient` factory reading `settings` and injecting `base_url/api_key/timeout` — the only place `settings` is touched; raise a clear config error if `base_url`/`api_key` unset.

**C. Domain (job type + payload)**
9. `domain/execution/enums.py`: add `LOCATION_TRACKER_PUSH_LOCATIONS = "location_tracker_push_locations"` to `TaskType` (in the integrations group near the email types).
10. `domain/execution/payloads/location_tracker_push.py`: `@dataclass(frozen=True) class LocationTrackerPushPayload` with `changes: list[dict]` (each: `position`, optional `article_number`/`sku`, optional `username`), `requested_by_user_id: str | None = None`. (Store entries as plain dicts so the payload is JSON-serializable.)

**D. Worker wiring + handler**
11. `services/infra/execution/task_router.py`: add `TaskType.LOCATION_TRACKER_PUSH_LOCATIONS: "queue:tasks"` to `QUEUE_MAP`.
12. `services/tasks/location_tracker/handle_push_item_locations.py`: `async def handle_push_item_locations(raw: dict, task_client_id: str) -> None` — `payload = LocationTrackerPushPayload(**raw)`, `client = get_location_tracker_client()`, `await client.patch_item_locations(payload.changes)`. Let `ExternalServiceError` propagate (worker retries up to `max_try`). Log start/success/failure like `handle_send_email_messages`.
13. `workers/tasks_worker.py`: import the handler and add `TaskType.LOCATION_TRACKER_PUSH_LOCATIONS: handle_push_item_locations` to `HANDLER_MAP`.

**E. Application services**
14. `services/commands/location_tracker/requests/__init__.py`: pydantic `PushItemLocationsRequest(entries: list[PushItemLocationEntry])` (non-empty, ≤200) where `PushItemLocationEntry` validates `position` non-empty and `item_targets` has ≥1 of `article_number`/`sku`; plus `parse_push_item_locations_request`. Also `SearchItemLocationsRequest`/parser validating `item_identity ⊆ {article_number, sku}` (default both) and `q`.
15. `services/commands/location_tracker/push_item_locations.py`: `async def push_item_locations(ctx)` — parse; default each entry `username` to `ctx.identity.get("username")`; build `changes` dicts; `async with maybe_begin(ctx.session): task = await create_instant_task(session=ctx.session, task_type=TaskType.LOCATION_TRACKER_PUSH_LOCATIONS, payload=asdict(LocationTrackerPushPayload(changes=changes, requested_by_user_id=ctx.user_id)), max_try=3)`. Return `{"enqueued": True, "task_client_id": task.client_id, "queued_count": len(changes)}`.
16. `services/queries/location_tracker/search_item_locations.py`: `async def search_item_locations(ctx)` — read `q`/`item_identity` from `ctx.query_params`, validate, call `get_location_tracker_client().get_item_locations(...)`, map via `map_location_items`, return the list of dicts.

**F. Router**
17. `routers/api_v1/location_tracker.py`: `router = APIRouter()`; PATCH body mirroring `PushItemLocationsRequest`.
    - `@router.patch("/items/location")` → `require_roles([ADMIN, MANAGER, SELLER, WORKER])`, `ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)`, `run_service(push_item_locations, ctx)`, `build_ok/build_err`.
    - `@router.get("/items/location")` → same roles; `q: str`, `item_identity: str | None = Query(None)` (comma-separated); `ServiceContext(incoming_data={}, query_params={"q": q, "item_identity": item_identity}, identity=claims, session=session)`, `run_service(search_item_locations, ctx)`.
18. `routers/api_v1/__init__.py`: import `location_tracker`; `app.include_router(location_tracker.router, prefix="/api/v1/location-tracker", tags=["location-tracker"])`.

**G. Tests** (per `19` + `15`)
19. Monkeypatch the client: PATCH command enqueues a task with the right type/payload; GET query maps response and rejects invalid `item_identity`; entry validation (missing position / empty item_targets); handler propagates `ExternalServiceError` on client failure (retry path). No network.

## Risks and mitigations

- Risk: Client reads credentials from `settings`/`os.environ` internally → violates `19` and hurts testability.
  Mitigation: Only `get_location_tracker_client()` touches `settings`; client takes constructor args (Acceptance #1).
- Risk: Double retry (client loop + worker `max_try`).
  Mitigation: Client does a **single** attempt and raises; retries are owned solely by the worker via `max_try=3` (Acceptance #1/#3).
- Risk: New `TaskType` not wired in all three places (enum, `QUEUE_MAP`, `HANDLER_MAP`) → task routed with "no queue mapped" or "no handler".
  Mitigation: Steps 9/11/13 enumerate all three; Validation asserts enqueue → processed.
- Risk: Payload not JSON-serializable (dataclasses of dataclasses).
  Mitigation: `changes` stored as plain dicts; payload via `asdict(...)` (Step 10/15).
- Risk: Missing base URL / key blocks calls.
  Mitigation: Factory raises a clear config error; `.env.example` documents the keys (Acceptance #6).
- Risk: `create_instant_task` called outside a transaction (factory requires an open tx).
  Mitigation: Wrap in `maybe_begin(ctx.session)` (Step 15).
- Risk: Secrets in logs.
  Mitigation: Never log the API key / full Authorization header; log status + path only.

## Validation plan

- App + worker import cleanly (`python -c "import beyo_manager"`; `python -m beyo_manager.workers.tasks_worker` starts and lists the new handler). OpenAPI shows `PATCH/GET /api/v1/location-tracker/items/location`.
- Enqueue smoke: call the PATCH endpoint → an `ExecutionTask` of type `location_tracker_push_locations` is created OPEN; the router registers `queue:tasks`; with the worker running against a stubbed client, the task reaches COMPLETED on 2xx and RETRY_SCHEDULED→FAIL after 3 failures.
- GET smoke (stubbed client): returns mapped list; invalid `item_identity` → validation error (400); client error → 502 (default) per Clarification.
- `pytest` on the new tests (client monkeypatched): all pass.
- Confirm **no** new file under `app/migrations/versions/`.

## Review log

- `2026-07-06` `owner`: initial draft (synchronous design).
- `2026-07-06` `owner`: revised to background-job design on the existing `tasks_worker` (`queue:tasks`, `max_try=3`); roles set to `[ADMIN, MANAGER, SELLER, WORKER]`; base URL + API key confirmed via env vars. Added contracts `16`, `51`, `08`; retry moved from client to worker.
- `2026-07-06` `codex`: implemented the location-tracker outbound adapter, queued PATCH command, synchronous GET query, worker handler, router registration, config/env wiring, and tests; resolved the remaining input-source and GET-failure decisions using the default assumptions.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
