from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products
from beyo_manager.services.infra.nevotex.normalizer import normalize_nevotex_candidates

_MAX_LIMIT = 20
_DEFAULT_LIMIT = 7


async def list_nevotex_upholsteries(ctx: ServiceContext) -> dict:
    q = str(ctx.query_params.get("q", "")).strip()
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)

    raw_products = await fetch_nevotex_raw_products(q=q, limit=limit)
    candidates = normalize_nevotex_candidates(raw_products)

    return {
        "upholsteries": candidates,
        "upholsteries_pagination": {
            "has_more": False,
            "limit": limit,
            "offset": 0,
        },
    }
