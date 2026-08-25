from sqlalchemy import and_, exists, func, or_, select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.pause_reasons.serializers import (
    serialize_configured_pause_reason,
)
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.pause_reasons.pause_reason_user_link import (
    PauseReasonUserLink,
)
from beyo_manager.models.tables.pause_reasons.pause_reason_working_section_link import (
    PauseReasonWorkingSectionLink,
)
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.pause_reasons.eligibility import (
    load_pause_reason_links,
    normalize_link_ids,
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _user_eligibility_clause(workspace_id: str, user_ids: list[str]):
    has_any_link = exists(
        select(1).where(
            PauseReasonUserLink.workspace_id == workspace_id,
            PauseReasonUserLink.pause_reason_id == PauseReason.client_id,
        )
    )
    matched_count = (
        select(func.count(func.distinct(PauseReasonUserLink.user_id)))
        .select_from(PauseReasonUserLink)
        .join(
            WorkspaceMembership,
            and_(
                WorkspaceMembership.workspace_id == PauseReasonUserLink.workspace_id,
                WorkspaceMembership.user_id == PauseReasonUserLink.user_id,
                WorkspaceMembership.is_active.is_(True),
            ),
        )
        .where(
            PauseReasonUserLink.workspace_id == workspace_id,
            PauseReasonUserLink.pause_reason_id == PauseReason.client_id,
            PauseReasonUserLink.user_id.in_(user_ids),
        )
        .correlate(PauseReason)
        .scalar_subquery()
    )
    return or_(~has_any_link, matched_count == len(user_ids))


def _working_section_eligibility_clause(
    workspace_id: str, working_section_ids: list[str]
):
    has_any_link = exists(
        select(1).where(
            PauseReasonWorkingSectionLink.workspace_id == workspace_id,
            PauseReasonWorkingSectionLink.pause_reason_id == PauseReason.client_id,
        )
    )
    matched_count = (
        select(
            func.count(func.distinct(PauseReasonWorkingSectionLink.working_section_id))
        )
        .select_from(PauseReasonWorkingSectionLink)
        .join(
            WorkingSection,
            and_(
                WorkingSection.workspace_id
                == PauseReasonWorkingSectionLink.workspace_id,
                WorkingSection.client_id
                == PauseReasonWorkingSectionLink.working_section_id,
                WorkingSection.is_deleted.is_(False),
            ),
        )
        .where(
            PauseReasonWorkingSectionLink.workspace_id == workspace_id,
            PauseReasonWorkingSectionLink.pause_reason_id == PauseReason.client_id,
            PauseReasonWorkingSectionLink.working_section_id.in_(working_section_ids),
        )
        .correlate(PauseReason)
        .scalar_subquery()
    )
    return or_(~has_any_link, matched_count == len(working_section_ids))


async def list_pause_reasons(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    pause_type = ctx.query_params.get("pause_type")
    user_ids = normalize_link_ids(ctx.query_params.get("user_ids") or [])
    working_section_ids = normalize_link_ids(
        ctx.query_params.get("working_section_ids") or []
    )

    stmt = select(PauseReason).where(
        PauseReason.workspace_id == ctx.workspace_id,
        PauseReason.is_deleted.is_(False),
    )
    if pause_type is not None:
        try:
            pause_type = PauseTypeEnum(pause_type)
        except ValueError:
            pause_type = None
        if pause_type is not None:
            stmt = stmt.where(PauseReason.pause_type == pause_type)
    if user_ids:
        stmt = stmt.where(_user_eligibility_clause(ctx.workspace_id, user_ids))
    if working_section_ids:
        stmt = stmt.where(
            _working_section_eligibility_clause(ctx.workspace_id, working_section_ids)
        )

    result = await ctx.session.execute(
        stmt.order_by(PauseReason.created_at.asc()).offset(offset).limit(limit + 1)
    )
    rows = result.scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    user_links, section_links = await load_pause_reason_links(
        ctx.session,
        workspace_id=ctx.workspace_id,
        pause_reason_ids=[row.client_id for row in page],
    )
    return {
        "pause_reasons": [
            serialize_configured_pause_reason(
                row,
                linked_user_ids=user_links[row.client_id],
                linked_working_section_ids=section_links[row.client_id],
            )
            for row in page
        ],
        "pause_reasons_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }
