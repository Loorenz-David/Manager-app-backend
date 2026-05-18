"""CMD-3: Soft-delete a Customer."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_delete_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_customer(ctx: ServiceContext) -> dict:
    """Soft-delete a Customer without cascading deletes."""
    request = parse_delete_customer_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Customer).where(
                Customer.workspace_id == ctx.workspace_id,
                Customer.client_id == request.client_id,
                Customer.is_deleted.is_(False),
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise NotFound("Customer not found.")

        customer.is_deleted = True
        customer.deleted_at = datetime.now(timezone.utc)
        customer.deleted_by_id = ctx.user_id

    return {}
