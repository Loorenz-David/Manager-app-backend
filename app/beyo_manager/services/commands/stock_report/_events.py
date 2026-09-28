from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

# H12: `build_workspace_event` expects an object with `.client_id`, but these builders
# are registered (master plan §6.5) with a `client_id: str` parameter — the moving
# assignment/row's client id, not an entity. `WorkspaceEvent` is constructed directly
# here instead of inventing a shim object for `build_workspace_event`.


def build_stock_report_item_updated_event(*, client_id, workspace_id, values):
    """Four quantity keys. `priority`/`priority_order` left this event on 2026-09-26
    with the snapshot change; they travel on `stock_report_item_snapshot:updated`."""
    return WorkspaceEvent(
        event_name="stock_report_item:updated",
        client_id=client_id,
        workspace_id=workspace_id,
        extra={
            "quantity_requested": values["quantity_requested"],
            "quantity_in_queue": values["quantity_in_queue"],
            "quantity_in_progress": values["quantity_in_progress"],
            "quantity_awaiting": values["quantity_awaiting"],
        },
    )


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def build_stock_report_item_snapshot_updated_event(*, client_id, workspace_id, values):
    """`client_id` is the **snapshot's** id; the row is named in `extra`."""
    return WorkspaceEvent(
        event_name="stock_report_item_snapshot:updated",
        client_id=client_id,
        workspace_id=workspace_id,
        extra={
            "stock_report_item_id": values["stock_report_item_id"],
            "version_id": values["version_id"],
            # H9 again: RETURNING yields the enum member on an ORM-typed column and a
            # plain string on a `text()` statement; both must serialize as the string.
            "priority": _enum_value(values["priority"]),
            "priority_order": values["priority_order"],
            "quantity_missing": values["quantity_missing"],
            "quantity_resolved": values["quantity_resolved"],
            # The two **stored** requested columns (draft versions, 2026-09-28);
            # the effective value is `manual ?? scanner ?? the row's live value`.
            "quantity_requested_scanner": values["quantity_requested_scanner"],
            "quantity_requested_manual": values["quantity_requested_manual"],
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
    if name.startswith("stock_report_item_snapshot:"):
        return ("snapshot", event.client_id, name.rsplit(":", 1)[1])
    if name.startswith("stock_task_assignment:"):
        return ("assignment", event.client_id, name.rsplit(":", 1)[1])
    return ("other", id(event))


def coalesce_stock_report_events(
    events, *, initial_row_values, initial_snapshot_values=None
):
    """MC-19's net-change rule (master plan §6.5, phase 8), one request wide.

    Per row (`stock_report_item:*`, keyed by the row's own `client_id`): keep only the
    **last** `:updated` event, and drop it entirely when its payload equals the row's
    initial values (a self-healing or no-op sequence emitted nothing observable) or
    when the same row also carries a `:created` or a `:deleted` in this request (a
    created-then-touched or about-to-be-deleted row gets only its one lifecycle
    event — the `:deleted` half also covers a 13A request that deletes several rows
    of one group, shifting a later row before deleting it).

    Per snapshot (`stock_report_item_snapshot:*`, keyed by the snapshot's id): the
    same last-wins rule against `initial_snapshot_values` (`_snapshot_values.py`),
    and dropped entirely when the snapshot's **row** carries a `:deleted` in this
    request — the cascade closes the snapshot with its row, and a position shift it
    received on the way out is not something a board should apply.

    Per assignment (`stock_task_assignment:*`, keyed by `(client_id, kind)`): keep
    only the last event of each kind.

    First-seen order is preserved: a kept event's position in the result is the
    position at which its `(entity, client_id, kind)` key first appeared in `events`,
    never the position of the occurrence whose payload was kept.
    """
    initial_snapshot_values = initial_snapshot_values or {}
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
        entity, client_id, *rest = key
        event = last_by_key[key]
        if entity == "row" and rest[0] == "updated":
            if client_id in row_created or client_id in row_deleted:
                continue
            initial = initial_row_values.get(client_id)
            if initial is not None and event.extra == initial:
                continue
        if entity == "snapshot" and rest[0] == "updated":
            if event.extra.get("stock_report_item_id") in row_deleted:
                continue
            initial = initial_snapshot_values.get(client_id)
            if initial is not None and event.extra == initial:
                continue
        result.append(event)
    return result
