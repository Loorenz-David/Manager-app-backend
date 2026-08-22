from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.engine import make_url

from beyo_manager.config import settings
from beyo_manager.models import database as database_module
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import seed_pause_reasons
from beyo_manager.services.infra.redis.keys import make_key
from beyo_manager.models import Base
from tests.conftest import pytest_collection_modifyitems
from tests.database_isolation import (
    EXPECTED_HEAD,
    LEGACY_RECLAIM_ENV,
    REQUIRED_PUBLIC_TABLES,
    MARKER_SCHEMA,
    DatabaseIsolation,
    UnsafeDatabaseError,
    _connect,
    assert_migrated_schema,
    assert_disposable_database,
    migration_head_revision,
    expected_public_tables,
    resolve_template_database_name,
    resolve_test_slot,
    resolve_worker_database_name,
)


@pytest.fixture(scope="module", autouse=True)
async def assert_test_database_membership_is_reclaimed(
    isolated_database: DatabaseIsolation,
):
    """Require this criterion module to reclaim every disposable database it creates."""
    owned_names = {
        isolated_database.template_database_name,
        isolated_database.worker_database_name,
    }
    before = set(await isolated_database.database_names()) & owned_names
    sibling = DatabaseIsolation(settings.database_url, worker_id="gw990")
    await sibling.start()
    try:
        yield
    finally:
        after = set(await isolated_database.database_names()) & owned_names
        try:
            assert after == before, (
                "criterion module changed this worker's database membership: "
                f"before={sorted(before)}, after={sorted(after)}"
            )
        finally:
            if sibling._started:
                await sibling.stop()


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
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
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


def test_worker_name_resolution_uses_xdist_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw17")
    assert resolve_worker_database_name() == "beyo_test_main_gw17"


def test_shipped_default_reaches_an_xdist_worker(pytestconfig: pytest.Config) -> None:
    """Prove the shipped pytest configuration, rather than a CLI override, is parallel."""
    args = list(pytestconfig.invocation_params.args)
    if any(
        arg == "-n"
        or arg.startswith("-n")
        or arg == "--numprocesses"
        or arg.startswith("--numprocesses=")
        for arg in args
    ):
        pytest.skip("serial comparator deliberately overrides the shipped parallel default")

    addopts = pytestconfig.getini("addopts")
    assert any(
        (
            arg == "--dist"
            and index + 1 < len(addopts)
            and addopts[index + 1] == "loadfile"
        )
        or arg == "--dist=loadfile"
        for index, arg in enumerate(addopts)
    ), f"shipped parallel default is missing --dist loadfile: {addopts!r}"
    assert any(
        (
            arg == "-n"
            and index + 1 < len(addopts)
            and addopts[index + 1].isdigit()
            and int(addopts[index + 1]) > 0
        )
        or (arg.startswith("-n") and arg[2:].isdigit() and int(arg[2:]) > 0)
        or (
            arg == "--numprocesses"
            and index + 1 < len(addopts)
            and addopts[index + 1].isdigit()
            and int(addopts[index + 1]) > 0
        )
        or (
            arg.startswith("--numprocesses=")
            and arg.split("=", 1)[1].isdigit()
            and int(arg.split("=", 1)[1]) > 0
        )
        for index, arg in enumerate(addopts)
    ), f"shipped parallel default is missing a positive worker count: {addopts!r}"
    assert re.fullmatch(r"gw\d+", os.environ.get("PYTEST_XDIST_WORKER", "")), (
        "the shipped default did not reach an xdist worker"
    )


@pytest.mark.parametrize("slot", ["Alpha", "al pha", "alpha_beta", "", "a" * 13])
def test_slot_resolution_rejects_invalid_values(slot: str) -> None:
    with pytest.raises(UnsafeDatabaseError):
        resolve_test_slot(slot)


def test_collection_order_hook_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BEYO_TEST_COLLECTION_ORDER", raising=False)
    items = ["first", "second", "third"]
    pytest_collection_modifyitems(None, items)
    assert items == ["first", "second", "third"]


def test_collection_probe_hook_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BEYO_TEST_COLLECTION_PROBE", raising=False)
    items = ["regular", "phase3-probe"]
    pytest_collection_modifyitems(None, items)
    assert items == ["regular", "phase3-probe"]


def test_collection_probe_hook_accepts_explicit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEYO_TEST_COLLECTION_PROBE", "off")
    items = ["regular", "phase3-probe"]
    pytest_collection_modifyitems(None, items)
    assert items == ["regular", "phase3-probe"]


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


