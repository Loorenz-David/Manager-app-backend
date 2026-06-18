# PLAN_internal_upholstery_without_requirement_20260617

## Metadata

- Plan ID: `PLAN_internal_upholstery_without_requirement_20260617`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-17T12:23:21Z`
- Last updated at (UTC): `2026-06-17T13:10:16Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`

## Goal and intent

- Goal: Allow `ItemUpholstery` creation with `source=internal`, positive `amount_meters`, and no `upholstery_id`, while intentionally skipping requirement creation and all inventory requirement calculations until an `upholstery_id` is later provided.
- Business/user intent: Support incomplete intake payloads during task and item creation without rejecting the upholstery entry, while avoiding fake or broken inventory linkage when no catalog upholstery has been selected yet.
- Non-goals: No migration. No placeholder `ItemUpholsteryRequirement` row. No change to customer-source behavior. No change to inventory math once an actual `upholstery_id` exists.

## Scope

- In scope:
  - Shared `ItemUpholstery` creation behavior used by task creation, item creation, and standalone item-upholstery creation
  - Validation changes in `create_task`, `create_item`, and standalone `create_item_upholstery`
  - Later-link activation behavior in `update_item_upholstery` when an internal upholstery created without `upholstery_id` is subsequently linked
  - Query-layer corrections so deferred internal upholsteries still appear in manager-facing pending upholstery views as `missing_selection`
  - Specific business-error responses for requirement-dependent actions invoked before upholstery selection is completed
  - PATCH-route/update-path safeguards so omitted fields are not conflated with explicit nulls during first-link activation
  - Tests covering create, serialize, and later-link flows
- Out of scope:
  - Any DB schema change
  - New API fields or wire-format changes
  - Any broader requirement-lifecycle redesign
  - Relaxing the rule for internal upholstery with missing `upholstery_id` and missing quantity
- Assumptions:
  - `amount_meters` request parsing already normalizes `<= 0` to `None` for create flows
  - `active_requirement_id` may safely remain `NULL` on `item_upholsteries`
  - Read serializers already tolerate an empty requirements list and `active_requirement_id=None`

## Clarifications required

- [ ] None — scope and intended lifecycle behavior are fully specified for implementation.

## Acceptance criteria

1. Creating internal `item_upholstery` without `upholstery_id` and with positive `amount_meters` succeeds through all create entrypoints and persists an `ItemUpholstery` row with `active_requirement_id = NULL`.
2. No `ItemUpholsteryRequirement` row is created for that scenario, and no inventory helper is called.
3. Internal create requests with missing `upholstery_id` and no positive `amount_meters` still fail validation.
4. Existing internal create requests with `upholstery_id` continue to create the initial requirement exactly as they do today.
5. Existing customer-source create behavior remains unchanged.
6. Updating one of these internal-no-id records later with a valid `upholstery_id` creates the first active requirement at update time and resumes normal inventory-backed requirement behavior.
7. Seat tasks whose internal upholstery row exists but still has `upholstery_id = NULL` remain visible in the pending upholstery list and counts, and are classified as `missing_selection`.
8. Requirement-dependent commands invoked before upholstery selection return a specific business error explaining that upholstery must be selected first, rather than a generic active-requirement failure.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/under_construction/intention/INTENTION_task_system_20260518.md`: confirms `create_task` is atomic and uses existing session-level helpers for embedded item upholstery.
- `backend/docs/architecture/under_construction/intention/INTENTION_item_crud_and_issues_20260517.md`: confirms `create_item` uses `_create_item_upholstery_in_session` and defines existing item-level create expectations.
- `backend/docs/architecture/implemented_summaries/SUMMARY_item_upholstery_requirement_lifecycle_20260516.md`: confirms the current requirement lifecycle, `active_requirement_id` convention, and inventory mutation expectations.
- `backend/docs/architecture/archives/implementation/PLAN_update_requirement_quantity_20260523.md`: confirms existing command assumptions around active requirements and requirement-dependent quantity mutation behavior.

### Local extensions loaded

- `none`: no separate local contract overlays were found in `backend/docs/architecture`.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract/intention/summary instead
- **What exists** → reading is legitimate

