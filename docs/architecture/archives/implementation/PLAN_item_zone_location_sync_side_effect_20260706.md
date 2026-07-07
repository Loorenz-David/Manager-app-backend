# PLAN_item_zone_location_sync_side_effect_20260706

## Metadata

- Plan ID: `PLAN_item_zone_location_sync_side_effect_20260706`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-06T00:00:00Z`
- Last updated at (UTC): `2026-07-06T20:46:46Z`
- Related issue/ticket: `N/A`
- Intention plan: `N/A`
- Builds on: `PLAN_add_item_zone_column_20260706` (item_zone column + write paths — already implemented) and `PLAN_location_tracker_outbound_integration_20260706` (outbound client + `LOCATION_TRACKER_PUSH_LOCATIONS` job — already implemented).

## Goal and intent

- Goal: When an item's `item_zone` is added or updated, fire a side effect that pushes the zone to the location-tracker app as the item's **position** (`PATCH manager-app/items/location`), via the existing background-job pipeline. Wire this into the three item write commands, and extend the post-handling completion flow to record the item's **completion zone** onto `item.item_zone` and push it.
- Business/user intent: Keep the external location-tracker's item position in sync with our `item_zone`, asynchronously and durably, without blocking the request. At post-handling completion, the request carries the **completion zone** (where the item was actually placed at the moment of completion); if the request omits it, we fall back to `task.assortment` (the end-zone goal the user set at the start). That resolved zone is written to `item.item_zone` and pushed. **`item_position` (our column) is never read or written by any part of this feature** — only `item_zone` is.
- Non-goals:
  - No new DB model, column, or migration (`item_zone` already exists).
  - No new external client — reuse `services/infra/location_tracker/` and the existing `TaskType.LOCATION_TRACKER_PUSH_LOCATIONS` job + `handle_push_item_locations` handler on the existing general `tasks_worker` (`queue:tasks`).
  - No inbound integration.
  - No change to the location-tracker PATCH payload shape (`{position, item_targets: [{article_number, sku}], username}`).

## Scope

- In scope:
  1. A shared enqueue helper that, given an item, enqueues a `LOCATION_TRACKER_PUSH_LOCATIONS` job with a single change (`position = item.item_zone`, `item_targets = [{article_number, sku}]`, `username`). Skips silently when there is no zone or no article_number/sku to target. Emits no events; joins the caller's transaction.
  2. Call the helper from the three item write commands when `item_zone` is set/changed: `create_item.py`, `find_or_create_item.py` (create + update branches), `update_item.py`.
  3. Extend `complete_task_post_handling.py`: accept an optional **`completion_zone`** in the request, resolve the effective zone (`request.completion_zone or task.assortment`), write it to the task's PRIMARY item's `item_zone` through the existing item-update logic (so the socket layer fires and the push is enqueued), then complete post-handling. Skip the item write + enqueue entirely when there is no effective zone.
  4. Refactor `update_item` into a subordinate-safe in-session core (`_update_item_in_session(...) -> (Item, pending_events)`) + a thin `update_item(ctx)` wrapper, so post-handling can reuse the item-update socket behavior **without** violating the subordinate event-emission rule (`06_commands_local.md`).
  5. Update `_CompleteTaskPostHandlingBody` (router) and `CompleteTaskPostHandlingRequest` (service) to include `completion_zone: str | None = None`.
- Out of scope:
  - `item_position` (our column) entirely — it is never read or written anywhere in this feature. The three item commands push `item_zone` outbound only; they do not touch `item_position`.
  - A dedicated new `TaskType` / worker (see Clarification #3 — default: reuse).
- Assumptions:
  - The task's item is its **PRIMARY** `TaskItem` (`role == TaskItemRoleEnum.PRIMARY`, `removed_at IS NULL`), resolved to `Item`.
  - `task.assortment` (`String(255) | None` on the `Task`) is the post-handling fallback zone — the end-zone goal set at task creation.
  - The location-tracker client requires at least one of `article_number`/`sku`; if the item has neither, the push is skipped.
  - `username` on the change defaults to `ctx.identity.get("username")`; `requested_by_user_id = ctx.user_id`.

## Clarifications required

- [x] **`item_position` involvement** — RESOLVED: `item_position` is **out of scope entirely**. No flow reads or writes it. Only `item_zone` is updated (item commands push it outbound; post-handling writes it to `item.item_zone`).
- [x] **Post-handling source/semantics** — RESOLVED: the request carries the **completion zone** (actual placement at completion). Effective zone = `request.completion_zone or task.assortment`. That value is written to `item.item_zone` (not `item_position`) and pushed. If neither is present → no item write, no push.
- [ ] **Request key name** — the post-handling request key is renamed to `completion_zone` in this plan (from the earlier `item_zone`). Confirm this exact name, or supply the preferred one (e.g. `item_completion_zone`). Blocks the router body + service request field name only.
- [x] **Reuse vs. dedicated job type** — RESOLVED: **reuse** the existing `LOCATION_TRACKER_PUSH_LOCATIONS` job (identical payload + handler + client; the general `tasks_worker` already processes it). No new `TaskType`/handler.
- [x] **No-target items** — RESOLVED: if the item has neither `article_number` nor `sku`, **skip + log** (cannot address the external item); the helper returns `False`.

## Acceptance criteria

1. A reusable helper (e.g. `services/commands/location_tracker/enqueue_item_zone_push.py::enqueue_item_zone_location_push(session, item, *, username, requested_by_user_id) -> bool`) enqueues exactly one `LOCATION_TRACKER_PUSH_LOCATIONS` execution task (`max_try=3`) with payload `changes = [{position: item.item_zone, item_targets: [{article_number, sku}], username}]`, only when `item.item_zone` is truthy **and** at least one of `article_number`/`sku` is present; otherwise returns `False` and enqueues nothing. It calls `create_instant_task` inside the caller's open transaction and dispatches no events.
2. `create_item`: when the created item has a non-empty `item_zone`, the helper is invoked (inside the command's `maybe_begin`) so a push is enqueued atomically with the insert.
3. `find_or_create_item`: the helper is invoked in the **create** branch when `item_zone` is set, and in the **update** branch when `"item_zone" in request.model_fields_set`.
4. `update_item`: the helper is invoked when `"item_zone" in request.model_fields_set`. `update_item` still emits `item:updated` exactly once, and its public behavior/return is unchanged.
5. `update_item` is split into `_update_item_in_session(session, *, workspace_id, user_id, username, request) -> (Item, list[DomainEvent])` (no dispatch, subordinate-safe) and a thin `update_item(ctx)` wrapper that owns the transaction and dispatches the returned events after commit. The item-update route is unchanged and still works.
6. `complete_task_post_handling`:
   - Accepts `completion_zone: str | None`.
   - Loads the task's PRIMARY item and the task's `assortment`.
   - Computes `effective_zone = (request.completion_zone or task.assortment)` (whitespace-stripped; empty treated as absent).
   - If `effective_zone` is falsy or there is no primary item: performs **no** item write and enqueues **no** push (post-handling completion itself still proceeds as today).
   - Else: writes `item.item_zone = effective_zone` via `_update_item_in_session` (request `{client_id, item_zone: effective_zone}`), which sets the field, enqueues the push once (because `item_zone` is in the field set), and returns the `item:updated` event. `item_position` is never touched.
   - All events (`item:updated` if any + `task_post_handling:completed`) are dispatched **after** the single owning commit; the item write, the post-handling state change, and the job enqueue are atomic in one transaction.
7. `route_complete_task_post_handling` body schema (`_CompleteTaskPostHandlingBody`) includes `completion_zone: str | None = None`, passed through `model_dump(exclude_unset=True)`.
8. No new migration. Reuses the existing job type/handler/client. Tests cover: helper enqueue + skip conditions; each item command triggering enqueue on `item_zone` set/change; post-handling zone resolution (`request.completion_zone` > `task.assortment`), skip-when-neither, and event/enqueue composition; confirmation that `item_position` is never written.

## Contracts and skills

Resolution per `task_system/backend_contract_goal_mapping_guide.md`. Contracts live in `backend/architecture/`.

### Contracts loaded

Selected — core (always):
- `architecture/01_architecture.md`: layering.
- `architecture/04_context.md`: `ServiceContext` (identity/user_id/workspace_id, incoming_data).
- `architecture/05_errors.md`: `NotFound`/`ValidationError` usage.
- `architecture/06_commands.md` + `architecture/06_commands_local.md`: **primary discipline here** — `maybe_begin` propagation, the single-commit rule, and especially the **subordinate event-emission rule** that drives the `update_item` refactor and the post-handling event composition.
- `architecture/09_routers.md`: updating the post-handling body schema; thin handler unchanged otherwise.
- `architecture/21_naming_conventions.md`: helper/module naming.
- `architecture/40_identity.md`, `architecture/41_user.md`: `username` / actor from identity for the change payload.
- `architecture/42_event.md`: `item:updated` / `task_post_handling:completed` event shapes and dispatch-after-commit.
- `architecture/48_presence.md`: baseline (no change).

Added from guide — goal bundle: **CRUD + realtime**
- `architecture/11_infra_events.md`: `event_bus.dispatch`, collecting `pending_events` from subordinate helpers.
- `architecture/13_sockets.md`: the socket layer that `item:updated` drives (the reason to reuse the item-update logic).
- `architecture/15_testing.md`: unit tests for the helper, the command triggers, and post-handling composition.

Added from guide — trigger expansion: **background job / worker** ("worker", "background")
- `architecture/16_background_jobs.md`: `create_instant_task(..., max_try=3)` enqueue inside the transaction; reuse of the existing execution-task pipeline.

Supporting reference (already-implemented integration):
- `architecture/19_integrations.md`: the outbound client/adapter being reused (credential injection, mapper) — no new integration code, referenced for correctness.

### Local extensions loaded

- `architecture/06_commands_local.md` — `maybe_begin`, single-commit point, and the subordinate event rule (baseline `06_commands.md`). **Governs the whole plan.**

### Excluded contracts

- `architecture/03_models.md`, `architecture/30_migrations.md` — no schema change (`item_zone` exists).
- `architecture/08_domain.md`, `architecture/51_worker_runtime.md` — no new `TaskType` or handler (reusing `LOCATION_TRACKER_PUSH_LOCATIONS` + `handle_push_item_locations`); load only if Clarification #3 selects a dedicated type.
- `architecture/07_queries.md` (+local) — the primary-item load is a small in-command read, not a query service.
- `architecture/46_serialization.md` — no response-shape change.
- `architecture/55` (search) — n/a.

### File read intent — pattern vs. relational

Relational reads already performed (permitted): `complete_task_post_handling.py` (current flow + request model), `create_item.py` / `find_or_create_item.py` / `update_item.py` (event dispatch + `_DIRECT_FIELDS` + structure), `create_task.py:161-168` (subordinate `find_or_create_item` call pattern), `transaction.py` (`maybe_begin` semantics), `task_item.py` + `TaskItemRoleEnum` (PRIMARY relationship), `routers/api_v1/tasks.py` (`_CompleteTaskPostHandlingBody`, route), and the already-implemented location-tracker command/handler/payload (`push_item_locations.py`, `handle_push_item_locations.py`, `LocationTrackerPushPayload`).

Prohibited (pattern reads): do not open unrelated commands to re-derive the command/enqueue shape — `06_commands(+local)` and `16_background_jobs` define it; the files above were read once for their concrete behavior.

### Skill selection

- Primary skill: `N/A` (composition of existing commands + existing job; the only non-trivial part is the subordinate-safe refactor, governed by `06_commands_local`).
- Router trigger terms: `side effect, background job, socket event, subordinate command, item update`.
- Excluded alternatives: none.

## Implementation plan

**A. Shared enqueue helper**
1. `services/commands/location_tracker/enqueue_item_zone_push.py`:
   `async def enqueue_item_zone_location_push(session, item, *, username: str | None, requested_by_user_id: str | None) -> bool`.
   - `zone = (item.item_zone or "").strip()`; if not `zone` → return `False`.
   - `target = {k: v for k, v in {"article_number": item.article_number, "sku": item.sku}.items() if v}`; if empty → log + return `False`.
   - `change = {"position": zone, "item_targets": [target], "username": username or None}`.
   - `await create_instant_task(session=session, task_type=TaskType.LOCATION_TRACKER_PUSH_LOCATIONS, payload=asdict(LocationTrackerPushPayload(changes=[change], requested_by_user_id=requested_by_user_id)), max_try=3)`; return `True`. (No event dispatch. Caller owns the transaction.)

**B. Item commands (call the helper inside their `maybe_begin`)**
2. `create_item.py`: after `await ctx.session.flush()` for the item, if `item.item_zone`: `await enqueue_item_zone_location_push(ctx.session, item, username=ctx.identity.get("username"), requested_by_user_id=ctx.user_id)`. (Do not change `item_position` — Clarification #1 default.) The existing `item:created` dispatch is unchanged.
3. `find_or_create_item.py`: in the **update** branch, after applying `_DIRECT_FIELDS`, if `"item_zone" in request.model_fields_set`: call the helper on `existing`. In the **create** branch, after flush, if `item.item_zone`: call the helper on `item`.
4. `update_item.py`: after the mutation, if `"item_zone" in request.model_fields_set`: call the helper on `item` (see refactor in C — the helper call lives in the in-session core so post-handling reuse also triggers it appropriately; but for post-handling the trigger is position-derived, so keep the command-level trigger keyed on `item_zone in model_fields_set`).

**C. `update_item` subordinate-safe refactor**
5. Extract `_update_item_in_session(session, *, workspace_id, user_id, username, request) -> tuple[Item, list[DomainEvent]]` containing the current mutation + history logic; it returns the loaded `item` and `[build_workspace_event(item, "item:updated")]` (collected, **not** dispatched). It performs the `item_zone`-triggered enqueue helper call internally (so both the top-level command and post-handling reuse get the push when `item_zone` changes).
6. Rewrite `update_item(ctx)` as: parse request → `async with maybe_begin(ctx.session): item, events = await _update_item_in_session(...)` → `await event_bus.dispatch(events)` after the block → return `{"client_id": item.client_id}`. Route unchanged.

**D. Post-handling extension**
7. `complete_task_post_handling.py`:
   - Add `completion_zone: str | None = None` to `CompleteTaskPostHandlingRequest`.
   - Add `_load_primary_item(session, workspace_id, task_id) -> Item | None` (join `TaskItem` PRIMARY + `Item`, `removed_at IS NULL`, `is_deleted == False`) and load `task.assortment` for the resolved `task_id` (a small select on `Task`).
   - Inside the existing `maybe_begin` block, after resolving the post-handling `instance` and its `task_id`: compute `effective_zone = ((request.completion_zone or task_assortment) or "").strip() or None`.
   - If there is a primary `item` and `effective_zone`: call `_update_item_in_session(session, workspace_id=ctx.workspace_id, user_id=ctx.user_id, username=ctx.identity.get("username"), request=UpdateItemRequest(client_id=item.client_id, item_zone=effective_zone))`; extend `pending_events` with the returned `item:updated` event. The core sets `item.item_zone`, enqueues the push once (via the `item_zone`-triggered helper), and touches nothing else. No separate/explicit enqueue call is made here.
   - Keep the existing post-handling state transition + history.
   - After the block: `await event_bus.dispatch(pending_events + [build_workspace_event(instance, "task_post_handling:completed", workspace_id=ctx.workspace_id)])`.
8. `routers/api_v1/tasks.py`: add `completion_zone: str | None = None` to `_CompleteTaskPostHandlingBody` (already passed via `model_dump(exclude_unset=True)`).

**E. Tests**
9. `tests/`: helper enqueues one task / skips on no-zone / skips on no-target; each item command triggers the helper on `item_zone` set/change (monkeypatch `create_instant_task`); post-handling: `request.completion_zone` wins over `task.assortment`, falls back to `task.assortment` when the request omits it, skips when both absent (no item write, no enqueue), writes `item.item_zone` (never `item_position`), and dispatches `item:updated` + `task_post_handling:completed` after commit. Monkeypatch the client/enqueue — no network.

## Risks and mitigations

- Risk: **Double enqueue** in post-handling.
  Mitigation: post-handling never calls the enqueue helper directly — it always writes `item.item_zone = effective_zone` through `_update_item_in_session`, whose single `item_zone`-triggered enqueue fires exactly once. A test asserts one task enqueued per completion with an effective zone, zero otherwise.
- Risk: **Subordinate event-rule violation** — reusing full `update_item` inside post-handling would dispatch `item:updated` before the outer commit.
  Mitigation: the `_update_item_in_session` split returns events for the parent to dispatch after commit (Acceptance #5/#6), per `06_commands_local`.
- Risk: `create_instant_task` requires an open transaction.
  Mitigation: the helper is only ever called inside a `maybe_begin` block of the calling command (Acceptance #1).
- Risk: Enqueue fires for an item change that later rolls back.
  Mitigation: enqueue joins the same transaction as the item write; both commit or roll back together.
- Risk: Item has no `article_number`/`sku` → external push cannot target it.
  Mitigation: helper skips + logs (Clarification #4); returns `False`.
- Risk: `item_zone` empty string vs. `None` — whitespace-only should not trigger a push.
  Mitigation: `.strip()` and treat empty as absent in the helper and in `effective_zone`.
- Risk: Behavioral drift in `update_item` from the refactor.
  Mitigation: keep the wrapper's parse/return/dispatch identical; only move the body into the in-session core; the route test must still pass.

## Validation plan

- App imports cleanly; item-update route still returns `{client_id}` and emits `item:updated` once.
- Unit tests (monkeypatched `create_instant_task` / client): all pass; assert exactly one enqueue per triggering path and zero when skipped.
- Enqueue smoke (stubbed client, worker running): updating an item's `item_zone` creates one `location_tracker_push_locations` task whose payload `changes[0].position == item_zone` and `item_targets == [{article_number/sku present}]`.
- Post-handling smoke: `POST /tasks/{id}/post-handling/complete` with `completion_zone` → primary item's `item_zone` updated (not `item_position`), `item:updated` + `task_post_handling:completed` emitted, one push enqueued (position == completion_zone); without `completion_zone` but with `task.assortment` → item_zone set to assortment, one push; with neither → completion succeeds, no item write, no enqueue.
- Confirm **no** new file under `app/migrations/versions/`.

## Review log

- `2026-07-06` `owner`: drafted after tracing the four write sites, the PRIMARY task-item relationship, and the reused `LOCATION_TRACKER_PUSH_LOCATIONS` job. Identified the `update_item` subordinate event-rule conflict as the design-critical point.
- `2026-07-06` `owner`: corrected post-handling semantics — `item_position` is entirely out of scope; the request carries `completion_zone`, the DB fallback is `task.assortment`, and the resolved value is written to `item.item_zone`. Because post-handling now always writes `item_zone`, the earlier double-enqueue risk is eliminated (the `update_item` core enqueues exactly once).

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `claude`
