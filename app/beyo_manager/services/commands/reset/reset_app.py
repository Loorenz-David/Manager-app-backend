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
from beyo_manager.services.commands.reset.phases.delete_working_section_supported_issue_types import (
    delete_working_section_supported_issue_types,
)
from beyo_manager.services.commands.reset.phases.delete_working_section_dependencies import (
    delete_working_section_dependencies,
)
from beyo_manager.services.commands.reset.phases.delete_working_sections import delete_working_sections
from beyo_manager.services.commands.reset.phases.delete_issue_severities import delete_issue_severities
from beyo_manager.services.commands.reset.phases.delete_issue_types import delete_issue_types
from beyo_manager.services.commands.reset.phases.delete_item_categories import delete_item_categories
from beyo_manager.services.commands.reset.phases.delete_task_history_records import (
    delete_task_history_records,
)
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
from beyo_manager.services.commands.reset.phases.delete_tasks import delete_tasks
from beyo_manager.services.commands.reset.phases.delete_upholstery_inventories import (
    delete_upholstery_inventories,
)
from beyo_manager.services.commands.reset.phases.delete_upholsteries import delete_upholsteries
from beyo_manager.services.commands.reset.phases.delete_static_costs import delete_static_costs
from beyo_manager.services.commands.reset.phases.delete_working_section_memberships import (
    delete_working_section_memberships,
)
from beyo_manager.services.commands.reset.phases.delete_user_shift_state_records import (
    delete_user_shift_state_records,
)
from beyo_manager.services.commands.reset.phases.delete_workspace_memberships import (
    delete_workspace_memberships,
)
from beyo_manager.services.commands.reset.phases.delete_users import delete_orphan_bootstrap_users
from beyo_manager.services.commands.reset.phases.delete_roles import delete_orphan_bootstrap_roles
from beyo_manager.services.commands.reset.phases.delete_audit_logs import delete_audit_logs
from beyo_manager.services.commands.reset.phases.delete_pending_uploads import delete_pending_uploads
from beyo_manager.services.commands.reset.phases.delete_workspace_roles import delete_workspace_roles
from beyo_manager.services.commands.reset.phases.delete_workspace import delete_workspace


async def reset_app(ctx: ServiceContext) -> dict:
    """
    Reset/clear all workspace data (bootstrap and operational).
    
    Deletes all workspace-scoped data in reverse dependency order:
    
    Bootstrap data:
    1. issue_category_configs
    2. working_section_item_categories
    3. working_section_supported_issue_types
    4. working_section_dependencies
    5. working_sections
    6. issue_severities
    7. issue_types
    8. item_categories
    
    Task system:
    9. task_history_records
    10. task_events
    11. step_state_records
    12. task_step_assignment_records
    13. task_step_dependencies
    14. task_steps
    15. task_items
    16. tasks
    
    Upholstery:
    17. upholstery_inventories
    18. upholsteries
    
    Other operational data:
    20. static_costs
    21. working_section_memberships
    22. user_shift_state_records
    
    Core workspace structures:
    23. workspace_memberships (users remain global and unaffected)
    24. audit_logs
    25. workspace_roles
    26. workspace
    
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
        # Bootstrap data
        await delete_issue_category_configs(ctx.session, workspace_id)
        await delete_working_section_item_categories(ctx.session, workspace_id)
        await delete_working_section_supported_issue_types(ctx.session, workspace_id)
        await delete_working_section_dependencies(ctx.session, workspace_id)
        await delete_working_sections(ctx.session, workspace_id)
        await delete_issue_severities(ctx.session, workspace_id)
        await delete_issue_types(ctx.session, workspace_id)
        await delete_item_categories(ctx.session, workspace_id)
        
        # Task system data
        await delete_task_history_records(ctx.session, workspace_id)
        await delete_task_events(ctx.session, workspace_id)
        await delete_step_state_records(ctx.session, workspace_id)
        await delete_task_step_assignment_records(ctx.session, workspace_id)
        await delete_task_step_dependencies(ctx.session, workspace_id)
        await delete_task_steps(ctx.session, workspace_id)
        await delete_task_items(ctx.session, workspace_id)
        await delete_tasks(ctx.session, workspace_id)
        
        # Upholstery data
        await delete_upholstery_inventories(ctx.session, workspace_id)
        await delete_upholsteries(ctx.session, workspace_id)
        
        # Other operational data
        await delete_static_costs(ctx.session, workspace_id)
        await delete_working_section_memberships(ctx.session, workspace_id)
        await delete_user_shift_state_records(ctx.session, workspace_id)
        
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
