"""Copy a presentation's slides, media, timeline elements and audience targets
onto a new version.

In-session helper (not a command). The caller owns the transaction. View-state
records and publication/archival timestamps are intentionally NOT copied. Media
rows get new client_ids, so timeline element ``media_id`` references are remapped
to the copied media.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.base.identity import generate_id
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_app_target import (
    AppUpdatePresentationAppTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_role_target import (
    AppUpdatePresentationRoleTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_slide import (
    AppUpdatePresentationSlide,
)
from beyo_manager.models.tables.app_update_presentations.presentation_user_target import (
    AppUpdatePresentationUserTarget,
)
from beyo_manager.models.tables.app_update_presentations.presentation_workspace_target import (
    AppUpdatePresentationWorkspaceTarget,
)
from beyo_manager.models.tables.app_update_presentations.slide_element import (
    AppUpdateSlideElement,
)
from beyo_manager.models.tables.app_update_presentations.slide_media import (
    AppUpdateSlideMedia,
)


async def copy_presentation_children_in_session(
    session: AsyncSession,
    source: AppUpdatePresentation,
    target: AppUpdatePresentation,
) -> None:
    for slide in source.slides:
        if slide.is_deleted:
            continue
        new_slide = AppUpdatePresentationSlide(
            presentation_id=target.client_id,
            sequence_order=slide.sequence_order,
            title=slide.title,
            description=slide.description,
            layout_type=slide.layout_type,
            action_label=slide.action_label,
            action_route=slide.action_route,
            playback_mode=slide.playback_mode,
            duration_ms=slide.duration_ms,
            composition_schema_version=slide.composition_schema_version,
            background_color=slide.background_color,
        )
        session.add(new_slide)
        await session.flush()

        media_id_map: dict[str, str] = {}
        for media in slide.media:
            if media.is_deleted:
                continue
            new_media_id = generate_id(AppUpdateSlideMedia.CLIENT_ID_PREFIX)
            media_id_map[media.client_id] = new_media_id
            session.add(
                AppUpdateSlideMedia(
                    client_id=new_media_id,
                    slide_id=new_slide.client_id,
                    sequence_order=media.sequence_order,
                    media_type=media.media_type,
                    storage_key=media.storage_key,
                    poster_storage_key=media.poster_storage_key,
                    fallback_storage_key=media.fallback_storage_key,
                    alt_text=media.alt_text,
                    mime_type=media.mime_type,
                    width=media.width,
                    height=media.height,
                    duration_ms=media.duration_ms,
                    is_looping=media.is_looping,
                )
            )

        for element in slide.elements:
            if element.is_deleted:
                continue
            session.add(
                AppUpdateSlideElement(
                    slide_id=new_slide.client_id,
                    element_type=element.element_type,
                    sequence_order=element.sequence_order,
                    layer_index=element.layer_index,
                    start_ms=element.start_ms,
                    end_ms=element.end_ms,
                    media_id=media_id_map.get(element.media_id) if element.media_id else None,
                    text_content=element.text_content,
                    layout=element.layout,
                    style=element.style,
                    enter_animation=element.enter_animation,
                    exit_animation=element.exit_animation,
                )
            )

    for app_target in source.app_targets:
        session.add(
            AppUpdatePresentationAppTarget(
                presentation_id=target.client_id, app_key=app_target.app_key
            )
        )
    for role_target in source.role_targets:
        session.add(
            AppUpdatePresentationRoleTarget(
                presentation_id=target.client_id, role_key=role_target.role_key
            )
        )
    for workspace_target in source.workspace_targets:
        session.add(
            AppUpdatePresentationWorkspaceTarget(
                presentation_id=target.client_id,
                workspace_id=workspace_target.workspace_id,
            )
        )
    for user_target in source.user_targets:
        session.add(
            AppUpdatePresentationUserTarget(
                presentation_id=target.client_id, user_id=user_target.user_id
            )
        )
    await session.flush()
