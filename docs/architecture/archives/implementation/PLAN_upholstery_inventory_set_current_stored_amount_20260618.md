# PLAN_upholstery_inventory_set_current_stored_amount_20260618

## Metadata

- Plan ID: `PLAN_upholstery_inventory_set_current_stored_amount_20260618`
- Status: `archived`
- Owner agent: `gpt-5.3-codex`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Last updated at (UTC): `2026-06-18T14:00:54Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_upholstery_inventory_set_current_stored_amount_20260618.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_set_current_stored_amount_20260618.md`

## Goal and intent

- Goal: Add a dedicated upholstery-inventory router + command that sets only `current_stored_amount_meters` and then recalculates related `ItemUpholsteryRequirement` states using the same stored-pool allocation behavior currently used after stock confirmation.
- Business/user intent: Inventory managers must be able to correct stock to an absolute amount (including decreases), while requirement availability stays consistent with real stock.
- Non-goals:
  - No schema migration.
  - No change to `PATCH /api/v1/upholstery-inventories/{client_id}` planning fields contract.
  - No changes to order lifecycle (`create_upholstery_order`, `receive_upholstery_order`) beyond optional extraction of shared helper logic.

## Scope

- In scope:
  - Add new endpoint to set absolute stored amount only.
  - Add request model/parser for the new operation.
  - Add new command that updates `current_stored_amount_meters`, recomputes `inventory_condition`, and recalculates requirement states.
  - Implement reverse recalculation for decreases: lower-priority `AVAILABLE` requirements are demoted to `NEEDS_ORDERING` when coverage is no longer sufficient.
  - Reuse the same forward allocation semantics used by stock confirmation path (`mode="stored"` allocator behavior).
  - Emit requirement state-change workspace events for changed requirements.
  - Add tests for both increase and decrease scenarios.
- Out of scope:
  - Reworking pooled allocation algorithm internals (`run_skip_and_continue_allocation`) unless strictly required by this route.
  - Notifications redesign (only preserve current behavior; no new notification types).
  - Bulk/multi-inventory adjustment endpoint.
- Assumptions:
  - New amount is absolute and must be `>= 0`.
  - Requirement demotion on stock decrease applies to `AVAILABLE` requirements only.
  - Demotion priority is reverse of availability promotion priority (least-priority available is demoted first).

## Clarifications required

- [x] Confirm endpoint path naming. **Resolved: implemented as `PATCH /api/v1/upholstery-inventories/{client_id}/current-stored-amount`.**
- [x] Confirm whether `ORDERED` requirements should ever be demoted during a stock decrease. **Resolved: only `AVAILABLE` requirements are demoted back to `NEEDS_ORDERING`; `ORDERED` requirements are never demoted.**
- [x] Confirm whether `ORDERED` requirements are candidates for the forward promotion pass. **Resolved: yes — both `ORDERED` and `NEEDS_ORDERING` requirements are forward-pass candidates, matching `_allocate_received_requirements` behavior.**

## Acceptance criteria

1. A new router exists that updates only `current_stored_amount_meters` for an inventory record.
2. Setting stored amount to a higher value can promote eligible requirements to `AVAILABLE` using the same stored-pool allocation semantics as current stock-confirmation flow.
3. Setting stored amount to a lower value demotes least-priority `AVAILABLE` requirements to `NEEDS_ORDERING` until coverage is valid.
4. `inventory_condition` is recomputed after the stored amount change.
5. No N+1 query pattern is introduced in recalculation logic.
6. Workspace-scoped and soft-delete guards remain enforced.
7. Tests cover increase, decrease, no-op amount, not-found, and validation failures.

## Contracts and skills

### Selected contracts

