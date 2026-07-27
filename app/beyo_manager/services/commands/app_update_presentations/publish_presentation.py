import logging
from datetime import datetime, timezone

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.domain.app_update_presentations.presentation_publication import (
    MediaForPublish,
    SlideForPublish,
    validate_publishable,
)
from beyo_manager.domain.app_update_presentations.presentation_states import (
    assert_valid_status_transition,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentations._sequencing import (
    apply_sequence_orders,
)
from beyo_manager.services.commands.app_update_presentations.requests import (
    parse_presentation_ref_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event

logger = logging.getLogger(__name__)


async def publish_presentation(ctx: ServiceContext) -> dict:
    request = parse_presentation_ref_request(ctx.incoming_data)
    pending_events: list = []

    async with maybe_begin(ctx.session):
        presentation = await load_presentation_full(
            ctx.session, ctx.workspace_id, request.client_id
        )
        # Newest-version-wins: multiple published versions may coexist. The
        # active/what's-new resolution serves the newest version each user is
        # eligible for, so publishing a new version does not require archiving
        # the old one.
        assert_valid_status_transition(
            presentation.status, PresentationStatusEnum.PUBLISHED
        )

        active_slides = sorted(
            (s for s in presentation.slides if not s.is_deleted),
            key=lambda s: s.sequence_order,
        )

        # Normalize slide + media sequences to contiguous 1..N during publish.
        slide_order_map = {
            s.client_id: i for i, s in enumerate(active_slides, start=1)
        }
        await apply_sequence_orders(
            ctx.session, {s.client_id: s for s in active_slides}, slide_order_map
        )

        slides_for_publish: list[SlideForPublish] = []
        for slide in active_slides:
            active_media = sorted(
                (m for m in slide.media if not m.is_deleted),
                key=lambda m: m.sequence_order,
            )
            media_order_map = {
                m.client_id: i for i, m in enumerate(active_media, start=1)
            }
            await apply_sequence_orders(
                ctx.session, {m.client_id: m for m in active_media}, media_order_map
            )
            active_element_count = sum(1 for e in slide.elements if not e.is_deleted)
            slides_for_publish.append(
                SlideForPublish(
                    sequence_order=slide_order_map[slide.client_id],
                    title=slide.title,
                    description=slide.description,
                    media=[
                        MediaForPublish(
                            media_type=str(m.media_type.value),
                            storage_key=m.storage_key,
                            sequence_order=media_order_map[m.client_id],
                        )
                        for m in active_media
                    ],
                    element_count=active_element_count,
                )
            )

        app_keys = {t.app_key.value for t in presentation.app_targets}
        role_keys = {t.role_key.value for t in presentation.role_targets}
        user_target_count = len(presentation.user_targets)

        validate_publishable(
            slides=slides_for_publish,
            starts_at=presentation.starts_at,
            expires_at=presentation.expires_at,
            audience_mode=presentation.audience_mode,
            user_target_count=user_target_count,
            app_keys=app_keys,
            role_keys=role_keys,
        )

        presentation.status = PresentationStatusEnum.PUBLISHED
        presentation.published_at = datetime.now(timezone.utc)
        presentation.updated_by_id = ctx.user_id

        pending_events.append(
            build_workspace_event(
                presentation,
                "app_update_presentation:published",
                extra={
                    "logical_client_id": presentation.logical_client_id,
                    "version": presentation.version,
                },
            )
        )

    logger.info(
        "app_update_presentation published | presentation_id=%s logical_client_id=%s "
        "version=%s workspace_id=%s",
        presentation.client_id,
        presentation.logical_client_id,
        presentation.version,
        ctx.workspace_id,
    )
    await event_bus.dispatch(pending_events)

    full = await load_presentation_full(ctx.session, ctx.workspace_id, request.client_id)
    return {"presentation": serialize_presentation_full(full)}
