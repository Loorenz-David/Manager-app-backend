"""Validate that referenced media rows exist, are live, and belong to the slide.

In-session helper (not a command).
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)


async def validate_media_refs_in_session(
    session: AsyncSession,
    slide_id: str,
    media_ids: Sequence[str],
) -> None:
    unique_ids = set(media_ids)
    if not unique_ids:
        return
    result = await session.execute(
        select(AppUpdateSlideMedia.client_id).where(
            AppUpdateSlideMedia.client_id.in_(unique_ids),
            AppUpdateSlideMedia.slide_id == slide_id,
            AppUpdateSlideMedia.is_deleted.is_(False),
        )
    )
    found = set(result.scalars().all())
    missing = unique_ids - found
    if missing:
        raise ValidationError(
            f"Media element(s) reference media that does not belong to this slide: "
            f"{sorted(missing)}."
        )
