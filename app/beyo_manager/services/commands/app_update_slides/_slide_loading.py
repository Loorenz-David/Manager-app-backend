"""Workspace/presentation-scoped slide + media loaders. Helpers, not commands."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)


async def load_slide_for_write(
    session: AsyncSession,
    presentation_id: str,
    slide_id: str,
) -> AppUpdatePresentationSlide:
    result = await session.execute(
        select(AppUpdatePresentationSlide).where(
            AppUpdatePresentationSlide.client_id == slide_id,
            AppUpdatePresentationSlide.presentation_id == presentation_id,
            AppUpdatePresentationSlide.is_deleted.is_(False),
        )
    )
    slide = result.scalar_one_or_none()
    if slide is None:
        raise NotFound("Slide not found.")
    return slide


async def next_slide_sequence_order(session: AsyncSession, presentation_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(AppUpdatePresentationSlide.sequence_order), 0) + 1).where(
            AppUpdatePresentationSlide.presentation_id == presentation_id,
            AppUpdatePresentationSlide.is_deleted.is_(False),
        )
    )
    return int(result.scalar_one())


async def load_media_for_write(
    session: AsyncSession,
    slide_id: str,
    media_id: str,
) -> AppUpdateSlideMedia:
    result = await session.execute(
        select(AppUpdateSlideMedia).where(
            AppUpdateSlideMedia.client_id == media_id,
            AppUpdateSlideMedia.slide_id == slide_id,
            AppUpdateSlideMedia.is_deleted.is_(False),
        )
    )
    media = result.scalar_one_or_none()
    if media is None:
        raise NotFound("Slide media not found.")
    return media


async def next_media_sequence_order(session: AsyncSession, slide_id: str) -> int:
    result = await session.execute(
        select(func.coalesce(func.max(AppUpdateSlideMedia.sequence_order), 0) + 1).where(
            AppUpdateSlideMedia.slide_id == slide_id,
            AppUpdateSlideMedia.is_deleted.is_(False),
        )
    )
    return int(result.scalar_one())
