from __future__ import annotations

import logging
from dataclasses import asdict

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.location_tracker_push import LocationTrackerPushPayload
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.infra.execution.task_factory import create_instant_task

logger = logging.getLogger(__name__)


async def enqueue_item_zone_location_push(
    session,
    item: Item,
    *,
    username: str | None,
    requested_by_user_id: str | None,
) -> bool:
    zone = (item.item_zone or "").strip()
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
                    }
                ],
                requested_by_user_id=requested_by_user_id,
            )
        ),
        max_try=3,
    )
    return True
