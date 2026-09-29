"""Deployment migration job: bring the schema to head, then install the database triggers.

    python -m scripts.migrate           # migrate (container: `docker compose run --rm migrate`)
    python -m scripts.migrate --check   # read-only: exit 3 if migrations are pending

This is the only process that changes the schema. The API and workers never
migrate on start, so replicas cannot race each other, and a deployment can stop
before replacing the application when this job fails.

Steps, in order, each only if the previous one succeeded:

1. Take a Postgres advisory lock, so two deployments cannot migrate the same
   database at once. Advisory locks are per database: production and staging on
   one RDS instance do not block each other.
2. `alembic upgrade head` — the same command legacy production runs.
3. `python -m scripts.apply_db_triggers` — installs the NOTIFY trigger the task
   router listens on. It lives outside Alembic, so it must run after every upgrade.

Migrations commit one revision at a time (`transaction_per_migration` in
`migrations/env.py`). If one fails, the database stays at the last revision that
succeeded; fixing the cause and running this job again continues from there.
Nothing is rolled back automatically.

A database at a revision this code does not know was migrated by a newer release.
That is the normal state after rolling back to an older image: the rollback must
deploy the image without running this job (migrations are expected to stay
backward compatible), so the job refuses rather than guess.

Exit codes: 0 success, 1 a step failed, 2 the lock was not acquired in time,
3 (`--check` only) migrations are pending, 4 the database is ahead of this code.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
from alembic.config import Config
from alembic.script import ScriptDirectory

from beyo_manager.config import settings
from beyo_manager.core.logging.redaction import redact_url

APP_ROOT = Path(__file__).resolve().parents[1]

# Arbitrary constant shared by every copy of this job. Advisory locks are scoped to
# the current database, so the same key is safe across databases.
MIGRATION_LOCK_KEY = 7_220_517_390_261_742_001

EXIT_OK = 0
EXIT_STEP_FAILED = 1
EXIT_LOCK_TIMEOUT = 2
EXIT_PENDING = 3
EXIT_DATABASE_AHEAD = 4

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("alembic upgrade head", (sys.executable, "-m", "alembic", "upgrade", "head")),
    ("apply database triggers", (sys.executable, "-m", "scripts.apply_db_triggers")),
)

Runner = Callable[[Sequence[str]], int]


def _log(message: str) -> None:
    print(f"[migrate] {message}", flush=True)


def _safe_error(exc: BaseException) -> str:
    """The exception text with the database password masked, should a driver echo it."""
    message = f"{type(exc).__name__}: {exc}"
    try:
        password = urlsplit(settings.database_url or "").password
    except ValueError:
        password = None
    return message.replace(password, "***") if password else message


def _asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _script_directory() -> ScriptDirectory:
    config = Config(str(APP_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(APP_ROOT / "migrations"))
    return ScriptDirectory.from_config(config)


def code_heads() -> set[str]:
    return set(_script_directory().get_heads())


def code_revisions() -> set[str]:
    return {script.revision for script in _script_directory().walk_revisions()}


def _unknown(revisions: set[str]) -> set[str]:
    return revisions - code_revisions()


async def database_revisions(connection: asyncpg.Connection) -> set[str]:
    exists = await connection.fetchval(
        "SELECT to_regclass('alembic_version') IS NOT NULL"
    )
    if not exists:
        return set()
    rows = await connection.fetch("SELECT version_num FROM alembic_version")
    return {row["version_num"] for row in rows}


def _describe(revisions: set[str]) -> str:
    return ", ".join(sorted(revisions)) if revisions else "empty database"


def _run_subprocess(argv: Sequence[str]) -> int:
    return subprocess.run(list(argv), cwd=APP_ROOT).returncode


def run_steps(runner: Runner = _run_subprocess) -> int:
    """Run each step in order; stop at the first that fails."""
    for name, argv in STEPS:
        _log(f"step: {name}")
        started = time.monotonic()
        returncode = runner(argv)
        elapsed = time.monotonic() - started
        if returncode != 0:
            _log(
                f"FAILED: {name} (exit {returncode}, {elapsed:.1f}s); later steps not run"
            )
            return EXIT_STEP_FAILED
        _log(f"done: {name} ({elapsed:.1f}s)")
    return EXIT_OK


async def _acquire_lock(connection: asyncpg.Connection, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    announced = False
    while True:
        if await connection.fetchval(
            "SELECT pg_try_advisory_lock($1)", MIGRATION_LOCK_KEY
        ):
            return True
        if time.monotonic() >= deadline:
            return False
        if not announced:
            _log("another migration holds the lock; waiting")
            announced = True
        await asyncio.sleep(1)


async def migrate(lock_timeout_seconds: float, runner: Runner = _run_subprocess) -> int:
    heads = code_heads()
    _log(f"target database: {redact_url(settings.database_url)}")
    _log(f"code head: {_describe(heads)}")

    connection = await asyncpg.connect(_asyncpg_dsn(settings.database_url), timeout=10, server_settings={"application_name": "managerbeyo:migrate"})
    try:
        if not await _acquire_lock(connection, lock_timeout_seconds):
            _log(
                f"FAILED: migration lock not acquired within {lock_timeout_seconds:.0f}s; nothing changed"
            )
            return EXIT_LOCK_TIMEOUT
        try:
            before = await database_revisions(connection)
            _log(f"database before: {_describe(before)}")
            unknown = _unknown(before)
            if unknown:
                _log(
                    f"FAILED: database is at {_describe(unknown)}, which this code does not know; "
                    "a newer release migrated it. Deploy that release, or roll back without migrating."
                )
                return EXIT_DATABASE_AHEAD

            result = await asyncio.to_thread(run_steps, runner)

            after = await database_revisions(connection)
            _log(f"database after: {_describe(after)}")
            if result == EXIT_OK and after != heads:
                _log(
                    "FAILED: steps reported success but the database is not at the code head"
                )
                return EXIT_STEP_FAILED
            if result == EXIT_OK:
                _log("complete")
            return result
        finally:
            await connection.execute(
                "SELECT pg_advisory_unlock($1)", MIGRATION_LOCK_KEY
            )
    finally:
        await connection.close()


async def check() -> int:
    heads = code_heads()
    connection = await asyncpg.connect(_asyncpg_dsn(settings.database_url), timeout=10, server_settings={"application_name": "managerbeyo:migrate"})
    try:
        current = await database_revisions(connection)
    finally:
        await connection.close()
    _log(f"target database: {redact_url(settings.database_url)}")
    _log(f"code head: {_describe(heads)} | database: {_describe(current)}")
    if current == heads:
        _log("up to date")
        return EXIT_OK
    if _unknown(current):
        _log("database is ahead of this code (migrated by a newer release)")
        return EXIT_DATABASE_AHEAD
    _log("migrations pending")
    return EXIT_PENDING


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.migrate", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether migrations are pending; change nothing",
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=300.0,
        help="seconds to wait for another running migration to finish (default 300)",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            return asyncio.run(check())
        return asyncio.run(migrate(args.lock_timeout))
    except Exception as exc:  # connection failures and the like
        _log(f"FAILED: {_safe_error(exc)}")
        return EXIT_STEP_FAILED


if __name__ == "__main__":
    sys.exit(main())