@pytest.mark.parametrize(
    ("configured_host", "target_host"),
    [
        ("localhost", "LOCALHOST"),
        ("localhost", "::1"),
        ("localhost", "localhost."),
        ("localhost", "localhost.localdomain"),
        ("localhost", "ip6-localhost"),
    ],
)
def test_endpoint_aliases_are_confined_to_same_server(
    configured_host: str,
    target_host: str,
) -> None:
    configured = f"postgresql+asyncpg://postgres:postgres@{configured_host}:5433/beyo_manager"
    target_host_part = f"[{target_host}]" if ":" in target_host else target_host
    target = (
        "postgresql+asyncpg://postgres:postgres@"
        f"{target_host_part}:5433/beyo_test_main_gw0"
    )
    assert_disposable_database(
        "beyo_test_main_gw0",
        configured,
        target_database_url=target,
        marker_present=True,
    )


def test_endpoint_with_different_host_is_still_refused() -> None:
    with pytest.raises(UnsafeDatabaseError):
        assert_disposable_database(
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager",
            target_database_url=(
                "postgresql+asyncpg://postgres:postgres@other-host:5433/"
                "beyo_test_main_gw0"
            ),
            marker_present=True,
        )


def test_unspecified_endpoint_is_refused() -> None:
    with pytest.raises(UnsafeDatabaseError):
        assert_disposable_database(
            "beyo_test_main_gw0",
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/beyo_manager",
            target_database_url=(
                "postgresql+asyncpg://postgres:postgres@0.0.0.0:5433/"
                "beyo_test_main_gw0"
            ),
            marker_present=True,
        )


async def _remove_probe_databases(probe: DatabaseIsolation) -> None:
    for database_name in (probe.worker_database_name, probe.template_database_name):
        if await probe._database_exists(database_name):
            if not await probe._marker_present(database_name):
                inspection = await probe.inspect(database_name)
                assert inspection.public_table_count == 0
            await probe._drop_database_if_exists(database_name)


async def _assert_concurrent_starts_succeed(probes: list[DatabaseIsolation]) -> None:
    results = await asyncio.gather(*(probe.start() for probe in probes), return_exceptions=True)
    assert results == [None] * len(probes), results


@pytest.mark.asyncio
async def test_concurrent_starts_survive_absent_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEYO_TEST_SLOT", "p3absent")
    probes = [
        DatabaseIsolation(settings.database_url, worker_id="gw900"),
        DatabaseIsolation(settings.database_url, worker_id="gw901"),
    ]
    await _remove_probe_databases(probes[0])
    try:
        await _assert_concurrent_starts_succeed(probes)
    finally:
        for probe in probes:
            if probe._started:
                await probe.stop()
        await _remove_probe_databases(probes[0])


@pytest.mark.asyncio
async def test_concurrent_starts_survive_stale_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEYO_TEST_SLOT", "p3stale")
    seed = DatabaseIsolation(settings.database_url, worker_id="gw902")
    probes = [
        DatabaseIsolation(settings.database_url, worker_id="gw903"),
        DatabaseIsolation(settings.database_url, worker_id="gw904"),
    ]
    await _remove_probe_databases(seed)
    try:
        await seed.start()
        await seed.stop()
        connection = await _connect(seed._url, seed.template_database_name)
        try:
            await connection.execute("UPDATE alembic_version SET version_num = 'stale'")
        finally:
            await connection.close()
        await _assert_concurrent_starts_succeed(probes)
    finally:
        for probe in [seed, *probes]:
            if probe._started:
                await probe.stop()
        await _remove_probe_databases(seed)


