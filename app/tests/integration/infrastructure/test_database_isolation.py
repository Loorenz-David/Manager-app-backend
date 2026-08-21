from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from beyo_manager.config import settings
from beyo_manager.models import database as database_module
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import seed_pause_reasons
from beyo_manager.services.infra.redis.keys import make_key
from tests.conftest import pytest_collection_modifyitems
from tests.database_isolation import (
    EXPECTED_HEAD,
    EXPECTED_PUBLIC_TABLE_COUNT,
    LEGACY_RECLAIM_ENV,
    MARKER_SCHEMA,
    DatabaseIsolation,
    UnsafeDatabaseError,
    _connect,
    assert_disposable_database,
    resolve_template_database_name,
    resolve_test_slot,
    resolve_worker_database_name,
)


@pytest.fixture(scope="module", autouse=True)
async def assert_test_database_membership_is_reclaimed(
    isolated_database: DatabaseIsolation,
):
    """Require this criterion module to reclaim every disposable database it creates."""
    before = {
        name
        for name in await isolated_database.database_names()
        if name.startswith("beyo_test_")
    }
    yield
    after = {
        name
        for name in await isolated_database.database_names()
        if name.startswith("beyo_test_")
    }
    assert after == before, (
        "criterion module changed beyo_test_* database membership: "
        f"before={sorted(before)}, after={sorted(after)}"
    )


@pytest.mark.parametrize(
    ("worker_id", "slot", "expected"),
    [
        ("gw0", "alpha", "beyo_test_alpha_gw0"),
        ("gw11", "alpha", "beyo_test_alpha_gw11"),
        (None, "alpha", "beyo_test_alpha_main"),
        (None, None, "beyo_test_main_main"),
    ],
)
def test_worker_name_resolution(
    monkeypatch: pytest.MonkeyPatch,
    worker_id: str | None,
    slot: str | None,
    expected: str,
) -> None:
    monkeypatch.delenv("BEYO_TEST_SLOT", raising=False)
    assert resolve_worker_database_name(worker_id, slot=slot) == expected

    monkeypatch.setattr(settings, "test_slot", "shopify")
    assert resolve_worker_database_name() == "beyo_test_shopify_main"
    monkeypatch.setenv("BEYO_TEST_SLOT", "alpha")
    assert resolve_worker_database_name() == "beyo_test_alpha_main"


def test_template_name_is_per_slot() -> None:
    assert resolve_template_database_name("alpha") == "beyo_test_alpha_template"
    assert resolve_template_database_name("main") == "beyo_test_main_template"


def test_worker_name_resolution_rejects_unknown_worker() -> None:
    with pytest.raises(UnsafeDatabaseError):
        resolve_worker_database_name("worker-1")


@pytest.mark.parametrize("slot", ["Alpha", "al pha", "alpha_beta", "", "a" * 13])
def test_slot_resolution_rejects_invalid_values(slot: str) -> None:
    with pytest.raises(UnsafeDatabaseError):
        resolve_test_slot(slot)


def test_collection_order_hook_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BEYO_TEST_COLLECTION_ORDER", raising=False)
    items = ["first", "second", "third"]
    pytest_collection_modifyitems(None, items)
    assert items == ["first", "second", "third"]


def test_collection_order_hook_reverses_once_and_rejects_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEYO_TEST_COLLECTION_ORDER", "reverse")
    items = ["first", "second", "third"]
    pytest_collection_modifyitems(None, items)
    assert items == ["third", "second", "first"]

    monkeypatch.setenv("BEYO_TEST_COLLECTION_ORDER", "backwards")
    with pytest.raises(pytest.UsageError):
        pytest_collection_modifyitems(None, items)


def test_default_redis_key_uses_the_process_prefix() -> None:
    key = make_key("phase2", "probe")
    assert settings.redis_key_prefix != "beyo_manager"
    assert key.startswith(f"{settings.redis_key_prefix}:phase2:")


