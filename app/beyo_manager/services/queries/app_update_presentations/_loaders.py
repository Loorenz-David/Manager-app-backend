"""Eager-load option builders for presentation read queries."""

from sqlalchemy.orm import selectinload

from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)


def full_graph_options():
    """selectinload options for slides -> media + slides -> elements -> media,
    plus every target dimension. One extra SELECT per relationship regardless of
    row count (no N+1)."""
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
