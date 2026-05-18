"""QUERY-1 list customers | QUERY-2 get customer detail with linked items."""

from sqlalchemy import func, select

from beyo_manager.domain.customers.serializers import serialize_customer, serialize_customer_detail
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_FILTER_COLUMNS = {
    "display_name": Customer.display_name,
    "primary_email": Customer.primary_email,
    "primary_phone_number": Customer.primary_phone_number,
}


async def list_customers(ctx: ServiceContext) -> dict:
    """List customers with optional q filtering and offset pagination."""
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")

    stmt = select(Customer).where(
        Customer.workspace_id == ctx.workspace_id,
        Customer.is_deleted.is_(False),
    )

    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_FILTER_COLUMNS)
    stmt = stmt.order_by(Customer.created_at.desc()).offset(offset).limit(limit + 1)

    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "customers_pagination": {
            "items": [serialize_customer(c) for c in page],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_customer(ctx: ServiceContext) -> dict:
    """Get one customer and include linked items via tasks -> task_items."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Customer).where(
            Customer.workspace_id == ctx.workspace_id,
            Customer.client_id == client_id,
            Customer.is_deleted.is_(False),
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise NotFound("Customer not found.")

    items_result = await ctx.session.execute(
        select(Item)
        .join(TaskItem, TaskItem.item_id == Item.client_id)
        .join(Task, Task.client_id == TaskItem.task_id)
        .where(
            Task.customer_id == customer.client_id,
            Task.workspace_id == ctx.workspace_id,
            Task.is_deleted.is_(False),
            TaskItem.removed_at.is_(None),
            Item.workspace_id == ctx.workspace_id,
            Item.is_deleted.is_(False),
        )
        .distinct()
        .order_by(Item.created_at.desc())
    )
    items = items_result.scalars().all()

    issue_counts: dict[str, int] = {}
    if items:
        item_ids = [item.client_id for item in items]
        count_result = await ctx.session.execute(
            select(ItemIssue.item_id, func.count(ItemIssue.client_id).label("cnt"))
            .where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.item_id.in_(item_ids),
                ItemIssue.is_deleted.is_(False),
            )
            .group_by(ItemIssue.item_id)
        )
        issue_counts = {row.item_id: row.cnt for row in count_result}

    return {"customer": serialize_customer_detail(customer, items, issue_counts)}
