from beyo_manager.config import settings
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.bootstrap.phases.seed_admin_user import seed_admin_user
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import seed_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_issue_category_configs import seed_issue_category_configs
from beyo_manager.services.commands.bootstrap.phases.seed_issue_severities import seed_issue_severities
from beyo_manager.services.commands.bootstrap.phases.seed_issue_types import seed_issue_types
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
        item_category_ids = await seed_item_categories(ctx.session, workspace_result["workspace_id"])
        issue_type_ids = await seed_issue_types(ctx.session, workspace_result["workspace_id"])
        await seed_issue_severities(ctx.session, workspace_result["workspace_id"])
        section_ids = await seed_working_sections(ctx.session, workspace_result["workspace_id"])
        await seed_issue_category_configs(
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
        worker_result = await seed_workers(
            ctx.session,
            settings,
            workspace_result,
            section_ids,
            user_result["admin_user_id"],
        )

    return {
        "workspace_id": workspace_result["workspace_id"],
        "admin_user_id": user_result["admin_user_id"],
        "worker_user_ids": worker_result,
        "roles_seeded": list(role_ids.keys()),
    }
