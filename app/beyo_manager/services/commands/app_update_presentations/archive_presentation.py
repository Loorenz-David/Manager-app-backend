import logging
from datetime import datetime, timezone

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.domain.app_update_presentations.presentation_states import (
    assert_valid_status_transition,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations.requests import (
    parse_presentation_ref_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event

logger = logging.getLogger(__name__)


async def archive_presentation(ctx: ServiceContext) -> dict:
    request = parse_presentation_ref_request(ctx.incoming_data)
    pending_events: list = []

    async with maybe_begin(ctx.session):
        # Archiving is allowed from draft or published — do not require draft.
        presentation = await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.client_id, require_draft=False
        )
        assert_valid_status_transition(
            presentation.status, PresentationStatusEnum.ARCHIVED
        )
        presentation.status = PresentationStatusEnum.ARCHIVED
        presentation.archived_at = datetime.now(timezone.utc)
        presentation.updated_by_id = ctx.user_id

        pending_events.append(
            build_workspace_event(
                presentation,
                "app_update_presentation:archived",
                extra={
                    "logical_client_id": presentation.logical_client_id,
                    "version": presentation.version,
                },
            )
        )

    logger.info(
        "app_update_presentation archived | presentation_id=%s workspace_id=%s",
        request.client_id,
        ctx.workspace_id,
    )
    await event_bus.dispatch(pending_events)

    full = await load_presentation_full(ctx.session, ctx.workspace_id, request.client_id)
    return {"presentation": serialize_presentation_full(full)}