@pytest.mark.asyncio
async def test_concurrent_starts_survive_current_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BEYO_TEST_SLOT", "p3current")
    seed = DatabaseIsolation(settings.database_url, worker_id="gw905")
    probes = [
        DatabaseIsolation(settings.database_url, worker_id="gw906"),
        DatabaseIsolation(settings.database_url, worker_id="gw907"),
    ]
    await _remove_probe_databases(seed)
    try:
        await seed.start()
        await seed.stop()
        connection = await _connect(seed._url, seed.template_database_name)

        for probe in probes:
            app_name = f"p3current_{probe.worker_database_name}"
            original_maintenance_connection = probe._maintenance_connection
            original_create_from_template = probe._create_database_from_template

            async def named_maintenance_connection(
                original=original_maintenance_connection,
                application_name=app_name,
            ):
                maintenance = await original()
                await maintenance.execute(
                    "SELECT set_config('application_name', $1, false)", application_name
                )
                return maintenance

            async def create_with_lock_observer(
                database_name: str,
                original=original_create_from_template,
                application_name=app_name,
            ) -> None:
                observer = await _connect(seed._url, "postgres")
                try:
                    lock_held = await observer.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT 1
                            FROM pg_locks AS locks
                            JOIN pg_stat_activity AS activity ON activity.pid = locks.pid
                            WHERE locks.locktype = 'advisory'
                              AND locks.granted
                              AND activity.application_name = $1
                        )
                        """,
                        application_name,
                    )
                finally:
                    await observer.close()
                if lock_held and not connection.is_closed():
                    await connection.close()
                await original(database_name)

            monkeypatch.setattr(probe, "_maintenance_connection", named_maintenance_connection)
            monkeypatch.setattr(
                probe,
                "_create_database_from_template",
                create_with_lock_observer,
            )
        try:
            await _assert_concurrent_starts_succeed(probes)
        finally:
            if not connection.is_closed():
                await connection.close()
    finally:
        for probe in [seed, *probes]:
            if probe._started:
                await probe.stop()
        await _remove_probe_databases(seed)


@pytest.mark.asyncio
async def test_new_migration_rebuilds_template_without_pinned_schema_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_root = Path(__file__).resolve().parents[3]
    versions_dir = app_root / "migrations" / "versions"
    previous_head = migration_head_revision(app_root)
    revision_id = f"p3c6{uuid4().hex[:10]}"
    revision_file = versions_dir / "phase3_c6_temporary_revision.py"
    assert not revision_file.exists()
    revision_file.write_text(
        "revision = %r\n"
        "down_revision = %r\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "def upgrade():\n    pass\n\n"
        "def downgrade():\n    pass\n"
        % (revision_id, previous_head)
    )
    monkeypatch.setenv("BEYO_TEST_SLOT", "p3c6")
    probe = DatabaseIsolation(settings.database_url, worker_id="gw908")
    try:
        heads = ScriptDirectory.from_config(Config(str(app_root / "alembic.ini"))).get_heads()
        assert heads == [revision_id]
        await probe.start()
        inspection = await probe.inspect(probe.template_database_name)
        assert inspection.head_revision == revision_id
        assert REQUIRED_PUBLIC_TABLES <= await probe.public_table_names(
            probe.template_database_name
        )
    finally:
        if probe._started:
            await probe.stop()
        await _remove_probe_databases(probe)
        revision_file.unlink(missing_ok=True)


def test_schema_assertion_rejects_missing_metadata_table_with_required_tables_present() -> None:
    metadata_only_tables = set(Base.metadata.tables) - REQUIRED_PUBLIC_TABLES
    missing_table = next(iter(metadata_only_tables))
    table_names = expected_public_tables() - {missing_table}

    with pytest.raises(RuntimeError, match=missing_table):
        assert_migrated_schema(
            "beyo_test_main_template",
            actual_head=EXPECTED_HEAD,
            expected_head=EXPECTED_HEAD,
            table_names=table_names,
        )


def test_schema_assertion_rejects_unenumerated_public_table() -> None:
    table_names = expected_public_tables() | {"unexpected_public_table"}

    with pytest.raises(RuntimeError, match="expected 107 public tables"):
        assert_migrated_schema(
            "beyo_test_main_template",
            actual_head=EXPECTED_HEAD,
            expected_head=EXPECTED_HEAD,
            table_names=table_names,
        )


@pytest.mark.asyncio
async def test_template_has_migrated_head_and_full_schema(isolated_database: DatabaseIsolation) -> None:
    inspection = await isolated_database.inspect(isolated_database.template_database_name)
    assert inspection.head_revision == EXPECTED_HEAD
    assert inspection.marker_present
    assert REQUIRED_PUBLIC_TABLES <= await isolated_database.public_table_names(
        isolated_database.template_database_name
    )


@pytest.mark.asyncio
async def test_worker_is_a_faithful_template_copy(isolated_database: DatabaseIsolation) -> None:
    template = await isolated_database.inspect(isolated_database.template_database_name)
    worker = await isolated_database.inspect(isolated_database.worker_database_name)
    assert worker.head_revision == template.head_revision == EXPECTED_HEAD
    assert REQUIRED_PUBLIC_TABLES <= await isolated_database.public_table_names(
        isolated_database.worker_database_name
    )
    assert worker.marker_present
    assert_disposable_database(
        isolated_database.worker_database_name,
        isolated_database.configured_database_url,
        target_database_url=isolated_database.worker_database_url,
        marker_present=worker.marker_present,
        public_table_count=worker.public_table_count,
    )


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
    owned_worker_names = {probe.worker_database_name}
    before = set(await probe.database_names()) & owned_worker_names
    legacy_name = "beyo_test_gw999"
    other_slot_name = "beyo_test_alpha_main"
    try:
        await probe._create_database_from_template(probe.worker_database_name)
        if mark_leftover:
            await probe._set_marker(probe.worker_database_name)
        assert set(await probe.database_names()) & owned_worker_names == (
            before | {probe.worker_database_name}
        )
        await probe.start()
        assert set(await probe.database_names()) & owned_worker_names == (
            before | {probe.worker_database_name}
        )

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
    assert set(await probe.database_names()) & owned_worker_names == before


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