Prohibited (pattern reads — contract already covers these):
- Reading another command only to copy `maybe_begin`, `flush`, or error-raising structure
- Reading another router only to copy handler wiring
- Reading another serializer only to copy response construction style

Permitted (relational reads — understanding what exists):
- Reading the current `create_task`, `create_item`, `create_item_upholstery`, and `update_item_upholstery` implementations to locate existing guards and helper boundaries
- Reading the item and task serializers to verify `active_requirement_id` and empty requirement-list behavior
- Reading requirement mutation commands to identify which commands assume `active_requirement_id` must exist
- Reading pending-upholstery and task query services to verify how deferred internal upholsteries must stay discoverable after creation

### Skill selection

- Primary skill: `n/a (repo-local planning only)`
- Router trigger terms: `task`, `item_upholstery`, `requirement`, `upholstery_id`
- Excluded alternatives: `google-docs`, `documents` — not needed because this is a repo-native markdown plan

## Implementation plan

1. Tighten the business rule into one shared predicate and use it everywhere.
   - Introduce a small private helper near the item-upholstery creation flow that classifies create input into:
     - inventory-linkable now,
     - deferred internal link,
     - invalid.
   - Rule set:
     - `source=customer`: unchanged existing behavior.
     - `source=internal` with `upholstery_id`: unchanged existing behavior.
     - `source=internal` without `upholstery_id` and with positive `amount_meters`: allowed, but requirement creation is deferred.
     - `source=internal` without `upholstery_id` and without positive `amount_meters`: reject.
   - Keep this helper in the shared item-upholstery command layer so task create, item create, and standalone create all consume the same rule.

2. Refactor `_create_item_upholstery_in_session` to make requirement creation conditional.
   - Preserve `ItemUpholstery` row creation exactly as today.
   - Split the current “always create initial requirement” behavior into an explicit branch:
     - if inventory-linkable now, call `_create_initial_requirement_for_item_upholstery(...)`
     - if deferred internal link, skip the call and leave `active_requirement_id=None`
   - Do not create a surrogate `MISSING_QUANTITY` requirement in the deferred branch.
   - Keep the helper return shape unchanged unless implementation requires a small internal-only flag; if a flag is added, it must not affect external API responses.

3. Normalize create-entrypoint validation to match the shared rule.
   - In `create_task`, replace the current unconditional internal-without-id rejection with the new conditional validation.
   - In `create_item`, replace the current unconditional internal-without-id rejection with the same conditional validation.
   - In standalone `create_item_upholstery`, replace the current unconditional internal-without-id rejection with the same conditional validation.
   - Preserve the current item-presence guard in `create_task` and any existing customer-source restrictions.
   - Do not change request schemas; this is service-layer validation only.

4. Define the later-link activation path in `update_item_upholstery`.
   - Support an existing `ItemUpholstery` with `active_requirement_id=None`.
   - If such a row is internal, has positive `amount_meters`, and receives a first valid `upholstery_id`, create the initial requirement at update time by calling the same `_create_initial_requirement_for_item_upholstery(...)` helper.
   - Keep existing swap logic only for rows that already have an active requirement.
   - Do not treat the deferred-internal case as a swap from one requirement to another.
   - Keep rejecting update paths that would require inventory operations without a resolved `upholstery_id`.
   - Update the PATCH path to preserve omitted-vs-explicit-null intent during update evaluation, so first-link activation is driven by actual user-provided changes rather than `model_dump()` default nulls.

5. Preserve downstream invariants and explicit failure modes.
   - Leave serializers unchanged unless a test exposes a gap; they should continue returning:
     - `active_requirement_id: null`
     - `item_upholstery_requirements: []`
   - Leave requirement-mutating commands strict, but replace generic “active requirement not found” style failures with a clearer business error for deferred internal upholsteries, e.g. that upholstery selection must be completed first.
   - Do not silently auto-create requirements from unrelated actions such as quantity-only edits unless `upholstery_id` becomes available.

