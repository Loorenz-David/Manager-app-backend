import logging

from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_full,
)
from beyo_manager.domain.files.enums import PendingUploadStatusEnum
from beyo_manager.errors.base import DomainError
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

logger = logging.getLogger(__name__)

# ── TEMPORARY DIAGNOSTICS ─────────────────────────────────────────────────
# Step-by-step tracing added to pin down a production failure in this flow.
# Remove once the failing operation is identified. Only non-sensitive
# identifiers and object metadata are emitted here — never credentials,
# authorization headers, presigned URLs, tokens or user content.
_DIAG = "add_slide_media"

_PAYLOAD_LOG_KEYS = (
    "presentation_id",
    "slide_id",
    "media_type",
    "pending_upload_client_id",
    "storage_key",
    "poster_storage_key",
    "fallback_storage_key",
    "mime_type",
    "width",
    "height",
    "duration_ms",
    "is_looping",
)


def _sanitized_payload(data: dict) -> dict:
    """Whitelisted view of the incoming payload; free-text fields are reduced to flags."""
    if not isinstance(data, dict):
        return {"payload_type": type(data).__name__}
    safe = {key: data[key] for key in _PAYLOAD_LOG_KEYS if data.get(key) is not None}
    safe["has_alt_text"] = bool(data.get("alt_text"))
    safe["unexpected_keys"] = sorted(
        set(data) - set(_PAYLOAD_LOG_KEYS) - {"alt_text"}
    )
    return safe


def _diag(event: str, message: str, *args) -> None:
    logger.info(
        f"{_DIAG}: {message}",
        *args,
        extra={"event_type": f"{_DIAG}.{event}", "service": _DIAG},
    )


async def _resolve_pending_upload(ctx: ServiceContext, pending_upload_client_id: str):
    result = await ctx.session.execute(
        select(PendingUpload).where(
            PendingUpload.client_id == pending_upload_client_id,
            PendingUpload.workspace_id == ctx.workspace_id,
        )
    )
    upload = result.scalar_one_or_none()
    if upload is None:
        _diag(
            "pending_upload.missing",
            "pending upload lookup returned no row | pending_upload_client_id=%s workspace_id=%s",
            pending_upload_client_id,
            ctx.workspace_id,
        )
        raise NotFound("Pending upload not found.")
    _diag(
        "pending_upload.resolved",
        "pending upload resolved | pending_upload_client_id=%s status=%s "
        "content_type=%s size_bytes=%s storage_key=%s",
        pending_upload_client_id,
        getattr(upload.status, "value", upload.status),
        upload.content_type,
        upload.size_bytes,
        upload.storage_key,
    )
    return upload


