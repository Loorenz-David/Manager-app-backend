from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg
from sqlalchemy.engine import URL, make_url


TEST_DATABASE_PATTERN = re.compile(r"^beyo_test_(?:template|main|gw\d+)$")
TEST_DATABASE_PREFIX = "beyo_test_"
TEMPLATE_DATABASE_NAME = "beyo_test_template"
MARKER_SCHEMA = "beyo_test_metadata"
MARKER_TABLE = "database_marker"
MARKER_KEY = "test_database_v1"
EXPECTED_HEAD = "c1d2e3f4a5b6"
EXPECTED_PUBLIC_TABLE_COUNT = 107


class UnsafeDatabaseError(RuntimeError):
    """Raised before a destructive operation targets an unapproved database."""


def resolve_worker_database_name(worker_id: str | None = None) -> str:
    """Map pytest-xdist's worker id to the bounded database name for that process."""
    worker_id = worker_id if worker_id is not None else os.getenv("PYTEST_XDIST_WORKER")
    if worker_id is None or worker_id == "":
        worker_id = "main"
    if worker_id != "main" and not re.fullmatch(r"gw\d+", worker_id):
        raise UnsafeDatabaseError(f"Unsupported pytest worker id: {worker_id!r}")
    return f"{TEST_DATABASE_PREFIX}{worker_id}"


def _parse_database_url(database_url: str | None) -> URL:
    if not database_url or not isinstance(database_url, str):
        raise UnsafeDatabaseError("DATABASE_URL is missing")
    try:
        parsed = make_url(database_url)
    except Exception as exc:
        raise UnsafeDatabaseError("DATABASE_URL is malformed") from exc
    if parsed.drivername not in {"postgresql+asyncpg", "postgresql"}:
        raise UnsafeDatabaseError("DATABASE_URL must use PostgreSQL")
    if not parsed.host or not parsed.database or not parsed.username:
        raise UnsafeDatabaseError("DATABASE_URL must include host, username, and database")
    return parsed


def assert_disposable_database(
    database_name: str,
    configured_database_url: str | None,
    *,
    marker_present: bool,
) -> None:
    """Fail closed unless ``database_name`` is a marked, non-configured test DB."""
    if not TEST_DATABASE_PATTERN.fullmatch(database_name):
        raise UnsafeDatabaseError(f"Database name is not disposable: {database_name!r}")

    configured = _parse_database_url(configured_database_url)
    if configured.database == database_name:
        raise UnsafeDatabaseError(
            f"Refusing to destroy the configured database: {database_name!r}"
        )
    if not marker_present:
        raise UnsafeDatabaseError(f"Database lacks the disposable marker: {database_name!r}")