- `../architecture/01_architecture.md`: enforce layer boundaries and dependency direction.
- `../architecture/04_context.md`: `ServiceContext` usage and workspace scoping.
- `../architecture/05_errors.md`: domain error mapping and raising rules.
- `../architecture/06_commands.md`: write-command structure, parse-first flow, transaction boundaries.
- `../architecture/07_queries.md`: read discipline for supporting recalculation data loads.
- `../architecture/09_routers.md`: route shape, dependency injection, and handler order.
- `../architecture/21_naming_conventions.md`: naming for new route, body class, and command file.
- `../architecture/40_identity.md`: `client_id` identity and FK usage.
- `../architecture/41_user.md`: updater attribution patterns (`updated_by_id`).
- `../architecture/42_event.md`: post-commit domain event dispatch conventions.
- `../architecture/48_presence.md`: alignment with viewer-aware downstream notification/event assumptions.
- `../architecture/03_models.md`: model read constraints and relationship-loading discipline.
- `../architecture/08_domain.md`: pure business rules for condition evaluation and allocation math boundaries.
- `../architecture/11_infra_events.md`: event bus usage and post-commit dispatch.
- `../architecture/13_sockets.md`: event naming interoperability with realtime clients.
- `../architecture/15_testing.md`: required command/router test coverage.

### Added from guide

- `../architecture/03_models.md`: included by CRUD + realtime goal bundle.
- `../architecture/08_domain.md`: included by CRUD + realtime goal bundle.
- `../architecture/11_infra_events.md`: included by CRUD + realtime goal bundle; needed for requirement state-change events.
- `../architecture/13_sockets.md`: included by CRUD + realtime goal bundle; backend event naming must remain client-compatible.
- `../architecture/15_testing.md`: included by CRUD + realtime goal bundle; change is stateful and requires regression tests.

### Local extensions loaded

- `../architecture/06_commands_local.md`: local transaction propagation (`maybe_begin`) policy and commit ownership.
- `../architecture/07_queries_local.md`: app-local offset pagination convention awareness (no impact on this command but required by core loading rules).
- `../architecture/40_identity_local.md`: app prefix registry context.
- `../architecture/41_user_local.md`: no additional behavioral delta used in this plan.
- `../architecture/42_event_local.md`: no override currently defined.
- `../architecture/48_presence_local.md`: presence/view local behavior unchanged by this plan.

### Read order

- `../architecture/01_architecture.md` (baseline)
- `../architecture/04_context.md` (baseline)
- `../architecture/05_errors.md` (baseline)
- `../architecture/06_commands.md` (baseline)
- `../architecture/06_commands_local.md` (app delta)
- `../architecture/07_queries.md` (baseline)
- `../architecture/07_queries_local.md` (app delta)
- `../architecture/09_routers.md` (baseline)
- `../architecture/21_naming_conventions.md` (baseline)
- `../architecture/40_identity.md` (baseline)
- `../architecture/40_identity_local.md` (app delta)
- `../architecture/41_user.md` (baseline)
- `../architecture/41_user_local.md` (app delta)
- `../architecture/42_event.md` (baseline)
- `../architecture/42_event_local.md` (app delta)
- `../architecture/48_presence.md` (baseline)
- `../architecture/48_presence_local.md` (app delta)
- `../architecture/03_models.md` (baseline)
- `../architecture/08_domain.md` (baseline)
- `../architecture/11_infra_events.md` (baseline)
- `../architecture/13_sockets.md` (baseline)
- `../architecture/15_testing.md` (baseline)

Applied precedence:
- Local extension overrides baseline only for this app.

### Excluded contracts

- `../architecture/30_migrations.md`: excluded because this plan introduces no schema change.
- `../architecture/12_infra_redis.md`: excluded; no new Redis behavior.
- `../architecture/16_background_jobs.md`: excluded; no new worker flow.
- `../architecture/55_query_filters.md`: excluded; no new list filtering.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** -> read the contract instead (`06_commands.md`, `09_routers.md`, etc.)
- **What exists** -> reading is legitimate (existing behavior, return shapes, field names, module connections)

Prohibited (pattern reads — contract already covers these):
- Reading another command to infer transaction and parser skeleton.
- Reading another router to infer `run_service` wiring pattern.