6. Keep deferred internal upholsteries visible in manager-facing discovery flows.
   - Update the seat-task pending-upholstery query and counts logic so an existing internal `ItemUpholstery` row with `upholstery_id=None` is still classified as `missing_selection`.
   - Do this as a derived query reason using existing fields, not by adding a persisted state column or enum to `ItemUpholstery`.
   - Review any task-list filtering or upholstery-related manager views that currently depend on joined requirement rows and ensure the new deferred case is not silently excluded where the business expectation is “still pending upholstery selection”.

7. Add targeted automated coverage for all affected branches.
   - Create tests for create-task embedded upholstery:
     - internal + amount + no `upholstery_id` succeeds
     - no requirement row exists
   - Create equivalent tests for create-item and standalone create-item-upholstery.
   - Add negative tests:
     - internal + no `upholstery_id` + no positive amount fails
   - Add regression tests:
     - internal + `upholstery_id` still creates requirement
     - customer-source behavior unchanged
   - Add update-flow tests:
     - create deferred internal upholstery
     - later patch in `upholstery_id`
     - verify first active requirement is created and linked
   - Add pending-upholstery query tests:
     - deferred internal upholstery appears in pending lists/counts as `missing_selection`
   - Add response-shape tests:
     - item/task detail includes the upholstery object with `active_requirement_id=null` and empty requirements before later linking.
   - Add requirement-action error tests:
     - deferred internal upholstery returns the new specific business error when in-use/completed/surplus/update-quantity actions are attempted before selection.

## Risks and mitigations

- Risk: Different create entrypoints drift again and reintroduce inconsistent validation.
  Mitigation: Put the allow/defer/reject decision in one shared helper and keep entrypoint-specific guards minimal.

- Risk: `update_item_upholstery` assumes every row has an active requirement and breaks on deferred rows.
  Mitigation: Add an explicit no-active-requirement branch and only execute swap/fail-old-requirement logic when `active_requirement_id` exists.

- Risk: Later requirement creation could accidentally run inventory math with `upholstery_id=None`.
  Mitigation: Gate all requirement activation on a resolved `upholstery_id` before calling any inventory helper.

- Risk: Existing commands that mutate requirements become confusing on rows with no requirement.
  Mitigation: Replace generic missing-requirement errors with a specific business error that tells the caller upholstery selection must be completed first.

- Risk: Deferred internal upholsteries disappear from operational manager queues because current pending views only understand “no row exists” or “quantity missing”.
  Mitigation: Extend the query-layer classification so `source=internal` with `upholstery_id=NULL` is still surfaced as `missing_selection`.

- Risk: PATCH updates misinterpret omitted optional fields as explicit nulls and accidentally trigger or skip first-link logic.
  Mitigation: Preserve field-intent semantics in the PATCH path by using unset-aware request handling.

## Validation plan

- `backend/app` targeted automated tests for:
  - create-task embedded internal upholstery without `upholstery_id`
  - create-item internal upholstery without `upholstery_id`
  - standalone create-item-upholstery without `upholstery_id`
  - later PATCH linking of `upholstery_id`
- Query checks:
  - seat pending-upholstery list/counts still include deferred internal upholsteries as `missing_selection`
- Serialization checks:
  - GET item/task detail returns `active_requirement_id = null`
  - requirements array is empty before later linking
- Regression checks:
  - internal-with-id branch still creates requirement and inventory linkage
  - customer-source branch remains unchanged
- Error-behavior checks:
  - requirement-dependent actions on deferred internal upholsteries return the new specific business error
- Static verification:
  - search for duplicated internal-without-id validation logic and remove branch drift where possible
  - verify the PATCH update path uses unset-aware semantics for optional fields

## Review log

- `2026-06-17` `codex`: Drafted the implementation plan from current task, item, and item-upholstery lifecycle behavior. Locked the deferred-requirement design: allow internal-without-id only when quantity exists, and activate requirement creation later when `upholstery_id` is set.
- `2026-06-17` `codex`: Added follow-up corrections after gap review: deferred internal upholsteries must remain visible in pending upholstery views as `missing_selection`, requirement-dependent actions should return specific business errors before selection is completed, and the PATCH update flow must preserve omitted-vs-null intent.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
