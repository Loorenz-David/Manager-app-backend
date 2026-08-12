import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.script.revision import RevisionMap
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


def _repair_legacy_revision_graph() -> None:
    """Linearize the historical cycle without rewriting applied revisions.

    The role-specialization revisions were later grafted onto a branch that the
    image/task-note revision already depended on.  That left this cycle in the
    on-disk Alembic graph::

        a3b5 -> 8cf5 -> 6f4d -> 7e1c -> 71df -> 26d4 -> 4f2e -> a3b5

    Existing databases at head do not traverse the graph, but a cold upgrade
    asks Alembic to topologically sort it and loops before the first migration
    can run.  Reparenting 8cf5 to the earlier branch predecessor preserves all
    migration bodies and makes the runtime graph acyclic.  The compatibility
    repair is guarded by the exact historical shape so a later, corrected graph
    is left alone.
    """
    script = getattr(getattr(context, "_proxy", None), "script", None)
    if script is None:
        return

    current_map = script.revision_map._revision_map
    revisions = [revision for revision in current_map.values() if revision is not None]
    by_id = {revision.revision: revision for revision in revisions}
    image_notes = by_id.get("8cf57fa23110")
    role_specialization = by_id.get("a3b5c7d9e1f2")
    role_merge = by_id.get("6f4d2c1b9a7e")
    if (
        image_notes is None
        or role_specialization is None
        or role_merge is None
        or image_notes.down_revision != "a3b5c7d9e1f2"
        or role_specialization.down_revision != "4f2e9a7b6c1d"
        or "8cf57fa23110" not in role_merge.down_revision
    ):
        return

    image_notes.down_revision = "183fb6115bd3"
    for revision in revisions:
        revision.nextrev = frozenset()
        revision._all_nextrev = frozenset()
    script.revision_map = RevisionMap(lambda: iter(revisions))


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


def _ensure_cold_build_workspace(*, ctx, step, **_) -> None:
    """Provide the minimal catalog anchor required by later data migrations."""
    if step.up_revision_id != "a1312183fdfb" or ctx.as_sql:
        return
    ctx.connection.execute(
        text(
            """
            INSERT INTO workspaces (name, time_zone, created_by_id, created_at, client_id)
            SELECT 'Migration workspace', 'UTC', NULL, now(), 'mig_cold_build_workspace'
            WHERE NOT EXISTS (SELECT 1 FROM workspaces)
            """
        )
    )


def run_migrations_offline() -> None:
    _repair_legacy_revision_graph()
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
    _repair_legacy_revision_graph()
    # transaction_per_migration=True commits after each migration instead of wrapping the
    # whole `upgrade` in one transaction. This is required so a migration that adds a
    # Postgres enum value commits before a later migration inserts a row using it
    # (Postgres forbids using a new enum value within the transaction that added it).
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transaction_per_migration=True,
        include_object=_include_object,
        on_version_apply=(_ensure_cold_build_workspace, _restore_cold_build_role_enum),
    )
    with context.begin_transaction():
        context.run_migrations()


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
