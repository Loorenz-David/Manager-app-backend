from datetime import datetime, timezone

from sqlalchemy import delete, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.issue_types.issue_type import IssueType
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency
from beyo_manager.models.tables.working_sections.working_section_item_category import WorkingSectionItemCategory
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.working_sections._check_dependency_cycle import check_for_dependency_cycle
from beyo_manager.services.commands.working_sections.requests.edit_working_section_request import (
    WorkingSectionEditRequest,
    parse_edit_working_section_request,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def edit_working_section(ctx: ServiceContext) -> dict:
    request: WorkingSectionEditRequest = parse_edit_working_section_request(ctx.incoming_data)
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

        if "name" in request.model_fields_set:
            name_conflict = await ctx.session.scalar(
                select(WorkingSection.client_id).where(
                    WorkingSection.workspace_id == ctx.workspace_id,
                    WorkingSection.client_id != request.client_id,
                    WorkingSection.name == request.name,
                    WorkingSection.is_deleted.is_(False),
                )
            )
            if name_conflict is not None:
                raise ConflictError(f"A working section named '{request.name}' already exists.")
            section.name = request.name

        if "image" in request.model_fields_set:
            section.image = request.image

        if "working_section_dependencies" in request.model_fields_set:
            dep_ids: list[str] = request.working_section_dependencies or []
            if dep_ids:
                if len(dep_ids) != len(set(dep_ids)):
                    raise ValidationError("Duplicate IDs in working_section_dependencies are not allowed.")

                dep_ids_found = set(
                    (
                        await ctx.session.execute(
                            select(WorkingSection.client_id).where(
                                WorkingSection.workspace_id == ctx.workspace_id,
                                WorkingSection.client_id.in_(dep_ids),
                                WorkingSection.is_deleted.is_(False),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for dep_id in dep_ids:
                    if dep_id not in dep_ids_found:
                        raise NotFound(f"Working section dependency '{dep_id}' was not found.")

                await check_for_dependency_cycle(
                    ctx.session,
                    ctx.workspace_id,
                    request.client_id,
                    dep_ids,
                )

            await ctx.session.execute(
                delete(WorkingSectionDependency).where(
                    WorkingSectionDependency.workspace_id == ctx.workspace_id,
                    WorkingSectionDependency.dependent_section_id == request.client_id,
                )
            )
            for dep_id in dep_ids:
                ctx.session.add(
                    WorkingSectionDependency(
                        workspace_id=ctx.workspace_id,
                        dependent_section_id=request.client_id,
                        prerequisite_section_id=dep_id,
                    )
                )

        if "working_section_item_categories" in request.model_fields_set:
            cat_ids: list[str] = request.working_section_item_categories or []
            if cat_ids:
                if len(cat_ids) != len(set(cat_ids)):
                    raise ValidationError("Duplicate IDs in working_section_item_categories are not allowed.")

                cat_ids_found = set(
                    (
                        await ctx.session.execute(
                            select(ItemCategory.client_id).where(
                                ItemCategory.workspace_id == ctx.workspace_id,
                                ItemCategory.client_id.in_(cat_ids),
                                ItemCategory.is_deleted.is_(False),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for cat_id in cat_ids:
                    if cat_id not in cat_ids_found:
                        raise NotFound(f"Item category '{cat_id}' was not found.")

            await ctx.session.execute(
                delete(WorkingSectionItemCategory).where(
                    WorkingSectionItemCategory.workspace_id == ctx.workspace_id,
                    WorkingSectionItemCategory.working_section_id == request.client_id,
                )
            )
            for cat_id in cat_ids:
                ctx.session.add(
                    WorkingSectionItemCategory(
                        workspace_id=ctx.workspace_id,
                        working_section_id=request.client_id,
                        item_category_id=cat_id,
                    )
                )

        if "working_section_supported_issue_types" in request.model_fields_set:
            issue_type_ids: list[str] = request.working_section_supported_issue_types or []
            if issue_type_ids:
                if len(issue_type_ids) != len(set(issue_type_ids)):
                    raise ValidationError(
                        "Duplicate IDs in working_section_supported_issue_types are not allowed."
                    )

                issue_type_ids_found = set(
                    (
                        await ctx.session.execute(
                            select(IssueType.client_id).where(
                                IssueType.workspace_id == ctx.workspace_id,
                                IssueType.client_id.in_(issue_type_ids),
                                IssueType.is_deleted.is_(False),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for issue_type_id in issue_type_ids:
                    if issue_type_id not in issue_type_ids_found:
                        raise NotFound(f"Issue type '{issue_type_id}' was not found.")

            await ctx.session.execute(
                delete(WorkingSectionSupportedIssueType).where(
                    WorkingSectionSupportedIssueType.workspace_id == ctx.workspace_id,
                    WorkingSectionSupportedIssueType.working_section_id == request.client_id,
                )
            )
            for issue_type_id in issue_type_ids:
                ctx.session.add(
                    WorkingSectionSupportedIssueType(
                        workspace_id=ctx.workspace_id,
                        working_section_id=request.client_id,
                        issue_type_id=issue_type_id,
                    )
                )

        section.updated_at = datetime.now(timezone.utc)
        section.updated_by_id = ctx.user_id
        pending_events.append(build_workspace_event(section, "working_section:updated"))

    await dispatch(pending_events)
    return {}
