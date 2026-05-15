from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.working_sections.requests.delete_working_section_request import (
    WorkingSectionDeleteRequest,
    parse_delete_working_section_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def delete_working_section(ctx: ServiceContext) -> dict:
    request: WorkingSectionDeleteRequest = parse_delete_working_section_request(ctx.incoming_data)
    pending_events: list = []

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.client_id == request.client_id,
                WorkingSection.is_deleted.is_(False),
            )
        )
        section = result.scalar_one_or_none()
        if section is None:
            raise NotFound("Working section not found.")

        section.is_deleted = True
        section.deleted_at = datetime.now(timezone.utc)
        section.deleted_by_id = ctx.user_id
        pending_events.append(build_workspace_event(section, "working_section:deleted"))

    await dispatch(pending_events)
    return {}
