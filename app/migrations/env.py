import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic detects schema changes.
from beyo_manager.models import Base  # noqa: F401
from beyo_manager.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Convention: a table whose name ends in this suffix is MIGRATION-OWNED BOOKKEEPING —
# created by a migration in raw SQL, read only by that migration's downgrade (or a
# later migration's cleanup), and deliberately absent from ORM metadata because it is
# not a domain table and must not gain a model.
#
# Without this filter, autogenerate sees such a table in the database but not in
# `Base.metadata` and emits `op.drop_table(...)` for it in the next unrelated
# revision — silently destroying the record that makes its owning migration
# reversible (e.g. `transition_reason_backfill_journal`). Any future raw-SQL
# bookkeeping table must use this suffix to inherit the same protection.
_MIGRATION_BOOKKEEPING_SUFFIX = "_journal"


def _include_object(object_, name, type_, reflected, compare_to):
    """Keep autogenerate's hands off migration-owned bookkeeping tables.

    The excluded case is exactly `reflected and compare_to is None` — a table that
    exists in the database with no metadata counterpart, which autogenerate would
    otherwise drop. A genuine ORM table that happened to use the suffix would have a
    metadata counterpart and is unaffected.
    """
    if (
        type_ == "table"
        and reflected
        and compare_to is None
        and name.endswith(_MIGRATION_BOOKKEEPING_SUFFIX)
    ):
        return False
    return True


def _restore_cold_build_role_enum(*, ctx, step, **_) -> None:
    """Restore the schema that the superseded role-enum revision used to build.

    Revision 71df is intentionally a no-op for databases that already received
    the replacement specialization branch.  On a cold database that leaves
    the later 6f4d rename without its source enum.  Apply the old shape after
    the initial schema migration, before the graph reaches 6f4d; the guard
    keeps existing partial upgrades safe.
    """
    if step.up_revision_id != "a1312183fdfb" or ctx.as_sql:
        return
    ctx.connection.execute(
        text(
            """
            DO $$
            BEGIN
                IF to_regtype('workspace_role_name_enum') IS NULL
                   AND to_regtype('workspace_role_specialization_enum') IS NULL THEN
                    CREATE TYPE workspace_role_name_enum AS ENUM ('wood_worker');
                    ALTER TABLE workspace_roles ALTER COLUMN name DROP NOT NULL;
                    UPDATE workspace_roles SET name = NULL;
                    ALTER TABLE workspace_roles
                        ALTER COLUMN name TYPE workspace_role_name_enum
                        USING name::workspace_role_name_enum;
                END IF;
            END $$;
            """
        )
    )


_COLD_BUILD_WORKSPACE_ID = "mig_cold_build_workspace"


def _cold_build_workspace_callbacks(connection):
    """Temporarily anchor a genuinely cold build, then remove its residue.

    The historical pause-reason migrations require one workspace while the
    schema is built from empty. The anchor is created only when neither
    ``alembic_version`` nor ``workspaces`` exists, and cleanup runs in the
    caller's ``finally`` block so a successful or failed build cannot leave the
    synthetic workspace (or its anchor-owned pause reasons) behind.
    """
    is_cold_build = connection.execute(
        text(
            """
            SELECT NOT EXISTS (
                       SELECT 1
                       FROM information_schema.tables
                       WHERE table_schema = current_schema()
                         AND table_name = 'alembic_version'
                   )
               AND NOT EXISTS (
                       SELECT 1
                       FROM information_schema.tables
                       WHERE table_schema = current_schema()
                         AND table_name = 'workspaces'
                   )
            """
        )
    ).scalar_one()
    created = False

    def ensure(*, ctx, step, **_) -> None:
        nonlocal created
        if not is_cold_build or step.up_revision_id != "a1312183fdfb" or ctx.as_sql:
            return
        created_id = ctx.connection.execute(
            text(
                """
                INSERT INTO workspaces (name, time_zone, created_by_id, created_at, client_id)
                VALUES ('Migration workspace', 'UTC', NULL, now(), :client_id)
                RETURNING client_id
                """
            ),
            {"client_id": _COLD_BUILD_WORKSPACE_ID},
        ).scalar_one_or_none()
        created = created_id == _COLD_BUILD_WORKSPACE_ID

    def cleanup() -> None:
        if not created:
            return
        connection.execute(
            text("DELETE FROM pause_reasons WHERE workspace_id = :workspace_id"),
            {"workspace_id": _COLD_BUILD_WORKSPACE_ID},
        )
        connection.execute(
            text("DELETE FROM workspaces WHERE client_id = :workspace_id"),
            {"workspace_id": _COLD_BUILD_WORKSPACE_ID},
        )

    return ensure, cleanup


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    # transaction_per_migration=True commits after each migration instead of wrapping the
    # whole `upgrade` in one transaction. This is required so a migration that adds a
    # Postgres enum value commits before a later migration inserts a row using it
    # (Postgres forbids using a new enum value within the transaction that added it).
    ensure_cold_build_workspace, cleanup_cold_build_workspace = _cold_build_workspace_callbacks(connection)
    # The callback above performs a preflight query, which opens SQLAlchemy's
    # implicit transaction before Alembic can establish per-migration boundaries.
    # Clear that read-only transaction so Alembic can commit the migration.
    connection.rollback()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transaction_per_migration=True,
        include_object=_include_object,
        on_version_apply=(ensure_cold_build_workspace, _restore_cold_build_role_enum),
    )
    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        cleanup_cold_build_workspace()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
