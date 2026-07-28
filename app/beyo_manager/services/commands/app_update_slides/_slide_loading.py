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
from beyo_manager.services.commands.app_update_presentations._sequencing import (
    apply_sequence_orders,
)


async def load_slide_for_write(
    session: AsyncSession,
    presentation_id: str,
    slide_id: str,
    *,
    for_update: bool = False,
) -> AppUpdatePresentationSlide:
    """Fetch a slide scoped to its presentation and not soft-deleted.

    ``for_update`` takes a row lock on the slide, which serialises the slide's
    whole media sequence space. Callers that allocate or renumber
    ``sequence_order`` on ``app_update_slide_media`` must pass it: the next
    value is derived from a MAX over the sibling rows, and under READ COMMITTED
    two concurrent readers would otherwise compute the same value. The lock goes
    on the parent slide because the row being inserted does not exist yet.
    """
    statement = select(AppUpdatePresentationSlide).where(
        AppUpdatePresentationSlide.client_id == slide_id,
        AppUpdatePresentationSlide.presentation_id == presentation_id,
        AppUpdatePresentationSlide.is_deleted.is_(False),
    )
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
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


async def compact_slide_sequence(
    session: AsyncSession,
    presentation_id: str,
    *,
    exclude_slide_id: str | None = None,
) -> None:
    """Renumber a presentation's active slides to a contiguous 1..N.

    Slide-level counterpart of ``compact_media_sequence``. Caller owns the
    transaction and must hold the presentation row lock.
    """
    statement = select(AppUpdatePresentationSlide).where(
        AppUpdatePresentationSlide.presentation_id == presentation_id,
        AppUpdatePresentationSlide.is_deleted.is_(False),
    )
    if exclude_slide_id is not None:
        statement = statement.where(AppUpdatePresentationSlide.client_id != exclude_slide_id)

    result = await session.execute(
        statement.order_by(AppUpdatePresentationSlide.sequence_order)
    )
    survivors = result.scalars().all()
    order_map = {slide.client_id: position for position, slide in enumerate(survivors, start=1)}
    await apply_sequence_orders(
        session, {slide.client_id: slide for slide in survivors}, order_map
    )


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
    """Next append position among *active* media.

    Counting only active rows is correct — soft-deleted media release their slot
    (uix_app_update_slide_media_slide_sequence_active). Callers must hold the
    slide row lock; see ``load_slide_for_write(for_update=True)``.
    """
    result = await session.execute(
        select(func.coalesce(func.max(AppUpdateSlideMedia.sequence_order), 0) + 1).where(
            AppUpdateSlideMedia.slide_id == slide_id,
            AppUpdateSlideMedia.is_deleted.is_(False),
        )
    )
    return int(result.scalar_one())


async def compact_media_sequence(
    session: AsyncSession,
    slide_id: str,
    *,
    exclude_media_id: str | None = None,
) -> None:
    """Renumber a slide's active media to a contiguous 1..N.

    Keeps the active set matching what publish asserts
    (``assert_contiguous_sequence``) instead of leaving a gap behind every
    delete for publish to repair later. Caller owns the transaction and must
    hold the slide row lock.
    """
    statement = select(AppUpdateSlideMedia).where(
        AppUpdateSlideMedia.slide_id == slide_id,
        AppUpdateSlideMedia.is_deleted.is_(False),
    )
    if exclude_media_id is not None:
        statement = statement.where(AppUpdateSlideMedia.client_id != exclude_media_id)

    result = await session.execute(statement.order_by(AppUpdateSlideMedia.sequence_order))
    survivors = result.scalars().all()
    order_map = {media.client_id: position for position, media in enumerate(survivors, start=1)}
    await apply_sequence_orders(
        session, {media.client_id: media for media in survivors}, order_map
    )
