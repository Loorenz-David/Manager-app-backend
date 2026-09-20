from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

# H12: `build_workspace_event` expects an object with `.client_id`, but these builders
# are registered (master plan §6.5) with a `client_id: str` parameter — the moving
# assignment/row's client id, not an entity. `WorkspaceEvent` is constructed directly
# here instead of inventing a shim object for `build_workspace_event`.


def build_stock_report_item_updated_event(*, client_id, workspace_id, values):
    priority = values["priority"]
    return WorkspaceEvent(
        event_name="stock_report_item:updated",
        client_id=client_id,
        workspace_id=workspace_id,
        extra={
            "quantity_requested": values["quantity_requested"],
            "quantity_in_queue": values["quantity_in_queue"],
            "quantity_in_progress": values["quantity_in_progress"],
            "quantity_awaiting": values["quantity_awaiting"],
            # H9: RETURNING yields a StockReportPriorityEnum member; event payloads are
            # never serialized by the dispatcher, so an enum here would pass every test
            # in this batch (dispatch is monkeypatched away) and fail in production.
            "priority": priority.value if priority is not None else None,
            "priority_order": values["priority_order"],
        },
    )


def build_stock_task_assignment_event(
    kind, *, client_id, workspace_id, stock_report_item_id, task_id, state
):
    return WorkspaceEvent(
        event_name=f"stock_task_assignment:{kind}",
        client_id=client_id,
        workspace_id=workspace_id,
        extra={
            "stock_report_item_id": stock_report_item_id,
            "task_id": task_id,
            "state": state,
        },
    )
