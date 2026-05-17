from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.commands.users.requests.record_view_events_request import (
    parse_record_view_events_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.presence.presence import mark_left, mark_viewing
from beyo_manager.services.infra.presence.user_view_key import (
    clear_user_view_if_matches,
    set_user_view,
)


async def record_view_events(ctx: ServiceContext) -> dict:
    request = parse_record_view_events_request(ctx.incoming_data)

    for item in request.records:
        entity_type = item.entity_type.value
        if item.ended_at is None:
            mark_viewing(entity_type, item.entity_client_id, ctx.user_id)
            await set_user_view(ctx.user_id, entity_type, item.entity_client_id)
        else:
            mark_left(entity_type, item.entity_client_id, ctx.user_id)
            await clear_user_view_if_matches(ctx.user_id, entity_type, item.entity_client_id)

    async with ctx.session.begin():
        for item in request.records:
            entity_type = item.entity_type.value
            start_payload = {
                "user_id": ctx.user_id,
                "entity_type": entity_type,
                "entity_client_id": item.entity_client_id,
                "started_at": item.started_at.isoformat(),
            }
            await create_instant_task(ctx.session, TaskType.RECORD_VIEW_START, start_payload)

            if item.ended_at is not None:
                end_payload = {
                    "user_id": ctx.user_id,
                    "entity_type": entity_type,
                    "entity_client_id": item.entity_client_id,
                    "ended_at": item.ended_at.isoformat(),
                }
                await create_instant_task(ctx.session, TaskType.RECORD_VIEW_END, end_payload)

    return {}
