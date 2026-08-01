# DEBUG_test_suite_runs_against_the_development_database_20260801

## Metadata

- Debug ID: `DEBUG_test_suite_runs_against_the_development_database_20260801`
- Status: `documented — not fixed`
- Owner agent: `claude-opus-5`
- Created at (UTC): `2026-08-01T00:00:00Z`
- Parent plan: none — found while working on the realtime event layer, unrelated to it
- Issue reference: none
- Debug iteration: `1`

## Problem statement

- **Observed behavior.** `pytest` runs against `beyo_manager` on port 5433 — the **development**
  database. Integration tests commit into it, so it accumulates test data permanently. It currently
  holds **1,715 workspaces and 1,497 users**.
- **Expected behavior.** Tests run against `app_test` on port 5432, which `.env.testing` already
  configures for exactly this purpose.
- **Impact scope.** Two things, and the second is the expensive one:
  1. Development data is polluted by every test run, and has been since this was set up.
  2. **The suite's failures cannot be trusted.** 15 integration tests fail, and their errors are all
     state-shaped — duplicate keys, foreign-key violations, `assert 695 == 0`. There is currently no
     way to tell a real defect from accumulated sediment without fixing this first.

## Evidence

Measured 2026-08-01.

| | `beyo_manager` (dev, `localhost:5433`) | `app_test` (`127.0.0.1:5432`) |
|---|---|---|
| Selected by | `.env` (the default) | `.env.testing` (`APP_ENV=testing`) |
| Alembic version | `2645b4327b17` — **at head** | `67cfba8fcb2d` — **behind head** |
| Workspaces | 1,715 | 4,118 |
| Users | 1,497 | — |
| Roles | 4 | 1 |
| `ws_test` workspace | absent | — |

Both Postgres servers are running. Confirming which database the suite actually uses:

```
$ python -c "from beyo_manager.config import settings; print(settings.environment, settings.database_url)"
development  postgresql+asyncpg://…@localhost:5433/beyo_manager
```

## Root cause

`config.py` picks its env file from one variable, at import time:

```python
def _resolve_env_file() -> str:
    app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    if app_env == "testing":
        return ".env.testing"
    ...
    return ".env"
```

The Makefile sets `APP_ENV=development` explicitly on **twenty** targets — `run`, `db-migrate`, every
worker. The test target does not:

```makefile
test:
	pytest -m 'not e2e'
```

Nor does `pytest.ini`, nor `tests/conftest.py`. So the suite takes the default and loads `.env`.

The intent was plainly the opposite: `.env.testing` exists and already isolates Redis (database index
1, key prefix `app_testing`). Only the database half was left unwired.

## Secondary finding — `app_test` is not ready either

It cannot simply be switched on. `app_test` is behind head on migrations, holds 4,118 workspaces of
its own, and has 1 role where the suite needs the seeded set (several tests do
`select(Role).where(Role.name == WORKER)` then `.scalar_one()`, which raises when the row is absent).
It needs migrating, emptying and seeding before it is usable.

Unlike the dev database, emptying it is safe — that is what it is for.

## Fix plan

Run from `backend/app/`. Steps 1–2 are prerequisites; step 3 is the only destructive one and it is
safe **only after** step 5's switch exists, or with `APP_ENV=testing` set explicitly on the command.

1. **Complete `.env.testing`.** It is missing `SECRET_KEY` and `JWT_SECRET_KEY`, both in the config's
   `required` list, so `APP_ENV=testing` currently dies with
   `ValidationError: Missing required settings: jwt_secret_key`. Test-only values; any string.

2. **Migrate the test database to head.**
   ```
   APP_ENV=testing alembic upgrade head
   ```

3. **Empty it.**
   ```
   APP_ENV=testing python scripts/wipe_all_data.py --yes
   ```
   `wipe_all_data.py` truncates every table in the schema of whatever `APP_ENV` resolves to. Without
   the prefix it would truncate the **development** database. Do not run it from muscle memory.

