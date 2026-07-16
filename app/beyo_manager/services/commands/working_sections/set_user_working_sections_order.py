from sqlalchemy import select

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.commands.working_sections.requests.set_user_sections_order_request import (
    SetUserSectionsOrderRequest,
    parse_set_user_sections_order_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_user_event


async def set_user_working_sections_order(ctx: ServiceContext) -> dict:
    """Rewrite the per-user ordering of a worker's active sections (replace semantics).

    The payload must list exactly the user's current active section memberships, in the
    desired order; each membership's ``sort_order`` is rewritten to its list index. This
    is the single writer that reorders existing memberships (assign/register only append).
    """
    request: SetUserSectionsOrderRequest = parse_set_user_sections_order_request(ctx.incoming_data)

    if len(request.ordered_working_section_ids) != len(set(request.ordered_working_section_ids)):
        raise ValidationError("Duplicate IDs in ordered_working_section_ids are not allowed.")

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(WorkingSectionMembership).where(
                WorkingSectionMembership.workspace_id == ctx.workspace_id,
                WorkingSectionMembership.user_id == request.user_id,
                WorkingSectionMembership.removed_at.is_(None),
            )
        )
        memberships: list[WorkingSectionMembership] = list(result.scalars().all())
        membership_by_section = {m.working_section_id: m for m in memberships}

        requested_ids = set(request.ordered_working_section_ids)
        active_ids = set(membership_by_section)
        if requested_ids != active_ids:
            missing = active_ids - requested_ids
            unknown = requested_ids - active_ids
            details = []
            if unknown:
                details.append(f"not active for user: {sorted(unknown)}")
            if missing:
                details.append(f"missing from payload: {sorted(missing)}")
            raise ValidationError(
                "ordered_working_section_ids must list exactly the user's active sections "
                f"({'; '.join(details)})."
            )

        for sort_order, section_id in enumerate(request.ordered_working_section_ids):
            membership_by_section[section_id].sort_order = sort_order

    await dispatch(
        [
            build_user_event(
                user_id=request.user_id,
                event_name="user:working_sections_updated",
                client_id=request.user_id,
                extra={"working_section_ids": request.ordered_working_section_ids},
            )
        ]
    )
    return {"ordered_section_ids": request.ordered_working_section_ids}
