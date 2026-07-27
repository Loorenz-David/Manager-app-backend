from collections import defaultdict
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from beyo_manager.domain.app_update_presentations.serializers import (
    serialize_presentation_list_item,
)
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.services.context import ServiceContext

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _parse_dt(value: str | None, field: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field}: must be an ISO-8601 datetime.") from exc


async def list_presentations(ctx: ServiceContext) -> dict:
    params = ctx.query_params
    limit = min(int(params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(params.get("offset", 0))

    stmt = select(AppUpdatePresentation).where(
        AppUpdatePresentation.workspace_id == ctx.workspace_id,
        AppUpdatePresentation.is_deleted.is_(False),
    )

    status = params.get("status")
    if status:
        stmt = stmt.where(AppUpdatePresentation.status == status)

    logical_client_id = params.get("logical_client_id")
    if logical_client_id:
        stmt = stmt.where(
            AppUpdatePresentation.logical_client_id == logical_client_id
        )

    version = params.get("version")
    if version is not None and version != "":
        stmt = stmt.where(AppUpdatePresentation.version == int(version))

    app_key = params.get("app_key")
    if app_key:
        stmt = stmt.where(
            AppUpdatePresentation.app_targets.any(
                AppUpdatePresentationAppTarget.app_key == app_key
            )
        )

    role_key = params.get("role_key")
    if role_key:
        stmt = stmt.where(
            AppUpdatePresentation.role_targets.any(
                AppUpdatePresentationRoleTarget.role_key == role_key
            )
        )

    published_after = _parse_dt(params.get("published_after"), "published_after")
    if published_after:
        stmt = stmt.where(AppUpdatePresentation.published_at >= published_after)
    published_before = _parse_dt(params.get("published_before"), "published_before")
    if published_before:
        stmt = stmt.where(AppUpdatePresentation.published_at < published_before)

    q = params.get("q")
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                AppUpdatePresentation.title.ilike(like),
                AppUpdatePresentation.summary.ilike(like),
            )
        )

    stmt = stmt.order_by(
        AppUpdatePresentation.created_at.desc(),
        AppUpdatePresentation.client_id.desc(),
    ).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()
    page = rows[:limit]

    slides_by_presentation = await _load_deck_previews(
        ctx, [p.client_id for p in page]
    )

    return {
        "app_update_presentations_pagination": {
            "items": [
                serialize_presentation_list_item(
                    p, slides_by_presentation.get(p.client_id, [])
                )
                for p in page
            ],
            "has_more": len(rows) > limit,
            "limit": limit,
            "offset": offset,
        }
    }


async def _load_deck_previews(
    ctx: ServiceContext, presentation_ids: list[str]
) -> dict[str, list[AppUpdatePresentationSlide]]:
    """Batch-load non-deleted slides (with their media) for the page's decks so
    the card fields can be derived without a per-row query. Two SELECTs total
    (slides + a single selectin for media), regardless of page size."""
    if not presentation_ids:
        return {}
    result = await ctx.session.execute(
        select(AppUpdatePresentationSlide)
        .where(
            AppUpdatePresentationSlide.presentation_id.in_(presentation_ids),
            AppUpdatePresentationSlide.is_deleted.is_(False),
        )
        .options(selectinload(AppUpdatePresentationSlide.media))
    )
    slides_by_presentation: dict[str, list[AppUpdatePresentationSlide]] = defaultdict(list)
    for slide in result.scalars().all():
        slides_by_presentation[slide.presentation_id].append(slide)
    return slides_by_presentation
