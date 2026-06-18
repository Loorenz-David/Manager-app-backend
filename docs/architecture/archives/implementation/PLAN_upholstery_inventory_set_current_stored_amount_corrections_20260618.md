# PLAN_upholstery_inventory_set_current_stored_amount_corrections_20260618

## Metadata

- Plan ID: `PLAN_upholstery_inventory_set_current_stored_amount_corrections_20260618`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-18T00:00:00Z`
- Last updated at (UTC): `2026-06-18T15:04:53Z`
- Related issue/ticket: —
- Intention plan: —
- Source review: `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_set_current_stored_amount_20260618.md`
- Corrects: `backend/docs/architecture/archives/implementation/PLAN_upholstery_inventory_set_current_stored_amount_20260618.md`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_upholstery_inventory_set_current_stored_amount_corrections_20260618.md`

## Goal and intent

- Goal: Apply five targeted corrections to the `set_current_stored_amount_inventory` implementation identified during post-implementation review: two code quality fixes, two test assertion gaps, and one missing test file.
- Business/user intent: Bring the implementation to the full acceptance criteria defined in the original plan, including test coverage for role access and the `in_need` invariant, and leave a runnable integration test source on disk.
- Non-goals:
  - No logic changes to the command, demotion helper, or forward allocation helper.
  - No changes to `_pooled_requirement_allocation.py` or `receive_upholstery_order.py`.
  - No schema or migration changes.

## Scope

- In scope:
  - Add `AsyncSession` type annotation to `session` parameter of `_load_requirement_candidates`.
  - Add docstring to `SetCurrentStoredAmountInventoryRequest`.
  - Add WORKER role rejection test to the router test module.
  - Add `in_need` unchanged assertion to the promotion command test.
  - Create the missing integration test source file for `set_current_stored_amount_inventory`.
- Out of scope:
  - Changing the command algorithm or helper logic.
  - Backporting `updated_at` stamping into `allocate_pooled_requirements` (separate plan if desired).
  - Running DB-backed integration tests in a sandbox without Postgres access.

## Clarifications required

- None. All five corrections are unambiguous from the review findings.

## Acceptance criteria

1. `_load_requirement_candidates` has `session: AsyncSession` type annotation; the `# type: ignore[arg-type]` comment in the test session mock is no longer required for this reason.
2. `SetCurrentStoredAmountInventoryRequest` has a one-line docstring consistent with sibling classes in the same file.
3. Router test module contains a test asserting that a WORKER-role claims dict is rejected (results in a non-200 response or the dependency raises).
4. Promotion command test (`test_set_current_stored_amount_inventory_promotes_expected_candidates`) asserts `inventory.current_amount_in_need_meters` is unchanged after the command runs.
5. Integration test source file exists at `tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py` with DB-backed scenarios for increase, decrease, no-op, and not-found cases.

## Contracts and skills

### Contracts loaded

- `../architecture/06_commands.md`: command structure and transaction ownership — for integration test shape.
- `../architecture/09_routers.md`: route handler structure — for router role-gate test pattern.
- `../architecture/15_testing.md`: required test coverage rules — primary driver for all five corrections.

### Local extensions loaded

- `../architecture/06_commands_local.md`: transaction propagation policy — confirm `maybe_begin` vs `begin` in integration test setup.

### File read intent — pattern vs. relational

Before reading any file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead.
- **What exists** → reading is legitimate.

Permitted (relational reads):
- Reading existing integration test files in `tests/integration/services/commands/` to match the DB fixture and session setup pattern used by the project.
- Reading the router test module to understand how role-gate tests are structured for other routes.
- Reading `set_current_stored_amount_inventory.py` to confirm exact parameter name for the type annotation fix.

Prohibited (pattern reads — contract covers these):
- Reading another command to infer transaction or parse shape for the integration test.

### Skill selection

- Primary skill: targeted bug-fix / test-gap correction — no full CRUD skill needed.
- Excluded alternatives: full CRUD + realtime planning skill — excluded because no new routes or logic are being added.

