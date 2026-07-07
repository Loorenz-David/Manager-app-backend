from __future__ import annotations

import logging

from beyo_manager.domain.execution.payloads.location_tracker_push import LocationTrackerPushPayload
from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.location_tracker import get_location_tracker_client

logger = logging.getLogger(__name__)


async def handle_push_item_locations(raw: dict, task_client_id: str) -> None:
    payload = LocationTrackerPushPayload(**raw)
    client = get_location_tracker_client()
    logger.info(
        "location_tracker_push_locations | start | task_id=%s changes=%d",
        task_client_id,
        len(payload.changes),
    )
    try:
        await client.patch_item_locations(payload.changes)
    except ExternalServiceError:
        logger.warning("location_tracker_push_locations | failed | task_id=%s", task_client_id)
        raise
    except Exception:
        logger.exception("location_tracker_push_locations | unexpected failure | task_id=%s", task_client_id)
        raise

    logger.info("location_tracker_push_locations | completed | task_id=%s", task_client_id)
