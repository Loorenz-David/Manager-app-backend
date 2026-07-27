from datetime import datetime, timezone

from sqlalchemy import or_, select

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_active,
)
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
from beyo_manager.services.queries.app_update_presentations.get_active_presentation import (
    resolve_app_key,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50
_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


async def list_whats_new(ctx: ServiceContext) -> dict:
    """Consumer 'What's New' feed: the newest eligible version of every
    announcement this user can see, newest first, including already-seen and
    expired items so the user can revisit them. Future-scheduled items are
    excluded.
    """
    app_key = resolve_app_key(ctx)
    now = datetime.now(timezone.utc)
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))

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
        )
        .options(*full_graph_options())
    )
    candidates = result.scalars().all()

    eligible = [p for p in candidates if is_eligible(ctx, p, app_key)]
    winners = newest_version_per_logical(eligible)
    winners.sort(
        key=lambda p: (p.published_at or _MIN_DT, p.client_id), reverse=True
    )

    # Grouping/eligibility happen in memory (announcement counts per workspace
    # are small); paginate the reduced winner list.
    page = winners[offset : offset + limit]
    has_more = len(winners) > offset + limit

    views_by_presentation = await _load_views(ctx, [p.client_id for p in page])

    return {
        "app_update_whats_new_pagination": {
            "items": [
                serialize_presentation_active(
                    p, views_by_presentation.get(p.client_id)
                )
                for p in page
            ],
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        }
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