## Implementation plan

1. Fix `session` type annotation in `_load_requirement_candidates`
   - File: `backend/app/beyo_manager/services/commands/upholstery/set_current_stored_amount_inventory.py`
   - Change `session,` to `session: AsyncSession,` in the function signature.
   - Add `from sqlalchemy.ext.asyncio import AsyncSession` to imports if not already present (it is not currently imported in this file — `AsyncSession` is available via SQLAlchemy).

2. Add docstring to `SetCurrentStoredAmountInventoryRequest`
   - File: `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`
   - Add `"""Request to set the absolute stored stock amount for an inventory record."""` as the class body's first line, consistent with sibling classes.

3. Add WORKER role rejection test to router test module
   - File: `backend/app/tests/unit/test_upholstery_inventories_router.py`
   - Pattern: read existing role-gate unit tests in the project to match the approach (likely: patch `require_roles` or call `route_set_current_stored_amount` with a WORKER-role claims dict and assert the dependency raises `HTTPException` or `build_err` returns a 403).
   - Test name: `test_route_set_current_stored_amount_rejects_worker_role`.
   - The test must confirm the `[ADMIN, MANAGER]` gate is wired to this specific route (not just that `require_roles` works generically).

4. Add `in_need` unchanged assertion to promotion test
   - File: `backend/app/tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py`
   - In `test_set_current_stored_amount_inventory_promotes_expected_candidates`, after the existing state assertions, add:
     ```python
     assert inventory.current_amount_in_need_meters == Decimal("5.000")
     ```
   - The inventory fixture already sets `current_amount_in_need_meters=Decimal("5.000")` — this assertion verifies it was not mutated.

5. Create integration test source file
   - New file: `backend/app/tests/integration/services/commands/upholstery/test_set_current_stored_amount_inventory_integration.py`
   - Read existing integration test files in `tests/integration/services/commands/` to match the DB session fixture, workspace seed, and assertion style used by the project before writing.
   - Required scenarios:
     - **increase**: create inventory with low stored amount and one NEEDS_ORDERING requirement; call the command with a higher amount; assert the requirement is promoted to AVAILABLE and `inventory_condition` is recomputed.
     - **decrease**: create inventory with stored amount covering two AVAILABLE requirements; call the command with an amount covering only the higher-priority one; assert the lower-priority requirement is demoted to NEEDS_ORDERING and `in_need` is unchanged.
     - **no-op**: call the command with the same stored amount as current; assert no requirement state changes and `updated_by_id` on the inventory is unchanged.
     - **not-found**: call the command with a nonexistent `client_id`; assert `NotFound` is raised.
   - The file must be valid Python that can be collected by pytest even if skipped when the DB is unavailable (use a DB-unavailable skip marker if the project defines one, or `pytest.mark.integration`).

## Risks and mitigations

- Risk: integration test fixture pattern differs from existing integration tests in ways not visible from unit tests.
  Mitigation: step 5 explicitly requires reading existing integration tests before writing — do not infer pattern from unit tests or contracts alone.

- Risk: role-gate test approach for router differs from project convention (some projects test via HTTP client, others via direct handler call with mocked dependency).
  Mitigation: step 3 explicitly requires reading existing router tests before writing to match the convention.

## Validation plan

- Run `pytest tests/unit/test_upholstery_inventories_router.py tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py -v`: all existing tests must still pass, new tests must appear and pass.
- Confirm no `# type: ignore` comments remain in the test session mock that were present solely because of the missing `AsyncSession` annotation.
- Confirm `test_set_current_stored_amount_inventory_integration.py` is collected by pytest (`pytest --collect-only`) without import errors.

## Review log

- `2026-06-18` `claude-sonnet-4-6`: Correction plan created from post-implementation review of `SUMMARY_upholstery_inventory_set_current_stored_amount_20260618`. Five issues identified: missing type annotation, missing docstring, missing WORKER role test, missing `in_need` assertion in promotion test, missing integration test source file.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `codex`