@pytest.mark.parametrize(
    ("database_name", "configured_url", "target_url", "marker_present", "public_table_count"),
    [
        (
            "beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            True,
            107,
        ),
        (
            "beyo_test_gw0; DROP DATABASE beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_gw0; DROP DATABASE beyo_manager",
            True,
            0,
        ),
        (
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0",
            True,
            107,
        ),
        ("beyo_test_main_gw0", None, "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0", True, 0),
        ("beyo_test_main_gw0", "not-a-database-url", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0", True, 0),
        (
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@other-host:5433/beyo_test_main_gw0",
            True,
            0,
        ),
        (
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/beyo_test_main_gw0",
            True,
            0,
        ),
        (
            "beyo_test_main_gw٠",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw٠",
            True,
            107,
        ),
        (
            "beyo_test_main_gw0\n",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0",
            True,
            107,
        ),
        (
            "beyo_test_Alpha_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_Alpha_gw0",
            True,
            107,
        ),
        (
            "beyo_test_alpha_beta_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_alpha_beta_gw0",
            True,
            107,
        ),
        (
            "beyo_test_aaaaaaaaaaaaa_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_aaaaaaaaaaaaa_gw0",
            True,
            107,
        ),
    ],
)
def test_destructive_guard_rejects_every_unsafe_case(
    database_name: str,
    configured_url: str | None,
    target_url: str | None,
    marker_present: bool,
    public_table_count: int,
) -> None:
    with pytest.raises(UnsafeDatabaseError):
        assert_disposable_database(
            database_name,
            configured_url,
            target_database_url=target_url,
            marker_present=marker_present,
            public_table_count=public_table_count,
        )


def test_unmarked_empty_database_is_allowed_but_populated_one_is_not() -> None:
    target = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0"
    assert_disposable_database(
        "beyo_test_main_gw0",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager",
        target_database_url=target,
        marker_present=False,
        public_table_count=0,
    )
    with pytest.raises(UnsafeDatabaseError):
        assert_disposable_database(
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager",
            target_database_url=target,
            marker_present=False,
            public_table_count=1,
        )

    for target in (
        "mysql://postgres:postgres@127.0.0.1:5433/beyo_test_main_gw0",
        "postgresql+asyncpg://:postgres@127.0.0.1:5433/beyo_test_main_gw0",
        "not-a-database-url",
    ):
        with pytest.raises(UnsafeDatabaseError):
            assert_disposable_database(
                "beyo_test_main_gw0",
                "postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager",
                target_database_url=target,
                marker_present=True,
                public_table_count=0,
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
async def test_dev_database_counts_are_untouched(
    isolated_database: DatabaseIsolation,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = isolated_database.configured_row_counts_before_run
    assert before is not None
    after = await isolated_database.row_counts(isolated_database.configured_database_name)
    assert after == before
    active_database_name = make_url(settings.database_url).database
    assert active_database_name == isolated_database.worker_database_name

    untracked = DatabaseIsolation(
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_test_main"
    )

    async def unexpected_row_count(_database_name: str) -> dict[str, int]:
        raise AssertionError("row counts should not be read without a baseline")

    monkeypatch.setattr(untracked, "row_counts", unexpected_row_count)
    await untracked.assert_configured_database_unchanged()

    workspace = Workspace(name="phase2-bootstrap-pause-reasons")
    db_session.add(workspace)
    await db_session.flush()
    pause_reason_ids = await seed_pause_reasons(db_session, workspace.client_id)
    rows = (
        await db_session.scalars(
            select(PauseReason).where(PauseReason.workspace_id == workspace.client_id)
        )
    ).all()
    assert set(pause_reason_ids.values()) == {row.client_id for row in rows}
    assert rows
    assert all(row.is_system_managed is False for row in rows)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mark_leftover",
    [pytest.param(True, id="explicitly-marked")],
)
async def test_fixed_name_reabsorbs_an_interrupted_worker(
    isolated_database: DatabaseIsolation,
    mark_leftover: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = DatabaseIsolation(settings.database_url, worker_id="gw999")
    before = set(await probe.database_names())
    legacy_name = "beyo_test_gw999"
    other_slot_name = "beyo_test_alpha_main"
    try:
        await probe._create_database_from_template(probe.worker_database_name)
        if mark_leftover:
            await probe._set_marker(probe.worker_database_name)
        assert set(await probe.database_names()) == before | {probe.worker_database_name}
        await probe.start()
        assert set(await probe.database_names()) == before | {probe.worker_database_name}

        for database_name in (legacy_name, other_slot_name):
            if await probe._database_exists(database_name):
                await probe._set_marker(database_name)
                await probe._drop_database_if_exists(database_name)
        await probe._create_database(legacy_name)
        await probe._create_database(other_slot_name)

        monkeypatch.delenv(LEGACY_RECLAIM_ENV, raising=False)
        await probe.stop()
        await probe.start()
        await probe.stop()
        assert await probe._database_exists(legacy_name)
        assert await probe._database_exists(other_slot_name)

        monkeypatch.setenv(LEGACY_RECLAIM_ENV, "1")
        await probe.start()
        await probe.stop()
        assert not await probe._database_exists(legacy_name)
        assert await probe._database_exists(other_slot_name)
    finally:
        if probe._started:
            await probe.stop()
        for database_name in (probe.worker_database_name, legacy_name, other_slot_name):
            if await probe._database_exists(database_name):
                if not await probe._marker_present(database_name):
                    await probe._set_marker(database_name)
                await probe._drop_database_if_exists(database_name)
    assert set(await probe.database_names()) == before


@pytest.mark.asyncio
async def test_start_cleans_worker_when_interrupted_during_creation(
    isolated_database: DatabaseIsolation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = DatabaseIsolation(settings.database_url, worker_id="gw998")
    create_from_template = probe._create_database_from_template

    async def create_then_interrupt(database_name: str) -> None:
        await create_from_template(database_name)
        raise KeyboardInterrupt

    monkeypatch.setattr(probe, "_create_database_from_template", create_then_interrupt)
    try:
        with pytest.raises(KeyboardInterrupt):
            await probe.start()
        assert not await probe._database_exists(probe.worker_database_name)
    finally:
        if await probe._database_exists(probe.worker_database_name):
            if not await probe._marker_present(probe.worker_database_name):
                await probe._set_marker(probe.worker_database_name)
            if probe._started:
                await probe.stop()
            else:
                await probe._drop_database_if_exists(probe.worker_database_name)


@pytest.mark.asyncio
async def test_empty_unmarked_worker_is_droppable_but_populated_one_is_not(
    isolated_database: DatabaseIsolation,
) -> None:
    empty_probe = DatabaseIsolation(settings.database_url, worker_id="gw997")
    populated_probe = DatabaseIsolation(settings.database_url, worker_id="gw996")
    try:
        await empty_probe._create_database(empty_probe.worker_database_name)
        await empty_probe._drop_database_if_exists(empty_probe.worker_database_name)
        assert not await empty_probe._database_exists(empty_probe.worker_database_name)

        await populated_probe._create_database_from_template(populated_probe.worker_database_name)
        connection = await _connect(populated_probe._url, populated_probe.worker_database_name)
        try:
            await connection.execute(f'DROP SCHEMA "{MARKER_SCHEMA}" CASCADE')
        finally:
            await connection.close()
        with pytest.raises(UnsafeDatabaseError):
            await populated_probe._drop_database_if_exists(populated_probe.worker_database_name)
        assert await populated_probe._database_exists(populated_probe.worker_database_name)
    finally:
        if await populated_probe._database_exists(populated_probe.worker_database_name):
            await populated_probe._set_marker(populated_probe.worker_database_name)
            await populated_probe._drop_database_if_exists(populated_probe.worker_database_name)


@pytest.mark.asyncio
async def test_unmarked_template_shell_is_absorbed(
    isolated_database: DatabaseIsolation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEYO_TEST_SLOT", "phase2")
    probe = DatabaseIsolation(settings.database_url, worker_id="gw995")
    original_set_marker = probe._set_marker

    async def interrupt_template(database_name: str) -> None:
        if database_name == probe.template_database_name:
            raise KeyboardInterrupt
        await original_set_marker(database_name)

    monkeypatch.setattr(probe, "_set_marker", interrupt_template)
    try:
        with pytest.raises(KeyboardInterrupt):
            await probe.start()
        assert await probe._database_exists(probe.template_database_name)
        assert not await probe._marker_present(probe.template_database_name)

        monkeypatch.setattr(probe, "_set_marker", original_set_marker)
        await probe.start()
        assert (await probe.inspect(probe.template_database_name)).marker_present
    finally:
        if probe._started:
            await probe.stop()
        elif await probe._database_exists(probe.worker_database_name):
            await probe._set_marker(probe.worker_database_name)
            await probe._drop_database_if_exists(probe.worker_database_name)
        if await probe._database_exists(probe.template_database_name):
            await probe._drop_database_if_exists(probe.template_database_name)


@pytest.mark.asyncio
async def test_teardown_residue_proxy_detects_a_declared_probe_database_mutation(
    isolated_database: DatabaseIsolation,
) -> None:
    probe = DatabaseIsolation(settings.database_url, worker_id="gw994")
    await probe._create_database_from_template(probe.worker_database_name)
    probe_url = probe._url.set(database=probe.worker_database_name).render_as_string(
        hide_password=False
    )
    checker = DatabaseIsolation(probe_url, worker_id="gw993")
    try:
        checker.configured_row_counts_before_run = await checker.row_counts(
            checker.configured_database_name
        )
        connection = await _connect(probe._url, probe.worker_database_name)
        try:
            await connection.execute(
                """
                INSERT INTO workspaces (client_id, name, time_zone, created_at)
                VALUES ('ws_phase2_residue_probe', 'phase2 residue probe', 'UTC', now())
                """
            )
        finally:
            await connection.close()
        with pytest.raises(AssertionError, match="row counts changed"):
            await checker.assert_configured_database_unchanged()
    finally:
        if await probe._database_exists(probe.worker_database_name):
            await probe._drop_database_if_exists(probe.worker_database_name)
