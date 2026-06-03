from sqlalchemy import select

from beyo_manager.domain.working_sections.serializers import serialize_working_section_id_only
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
from beyo_manager.services.commands.working_sections.requests.create_working_section_request import (
    WorkingSectionCreateRequest,
    parse_create_working_section_request,
)
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.build_event import build_workspace_event


async def create_working_section(ctx: ServiceContext) -> dict:
    request: WorkingSectionCreateRequest = parse_create_working_section_request(ctx.incoming_data)
    pending_events: list = []

    if request.client_id is not None:
        validate_provided_client_id(request.client_id, "wsec")

    async with ctx.session.begin():
        section_kwargs: dict[str, str] = {}
        if request.client_id is not None:
            dup = await ctx.session.get(WorkingSection, request.client_id)
            if dup is not None:
                raise ConflictError("Provided client_id is already in use.")
            section_kwargs["client_id"] = request.client_id

        existing = await ctx.session.scalar(
            select(WorkingSection).where(
                WorkingSection.workspace_id == ctx.workspace_id,
                WorkingSection.name == request.name,
                WorkingSection.is_deleted.is_(False),
            )
        )
        if existing is not None:
            raise ConflictError(f"A working section named '{request.name}' already exists.")

        if request.working_section_dependencies:
            if len(request.working_section_dependencies) != len(set(request.working_section_dependencies)):
                raise ValidationError("Duplicate IDs in working_section_dependencies are not allowed.")

            dep_ids_found = set(
                (
                    await ctx.session.execute(
                        select(WorkingSection.client_id).where(
                            WorkingSection.workspace_id == ctx.workspace_id,
                            WorkingSection.client_id.in_(request.working_section_dependencies),
                            WorkingSection.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for dep_id in request.working_section_dependencies:
                if dep_id not in dep_ids_found:
                    raise NotFound(f"Working section dependency '{dep_id}' was not found.")

        if request.working_section_item_categories:
            if len(request.working_section_item_categories) != len(
                set(request.working_section_item_categories)
            ):
                raise ValidationError("Duplicate IDs in working_section_item_categories are not allowed.")

            cat_ids_found = set(
                (
                    await ctx.session.execute(
                        select(ItemCategory.client_id).where(
                            ItemCategory.workspace_id == ctx.workspace_id,
                            ItemCategory.client_id.in_(request.working_section_item_categories),
                            ItemCategory.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for cat_id in request.working_section_item_categories:
                if cat_id not in cat_ids_found:
                    raise NotFound(f"Item category '{cat_id}' was not found.")

        if request.working_section_supported_issue_types:
            if len(request.working_section_supported_issue_types) != len(
                set(request.working_section_supported_issue_types)
            ):
                raise ValidationError(
                    "Duplicate IDs in working_section_supported_issue_types are not allowed."
                )

            issue_type_ids_found = set(
                (
                    await ctx.session.execute(
                        select(IssueType.client_id).where(
                            IssueType.workspace_id == ctx.workspace_id,
                            IssueType.client_id.in_(request.working_section_supported_issue_types),
                            IssueType.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for issue_type_id in request.working_section_supported_issue_types:
                if issue_type_id not in issue_type_ids_found:
                    raise NotFound(f"Issue type '{issue_type_id}' was not found.")

        section = WorkingSection(
            **section_kwargs,
            workspace_id=ctx.workspace_id,
            name=request.name,
            image=request.image,
            order_list=request.order_list,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(section)
        await ctx.session.flush()

        for dep_id in request.working_section_dependencies:
            ctx.session.add(
                WorkingSectionDependency(
                    workspace_id=ctx.workspace_id,
                    dependent_section_id=section.client_id,
                    prerequisite_section_id=dep_id,
                )
            )

        for cat_id in request.working_section_item_categories:
            ctx.session.add(
                WorkingSectionItemCategory(
                    workspace_id=ctx.workspace_id,
                    working_section_id=section.client_id,
                    item_category_id=cat_id,
                )
            )

        for issue_type_id in request.working_section_supported_issue_types:
            ctx.session.add(
                WorkingSectionSupportedIssueType(
                    workspace_id=ctx.workspace_id,
                    working_section_id=section.client_id,
                    issue_type_id=issue_type_id,
                )
            )

        pending_events.append(build_workspace_event(section, "working_section:created"))

    await dispatch(pending_events)
    return serialize_working_section_id_only(section)