4. **Seed it.**
   ```
   APP_ENV=testing python scripts/ops.py seed
   ```

5. **Point the suite at it — in two places, both needed.**
   - `Makefile`: `test:` becomes `APP_ENV=testing pytest -m 'not e2e'`
   - `tests/conftest.py`: `os.environ.setdefault("APP_ENV", "testing")` as the **first** statement,
     above every `beyo_manager` import. This is what makes a bare `pytest` safe rather than only
     `make test`.

   **Ordering is load-bearing.** `_resolve_env_file()` runs the moment `config.py` is first imported.
   If any import above that line pulls in config — directly or transitively — `.env` is already
   loaded and the assignment has no effect. Verify with the one-liner under *Evidence*, which must
   print `testing … /app_test`.

6. **Re-run and record a true baseline.** Only then is a failing integration test evidence of a
   defect.

## Known limitation of this fix

It relocates the pollution rather than stopping it. Integration tests call commands; a command's
`maybe_begin` opens and **commits** its own transaction when none is active; the `db_session`
fixture's `rollback()` then has nothing left to undo. `app_test` will start filling up again on every
run.

The difference is that it becomes a disposable database you can truncate before a run without
thinking about it, instead of your development data.

Stopping the leak properly means restructuring the fixture so each test runs inside an outer
transaction rolled back at teardown (SAVEPOINT / `join_transaction_mode`), which every command's
`maybe_begin` would then join in subordinate mode instead of owning. That is a real piece of test
infrastructure work and its own task — do not fold it into the switch above.

## The 23 failures as of 2026-08-01

Recorded so the "true baseline" after the fix can be diffed against something. Verified identical on
a clean tree at `396be6d`, and **all fail in isolation too**, so this is not test ordering.

**8 unit — stale tests, unaffected by the database. Real work regardless of this document.**

| Test | Error |
|---|---|
| `test_items_router.py::test_route_list_item_issues_forwards_client_id` | no attribute `list_item_issues_by_item_id` |
| `test_items_router.py::test_route_delete_item_issues_forwards_ids` | no attribute `_DeleteIssuesBody` (now `_BatchDeleteIssuesBody`) |
| `test_case_type_serializers.py::test_serialize_case_type_entry_returns_contract_fields` | `CaseLinkEntityTypeEnum` has no attribute `item` |
| `test_endpoint_split.py::test_split_services_return_disjoint_worker_shapes` | test double `empty_page()` rejects `roles` kwarg |
| `test_dimension_migration.py` ×2 | dict-equality drift |
| `test_upholstery_inventories_router.py::test_route_list_upholstery_inventories_passes_filter_query_params` | dict-equality drift |
| `test_sign_in_user.py::test_sign_in_user_preserves_custom_workspace_role_name` | `sign_in_user.py:107 AttributeError: 'str' object has no attribute 'value'` |

The last one is the **only** failure whose traceback lands in production code rather than test code.
Worth reading before assuming it is drift like the others.

**15 integration — expected to be explained by this document, but not verified as such.**

`bootstrap/test_seed_working_sections_integration.py` (1), `items/test_batch_update_item_positions_integration.py` (2),
`shopify/test_create_shopify_metafield_preferences.py` (1), `task_steps/test_add_task_steps_integration.py` (1),
`tasks/test_task_date_field_updates_integration.py` (1), `upholstery/test_set_current_stored_amount_inventory_integration.py` (3),
`working_sections/test_batch_working_section_integration.py` (2), `working_sections/test_working_section_ordering_integration.py` (2),
`test_audit_log.py` (2).

Their errors: `duplicate key … ix_roles_name`, `duplicate key … uq_ws_supported_issue_types_unique`,
foreign-key violations on `items_workspace_id_fkey` / `items_created_by_id_fkey` /
`audit_logs_workspace_id_fkey`, `ConflictError: Provided client_id is already in use`,
`assert 695 == 0`, and `InvalidRequestError: A transaction is already begun on this Session`.