Permitted (relational reads — understanding what exists):
- Reading `confirm_ordered_to_stock_inventory.py` and `_inventory_mutations.py` to confirm current stock mutation behavior.
- Reading `receive_upholstery_order.py` to confirm pooled stored-mode allocation currently used to move requirements to `AVAILABLE`.
- Reading request parser module to extend with a new command-specific request model.

### Skill selection

- Primary skill: backend contract-governed CRUD + realtime planning (document-only protocol via contract mapping guide).
- Router trigger terms: `router`, `inventory`, `current stored amount`, `recalculation`, `available`, `needs_ordering`.
- Excluded alternatives: worker-runtime skills — excluded because this change is request-time command logic, not asynchronous runtime design.

## Implementation plan

1. Add router surface for absolute stock set
   - File: `backend/app/beyo_manager/routers/api_v1/upholstery_inventories.py`
   - Add body model:
     - `_SetCurrentStoredAmountBody` with `current_stored_amount_meters: Decimal`
   - Add handler:
     - `@router.patch("/{client_id}/current-stored-amount")`
     - role gate `[ADMIN, MANAGER]`
     - `ServiceContext(incoming_data={"client_id": client_id, "current_stored_amount_meters": body.current_stored_amount_meters}, ...)`
     - `run_service(set_current_stored_amount_inventory, ctx)`

2. Add request parser model for the new command
   - File: `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`
   - Add `SetCurrentStoredAmountInventoryRequest`:
     - `client_id: str`
     - `current_stored_amount_meters: Decimal`
     - validator: `>= 0`
     - optional quantization to `_METERS_SCALE` if used by existing request helpers.
   - Add parse function `parse_set_current_stored_amount_inventory_request(data: dict)` with standard pydantic-to-domain ValidationError mapping.

3. Extract shared requirement-ordering helper (prerequisite)
   - **Must be done before steps 4–6.** `_fetch_earliest_ready_by_at` currently lives in `receive_upholstery_order.py` as a module-private function (`_` prefix). Both the demotion pass (step 5) and the forward pass (step 6) need it, and importing a `_`-prefixed function across modules violates encapsulation.
   - Move `_fetch_earliest_ready_by_at` from `receive_upholstery_order.py` into `_pooled_requirement_allocation.py` (alongside `allocate_pooled_requirements` and `calculate_pooled_requirement_pool`).
   - Update the import in `receive_upholstery_order.py` to use the new location.
   - No behavioral change — pure relocation.

4. Implement new command
   - New file: `backend/app/beyo_manager/services/commands/upholstery/set_current_stored_amount_inventory.py`
   - Flow:
     - Parse request.
     - Open transaction with `async with ctx.session.begin()`.
     - Load inventory by workspace + client_id + `is_deleted = false`; raise `NotFound` if absent.
     - **Early exit**: if `request.current_stored_amount_meters == inv.current_stored_amount_meters`, return `{}` immediately — no mutations, no events. Perform this check after the inventory load inside the transaction block.
     - Capture `previous_stored_amount = inv.current_stored_amount_meters`.
     - Set `inv.current_stored_amount_meters = request.current_stored_amount_meters`.
     - Recompute `inv.inventory_condition = evaluate_inventory_condition(...)`.
     - Run requirement recalculation helper(s):
       - reverse pass for decrease (AVAILABLE → NEEDS_ORDERING) — step 5.
       - `await session.flush()` — required before the forward pass SELECT so that demoted requirements (state changed in memory) are visible to the next query. Do not rely on autoflush.
       - forward pass for increase/remaining capacity (ORDERED/NEEDS_ORDERING → AVAILABLE) — step 6.
     - Set `inv.updated_at`, `inv.updated_by_id`.
     - Collect changed requirement IDs by new state.
   - After commit:
     - Dispatch workspace events for changed requirement states (separate event per resulting state to preserve `new_state` clarity in payload).
     - Dispatch only if the respective ID list is non-empty.
   - Return `{}`.

