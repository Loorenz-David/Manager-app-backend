from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.config import settings
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.reset.phases.delete_issue_category_configs import (
    delete_issue_category_configs,
)
from beyo_manager.services.commands.reset.phases.delete_working_section_item_categories import (
    delete_working_section_item_categories,
)
from beyo_manager.services.commands.reset.phases.delete_working_section_daily_work_stats import (
    delete_working_section_daily_work_stats,
)
from beyo_manager.services.commands.reset.phases.delete_working_section_supported_issue_types import (
    delete_working_section_supported_issue_types,
)
from beyo_manager.services.commands.reset.phases.delete_working_section_dependencies import (
    delete_working_section_dependencies,
)
from beyo_manager.services.commands.reset.phases.delete_working_sections import delete_working_sections
from beyo_manager.services.commands.reset.phases.delete_issue_severities import delete_issue_severities
from beyo_manager.services.commands.reset.phases.delete_issue_types import delete_issue_types
from beyo_manager.services.commands.reset.phases.delete_item_issues import delete_item_issues
from beyo_manager.services.commands.reset.phases.delete_item_upholstery_requirements import (
    delete_item_upholstery_requirements,
)
from beyo_manager.services.commands.reset.phases.delete_item_upholsteries import delete_item_upholsteries
from beyo_manager.services.commands.reset.phases.delete_items import delete_items
from beyo_manager.services.commands.reset.phases.delete_item_categories import delete_item_categories
from beyo_manager.services.commands.reset.phases.delete_task_events import delete_task_events
from beyo_manager.services.commands.reset.phases.delete_step_state_records import delete_step_state_records
from beyo_manager.services.commands.reset.phases.delete_task_step_assignment_records import (
    delete_task_step_assignment_records,
)
from beyo_manager.services.commands.reset.phases.delete_task_step_dependencies import (
    delete_task_step_dependencies,
)
from beyo_manager.services.commands.reset.phases.delete_task_steps import delete_task_steps
from beyo_manager.services.commands.reset.phases.delete_task_items import delete_task_items
from beyo_manager.services.commands.reset.phases.delete_task_notes import delete_task_notes
from beyo_manager.services.commands.reset.phases.delete_tasks import delete_tasks
from beyo_manager.services.commands.reset.phases.delete_upholstery_inventories import (
    delete_upholstery_inventories,
)
from beyo_manager.services.commands.reset.phases.delete_upholsteries import delete_upholsteries
from beyo_manager.services.commands.reset.phases.delete_static_costs import delete_static_costs
from beyo_manager.services.commands.reset.phases.delete_working_section_memberships import (
    delete_working_section_memberships,
)
from beyo_manager.services.commands.reset.phases.delete_user_section_daily_work_stats import (
    delete_user_section_daily_work_stats,
)
from beyo_manager.services.commands.reset.phases.delete_user_daily_work_stats import (
    delete_user_daily_work_stats,
)
from beyo_manager.services.commands.reset.phases.delete_user_lifetime_stats import (
    delete_user_lifetime_stats,
)
from beyo_manager.services.commands.reset.phases.delete_user_shift_state_records import (
    delete_user_shift_state_records,
)
from beyo_manager.services.commands.reset.phases.delete_user_work_profiles import (
    delete_user_work_profiles,
)
from beyo_manager.services.commands.reset.phases.delete_workspace_memberships import (
    delete_workspace_memberships,
)
from beyo_manager.services.commands.reset.phases.delete_users import delete_orphan_bootstrap_users
from beyo_manager.services.commands.reset.phases.delete_roles import delete_orphan_bootstrap_roles
from beyo_manager.services.commands.reset.phases.delete_audit_logs import delete_audit_logs
from beyo_manager.services.commands.reset.phases.delete_customers import delete_customers
from beyo_manager.services.commands.reset.phases.delete_pending_uploads import delete_pending_uploads
from beyo_manager.services.commands.reset.phases.delete_workspace_roles import delete_workspace_roles
from beyo_manager.services.commands.reset.phases.delete_workspace import delete_workspace


