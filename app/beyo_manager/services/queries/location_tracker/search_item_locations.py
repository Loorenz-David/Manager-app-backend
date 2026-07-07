from dataclasses import asdict

from beyo_manager.services.commands.location_tracker.requests import (
    parse_search_item_locations_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.location_tracker import get_location_tracker_client
from beyo_manager.services.infra.location_tracker.mapper import map_location_items


async def search_item_locations(ctx: ServiceContext) -> list[dict]:
    request = parse_search_item_locations_request(ctx.query_params)
    client = get_location_tracker_client()
    raw_items = await client.get_item_locations(request.q, request.item_identity)
    return [asdict(item) for item in map_location_items(raw_items)]
