from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.bootstrap.phases.seed_case_types import seed_case_types
from beyo_manager.services.commands.bootstrap.phases.seed_admin_user import seed_admin_user
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import seed_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_issue_type_links import seed_issue_type_links
from beyo_manager.services.commands.bootstrap.phases.seed_issue_types import seed_issue_types
from beyo_manager.services.commands.bootstrap.phases.seed_item_economics_configuration import (
    seed_item_economics_configuration,
)
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import (
    seed_pause_reason_links,
    seed_pause_reasons,
)
from beyo_manager.services.commands.bootstrap.phases.seed_sku_templates import seed_sku_templates
from beyo_manager.services.commands.bootstrap.phases.seed_email_connection import seed_email_connection
from beyo_manager.services.commands.bootstrap.phases.seed_upholsteries import delete_seeded_upholsteries
from beyo_manager.services.commands.bootstrap.phases.seed_roles import seed_roles
from beyo_manager.services.commands.bootstrap.phases.seed_workers import seed_workers
from beyo_manager.services.commands.bootstrap.phases.seed_working_section_item_categories import seed_working_section_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import seed_working_sections
from beyo_manager.services.commands.bootstrap.phases.seed_workspace import seed_workspace
from beyo_manager.services.context import ServiceContext


async def bootstrap_app(ctx: ServiceContext) -> dict:
    if not (settings.bootstrap_admin_email and settings.bootstrap_admin_username and settings.bootstrap_admin_password):
        raise ValidationError("Bootstrap admin credentials are not configured in environment variables.")

    async with ctx.session.begin():
        role_ids = await seed_roles(ctx.session)
        workspace_result = await seed_workspace(ctx.session, settings, role_ids)
        pause_reason_ids = await seed_pause_reasons(ctx.session, workspace_result["workspace_id"])
        sku_template_ids = await seed_sku_templates(ctx.session, workspace_result["workspace_id"])
        await seed_case_types(ctx.session)
        item_category_ids = await seed_item_categories(ctx.session, workspace_result["workspace_id"])
        issue_type_ids = await seed_issue_types(ctx.session, workspace_result["workspace_id"])
        section_ids = await seed_working_sections(ctx.session, workspace_result["workspace_id"])
        await seed_issue_type_links(
            ctx.session,
            workspace_result["workspace_id"],
            issue_type_ids,
            item_category_ids,
            section_ids,
        )
        await seed_working_section_item_categories(
            ctx.session,
            workspace_result["workspace_id"],
            section_ids,
            item_category_ids,
        )
        user_result = await seed_admin_user(ctx.session, settings, workspace_result)
        await delete_seeded_upholsteries(
            ctx.session,
            workspace_result["workspace_id"],
            user_result["admin_user_id"],
        )
        worker_result = await seed_workers(
            ctx.session,
            settings,
            workspace_result,
            section_ids,
            user_result["admin_user_id"],
        )
        await seed_pause_reason_links(
            ctx.session,
            workspace_id=workspace_result["workspace_id"],
            pause_reason_ids=pause_reason_ids,
            worker_user_ids=worker_result,
        )
        fayoz_user_id = worker_result.get("Fayoz")
        if fayoz_user_id is None:
            raise ValidationError(
                "Bootstrap worker 'Fayoz' is required for item-economics configuration."
            )
        item_economics_result = await seed_item_economics_configuration(
            ctx.session,
            workspace_id=workspace_result["workspace_id"],
            creator_user_id=fayoz_user_id,
            section_ids=section_ids,
        )
        email_connection_result = await seed_email_connection(
            ctx.session,
            workspace_result,
            worker_result,
        )

    return {
        "workspace_id": workspace_result["workspace_id"],
        "admin_user_id": user_result["admin_user_id"],
        "worker_user_ids": worker_result,
        "roles_seeded": list(role_ids.keys()),
        "pause_reasons_seeded": list(pause_reason_ids.keys()),
        "sku_templates_seeded": list(sku_template_ids.keys()),
        "item_economics_configuration": item_economics_result,
        "email_connection": email_connection_result,
    }
