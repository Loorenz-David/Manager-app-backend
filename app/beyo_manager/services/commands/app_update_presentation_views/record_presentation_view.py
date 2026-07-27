import logging
from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.domain.app_update_presentations.audience_rules import (
    presentation_matches_context,
)
from beyo_manager.domain.app_update_presentations.enums import (
    PresentationStatusEnum,
    PresentationViewStatusEnum,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_view_state_full,
)
from beyo_manager.domain.app_update_presentations.view_state_rules import (
    COMPLETED,
    DISMISSED,
    PROGRESSED,
    SHOWN,
    assert_dismiss_allowed,
    assert_no_completion_regression,
    assert_valid_action,
    validate_slide_index,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.presentation_view import (
    AppUpdatePresentationView,
)
from beyo_manager.services.commands.app_update_presentations._presentation_loading import (
    load_presentation_full,
)
from beyo_manager.services.commands.app_update_presentation_views.requests import (
    parse_record_presentation_view_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext

logger = logging.getLogger(__name__)


def _assert_eligible(ctx: ServiceContext, presentation) -> None:
    """The acting user may only record view state for a presentation they can see."""
    if presentation.status != PresentationStatusEnum.PUBLISHED:
        raise NotFound("Presentation not found.")
    eligible = presentation_matches_context(
        audience_mode=presentation.audience_mode,
        app_targets={t.app_key.value for t in presentation.app_targets},
        role_targets={t.role_key.value for t in presentation.role_targets},
        workspace_targets={t.workspace_id for t in presentation.workspace_targets},
        user_targets={t.user_id for t in presentation.user_targets},
        app_key=ctx.identity.get("app_scope", ""),
        workspace_id=ctx.workspace_id,
        role_name=ctx.role_name,
        user_id=ctx.user_id,
    )
    if not eligible:
        raise NotFound("Presentation not found.")


def _apply_action(view, action, now, last_slide_index, is_dismissible) -> None:
    if last_slide_index is not None:
        view.last_slide_index = max(view.last_slide_index, last_slide_index)

    if action == SHOWN:
        if view.first_shown_at is None:
            view.first_shown_at = now
        view.last_shown_at = now
        view.view_count += 1
        if view.status != PresentationViewStatusEnum.COMPLETED:
            view.status = PresentationViewStatusEnum.SHOWN
    elif action == PROGRESSED:
        # Index already advanced above; do not change a terminal status.
        if view.status not in (
            PresentationViewStatusEnum.COMPLETED,
            PresentationViewStatusEnum.DISMISSED,
        ):
            view.status = PresentationViewStatusEnum.SHOWN
    elif action == DISMISSED:
        assert_dismiss_allowed(is_dismissible)
        assert_no_completion_regression(view.status, action)
        view.dismissed_at = now
        view.status = PresentationViewStatusEnum.DISMISSED
    elif action == COMPLETED:
        if view.completed_at is None:
            view.completed_at = now
        view.status = PresentationViewStatusEnum.COMPLETED


async def record_presentation_view(ctx: ServiceContext) -> dict:
    request = parse_record_presentation_view_request(ctx.incoming_data)
    assert_valid_action(request.action)
    now = datetime.now(timezone.utc)

    async with maybe_begin(ctx.session):
        presentation = await load_presentation_full(
            ctx.session, ctx.workspace_id, request.presentation_id
        )
        if presentation.version != request.version:
            raise ValidationError(
                "version does not match the requested presentation."
            )
        _assert_eligible(ctx, presentation)

        active_slide_count = len([s for s in presentation.slides if not s.is_deleted])
        if request.last_slide_index is not None:
            validate_slide_index(request.last_slide_index, active_slide_count)

        result = await ctx.session.execute(
            select(AppUpdatePresentationView).where(
                AppUpdatePresentationView.presentation_id == request.presentation_id,
                AppUpdatePresentationView.acting_user_id == ctx.user_id,
            )
        )
        view = result.scalar_one_or_none()
        if view is None:
            view = AppUpdatePresentationView(
                workspace_id=ctx.workspace_id,
                presentation_id=request.presentation_id,
                acting_user_id=ctx.user_id,
                status=PresentationViewStatusEnum.SHOWN,
                view_count=0,
                last_slide_index=0,
            )
            ctx.session.add(view)

        _apply_action(
            view,
            request.action,
            now,
            request.last_slide_index,
            presentation.is_dismissible,
        )
        await ctx.session.flush()
        response = serialize_view_state_full(view)

    if request.action == COMPLETED:
        logger.info(
            "app_update_presentation view completed | presentation_id=%s "
            "acting_user_id=%s workspace_id=%s",
            request.presentation_id,
            ctx.user_id,
            ctx.workspace_id,
        )
    return {"view_state": response}
