"""Shared workspace-scoped loaders for presentation commands.

Helper functions (not commands) — safe to import from multiple commands.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from beyo_manager.domain.app_update_presentations.presentation_states import (
    assert_presentation_is_draft,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)


async def load_presentation_for_write(
    session: AsyncSession,
    workspace_id: str,
    presentation_client_id: str,
    *,
    require_draft: bool = True,
    for_update: bool = False,
) -> AppUpdatePresentation:
    """Fetch a presentation scoped to the workspace and not soft-deleted.

    Raises NotFound for missing / deleted / wrong-workspace rows (IDOR guard).
    When ``require_draft`` is True, also asserts the presentation is a draft.

    ``for_update`` takes a row lock on the presentation, serialising its slide
    sequence space. Callers that allocate or renumber ``sequence_order`` on
    ``app_update_presentation_slides`` must pass it — the counterpart of
    ``load_slide_for_write(for_update=True)`` one level up. Where both locks are
    taken, the presentation is always locked first.
    """
    statement = select(AppUpdatePresentation).where(
        AppUpdatePresentation.client_id == presentation_client_id,
        AppUpdatePresentation.workspace_id == workspace_id,
        AppUpdatePresentation.is_deleted.is_(False),
    )
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    presentation = result.scalar_one_or_none()
    if presentation is None:
        raise NotFound("Presentation not found.")
    if require_draft:
        assert_presentation_is_draft(presentation.status)
    return presentation


def _full_graph_options():
    return (
        selectinload(AppUpdatePresentation.slides).selectinload(
            AppUpdatePresentationSlide.media
        ),
        selectinload(AppUpdatePresentation.slides)
        .selectinload(AppUpdatePresentationSlide.elements)
        .selectinload(AppUpdateSlideElement.media),
        selectinload(AppUpdatePresentation.app_targets),
        selectinload(AppUpdatePresentation.role_targets),
        selectinload(AppUpdatePresentation.workspace_targets),
        selectinload(AppUpdatePresentation.user_targets),
    )


async def load_presentation_full(
    session: AsyncSession,
    workspace_id: str,
    presentation_client_id: str,
) -> AppUpdatePresentation:
    """Load a presentation with its full slide/media/target graph eagerly."""
    result = await session.execute(
        select(AppUpdatePresentation)
        .where(
            AppUpdatePresentation.client_id == presentation_client_id,
            AppUpdatePresentation.workspace_id == workspace_id,
            AppUpdatePresentation.is_deleted.is_(False),
        )
        .options(*_full_graph_options())
    )
    presentation = result.scalar_one_or_none()
    if presentation is None:
        raise NotFound("Presentation not found.")
    return presentation