def _quoted_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise UnsafeDatabaseError(f"Unsafe PostgreSQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _asyncpg_connection_kwargs(url: URL, database_name: str) -> dict[str, object]:
    host = "127.0.0.1" if url.host == "localhost" else url.host
    return {
        "host": host,
        "port": url.port,
        "user": url.username,
        "password": url.password,
        "database": database_name,
    }


async def _connect(url: URL, database_name: str) -> asyncpg.Connection:
    return await asyncpg.connect(**_asyncpg_connection_kwargs(url, database_name))


@dataclass(frozen=True)
class DatabaseInspection:
    head_revision: str | None
    public_table_count: int
    marker_present: bool


class DatabaseIsolation:
    """Create one fresh, marked PostgreSQL database for one pytest process."""

    def __init__(self, configured_database_url: str, *, worker_id: str | None = None) -> None:
        self.configured_database_url = configured_database_url
        self._url = _parse_database_url(configured_database_url)
        self.worker_database_name = resolve_worker_database_name(worker_id)
        connection_host = "127.0.0.1" if self._url.host == "localhost" else self._url.host
        self.worker_database_url = str(
            self._url.set(host=connection_host, database=self.worker_database_name).render_as_string(
                hide_password=False
            )
        )
        self._app_root = Path(__file__).resolve().parents[1]
        self.configured_row_counts_before_run: dict[str, int] | None = None
        self._started = False

    @property
    def template_database_name(self) -> str:
        return TEMPLATE_DATABASE_NAME

    @property
    def configured_database_name(self) -> str:
        database_name = self._url.database
        if not database_name:
            raise UnsafeDatabaseError("DATABASE_URL has no database name")
        return database_name

    async def start(self) -> None:
        try:
            if not TEST_DATABASE_PATTERN.fullmatch(self.configured_database_name):
                self.configured_row_counts_before_run = await self.row_counts(
                    self.configured_database_name
                )
            await self._ensure_template()
            await self._drop_database_if_exists(self.worker_database_name)
            await self._create_database_from_template(self.worker_database_name)
            await self._set_marker(self.worker_database_name)
            self._started = True
        except Exception:
            await self._drop_database_if_exists(self.worker_database_name, best_effort=True)
            raise

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        await self._drop_database_if_exists(self.worker_database_name)

    async def inspect(self, database_name: str) -> DatabaseInspection:
        connection = await _connect(self._url, database_name)
        try:
            head_revision = await connection.fetchval(
                "SELECT version_num FROM alembic_version"
            )
            public_table_count = await connection.fetchval(
                """
                SELECT count(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            marker_present = await self._marker_present_on_connection(
                connection, database_name
            )
            return DatabaseInspection(
                head_revision=head_revision,
                public_table_count=public_table_count,
                marker_present=marker_present,
            )
        finally:
            await connection.close()

    async def database_names(self) -> list[str]:
        connection = await self._maintenance_connection()
        try:
            rows = await connection.fetch(
                "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
            )
            return [row["datname"] for row in rows]
        finally:
            await connection.close()

    async def public_table_names(self, database_name: str) -> set[str]:
        connection = await _connect(self._url, database_name)
        try:
            rows = await connection.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            return {row["table_name"] for row in rows}
        finally:
            await connection.close()

    async def row_counts(self, database_name: str) -> dict[str, int]:
        connection = await _connect(self._url, database_name)
        try:
            row = await connection.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM workspaces) AS workspaces,
                    (SELECT count(*) FROM users) AS users,
                    (SELECT count(*) FROM tasks) AS tasks,
                    (SELECT count(*) FROM working_sections) AS working_sections
                """
            )
            return dict(row)
        finally:
            await connection.close()

    async def _maintenance_connection(self) -> asyncpg.Connection:
        return await _connect(self._url, "postgres")

    async def _database_exists(self, database_name: str) -> bool:
        connection = await self._maintenance_connection()
        try:
            return bool(
                await connection.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1", database_name
                )
            )
        finally:
            await connection.close()

    async def _marker_present(self, database_name: str) -> bool:
        if not await self._database_exists(database_name):
            return False
        connection = await _connect(self._url, database_name)
        try:
            return await self._marker_present_on_connection(connection, database_name)
        finally:
            await connection.close()

    async def _marker_present_on_connection(
        self, connection: asyncpg.Connection, database_name: str
    ) -> bool:
        return bool(
            await connection.fetchval(
                f"""
                SELECT 1
                FROM {MARKER_SCHEMA}.{MARKER_TABLE}
                WHERE marker_key = $1 AND database_name = $2
                """,
                MARKER_KEY,
                database_name,
            )
        )

    async def _ensure_template(self) -> None:
        if not await self._database_exists(TEMPLATE_DATABASE_NAME):
            await self._create_database(TEMPLATE_DATABASE_NAME)
            await self._set_marker(TEMPLATE_DATABASE_NAME)
            await self._migrate_and_assert(TEMPLATE_DATABASE_NAME)
            return

        inspection = await self.inspect(TEMPLATE_DATABASE_NAME)
        if not inspection.marker_present:
            raise UnsafeDatabaseError(
                "Existing beyo_test_template lacks the disposable marker; refusing to replace it"
            )
        if (
            inspection.head_revision == EXPECTED_HEAD
            and inspection.public_table_count == EXPECTED_PUBLIC_TABLE_COUNT
            and not await self._has_legacy_baseline_source(TEMPLATE_DATABASE_NAME)
        ):
            return

        await self._drop_database_if_exists(TEMPLATE_DATABASE_NAME)
        await self._create_database(TEMPLATE_DATABASE_NAME)
        await self._set_marker(TEMPLATE_DATABASE_NAME)
        await self._migrate_and_assert(TEMPLATE_DATABASE_NAME)

    async def _has_legacy_baseline_source(self, database_name: str) -> bool:
        connection = await _connect(self._url, database_name)
        try:
            return bool(
                await connection.fetchval(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = $1
                      AND table_name = $2
                      AND column_name = 'baseline_source'
                    """,
                    MARKER_SCHEMA,
                    MARKER_TABLE,
                )
            )
        finally:
            await connection.close()

    async def _migrate_and_assert(self, database_name: str) -> None:
        env = os.environ.copy()
        env["APP_ENV"] = "development"
        connection_host = "127.0.0.1" if self._url.host == "localhost" else self._url.host
        env["DATABASE_URL"] = self._url.set(
            host=connection_host, database=database_name
        ).render_as_string(hide_password=False)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=self._app_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Alembic migration failed for {database_name}: {result.stderr.strip()}"
            )

        inspection = await self.inspect(database_name)
        required_tables = {"cost_model_versions", "item_cost_results", "step_state_records"}
        connection = await _connect(self._url, database_name)
        try:
            table_rows = await connection.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        finally:
            await connection.close()
        table_names = {row["table_name"] for row in table_rows}
        if inspection.head_revision != EXPECTED_HEAD:
            raise RuntimeError(
                f"Migration DDL assertion failed for {database_name}: "
                f"expected head {EXPECTED_HEAD}, got {inspection.head_revision!r}"
            )
        if inspection.public_table_count != EXPECTED_PUBLIC_TABLE_COUNT:
            raise RuntimeError(
                f"Migration DDL assertion failed for {database_name}: expected "
                f"{EXPECTED_PUBLIC_TABLE_COUNT} public tables, got {inspection.public_table_count}"
            )
        missing_tables = required_tables - table_names
        if missing_tables:
            raise RuntimeError(
                f"Migration DDL assertion failed for {database_name}: missing {sorted(missing_tables)}"
            )
        if not inspection.marker_present:
            raise RuntimeError(f"Migration DDL assertion failed: marker missing in {database_name}")

    async def _create_database_from_template(self, database_name: str) -> None:
        connection = await self._maintenance_connection()
        try:
            await connection.execute(
                f"CREATE DATABASE {_quoted_identifier(database_name)} "
                f"TEMPLATE {_quoted_identifier(TEMPLATE_DATABASE_NAME)}"
            )
        finally:
            await connection.close()

    async def _create_database(self, database_name: str) -> None:
        connection = await self._maintenance_connection()
        try:
            await connection.execute(f"CREATE DATABASE {_quoted_identifier(database_name)}")
        finally:
            await connection.close()

    async def _set_marker(self, database_name: str) -> None:
        connection = await _connect(self._url, database_name)
        try:
            await connection.execute(
                f"CREATE SCHEMA IF NOT EXISTS {MARKER_SCHEMA}"
            )
            await connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {MARKER_SCHEMA}.{MARKER_TABLE} (
                    marker_key text PRIMARY KEY,
                    database_name text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            await connection.execute(
                f"""
                INSERT INTO {MARKER_SCHEMA}.{MARKER_TABLE}
                    (marker_key, database_name)
                VALUES ($1, $2)
                ON CONFLICT (marker_key) DO UPDATE
                SET database_name = EXCLUDED.database_name
                """,
                MARKER_KEY,
                database_name,
            )
        finally:
            await connection.close()

    async def _drop_database_if_exists(
        self, database_name: str, *, best_effort: bool = False
    ) -> None:
        try:
            exists = await self._database_exists(database_name)
            if not exists:
                return
            marker_present = await self._marker_present(database_name)
            assert_disposable_database(
                database_name,
                self.configured_database_url,
                marker_present=marker_present,
            )
            connection = await self._maintenance_connection()
            try:
                await connection.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = $1 AND pid <> pg_backend_pid()
                    """,
                    database_name,
                )
                await connection.execute(
                    f"DROP DATABASE {_quoted_identifier(database_name)}"
                )
            finally:
                await connection.close()
        except Exception:
            if not best_effort:
                raise


def start_database_isolation(configured_database_url: str) -> DatabaseIsolation:
    """Synchronous pytest-fixture entry point; all database work remains async."""
    isolation = DatabaseIsolation(configured_database_url)
    asyncio.run(isolation.start())
    return isolation
