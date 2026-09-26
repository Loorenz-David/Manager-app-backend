from beyo_manager.config import settings
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent
from beyo_manager.errors.validation import ValidationError
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
from beyo_manager.services.commands.reset.phases.delete_issue_types import delete_issue_types
from beyo_manager.services.commands.reset.phases.delete_item_category_issue_types import (
    delete_item_category_issue_types,
)
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
from beyo_manager.services.commands.reset.phases.delete_stock_report_repair_records import delete_stock_report_repair_records
from beyo_manager.services.commands.reset.phases.delete_stock_task_assignments import delete_stock_task_assignments
from beyo_manager.services.commands.reset.phases.delete_stock_report_history_records import delete_stock_report_history_records
from beyo_manager.services.commands.reset.phases.delete_stock_report_items import delete_stock_report_items
from beyo_manager.services.commands.reset.phases.delete_stock_report_item_snapshots import delete_stock_report_item_snapshots
from beyo_manager.services.commands.reset.phases.delete_stock_report_snapshot_versions import delete_stock_report_snapshot_versions


async def reset_app(ctx: ServiceContext) -> dict:
    """
    Reset/clear all workspace data (bootstrap and operational).
    
    Deletes all workspace-scoped data in reverse dependency order:

    Stock report:
    1. stock_report_repair_records
    2. stock_task_assignments
    3. stock_report_history_records
    4. stock_report_item_snapshots
    5. stock_report_snapshot_versions
    6. stock_report_items

    Task system:
    5. task_events
    6. task_step_assignment_records
    7. task_step_dependencies
    8. step_state_records
    9. task_steps
    10. task_items
    11. task_notes
    12. tasks

    Bootstrap data:
    13. item_category_issue_types
    14. working_section_item_categories
    15. working_section_supported_issue_types
    16. working_section_dependencies
    17. user_section_daily_work_stats
    18. working_section_daily_work_stats
    19. working_section_memberships
    20. working_sections
    21. item_issues
    22. item_upholstery_requirements
    23. item_upholsteries
    24. items
    25. issue_types
    26. item_categories
    
    Upholstery:
    28. upholstery_inventories
    29. upholsteries
    
    Other operational data:
    30. static_costs
    31. user_shift_state_records
    32. customers
    33. user_work_profiles
    34. user_daily_work_stats
    35. user_lifetime_stats
    
    Core workspace structures:
    36. workspace_memberships (users remain global and unaffected)
    37. audit_logs
    38. workspace_roles
    39. workspace
    
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
        await delete_stock_report_repair_records(ctx.session, workspace_id)
        await delete_stock_task_assignments(ctx.session, workspace_id)
        await delete_stock_report_history_records(ctx.session, workspace_id)
        await delete_stock_report_item_snapshots(ctx.session, workspace_id)
        await delete_stock_report_snapshot_versions(ctx.session, workspace_id)
        await delete_stock_report_items(ctx.session, workspace_id)
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
        await delete_item_category_issue_types(ctx.session, workspace_id)
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