`audit_logs_workspace_id_fkey` is the clearest single case: the audit tests write
`workspace_id='ws_test'`, and no such row exists in the development database.

## What was verified, and what was not

**Verified:** which database the suite connects to; both databases' row counts and alembic versions;
that `APP_ENV` is set nowhere for tests; that `.env.testing` fails config validation today; that all
23 failures reproduce in isolation and are identical on a clean tree.

**Not verified:** that fixing the database actually clears the 15 integration failures. The errors are
consistent with it and `InvalidRequestError: A transaction is already begun` may well be something
else entirely. Treat "environmental" as the leading hypothesis, not a conclusion — the point of the
fix is to find out.

**Also not done:** `make reset-db` is a no-op. `run_reset_db()` in `beyo_manager/operations/db.py`
guards against running without `confirm`, then only calls `log_event`. It resets nothing. Either
implement it or drop the target, because its name promises something it does not do.

## This violates the testing contract explicitly

`architecture/15_testing.md` is not vague about it:

> Use a separate test database — **never the development or production database**

> **Never** set `SQLALCHEMY_DATABASE_URI` to the same value as development or production.

So this is not a gap the contract failed to anticipate. The rule exists and the wiring does not
follow it.

The same section also explains `ws_test`: it is the contract's canonical test workspace, used in the
`dependency_overrides` example for JWT claims. That is why `test_audit_log.py` writes
`workspace_id='ws_test'` and dies on a foreign key — the row is supposed to exist in a seeded test
database, and the development database has never heard of it.

## Related: the contract's event-bus suppression is unimplemented

Same file:

> `SUPPRESS_EVENT_BUS = True` prevents test runs from publishing events to Redis or triggering
> external calls. Commands in integration tests call emitters, but the bus no-ops.

`SUPPRESS_EVENT_BUS` **does not exist** anywhere in this codebase — neither does `TEST_DATABASE_URL`.
That whole `TestingConfig` section describes a Flask-style config class that was never built here;
this project uses pydantic-settings with `.env` files instead.

**This intersects with a change made on 2026-08-01.** Until then, event-bus handlers were registered
only in the FastAPI lifespan, so in the pytest process `dispatch()` found an empty handler list and
did nothing — accidentally implementing `SUPPRESS_EVENT_BUS` by way of a bug. Registration now
happens on import of the events package (see `architecture/11_infra_events.md`), so **integration
tests now genuinely publish to Redis.**

That is working as intended for the fix, and Redis is a required part of the test environment anyway
(`.env.testing` allocates it database index 1 and the key prefix `app_testing`; `conftest.py` has an
`isolated_redis_prefix` fixture). But it is a real change in test-time behaviour, and it already
produced one bug: a process-wide cached `AsyncRedisManager` broke across pytest's per-test event
loops, fixed by keying the cache on the running loop in `sockets/worker_emitter.py`.

Whoever picks this up should decide deliberately between two options rather than inherit the current
state by accident:

1. **Leave it.** Tests exercise the real delivery path. Costs a Redis dependency the suite already
   has, and a little latency.
2. **Implement suppression** as the contract describes — a settings flag that makes `dispatch()` a
   no-op under `APP_ENV=testing`, with the tests that assert on emission opting back in. Restores the
   contract's stated intent, at the cost of the real path going untested by default.

Either way `architecture/15_testing.md` needs editing, because it currently describes a mechanism
that does not exist.

## Contracts and skills

- Contracts loaded:
  - `backend/architecture/15_testing.md`: the separate-test-database rule and the `SUPPRESS_EVENT_BUS`
    rule, both quoted above; both currently unimplemented
- Related: `docs/repo_health.md` records the "no current failure passes in isolation" observation,
  which this confirms.
