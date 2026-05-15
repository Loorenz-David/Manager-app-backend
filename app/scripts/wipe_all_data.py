from __future__ import annotations

import argparse
import asyncio
import re

import asyncpg

from beyo_manager.config import settings


def _to_asyncpg_dsn(database_url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", database_url)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _build_truncate_sql(schema: str, tables: list[str]) -> str:
    qualified = ", ".join(f"{_quote_ident(schema)}.{_quote_ident(t)}" for t in tables)
    return f"TRUNCATE TABLE {qualified} RESTART IDENTITY CASCADE"


async def _list_tables(conn: asyncpg.Connection, *, schema: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        schema,
    )
    return [row["table_name"] for row in rows]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wipe all table data from the configured database (local development helper).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag to execute the wipe.",
    )
    parser.add_argument(
        "--schema",
        default="public",
        help="Database schema to wipe (default: public).",
    )
    parser.add_argument(
        "--include-alembic-version",
        action="store_true",
        help="Also truncate alembic_version table (default: preserved).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tables/SQL without executing TRUNCATE.",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        parser.error("Refusing to wipe data without --yes")

    if settings.environment.lower() == "production":
        raise RuntimeError("Refusing to run wipe script in production environment.")

    dsn = _to_asyncpg_dsn(settings.database_url)
    conn = await asyncpg.connect(dsn)
    try:
        tables = await _list_tables(conn, schema=args.schema)
        if not args.include_alembic_version:
            tables = [t for t in tables if t != "alembic_version"]

        if not tables:
            print("No tables found to wipe.")
            return 0

        truncate_sql = _build_truncate_sql(args.schema, tables)

        print(f"Environment: {settings.environment}")
        print(f"Schema: {args.schema}")
        print(f"Tables to wipe ({len(tables)}): {', '.join(tables)}")
        print(f"SQL: {truncate_sql}")

        if args.dry_run:
            print("Dry run only. No data was deleted.")
            return 0

        await conn.execute(truncate_sql)
        print("Wipe completed successfully.")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
