import importlib.util
import os
import subprocess
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from beyo_manager.models import Base


APP_ROOT = Path(__file__).parents[3]
BASE_REVISION = "5caae620088c"
DATA_REVISION = "5420acc6a7b3"
HEAD_REVISION = "be9dfe42a035"


def _url(name: str) -> str:
    return f"postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/{name}"


def _admin_dsn() -> str:
    return "postgresql://postgres:postgres@127.0.0.1:5433/postgres"


def _alembic(url: str, revision: str, *, check: bool = True) -> subprocess.CompletedProcess:
    environment = {
        **os.environ,
        "APP_ENV": "development",
        "DATABASE_URL": url,
        "PYTHONPATH": ".",
    }
    result = subprocess.run(
        ["alembic", "upgrade", revision],
        cwd=APP_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}")
    return result


def _alembic_downgrade(url: str, revision: str) -> None:
    environment = {
        **os.environ,
        "APP_ENV": "development",
        "DATABASE_URL": url,
        "PYTHONPATH": ".",
    }
    result = subprocess.run(
        ["alembic", "downgrade", revision],
        cwd=APP_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(f"alembic downgrade failed:\n{result.stdout}\n{result.stderr}")


async def _create_database(name: str) -> None:
    connection = await asyncpg.connect(_admin_dsn())
    try:
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()


async def _drop_database(name: str) -> None:
    connection = await asyncpg.connect(_admin_dsn())
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}"')
    finally:
        await connection.close()


async def _seed_items(url: str, rows: list[dict], *, collision: bool = False) -> None:
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg", "postgresql"))
    try:
        await connection.execute(
            """
            INSERT INTO users (client_id, created_at, username, email, password, online)
            VALUES ('usr_phase6', now(), 'phase6-user', 'phase6@example.test', 'test', false)
            """
        )
        await connection.execute(
            """
            INSERT INTO workspaces (client_id, name, time_zone, created_at, created_by_id)
            VALUES ('ws_phase6', 'Phase 6', 'UTC', now(), 'usr_phase6')
            """
        )
        for row in rows:
            await connection.execute(
                """
                INSERT INTO items (
                    client_id, workspace_id, state, quantity, can_have_upholstery,
                    created_at, created_by_id, is_deleted,
                    item_value_minor, item_cost_minor, item_currency
                ) VALUES ($1, 'ws_phase6', 'pending', 1, true, now(), $2, $3, $4, $5, $6)
                """,
                row["client_id"],
                row.get("created_by_id", "usr_phase6"),
                row.get("is_deleted", False),
                row.get("item_value_minor"),
                row.get("item_cost_minor"),
                row.get("item_currency"),
            )
        if collision:
            await connection.execute(
                """
                INSERT INTO item_valuations (
                    client_id, workspace_id, item_id, expected_sale_price_minor,
                    purchase_cost_minor, currency, created_at, created_by_id, is_deleted
                ) VALUES (
                    'ival_existing', 'ws_phase6', 'itm_collision', 999, NULL,
                    'euro', now(), 'usr_phase6', false
                )
                """
            )
    finally:
        await connection.close()


async def _fetch(url: str, query: str, *args):
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg", "postgresql"))
    try:
        return await connection.fetch(query, *args)
    finally:
        await connection.close()


async def _fetchval(url: str, query: str, *args):
    connection = await asyncpg.connect(url.replace("postgresql+asyncpg", "postgresql"))
    try:
        return await connection.fetchval(query, *args)
    finally:
        await connection.close()


async def _run_case(rows: list[dict], *, collision: bool = False, expected_refusal: str | None = None):
    name = f"beyo_manager_phase6_{uuid4().hex[:12]}"
    url = _url(name)
    await _create_database(name)
    try:
        _alembic(url, BASE_REVISION)
        await _seed_items(url, rows, collision=collision)
        result = _alembic(url, DATA_REVISION, check=False)
        if expected_refusal is not None:
            assert result.returncode != 0
            assert expected_refusal in result.stderr
            assert await _fetchval(url, "SELECT to_regclass('item_valuation_migration_journal')") is None
            assert await _fetchval(url, "SELECT count(*) FROM item_valuations") == 0
        else:
            assert result.returncode == 0, result.stderr
        return url
    except BaseException:
        await _drop_database(name)
        raise


@pytest.mark.integration
async def test_phase6_preflight_p1_p2_p3_refusals_leave_no_persisted_writes():
    cases = (
        ([{"client_id": "itm_p1", "item_value_minor": 10}], "P1"),
        ([{"client_id": "itm_p2", "item_value_minor": -10, "item_currency": "euro"}], "P2"),
        ([{"client_id": "itm_p3", "item_value_minor": 10, "item_currency": "euro", "created_by_id": None}], "P3"),
    )
    for rows, refusal in cases:
        name = f"beyo_manager_phase6_{uuid4().hex[:12]}"
        url = _url(name)
        await _create_database(name)
        try:
            _alembic(url, BASE_REVISION)
            await _seed_items(url, rows)
            result = _alembic(url, DATA_REVISION, check=False)
            assert result.returncode != 0
            assert refusal in result.stderr
            assert await _fetchval(url, "SELECT to_regclass('item_valuation_migration_journal')") is None
            assert await _fetchval(url, "SELECT count(*) FROM item_valuations") == 0
        finally:
            await _drop_database(name)


