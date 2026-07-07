from __future__ import annotations

from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.location_tracker_push import LocationTrackerPushPayload
from beyo_manager.services.commands.location_tracker.requests import (
    parse_push_item_locations_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.location_tracker.models import (
    ItemLocationTarget,
    ItemPositionChange,
)


async def push_item_locations(ctx: ServiceContext) -> dict:
    request = parse_push_item_locations_request(ctx.incoming_data)
    default_username = ctx.identity.get("username")
    changes: list[dict] = []

    for entry in request.entries:
        change = ItemPositionChange(
            position=entry.position,
            item_targets=[
                ItemLocationTarget(
                    article_number=target.article_number,
                    sku=target.sku,
                )
                for target in entry.item_targets
            ],
            username=entry.username or default_username or None,
        )
        changes.append(asdict(change))

    async with maybe_begin(ctx.session):
        task = await create_instant_task(
            session=ctx.session,
            task_type=TaskType.LOCATION_TRACKER_PUSH_LOCATIONS,
            payload=asdict(
                LocationTrackerPushPayload(
                    changes=changes,
                    requested_by_user_id=ctx.user_id or None,
                )
            ),
            max_try=3,
        )

    return {
        "enqueued": True,
        "task_client_id": task.client_id,
        "queued_count": len(changes),
    }
