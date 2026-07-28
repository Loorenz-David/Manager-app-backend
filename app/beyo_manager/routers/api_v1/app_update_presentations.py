import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.app_update_presentations.enums import (
    AppKeyEnum,
    AudienceModeEnum,
    PresentationCategoryEnum,
    PresentationTypeEnum,
    SlideLayoutEnum,
    SlideMediaTypeEnum,
    SlidePlaybackModeEnum,
)
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.app_update_presentation_audience.replace_audience import (
    replace_audience,
)
from beyo_manager.services.commands.app_update_presentation_views.record_presentation_view import (
    record_presentation_view,
)
from beyo_manager.services.commands.app_update_presentations.archive_presentation import (
    archive_presentation,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation import (
    create_presentation,
)
from beyo_manager.services.commands.app_update_presentations.create_presentation_version import (
    create_presentation_version,
)
from beyo_manager.services.commands.app_update_presentations.publish_presentation import (
    publish_presentation,
)
from beyo_manager.services.commands.app_update_presentations.update_presentation import (
    update_presentation,
)
from beyo_manager.services.commands.app_update_slide_media.add_slide_media import (
    add_slide_media,
)
from beyo_manager.services.commands.app_update_slide_media.delete_slide_media import (
    delete_slide_media,
)
from beyo_manager.services.commands.app_update_slide_media.generate_media_upload_url import (
    generate_media_upload_url,
)
from beyo_manager.services.commands.app_update_slide_media.reorder_slide_media import (
    reorder_slide_media,
)
from beyo_manager.services.commands.app_update_slide_media.update_slide_media import (
    update_slide_media,
)
from beyo_manager.services.commands.app_update_slide_composition.replace_slide_composition import (
    replace_slide_composition,
)
from beyo_manager.services.commands.app_update_slides.create_slide import create_slide
from beyo_manager.services.commands.app_update_slides.delete_slide import delete_slide
from beyo_manager.services.commands.app_update_slides.reorder_slides import reorder_slides
from beyo_manager.services.commands.app_update_slides.update_slide import update_slide
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations.get_active_presentation import (
    get_active_presentation,
)
from beyo_manager.services.queries.app_update_presentations.get_presentation import (
    get_presentation,
)
from beyo_manager.services.queries.app_update_presentations.get_presentation_preview import (
    get_presentation_preview,
)
from beyo_manager.services.queries.app_update_presentations.list_presentations import (
    list_presentations,
)
from beyo_manager.services.queries.app_update_presentations.list_whats_new import (
    list_whats_new,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()

logger = logging.getLogger(__name__)

_ADMIN_ROLES = [ADMIN, MANAGER]
_CONSUMER_ROLES = [ADMIN, MANAGER, WORKER, SELLER]


# ── Request bodies ────────────────────────────────────────────────────────
class CreatePresentationBody(BaseModel):
    client_id: str | None = None
    title: str
    summary: str | None = None
    presentation_type: PresentationTypeEnum | None = None
    category: PresentationCategoryEnum | None = None
    audience_mode: AudienceModeEnum | None = None
    display_priority: int | None = None
    is_dismissible: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class UpdatePresentationBody(BaseModel):
    title: str | None = None
    summary: str | None = None
    presentation_type: PresentationTypeEnum | None = None
    category: PresentationCategoryEnum | None = None
    audience_mode: AudienceModeEnum | None = None
    display_priority: int | None = None
    is_dismissible: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class SlideBody(BaseModel):
    title: str | None = None
    description: str | None = None
    layout_type: SlideLayoutEnum | None = None
    action_label: str | None = None
    action_route: str | None = None
    playback_mode: SlidePlaybackModeEnum | None = None
    duration_ms: int | None = None
    composition_schema_version: int | None = None
    background_color: str | None = None


class CompositionElementBody(BaseModel):
    element_type: str
    layer_index: int = 0
    start_ms: int = 0
    end_ms: int | None = None
    media_id: str | None = None
    text_content: str | None = None
    layout: dict | None = None
    style: dict | None = None
    enter_animation: dict | None = None
    exit_animation: dict | None = None


class SlideCompositionBody(BaseModel):
    playback_mode: SlidePlaybackModeEnum
    duration_ms: int | None = None
    composition_schema_version: int | None = None
    background_color: str | None = None
    elements: list[CompositionElementBody] = []


class ReorderSlidesBody(BaseModel):
    ordered_slide_ids: list[str]


class MediaUploadUrlBody(BaseModel):
    media_type: SlideMediaTypeEnum
    content_type: str
    file_name: str = ""
    file_size_bytes: int | None = None


class AddMediaBody(BaseModel):
    media_type: SlideMediaTypeEnum
    pending_upload_client_id: str | None = None
    storage_key: str | None = None
    poster_storage_key: str | None = None
    fallback_storage_key: str | None = None
    alt_text: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    is_looping: bool | None = None


class UpdateMediaBody(BaseModel):
    poster_storage_key: str | None = None
    fallback_storage_key: str | None = None
    alt_text: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    is_looping: bool | None = None


class ReorderMediaBody(BaseModel):
    ordered_media_ids: list[str]


class AudienceBody(BaseModel):
    audience_mode: AudienceModeEnum
    app_keys: list[AppKeyEnum] = []
    role_keys: list[RoleNameEnum] = []
    workspace_ids: list[str] = []
    user_ids: list[str] = []


class ViewStateBody(BaseModel):
    version: int
    action: str
    last_slide_index: int | None = None


def _ctx(claims, session, incoming=None, query_params=None) -> ServiceContext:
    return ServiceContext(
        incoming_data=incoming or {},
        query_params=query_params or {},
        identity=claims,
        session=session,
    )


async def _run(fn, ctx):
    outcome = await run_service(fn, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Static / collection routes (declared before wildcard /{id}) ───────────
@router.get("/active")
async def get_active_presentation_route(
    app_key: str = Query(..., max_length=64),
    claims: dict = Depends(require_roles(_CONSUMER_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        get_active_presentation, _ctx(claims, session, query_params={"app_key": app_key})
    )


@router.get("/history")
async def list_whats_new_route(
    app_key: str = Query(..., max_length=64),
    claims: dict = Depends(require_roles(_CONSUMER_ROLES)),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    query_params = {"app_key": app_key, "limit": limit, "offset": offset}
    return await _run(list_whats_new, _ctx(claims, session, query_params=query_params))


@router.put("")
async def create_presentation_route(
    body: CreatePresentationBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        create_presentation, _ctx(claims, session, incoming=body.model_dump(exclude_unset=True))
    )


@router.get("")
async def list_presentations_route(
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    logical_client_id: str | None = Query(None),
    version: int | None = Query(None),
    app_key: str | None = Query(None),
    role_key: str | None = Query(None),
    published_before: str | None = Query(None),
    published_after: str | None = Query(None),
):
    query_params = {
        "limit": limit,
        "offset": offset,
        "q": q,
        "status": status,
        "logical_client_id": logical_client_id,
        "version": version,
        "app_key": app_key,
        "role_key": role_key,
        "published_before": published_before,
        "published_after": published_after,
    }
    return await _run(list_presentations, _ctx(claims, session, query_params=query_params))


# ── Wildcard resource routes ──────────────────────────────────────────────
@router.get("/{presentation_client_id}/preview")
async def preview_presentation_route(
    presentation_client_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        get_presentation_preview,
        _ctx(claims, session, incoming={"client_id": presentation_client_id}),
    )


@router.get("/{presentation_client_id}")
async def get_presentation_route(
    presentation_client_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        get_presentation, _ctx(claims, session, incoming={"client_id": presentation_client_id})
    )


@router.patch("/{presentation_client_id}")
async def update_presentation_route(
    presentation_client_id: str,
    body: UpdatePresentationBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"client_id": presentation_client_id, **body.model_dump(exclude_unset=True)}
    return await _run(update_presentation, _ctx(claims, session, incoming=incoming))


@router.post("/{presentation_client_id}/publish")
async def publish_presentation_route(
    presentation_client_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        publish_presentation, _ctx(claims, session, incoming={"client_id": presentation_client_id})
    )


@router.post("/{presentation_client_id}/archive")
async def archive_presentation_route(
    presentation_client_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        archive_presentation, _ctx(claims, session, incoming={"client_id": presentation_client_id})
    )


@router.post("/{presentation_client_id}/new-version")
async def create_presentation_version_route(
    presentation_client_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        create_presentation_version,
        _ctx(claims, session, incoming={"client_id": presentation_client_id}),
    )


@router.post("/{presentation_client_id}/view-state")
async def record_presentation_view_route(
    presentation_client_id: str,
    body: ViewStateBody,
    claims: dict = Depends(require_roles(_CONSUMER_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"presentation_id": presentation_client_id, **body.model_dump(exclude_unset=True)}
    return await _run(record_presentation_view, _ctx(claims, session, incoming=incoming))


@router.put("/{presentation_client_id}/audience")
async def replace_audience_route(
    presentation_client_id: str,
    body: AudienceBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"presentation_id": presentation_client_id, **body.model_dump()}
    return await _run(replace_audience, _ctx(claims, session, incoming=incoming))


# ── Slides (static /slides/reorder before wildcard /slides/{slide_id}) ─────
@router.post("/{presentation_client_id}/slides/reorder")
async def reorder_slides_route(
    presentation_client_id: str,
    body: ReorderSlidesBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"presentation_id": presentation_client_id, **body.model_dump()}
    return await _run(reorder_slides, _ctx(claims, session, incoming=incoming))


@router.post("/{presentation_client_id}/slides")
async def create_slide_route(
    presentation_client_id: str,
    body: SlideBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"presentation_id": presentation_client_id, **body.model_dump(exclude_unset=True)}
    return await _run(create_slide, _ctx(claims, session, incoming=incoming))


@router.patch("/{presentation_client_id}/slides/{slide_id}")
async def update_slide_route(
    presentation_client_id: str,
    slide_id: str,
    body: SlideBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        **body.model_dump(exclude_unset=True),
    }
    return await _run(update_slide, _ctx(claims, session, incoming=incoming))


@router.delete("/{presentation_client_id}/slides/{slide_id}")
async def delete_slide_route(
    presentation_client_id: str,
    slide_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {"presentation_id": presentation_client_id, "slide_id": slide_id}
    return await _run(delete_slide, _ctx(claims, session, incoming=incoming))


@router.put("/{presentation_client_id}/slides/{slide_id}/composition")
async def replace_slide_composition_route(
    presentation_client_id: str,
    slide_id: str,
    body: SlideCompositionBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        **body.model_dump(),
    }
    return await _run(replace_slide_composition, _ctx(claims, session, incoming=incoming))


# ── Slide media ───────────────────────────────────────────────────────────
@router.post("/{presentation_client_id}/slides/{slide_id}/media/upload-url")
async def generate_media_upload_url_route(
    presentation_client_id: str,
    slide_id: str,
    body: MediaUploadUrlBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        **body.model_dump(exclude_unset=True),
    }
    return await _run(generate_media_upload_url, _ctx(claims, session, incoming=incoming))


@router.post("/{presentation_client_id}/slides/{slide_id}/media/reorder")
async def reorder_slide_media_route(
    presentation_client_id: str,
    slide_id: str,
    body: ReorderMediaBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        **body.model_dump(),
    }
    return await _run(reorder_slide_media, _ctx(claims, session, incoming=incoming))


@router.post("/{presentation_client_id}/slides/{slide_id}/media")
async def add_slide_media_route(
    presentation_client_id: str,
    slide_id: str,
    body: AddMediaBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        **body.model_dump(exclude_unset=True),
    }
    # TEMPORARY DIAGNOSTICS — remove with the tracing in add_slide_media.
    # Identifiers and media metadata only; no auth claims beyond the actor ids.
    logger.info(
        "add_slide_media route | presentation_id=%s slide_id=%s workspace_id=%s "
        "user_id=%s media_type=%s has_pending_upload=%s has_storage_key=%s "
        "mime_type=%s width=%s height=%s duration_ms=%s body_fields=%s",
        presentation_client_id,
        slide_id,
        claims.get("workspace_id"),
        claims.get("user_id"),
        getattr(body.media_type, "value", body.media_type),
        body.pending_upload_client_id is not None,
        body.storage_key is not None,
        body.mime_type,
        body.width,
        body.height,
        body.duration_ms,
        sorted(body.model_dump(exclude_unset=True).keys()),
        extra={
            "event_type": "add_slide_media.route",
            "service": "add_slide_media",
            "path": "/{presentation_client_id}/slides/{slide_id}/media",
            "method": "POST",
        },
    )
    return await _run(add_slide_media, _ctx(claims, session, incoming=incoming))


@router.patch("/{presentation_client_id}/slides/{slide_id}/media/{media_id}")
async def update_slide_media_route(
    presentation_client_id: str,
    slide_id: str,
    media_id: str,
    body: UpdateMediaBody,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        "media_id": media_id,
        **body.model_dump(exclude_unset=True),
    }
    return await _run(update_slide_media, _ctx(claims, session, incoming=incoming))


@router.delete("/{presentation_client_id}/slides/{slide_id}/media/{media_id}")
async def delete_slide_media_route(
    presentation_client_id: str,
    slide_id: str,
    media_id: str,
    claims: dict = Depends(require_roles(_ADMIN_ROLES)),
    session: AsyncSession = Depends(get_db),
):
    incoming = {
        "presentation_id": presentation_client_id,
        "slide_id": slide_id,
        "media_id": media_id,
    }
    return await _run(delete_slide_media, _ctx(claims, session, incoming=incoming))