5. Implement reverse recalculation helper (demotion path)
   - Preferred location: private helper in the new command file or extracted shared helper module under `services/commands/upholstery/`.
   - Query candidates:
     - `ItemUpholsteryRequirement` rows where `upholstery_inventory_id = inventory.client_id`, `state = AVAILABLE`, `is_deleted = false`.
   - Priority sorting for demotion (least-priority first = demoted first):
     - Fetch `ready_by_at` per candidate using `fetch_earliest_ready_by_at` (relocated to `_pooled_requirement_allocation.py` in step 3) with the non-pinned candidate IDs.
     - Pass the resulting map to both the demotion sort and the forward pass (step 6) to avoid a duplicate query.
     - Sort key (reverse of promotion order):
       ```python
       rba = ready_by_at_map.get(req.item_upholstery_id)
       key = (
           rba is not None,           # False (no deadline) sorts first → least urgent, demoted first
           -(rba.timestamp() if rba else 0),  # latest deadline sorts before earlier → less urgent
           -req.created_at.timestamp(),       # newest created sorts first → less established
       )
       ```
     - No tier1 concept at demotion time — all AVAILABLE requirements were originally promoted without caller-supplied priority pinning in this command's flow.
   - Demotion algorithm:
     - `sum_available = sum(req.amount_meters or Decimal("0") for req in candidates)`
     - `deficit = max(Decimal("0"), sum_available - new_stored_amount_meters)`
     - If `deficit == 0`: return empty list (no demotions needed).
     - Iterate sorted candidates; for each: demote `req.state = NEEDS_ORDERING`, accumulate `sum_demoted`, break when `sum_demoted >= deficit`.
     - Stamp `req.updated_by_id = actor_id` and `req.updated_at = datetime.now(timezone.utc)` on each demoted requirement.
     - Return list of demoted `item_upholstery_id` values.
   - **Critical invariant**: do NOT update `inv.current_amount_in_need_meters` during demotion. `in_need` is never decremented for AVAILABLE state transitions in this codebase (only decremented at `consume_to_in_use` and `complete_available_direct`). The pool formula in `_pooled_requirement_allocation.py` already accounts for AVAILABLE requirements being included in `in_need`.

6. Reuse existing forward allocation semantics
   - Candidates: `ItemUpholsteryRequirement` rows where `upholstery_inventory_id = inventory.client_id`, `state in (ORDERED, NEEDS_ORDERING)` (including requirements freshly demoted by step 5), `is_deleted = false`. Both ORDERED and NEEDS_ORDERING are included — same policy as `_allocate_received_requirements`.
   - No caller-supplied priority list for this command. Candidates fall into two tiers only:
     - Tier A (ORDERED state): sorted by `(ready_by_at is None, ready_by_at, created_at)`.
     - Tier B (NEEDS_ORDERING state): sorted by `(ready_by_at is None, ready_by_at, created_at)`.
   - Reuse the `ready_by_at` map already fetched in step 5 — do not issue a second `fetch_earliest_ready_by_at` query. Fetch it once for all non-pinned candidate IDs (union of demotion candidates and forward-pass candidates) before either pass runs.
   - Call `allocate_pooled_requirements(inventory=inv, ordered_candidates=tier_a + tier_b, target_state=AVAILABLE, mode="stored", actor_id=ctx.user_id, timestamp_field=None)`.
   - `allocate_pooled_requirements` will compute pool = `stored - (in_need - sum_candidates)`. Because `in_need` includes AVAILABLE amounts and `sum_candidates` covers all NEEDS_ORDERING+ORDERED amounts, pool effectively equals `stored - sum(remaining AVAILABLE amounts)` — correct after the demotion step updated requirement states and the explicit flush in step 4.
   - If code duplication with `_allocate_received_requirements` is high, extract shared helper:
     - e.g. `_recalculate_requirements_for_stored_pool(session, workspace_id, inventory, actor_id)` in `_pooled_requirement_allocation.py` or a new private module.

7. Keep event contract stable
   - Event name remains `item:upholstery-requirement-state-changed`.
   - Emit once per state bucket, e.g.:
     - AVAILABLE IDs event
     - NEEDS_ORDERING IDs event
   - Do not dispatch inside transaction block.

