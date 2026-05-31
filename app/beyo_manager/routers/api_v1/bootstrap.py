"""Bootstrap endpoint.

Example curl:
curl -X POST 'http://localhost:8000/api/v1/bootstrap' \
    -H 'X-Bootstrap-Secret: local-bootstrap-secret-dev'

Wipe DB data (testing/dev only):
curl -X DELETE 'http://localhost:8000/api/v1/bootstrap/wipe-db' \
    -H 'X-Bootstrap-Secret: local-bootstrap-secret-dev'
"""

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from beyo_manager.models.database import get_db_session
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.services.commands.bootstrap.bootstrap_app import bootstrap_app
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.config import settings

router = APIRouter()


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _build_truncate_sql(schema: str, tables: list[str]) -> str:
    qualified = ", ".join(f"{_quote_ident(schema)}.{_quote_ident(table)}" for table in tables)
    return f"TRUNCATE TABLE {qualified} RESTART IDENTITY CASCADE"


def _validate_bootstrap_secret(x_bootstrap_secret: str | None) -> None:
    if not settings.bootstrap_secret or not x_bootstrap_secret or x_bootstrap_secret != settings.bootstrap_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing bootstrap secret.")


@router.post("")
async def bootstrap_route(
    x_bootstrap_secret: str | None = Header(default=None, alias="X-Bootstrap-Secret"),
):
    _validate_bootstrap_secret(x_bootstrap_secret)

    session_iter = get_db_session()
    session = await anext(session_iter)
    try:
        ctx = ServiceContext(identity={}, incoming_data={}, session=session)
        outcome = await run_service(bootstrap_app, ctx)
        if not outcome.success:
            return build_err(outcome.error)
        return build_ok(outcome.data, warnings=[])
    finally:
        await session_iter.aclose()


@router.delete("/wipe-db")
async def wipe_db_route(
    x_bootstrap_secret: str | None = Header(default=None, alias="X-Bootstrap-Secret"),
):
    _validate_bootstrap_secret(x_bootstrap_secret)

    if settings.environment.lower() == "production":
        raise HTTPException(status_code=403, detail="Wipe DB endpoint is disabled in production.")

    session_iter = get_db_session()
    session = await anext(session_iter)
    try:
        rows = await session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            ),
            {"schema": "public"},
        )
        tables = [row[0] for row in rows]
        tables = [table for table in tables if table != "alembic_version"]

        if not tables:
            return build_ok({"wiped": False, "tables_count": 0, "message": "No tables found to wipe."}, warnings=[])

        truncate_sql = _build_truncate_sql("public", tables)
        await session.execute(text(truncate_sql))
        await session.commit()

        return build_ok(
            {
                "wiped": True,
                "schema": "public",
                "tables_count": len(tables),
                "excluded_tables": ["alembic_version"],
            },
            warnings=[],
        )
    finally:
        await session_iter.aclose()
