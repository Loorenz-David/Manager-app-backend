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


def _coalesce_key(event):
    name = event.event_name
    if name.startswith("stock_report_item:"):
        return ("row", event.client_id, name.rsplit(":", 1)[1])
    if name.startswith("stock_task_assignment:"):
        return ("assignment", event.client_id, name.rsplit(":", 1)[1])
    return ("other", id(event))


def coalesce_stock_report_events(events, *, initial_row_values):
    """MC-19's net-change rule (master plan §6.5, phase 8), one request wide.

    Per row (`stock_report_item:*`, keyed by the row's own `client_id`): keep only the
    **last** `:updated` event, and drop it entirely when its payload equals the row's
    initial values (a self-healing or no-op sequence emitted nothing observable) or
    when the same row also carries a `:created` or a `:deleted` in this request (a
    created-then-touched or about-to-be-deleted row gets only its one lifecycle
    event — the `:deleted` half also covers a 13A request that deletes several rows
    of one group, shifting a later row before deleting it).

    Per assignment (`stock_task_assignment:*`, keyed by `(client_id, kind)`): keep
    only the last event of each kind.

    First-seen order is preserved: a kept event's position in the result is the
    position at which its `(entity, client_id, kind)` key first appeared in `events`,
    never the position of the occurrence whose payload was kept.
    """
    last_by_key: dict[tuple, object] = {}
    first_index: dict[tuple, int] = {}
    row_created: set[str] = set()
    row_deleted: set[str] = set()

    for index, event in enumerate(events):
        key = _coalesce_key(event)
        if key[0] == "row":
            if key[2] == "created":
                row_created.add(key[1])
            elif key[2] == "deleted":
                row_deleted.add(key[1])
        last_by_key[key] = event
        first_index.setdefault(key, index)

    result = []
    for key in sorted(last_by_key, key=lambda candidate: first_index[candidate]):
        entity, client_id, kind = key
        event = last_by_key[key]
        if entity == "row" and kind == "updated":
            if client_id in row_created or client_id in row_deleted:
                continue
            initial = initial_row_values.get(client_id)
            if initial is not None and event.extra == initial:
                continue
        result.append(event)
    return result