@pytest.mark.integration
async def test_phase6_seeded_migration_journal_round_trip_and_metadata_shape():
    rows = [
        {"client_id": "itm_all_null"},
        {"client_id": "itm_currency_only", "item_currency": "euro"},
        {"client_id": "itm_valid", "item_value_minor": 1200, "item_cost_minor": 300, "item_currency": "euro"},
        {"client_id": "itm_deleted", "item_value_minor": 700, "item_currency": "euro", "is_deleted": True},
        {"client_id": "itm_collision", "item_value_minor": 200, "item_currency": "euro"},
    ]
    name = f"beyo_manager_phase6_{uuid4().hex[:12]}"
    url = _url(name)
    await _create_database(name)
    try:
        _alembic(url, BASE_REVISION)
        await _seed_items(url, rows, collision=True)
        _alembic(url, DATA_REVISION)
        assert await _fetchval(url, "SELECT count(*) FROM item_valuation_migration_journal") == 4
        assert await _fetchval(url, "SELECT count(*) FROM item_valuations WHERE client_id <> 'ival_existing'") == 1
        valuation = (await _fetch(url, "SELECT item_id, expected_sale_price_minor, purchase_cost_minor, currency FROM item_valuations WHERE client_id <> 'ival_existing'"))[0]
        assert dict(valuation) == {
            "item_id": "itm_valid",
            "expected_sale_price_minor": 1200,
            "purchase_cost_minor": 300,
            "currency": "euro",
        }
        assert await _fetchval(url, "SELECT valuation_client_id FROM item_valuation_migration_journal WHERE item_client_id = 'itm_deleted'") is None
        assert await _fetchval(url, "SELECT valuation_client_id FROM item_valuation_migration_journal WHERE item_client_id = 'itm_collision'") is None
        assert await _fetchval(url, "SELECT count(*) FROM item_valuations WHERE item_id = 'itm_deleted'") == 0
        assert await _fetchval(url, "SELECT count(*) FROM item_valuations WHERE item_id = 'itm_collision'") == 1
        migration_path = APP_ROOT / "migrations/versions/5420acc6a7b3_migrate_item_money_to_valuations.py"
        spec = importlib.util.spec_from_file_location("phase6_data_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_async_engine(url)
        try:
            before = await _fetchval(url, "SELECT count(*) FROM item_valuations")
            async with engine.begin() as connection:
                await connection.run_sync(migration._copy_eligible_valuations)
            assert await _fetchval(url, "SELECT count(*) FROM item_valuations") == before
        finally:
            await engine.dispose()

        _alembic(url, HEAD_REVISION)
        assert await _fetchval(url, "SELECT count(*) FROM information_schema.columns WHERE table_name = 'items' AND column_name IN ('item_value_minor', 'item_cost_minor', 'item_currency')") == 0

        # The manual valuation is intentionally not journaled and must survive both downgrades.
        connection = await asyncpg.connect(url.replace("postgresql+asyncpg", "postgresql"))
        try:
            await connection.execute(
                """
                INSERT INTO item_valuations (
                    client_id, workspace_id, item_id, purchase_cost_minor, currency,
                    created_at, created_by_id, is_deleted
                ) VALUES ('ival_manual', 'ws_phase6', 'itm_currency_only', 42, 'euro', now(), 'usr_phase6', false)
                """
            )
        finally:
            await connection.close()

        _alembic_downgrade(url, DATA_REVISION)
        assert await _fetchval(url, "SELECT count(*) FROM item_valuation_migration_journal") == 4
        _alembic_downgrade(url, BASE_REVISION)
        restored = await _fetch(
            url,
            """
            SELECT client_id, item_value_minor, item_cost_minor, item_currency
            FROM items WHERE client_id <> 'itm_all_null' ORDER BY client_id
            """,
        )
        assert [dict(row) for row in restored] == [
            {"client_id": "itm_collision", "item_value_minor": 200, "item_cost_minor": None, "item_currency": "euro"},
            {"client_id": "itm_currency_only", "item_value_minor": None, "item_cost_minor": None, "item_currency": "euro"},
            {"client_id": "itm_deleted", "item_value_minor": 700, "item_cost_minor": None, "item_currency": "euro"},
            {"client_id": "itm_valid", "item_value_minor": 1200, "item_cost_minor": 300, "item_currency": "euro"},
        ]
        assert await _fetchval(url, "SELECT to_regclass('item_valuation_migration_journal')") is None
        assert await _fetchval(url, "SELECT count(*) FROM item_valuations") == 2

        _alembic(url, HEAD_REVISION)
        assert await _fetchval(url, "SELECT count(*) FROM item_valuations WHERE client_id <> 'ival_manual'") == 2
        assert await _fetchval(
            url,
            """
            SELECT count(*)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_type t ON t.oid = a.atttypid
            WHERE c.relname = 'item_upholstery_requirements'
              AND a.attname = 'currency'
              AND t.typname = 'item_currency_enum'
              AND NOT a.attisdropped
            """,
        ) == 1

        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                def _compare(sync_connection):
                    context = MigrationContext.configure(sync_connection)
                    return compare_metadata(context, Base.metadata)

                differences = await connection.run_sync(_compare)
        finally:
            await engine.dispose()
        relevant = [
            difference
            for difference in differences
            if any(table_name in repr(difference) for table_name in ("items", "item_upholstery_requirements"))
        ]
        assert relevant == []
    finally:
        await _drop_database(name)
