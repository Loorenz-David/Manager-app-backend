from beyo_manager.domain.upholstery.enums import UpholsteryExternalProviderEnum
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.upholstery.list_external_upholsteries import (
    list_external_upholsteries,
)


async def list_nevotex_upholsteries(ctx: ServiceContext) -> dict:
    query_params = dict(ctx.query_params)
    query_params["provider"] = UpholsteryExternalProviderEnum.NEVOTEX
    wrapper_ctx = ServiceContext(
        identity=ctx.identity,
        incoming_data=ctx.incoming_data,
        session=ctx.session,
        query_params=query_params,
    )
    return await list_external_upholsteries(wrapper_ctx)