async def reset_app(ctx: ServiceContext) -> dict:
    """
    Reset/clear all workspace data (bootstrap and operational).
    
    Deletes all workspace-scoped data in reverse dependency order:
    
    Task system:
    1. task_events
    2. task_step_assignment_records
    3. task_step_dependencies
    4. step_state_records
    5. task_steps
    6. task_items
    7. task_notes
    8. tasks

    Bootstrap data:
    9. issue_category_configs
    10. working_section_item_categories
    11. working_section_supported_issue_types
    12. working_section_dependencies
    13. user_section_daily_work_stats
    14. working_section_daily_work_stats
    15. working_section_memberships
    16. working_sections
    17. item_issues
    18. item_upholstery_requirements
    19. item_upholsteries
    20. items
    21. issue_severities
    22. issue_types
    23. item_categories
    
    Upholstery:
    24. upholstery_inventories
    25. upholsteries
    
    Other operational data:
    26. static_costs
    27. user_shift_state_records
    28. customers
    29. user_work_profiles
    30. user_daily_work_stats
    31. user_lifetime_stats
    
    Core workspace structures:
    32. workspace_memberships (users remain global and unaffected)
    33. audit_logs
    34. workspace_roles
    35. workspace
    
    Note: Users are global entities (not workspace-scoped). Deleting workspace_memberships
    removes workspace access for users; orphaned users remain in the system.
    """
    if not ctx.workspace_id:
        raise ValidationError("workspace_id is required for reset operation")

    workspace_id = ctx.workspace_id
    should_delete_orphan_bootstrap_users = bool(
        ctx.incoming_data.get("delete_orphan_bootstrap_users", True)
    )
    deleted_bootstrap_roles = 0
    
    async with ctx.session.begin():
        # Task system data
        await delete_task_events(ctx.session, workspace_id)
        await delete_task_step_assignment_records(ctx.session, workspace_id)
        await delete_task_step_dependencies(ctx.session, workspace_id)
        await delete_step_state_records(ctx.session, workspace_id)
        await delete_task_steps(ctx.session, workspace_id)
        await delete_task_items(ctx.session, workspace_id)
        await delete_task_notes(ctx.session, workspace_id)
        await delete_tasks(ctx.session, workspace_id)

        # Bootstrap data
        await delete_issue_category_configs(ctx.session, workspace_id)
        await delete_working_section_item_categories(ctx.session, workspace_id)
        await delete_working_section_supported_issue_types(ctx.session, workspace_id)
        await delete_working_section_dependencies(ctx.session, workspace_id)
        await delete_user_section_daily_work_stats(ctx.session, workspace_id)
        await delete_working_section_daily_work_stats(ctx.session, workspace_id)
        await delete_working_section_memberships(ctx.session, workspace_id)
        await delete_working_sections(ctx.session, workspace_id)
        await delete_item_issues(ctx.session, workspace_id)
        await delete_item_upholstery_requirements(ctx.session, workspace_id)
        await delete_item_upholsteries(ctx.session, workspace_id)
        await delete_items(ctx.session, workspace_id)
        await delete_issue_severities(ctx.session, workspace_id)
        await delete_issue_types(ctx.session, workspace_id)
        await delete_item_categories(ctx.session, workspace_id)
        
        # Upholstery data
        await delete_upholstery_inventories(ctx.session, workspace_id)
        await delete_upholsteries(ctx.session, workspace_id)
        
        # Other operational data
        await delete_static_costs(ctx.session, workspace_id)
        await delete_user_shift_state_records(ctx.session, workspace_id)
        await delete_customers(ctx.session, workspace_id)
        await delete_user_work_profiles(ctx.session, workspace_id)
        await delete_user_daily_work_stats(ctx.session, workspace_id)
        await delete_user_lifetime_stats(ctx.session, workspace_id)
        
        # Core workspace structures
        await delete_workspace_memberships(ctx.session, workspace_id)
        if should_delete_orphan_bootstrap_users:
            await delete_orphan_bootstrap_users(
                ctx.session,
                bootstrap_admin_email=settings.bootstrap_admin_email,
                bootstrap_admin_username=settings.bootstrap_admin_username,
            )
        await delete_audit_logs(ctx.session, workspace_id)
        await delete_pending_uploads(ctx.session, workspace_id)
        await delete_workspace_roles(ctx.session, workspace_id)
        deleted_bootstrap_roles = await delete_orphan_bootstrap_roles(ctx.session)
        await delete_workspace(ctx.session, workspace_id)

    # Dispatch event after transaction
    await dispatch(
        [
            WorkspaceEvent(
                event_name="workspace:reset",
                client_id=workspace_id,
                workspace_id=workspace_id,
            )
        ]
    )

    return {
        "workspace_id": workspace_id,
        "delete_orphan_bootstrap_users": should_delete_orphan_bootstrap_users,
        "deleted_orphan_bootstrap_roles": deleted_bootstrap_roles,
    }
