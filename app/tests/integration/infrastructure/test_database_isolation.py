from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from beyo_manager.config import settings
from beyo_manager.models import database as database_module
from tests.database_isolation import (
    EXPECTED_HEAD,
    EXPECTED_PUBLIC_TABLE_COUNT,
    DatabaseIsolation,
    UnsafeDatabaseError,
    assert_disposable_database,
    resolve_worker_database_name,
)


@pytest.mark.parametrize(
    ("worker_id", "expected"),
    [("gw0", "beyo_test_gw0"), ("gw11", "beyo_test_gw11"), (None, "beyo_test_main")],
)
def test_worker_name_resolution(worker_id: str | None, expected: str) -> None:
    assert resolve_worker_database_name(worker_id) == expected


def test_worker_name_resolution_rejects_unknown_worker() -> None:
    with pytest.raises(UnsafeDatabaseError):
        resolve_worker_database_name("worker-1")


@pytest.mark.parametrize(
    ("database_name", "configured_url", "marker_present"),
    [
        ("beyo_manager", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager", True),
        (
            "beyo_test_gw0; DROP DATABASE beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            True,
        ),
        (
            "beyo_test_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_gw0",
            True,
        ),
        (
            "beyo_test_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            False,
        ),
        ("beyo_test_gw0", None, True),
        ("beyo_test_gw0", "not-a-database-url", True),
    ],
)
def test_destructive_guard_rejects_every_unsafe_case(
    database_name: str, configured_url: str | None, marker_present: bool
) -> None:
    with pytest.raises(UnsafeDatabaseError):
        assert_disposable_database(
            database_name, configured_url, marker_present=marker_present
        )


@pytest.mark.asyncio
async def test_template_has_migrated_head_and_full_schema(isolated_database: DatabaseIsolation) -> None:
    inspection = await isolated_database.inspect(isolated_database.template_database_name)
    assert inspection.head_revision == EXPECTED_HEAD
    assert inspection.public_table_count == EXPECTED_PUBLIC_TABLE_COUNT
    assert inspection.marker_present
    assert {
        "cost_model_versions",
        "item_cost_results",
        "step_state_records",
    } <= await isolated_database.public_table_names(
        isolated_database.template_database_name
    )


@pytest.mark.asyncio
async def test_worker_is_a_faithful_template_copy(isolated_database: DatabaseIsolation) -> None:
    template = await isolated_database.inspect(isolated_database.template_database_name)
    worker = await isolated_database.inspect(isolated_database.worker_database_name)
    assert worker.head_revision == template.head_revision == EXPECTED_HEAD
    assert worker.public_table_count == template.public_table_count == EXPECTED_PUBLIC_TABLE_COUNT
    assert worker.marker_present


@pytest.mark.asyncio
async def test_application_database_seam_points_at_worker(isolated_database: DatabaseIsolation) -> None:
    assert settings.database_url is not None
    assert isolated_database.worker_database_name in settings.database_url
    assert "beyo_manager" not in settings.database_url.rsplit("/", 1)[-1]
    assert database_module._engine is not None
    assert database_module._engine.url.database == isolated_database.worker_database_name


@pytest.mark.asyncio
async def test_dev_database_counts_are_untouched(isolated_database: DatabaseIsolation) -> None:
    before = isolated_database.configured_row_counts_before_run
    assert before is not None
    after = await isolated_database.row_counts(isolated_database.configured_database_name)
    assert after == before
    active_database_name = make_url(settings.database_url).database
    assert active_database_name == isolated_database.worker_database_name


@pytest.mark.asyncio
async def test_fixed_name_reabsorbs_an_interrupted_worker(
    isolated_database: DatabaseIsolation,
) -> None:
    probe = DatabaseIsolation(settings.database_url, worker_id="gw999")
    before = set(await probe.database_names())
    await probe._create_database(probe.worker_database_name)
    await probe._set_marker(probe.worker_database_name)
    assert set(await probe.database_names()) == before | {probe.worker_database_name}
    try:
        await probe.start()
        assert set(await probe.database_names()) == before | {probe.worker_database_name}
    finally:
        await probe.stop()
    assert set(await probe.database_names()) == before