8. Add/extend tests
   - Unit tests:
     - extend pooled allocation tests with reverse-demotion scenarios.
     - verify least-priority available gets demoted first.
   - Command tests:
     - set stored amount up: promotes expected candidates to AVAILABLE.
     - set stored amount down: demotes expected available candidates.
     - set unchanged amount: no state churn, no events dispatched.
     - not found inventory → `NotFound`.
     - negative amount → `ValidationError`.
     - after demotion: assert `inv.current_amount_in_need_meters` is unchanged from its pre-command value.
   - Router tests:
     - role access (ADMIN/MANAGER allowed, WORKER denied).
     - payload validation.

9. Update frontend handoff documentation
   - Extend existing handoff doc for upholstery inventories with the new route:
     - request body
     - response shape
     - side-effect notes (requirement state recalculation)

## Risks and mitigations

- Risk: implementer incorrectly updates `current_amount_in_need_meters` during demotion, breaking pool calculations.
  Mitigation: the invariant is stated explicitly in step 4 with the accounting rationale. Unit tests should verify `in_need` is unchanged after demotion.

- Risk: reverse-priority interpretation differs from business expectation.
  Mitigation: explicitly document and test demotion order with deterministic fixtures.

- Risk: divergence between this command and stock-receipt allocation path.
  Mitigation: extract shared ordering/allocation helper to keep a single source of truth.

- Risk: event payload ambiguity when both promotions and demotions happen in one request.
  Mitigation: dispatch separate events per resulting state bucket; skip dispatch if the ID list is empty.

- Risk: floating precision drift for meter values.
  Mitigation: enforce Decimal validation and quantization at parse boundary.

## Validation plan

- Prerequisite (step 3): confirm `_fetch_earliest_ready_by_at` import in `receive_upholstery_order.py` resolves correctly from `_pooled_requirement_allocation.py` after relocation; run existing `receive_upholstery_order` tests to verify no regression.
- Unit: `tests/unit/test_upholstery_pooled_requirement_allocation.py`
  - Add reverse demotion tests and mixed promotion/demotion stability checks.
- Command: add test module for `set_current_stored_amount_inventory` under `tests/unit/services/commands/upholstery/`.
  - Include explicit assertion: after a demotion scenario, `inv.current_amount_in_need_meters` equals its pre-command value.
- Router: add route-level tests under `tests/unit/routers/api_v1/` for the new endpoint.
- Manual API checks:
  - Decrease stored amount below total available demand → lower-priority AVAILABLE requirements become NEEDS_ORDERING.
  - Increase stored amount → eligible ORDERED/NEEDS_ORDERING requirements become AVAILABLE.
  - Inventory condition reflects new stored amount.

## Review log

- `2026-06-18` `gpt-5.3-codex`: Initial implementation plan created from contract-guided analysis and existing upholstery command flow mapping.
- `2026-06-18` `claude-sonnet-4-6`: Plan review against live codebase. Corrections applied:
  - Resolved ORDERED inclusion in forward pass (yes, same as `_allocate_received_requirements`).
  - Resolved ORDERED demotion policy (no, only AVAILABLE is demoted).
  - Step 3 (now step 4): removed `maybe_begin` hedge; added no-op early-exit guard (inside transaction block after load); added explicit `await session.flush()` between demotion and forward pass.
  - Step 4 (now step 5): specified exact deficit formula; added `_fetch_earliest_ready_by_at` JOIN requirement for demotion sort with corrected Python sort key; added `updated_at` stamp; added `in_need` invariant.
  - Step 5 (now step 6): clarified no tier1; documented single shared `ready_by_at` map fetch for both passes; confirmed ORDERED + NEEDS_ORDERING candidate set.
  - New step 3: prerequisite extraction of `_fetch_earliest_ready_by_at` from `receive_upholstery_order.py` into `_pooled_requirement_allocation.py` to enable sharing across modules.
  - Risks: added `in_need` mutation risk as top entry.
  - Validation plan: added prerequisite regression check; added explicit `in_need` unchanged assertion to command tests.
  - Steps renumbered 1–9 to accommodate new prerequisite step.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
