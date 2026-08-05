from __future__ import annotations

import logging
from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.location_tracker_push import LocationTrackerPushPayload
from beyo_manager.domain.items.location_push import normalize_zone
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.location_tracker._resolve_needs_fixing import (
    resolve_item_needs_fixing,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task

logger = logging.getLogger(__name__)


async def enqueue_item_zone_location_push(
    session,
    item: Item,
    *,
    username: str | None,
    requested_by_user_id: str | None,
    needs_fixing: bool | None = None,
) -> bool:
    """Queue one outbound zone push for item.

    needs_fixing left as None is resolved from the item's live task links. Callers holding the
    task type pass the flag explicitly — create_task must, since it enqueues before its
    TaskItem row exists and a lookup would come back empty.
    """
    zone = normalize_zone(item.item_zone)
    if not zone:
        return False

    target = {
        key: value
        for key, value in {
            "article_number": item.article_number,
            "sku": item.sku,
        }.items()
        if value
    }
    if not target:
        logger.info(
            "location_tracker_item_zone_push | skipped | item_id=%s reason=no_target_identifiers",
            item.client_id,
        )
        return False

    if needs_fixing is None:
        needs_fixing = await resolve_item_needs_fixing(session, item.client_id)

    await create_instant_task(
        session=session,
        task_type=TaskType.LOCATION_TRACKER_PUSH_LOCATIONS,
        payload=asdict(
            LocationTrackerPushPayload(
                changes=[
                    {
                        "position": zone,
                        "item_targets": [target],
                        "username": username or None,
                        "needs_fixing": needs_fixing,
                    }
                ],
                requested_by_user_id=requested_by_user_id,
            )
        ),
        max_try=3,
    )
    return True
