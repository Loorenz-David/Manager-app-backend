from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.history.list_history_records import list_history_records
from beyo_manager.services.run_service import run_service

router = APIRouter()


async def _run(query, data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(
        query,
        ServiceContext(identity=claims, incoming_data=data, session=session),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.get("")
async def list_history_records_route(
    entity_type: str,
    entity_client_id: str,
    change_type: str | None = None,
    field_name: str | None = None,
    offset: int = 0,
    limit: int = 50,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_history_records,
        {
            "entity_type": entity_type,
            "entity_client_id": entity_client_id,
            "change_type": change_type,
            "field_name": field_name,
            "offset": offset,
            "limit": limit,
        },
        claims,
        session,
    )
