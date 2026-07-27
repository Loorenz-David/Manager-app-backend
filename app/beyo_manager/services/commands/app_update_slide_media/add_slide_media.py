from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)
from beyo_manager.models.tables.files.pending_upload import PendingUpload
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_for_write,
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_slide_media.requests import (
    parse_add_slide_media_request,
)
from beyo_manager.services.commands.app_update_slides._slide_loading import (
    load_slide_for_write,
    next_media_sequence_order,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.storage import get_storage_client


async def _resolve_pending_upload(ctx: ServiceContext, pending_upload_client_id: str):
    result = await ctx.session.execute(
        select(PendingUpload).where(
            PendingUpload.client_id == pending_upload_client_id,
            PendingUpload.workspace_id == ctx.workspace_id,
        )
    )
    upload = result.scalar_one_or_none()
    if upload is None:
        raise NotFound("Pending upload not found.")
    return upload


async def add_slide_media(ctx: ServiceContext) -> dict:
    request = parse_add_slide_media_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        await load_presentation_for_write(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        await load_slide_for_write(
            ctx.session, request.presentation_id, request.slide_id
        )

        storage_key = request.storage_key
        mime_type = request.mime_type
        upload = None
        if request.pending_upload_client_id:
            upload = await _resolve_pending_upload(
                ctx, request.pending_upload_client_id
            )
            storage_key = upload.storage_key
            mime_type = mime_type or upload.content_type

        if not storage_key:
            raise ValidationError(
                "Either pending_upload_client_id or storage_key is required."
            )

        # Verify the object actually landed in storage before recording it.
        if get_storage_client().head_object(storage_key) is None:
            raise ValidationError("Uploaded object was not found in storage.")

        if upload is not None:
            upload.status = PendingUploadStatusEnum.CONFIRMED

        sequence_order = await next_media_sequence_order(ctx.session, request.slide_id)
        media = AppUpdateSlideMedia(
            slide_id=request.slide_id,
            sequence_order=sequence_order,
            media_type=request.media_type,
            storage_key=storage_key,
            poster_storage_key=request.poster_storage_key,
            fallback_storage_key=request.fallback_storage_key,
            alt_text=request.alt_text,
            mime_type=mime_type,
            width=request.width,
            height=request.height,
            duration_ms=request.duration_ms,
            is_looping=request.is_looping if request.is_looping is not None else False,
        )
        ctx.session.add(media)
        await ctx.session.flush()

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    return {"presentation": serialize_presentation_full(full)}
