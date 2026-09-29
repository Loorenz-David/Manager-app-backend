"""The deployment migration job, run for real as a subprocess against a scratch database.

Covers what a deployment depends on: a fresh database reaches head with the task
trigger installed; a second run changes nothing; `--check` tells pending from up to
date; a concurrent run waits for the lock and then gives up without touching
anything; an unreachable database fails with a non-zero exit and no password in
the output.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from beyo_manager.config import settings
from scripts import migrate as migrate_module

pytestmark = pytest.mark.integration

APP_ROOT = Path(__file__).parents[3]


def _scratch_url(name: str) -> str:
    return (
        make_url(settings.database_url)
        .set(database=name)
        .render_as_string(hide_password=False)
    )


def _admin_dsn() -> str:
    url = make_url(settings.database_url).set(
        drivername="postgresql", database="postgres"
    )
    return url.render_as_string(hide_password=False)


def _dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _run_job(database_url: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.migrate", *args],
        cwd=APP_ROOT,
        env={**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
        timeout=600,
    )


@pytest.fixture
async def scratch_database():
    name = f"migrate_job_{uuid4().hex[:10]}"
    admin = await asyncpg.connect(_admin_dsn())
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    try:
        yield _scratch_url(name)
    finally:
        admin = await asyncpg.connect(_admin_dsn())
        try:
            await admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1",
                name,
            )
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
        finally:
            await admin.close()


async def test_fresh_database_is_migrated_to_head_with_trigger_and_rerun_is_a_no_op(
    scratch_database,
):
    heads = migrate_module.code_heads()

    pending = _run_job(scratch_database, "--check")
    assert pending.returncode == migrate_module.EXIT_PENDING, (
        pending.stdout + pending.stderr
    )

    first = _run_job(scratch_database)
    assert first.returncode == migrate_module.EXIT_OK, first.stdout + first.stderr
    assert "database before: empty database" in first.stdout

    connection = await asyncpg.connect(_dsn(scratch_database))
    try:
        revisions = {
            row["version_num"]
            for row in await connection.fetch("SELECT version_num FROM alembic_version")
        }
        trigger_count = await connection.fetchval(
            "SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_task_open' AND NOT tgisinternal"
        )
    finally:
        await connection.close()
    assert revisions == heads
    assert trigger_count == 1

    second = _run_job(scratch_database)
    assert second.returncode == migrate_module.EXIT_OK, second.stdout + second.stderr
    assert f"database before: {', '.join(sorted(heads))}" in second.stdout

    up_to_date = _run_job(scratch_database, "--check")
    assert up_to_date.returncode == migrate_module.EXIT_OK
    assert "up to date" in up_to_date.stdout


async def test_concurrent_run_gives_up_on_the_lock_without_changing_anything(
    scratch_database,
):
    holder = await asyncpg.connect(_dsn(scratch_database))
    try:
        assert await holder.fetchval(
            "SELECT pg_try_advisory_lock($1)", migrate_module.MIGRATION_LOCK_KEY
        )

        blocked = _run_job(scratch_database, "--lock-timeout", "2")

        assert blocked.returncode == migrate_module.EXIT_LOCK_TIMEOUT, (
            blocked.stdout + blocked.stderr
        )
        assert await holder.fetchval("SELECT to_regclass('alembic_version')") is None
    finally:
        await holder.close()


async def test_database_ahead_of_the_code_is_refused_without_changes(scratch_database):
    """After a newer release migrated the database, an older image must not try to migrate it."""
    connection = await asyncpg.connect(_dsn(scratch_database))
    try:
        await connection.execute(
            "CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)"
        )
        await connection.execute("INSERT INTO alembic_version VALUES ('fffffffffff0')")

        checked = _run_job(scratch_database, "--check")
        migrated = _run_job(scratch_database)

        assert checked.returncode == migrate_module.EXIT_DATABASE_AHEAD, checked.stdout
        assert migrated.returncode == migrate_module.EXIT_DATABASE_AHEAD, (
            migrated.stdout
        )
        assert "roll back without migrating" in migrated.stdout
        assert "step: alembic upgrade head" not in migrated.stdout
        assert await connection.fetchval("SELECT to_regclass('workspaces')") is None
    finally:
        await connection.close()


def test_unreachable_database_fails_without_leaking_the_password():
    password = "Unreachable-db-pa55word"
    result = _run_job(
        f"postgresql+asyncpg://app:{password}@127.0.0.1:1/nowhere",
        "--lock-timeout",
        "1",
    )

    assert result.returncode == migrate_module.EXIT_STEP_FAILED
    assert "FAILED" in result.stdout
    assert password not in result.stdout + result.stderr
    assert (
        "target database: postgresql+asyncpg://app:***@127.0.0.1:1/nowhere"
        in result.stdout
    )
