---
plan: test_isolation_and_xdist/plans/plan_1.md
role: implement
state: IMPLEMENTED
date: 2026-08-21
actor: codex
---

# Phase 1 implementation handoff

Implemented serial per-process PostgreSQL database isolation. **⚠ OWNER DECISIONS REQUIRED (0).**

## Scope and architectural finding

The existing seam is the process-wide `settings.database_url` consumed by the application
database module. The test suite also relies on pre-existing development reference rows; a
schema-only template changed the inherited failure set. The final design therefore creates a
migrated, marked template and restores baseline data into it, retaining migration-owned seed rows
and the isolation marker. No production-domain files were changed.

Phase 2 remains out of scope: installing xdist, invoking `-n`, or proving parallel execution.

## Delivered implementation

- [`app/tests/database_isolation.py`](../../../../../../app/tests/database_isolation.py) owns
  worker-name resolution, fail-closed guards, template migration/DDL assertions, baseline
  snapshot restore, worker creation, marker management, and teardown.
- [`app/tests/conftest.py`](../../../../../../app/tests/conftest.py) starts one session-scoped
  worker database, swaps `settings.database_url` to its URL, and restores it before cleanup.
- [`app/tests/integration/infrastructure/test_database_isolation.py`](../../../../../../app/tests/integration/infrastructure/test_database_isolation.py)
  covers C1-C8.
- [`plans/plan_1.md`](../../plans/plan_1.md) is marked `IMPLEMENTED` and contains the append-only
  review log.

The full write perimeter for this phase was the two test infrastructure modules, their criterion
test module, this plan, this handoff, and the additive Architecture Graph records. Mutation probes
touched only `app/tests/database_isolation.py` and `app/tests/conftest.py`; every mutation was
reverted. Existing unrelated working-tree changes under `app/beyo_manager/` were preserved and
are not part of this handoff.

## Safety invariant

Before any destructive operation, the target must match exactly
`^beyo_test_(template|main|gw\d+)$`, must differ from the configured `DATABASE_URL` database,
the URL must parse as PostgreSQL with host/user/database, and the target must contain the exact
`beyo_test_metadata.database_marker` marker. Only then may a maintenance connection terminate
target sessions and issue `DROP DATABASE`; malformed, missing, configured, unmarked, or
injection-shaped targets fail closed.

## Lifecycle

```text
configured DATABASE_URL
        |
        v
resolve PYTEST_XDIST_WORKER (serial => beyo_test_main)
        |
        v
ensure marked template -> Alembic upgrade -> DDL assertions -> baseline data restore
        |
        v
guard fixed worker name -> drop marked residue -> CREATE DATABASE ... TEMPLATE beyo_test_template
        |
        v
mark worker -> settings.database_url = worker URL -> initialize test DB per test
        |
        v
restore original settings URL -> guard worker -> terminate worker stragglers -> DROP worker
```

The template is persistent and expected. Worker databases are process-local and are removed on
normal teardown; a fixed interrupted worker name is reabsorbed on the next start.

## Verification and evidence ledger

Tree identity for the closing test run was the pre-checkpoint working tree; the final checkpoint
SHA is recorded below. Commands were run from `backend/app` unless stated otherwise.

| Hypothesis | Scope and command | Result / ID delta |
|---|---|---|
| C1 resolver maps worker IDs exactly | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py -k worker_name_resolution` with constant-name mutation | Mutation red: 2 failed, 2 passed; source restored |
| C2 guard fails closed | `... -k destructive_guard` with immediate-return mutation | Mutation red: 6 failed; source restored |
| C3 template contains real DDL | `... -k template_has_migrated` with `alembic stamp` mutation and rebuilt template | Mutation red on expected 107-table assertion; source restored |
| C4 worker copies template | `... -k faithful_template` without `TEMPLATE` mutation | Mutation red on missing migrated schema; source restored |
| C5 application seam uses worker | `... -k application_database_seam` after removing URL override | Mutation red on development URL; source restored |
| C6 dev DB is not active | `... -k dev_database_counts` with dev URL override | Mutation red on active database name; source restored |
| C8 fixed names reabsorb residue | `... -k fixed_name_reabsorbs` with unique suffix mutation | Mutation errored and created only the exact disposable probe artifact `beyo_test_main9`; it was explicitly removed, then the source was restored |
| C1-C8 contract | `PYTHONPATH=. pytest -q tests/integration/infrastructure/test_database_isolation.py` | 15 passed in 10.72s |
| Full serial suite | `env PYTHONPATH=. pytest -m 'not e2e' -q --tb=no` | 2535 passed, 26 inherited failures, 1 deselected, 2 warnings in 169.71s; `comm` both directions empty against the 26-ID baseline |
| Residue and dev preservation | read-only PostgreSQL database list and four row counts before/after suite runs | Counts remained `11253/9809/2445/1955`; only `beyo_test_template` remained; no worker DB remained |
| Static quality | `ruff check` on changed test modules; `git diff --check` | Passed |

The first exploratory full run with an empty template produced 32 failures. Ten IDs were added
and four baseline IDs disappeared because tests expected development reference data. This was
diagnosed and corrected by the baseline data restore; the closing run is the authoritative C7
stamp and matches the original 26 IDs exactly.

## Findings and remaining risks

The dead/broken `async_engine` and `count_queries` fixtures were removed as in-perimeter cleanup;
the two duplicate local `executed_statements` definitions remain. The function-scoped
`initialize_database` fixture remains unchanged because its scope is part of isolation semantics.
The baseline snapshot currently uses Docker Compose PostgreSQL client tools when available to
match the server version; the local CLI fallback uses explicit connection parameters and requires
a password. The template is tied to the configured development database's baseline marker, so it
is rebuilt rather than silently reused when the schema or source baseline changes.

## Architecture Graph state

One additive batch recorded:

- `infrastructure-test-database-isolation` (infrastructure)
- `test-database-isolation-contract` (configuration)
- `infrastructure-test-database-isolation --configured_by--> test-database-isolation-contract`

Graph revision after the batch:
`4caa1afe361b7906bd6aed854d0ded5897a6927d3e5e9f13f29e81e7177508fc`.

## Checkpoint

The implementation is ready for independent review. The checkpoint commit is created after this
handoff and is reported in the final response; phase 2 parallelism is not included.