async def add_slide_media(ctx: ServiceContext) -> dict:
    _diag(
        "request.received",
        "service entered | workspace_id=%s user_id=%s role=%s payload=%s",
        ctx.workspace_id,
        ctx.user_id,
        ctx.role_name,
        _sanitized_payload(ctx.incoming_data),
    )

    request = parse_add_slide_media_request(ctx.incoming_data)
    _diag(
        "request.parsed",
        "payload validated | presentation_id=%s slide_id=%s media_type=%s "
        "pending_upload_client_id=%s storage_key=%s mime_type=%s "
        "width=%s height=%s duration_ms=%s",
        request.presentation_id,
        request.slide_id,
        getattr(request.media_type, "value", request.media_type),
        request.pending_upload_client_id,
        request.storage_key,
        request.mime_type,
        request.width,
        request.height,
        request.duration_ms,
    )

    owns_transaction = not ctx.session.in_transaction()
    _diag(
        "tx.enter",
        "entering transaction block | owner=%s presentation_id=%s slide_id=%s",
        owns_transaction,
        request.presentation_id,
        request.slide_id,
    )

    try:
        async with maybe_begin(ctx.session):
            await load_presentation_for_write(
                ctx.session, ctx.workspace_id, request.presentation_id
            )
            _diag(
                "db.presentation_loaded",
                "presentation loaded for write | presentation_id=%s workspace_id=%s",
                request.presentation_id,
                ctx.workspace_id,
            )

            await load_slide_for_write(
                ctx.session, request.presentation_id, request.slide_id
            )
            _diag(
                "db.slide_loaded",
                "slide loaded for write | presentation_id=%s slide_id=%s",
                request.presentation_id,
                request.slide_id,
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
                _diag(
                    "storage.key_missing",
                    "no storage key resolved | presentation_id=%s slide_id=%s",
                    request.presentation_id,
                    request.slide_id,
                )
                raise ValidationError(
                    "Either pending_upload_client_id or storage_key is required."
                )

            _diag(
                "storage.head_object.start",
                "verifying object in storage | storage_key=%s mime_type=%s",
                storage_key,
                mime_type,
            )
            # Verify the object actually landed in storage before recording it.
            try:
                head = get_storage_client().head_object(storage_key)
            except Exception as exc:
                logger.exception(
                    "%s: head_object raised | storage_key=%s exc_type=%s exc_message=%s",
                    _DIAG,
                    storage_key,
                    type(exc).__name__,
                    exc,
                    extra={
                        "event_type": f"{_DIAG}.storage.head_object.error",
                        "service": _DIAG,
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
                raise
            _diag(
                "storage.head_object.done",
                "head_object result | storage_key=%s found=%s content_length=%s content_type=%s",
                storage_key,
                head is not None,
                (head or {}).get("content_length"),
                (head or {}).get("content_type"),
            )
            if head is None:
                raise ValidationError("Uploaded object was not found in storage.")

            if upload is not None:
                upload.status = PendingUploadStatusEnum.CONFIRMED
                _diag(
                    "db.pending_upload_confirmed",
                    "pending upload marked confirmed | pending_upload_client_id=%s",
                    request.pending_upload_client_id,
                )

            sequence_order = await next_media_sequence_order(
                ctx.session, request.slide_id
            )
            _diag(
                "db.sequence_order",
                "next media sequence order resolved | slide_id=%s sequence_order=%s",
                request.slide_id,
                sequence_order,
            )

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
            _diag(
                "db.insert.flush.start",
                "flushing slide media insert | slide_id=%s sequence_order=%s "
                "storage_key=%s mime_type=%s width=%s height=%s duration_ms=%s",
                request.slide_id,
                sequence_order,
                storage_key,
                mime_type,
                request.width,
                request.height,
                request.duration_ms,
            )
            await ctx.session.flush()
            _diag(
                "db.insert.flush.done",
                "slide media insert flushed | slide_id=%s media_client_id=%s",
                request.slide_id,
                getattr(media, "client_id", None),
            )
    except Exception as exc:
        # Not a handler — the exception is re-raised untouched. This only marks
        # where the transaction block unwound (rollback happens here when this
        # call owns the transaction). Domain rejections are expected control
        # flow, so they stay at INFO without a traceback; anything else is the
        # failure we are hunting and gets the full stack.
        is_domain = isinstance(exc, DomainError)
        logger.log(
            logging.INFO if is_domain else logging.ERROR,
            "%s: transaction block aborted | domain_error=%s owner=%s rolled_back=%s "
            "presentation_id=%s slide_id=%s exc_type=%s exc_message=%s",
            _DIAG,
            is_domain,
            owns_transaction,
            owns_transaction,
            request.presentation_id,
            request.slide_id,
            type(exc).__name__,
            exc,
            exc_info=not is_domain,
            extra={
                "event_type": f"{_DIAG}.tx.aborted",
                "service": _DIAG,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise

    _diag(
        "tx.exit",
        "transaction block exited cleanly | owner=%s committed=%s "
        "presentation_id=%s slide_id=%s",
        owns_transaction,
        owns_transaction,
        request.presentation_id,
        request.slide_id,
    )

    full = await load_presentation_full(
        ctx.session, ctx.workspace_id, request.presentation_id
    )
    _diag(
        "response.serialize",
        "presentation reloaded for response | presentation_id=%s slide_count=%s",
        request.presentation_id,
        len(full.slides or []),
    )
    return {"presentation": serialize_presentation_full(full)}
