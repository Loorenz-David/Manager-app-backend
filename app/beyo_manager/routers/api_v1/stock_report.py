from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from beyo_manager.services.commands.stock_report.repair_stock_report import (
    repair_stock_report,
)
from beyo_manager.services.queries.stock_report.get_stock_report_consistency import (
    get_stock_report_consistency,
)

router = APIRouter()


async def _run(service, claims: dict, session: AsyncSession):
    outcome = await run_service(
        service, ServiceContext(identity=claims, incoming_data={}, session=session)
    )
    return build_err(outcome.error) if not outcome.success else build_ok(outcome.data)


@router.get("/consistency")
async def route_get_stock_report_consistency(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_stock_report_consistency, claims, session)


@router.post("/repair")
async def route_repair_stock_report(
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(repair_stock_report, claims, session)
