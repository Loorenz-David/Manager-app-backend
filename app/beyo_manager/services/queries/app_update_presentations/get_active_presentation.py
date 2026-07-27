import logging
from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.app_update_presentations.enums import (
    AppKeyEnum,
    PresentationStatusEnum,
)
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_active,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.models.tables.app_update_presentations.presentation_view import (
    AppUpdatePresentationView,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.app_update_presentations._eligibility import (
    is_eligible,
    newest_version_per_logical,
)
from beyo_manager.services.queries.app_update_presentations._loaders import (
    full_graph_options,
)

logger = logging.getLogger(__name__)

_VALID_APP_KEYS = {a.value for a in AppKeyEnum}
_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


def resolve_app_key(ctx: ServiceContext) -> str:
    """Validate the requested app_key and cross-check it against the signed
    ``app_scope`` claim so a client cannot request a scope it is not signed in as."""
    requested = ctx.query_params.get("app_key")
    if not requested:
        raise ValidationError("app_key query parameter is required.")
    if requested not in _VALID_APP_KEYS:
        raise ValidationError(f"app_key '{requested}' is not a recognized application.")
    claim_scope = ctx.identity.get("app_scope", "")
    if requested != claim_scope:
        raise ValidationError(
            "app_key must match the application this session is signed in as."
        )
    return requested


async def get_active_presentation(ctx: ServiceContext) -> dict:
    app_key = resolve_app_key(ctx)
    now = datetime.now(timezone.utc)

    result = await ctx.session.execute(
        select(AppUpdatePresentation)
        .where(
            AppUpdatePresentation.workspace_id == ctx.workspace_id,
            AppUpdatePresentation.status == PresentationStatusEnum.PUBLISHED,
            AppUpdatePresentation.is_deleted.is_(False),
            or_(
                AppUpdatePresentation.starts_at.is_(None),
                AppUpdatePresentation.starts_at <= now,
            ),
            or_(
                AppUpdatePresentation.expires_at.is_(None),
                AppUpdatePresentation.expires_at > now,
            ),
        )
        .options(*full_graph_options())
    )
    candidates = result.scalars().all()

    # Only presentations this acting user is eligible for, then reduce to the
    # newest version per logical announcement (newest-version-wins).
    eligible = [p for p in candidates if is_eligible(ctx, p, app_key)]
    winners = newest_version_per_logical(eligible)
    if not winners:
        return {"presentation": None}

    views_by_presentation = await _load_views(ctx, [p.client_id for p in winners])

    # A winner the user already completed is done — do not fall back to an older
    # version of the same announcement.
    servable = [
        p
        for p in winners
        if not (
            views_by_presentation.get(p.client_id)
            and views_by_presentation[p.client_id].completed_at is not None
        )
    ]
    if not servable:
        return {"presentation": None}

    servable.sort(
        key=lambda p: (
            p.display_priority,
            p.published_at or _MIN_DT,
            p.client_id,
        ),
        reverse=True,
    )
    winner = servable[0]

    logger.info(
        "active presentation resolved | presentation_id=%s logical_client_id=%s "
        "version=%s app_key=%s acting_user_id=%s workspace_id=%s",
        winner.client_id,
        winner.logical_client_id,
        winner.version,
        app_key,
        ctx.user_id,
        ctx.workspace_id,
    )
    return {
        "presentation": serialize_presentation_active(
            winner, views_by_presentation.get(winner.client_id)
        )
    }


async def _load_views(ctx: ServiceContext, presentation_ids: list[str]) -> dict:
    if not presentation_ids:
        return {}
    result = await ctx.session.execute(
        select(AppUpdatePresentationView).where(
            AppUpdatePresentationView.acting_user_id == ctx.user_id,
            AppUpdatePresentationView.presentation_id.in_(presentation_ids),
        )
    )
    return {v.presentation_id: v for v in result.scalars().all()}
