from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.commands.working_sections.requests.unassign_user_request import (
    UnassignUserRequest,
    parse_unassign_user_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_user_event


async def unassign_user_from_working_sections(ctx: ServiceContext) -> dict:
    request: UnassignUserRequest = parse_unassign_user_request(ctx.incoming_data)

    if len(request.working_section_ids) != len(set(request.working_section_ids)):
        raise ValidationError("Duplicate IDs in working_section_ids are not allowed.")

    async with ctx.session.begin():
        memberships: list[WorkingSectionMembership] = []
        for section_id in request.working_section_ids:
            result = await ctx.session.execute(
                select(WorkingSectionMembership).where(
                    WorkingSectionMembership.workspace_id == ctx.workspace_id,
                    WorkingSectionMembership.working_section_id == section_id,
                    WorkingSectionMembership.user_id == request.user_id,
                    WorkingSectionMembership.removed_at.is_(None),
                )
            )
            membership = result.scalar_one_or_none()
            if membership is None:
                raise NotFound(
                    f"No active membership found for user in section '{section_id}'."
                )
            memberships.append(membership)

        now = datetime.now(timezone.utc)
        for membership in memberships:
            membership.removed_at = now
            membership.removed_by_id = ctx.user_id

    await dispatch(
        [
            build_user_event(
                user_id=request.user_id,
                event_name="user:working_sections_updated",
                client_id=request.user_id,
                extra={"working_section_ids": request.working_section_ids},
            )
        ]
    )
    return {"unassigned_section_ids": request.working_section_ids}
