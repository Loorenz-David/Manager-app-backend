"""CMD-2: Update Customer fields with null-vs-omit semantics."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_update_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "display_name",
    "customer_type",
    "status",
    "primary_email",
    "primary_phone_number",
    "address",
}


async def update_customer(ctx: ServiceContext) -> dict:
    """Update only fields explicitly provided in the request payload."""
    request = parse_update_customer_request(ctx.incoming_data)

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

        for field_name in _DIRECT_FIELDS:
            if field_name in request.model_fields_set:
                setattr(customer, field_name, getattr(request, field_name))

        if "primary_email" in request.model_fields_set:
            customer.primary_email_normalized = request.primary_email
        if "primary_phone_number" in request.model_fields_set:
            customer.primary_phone_number_normalized = request.primary_phone_number

        customer.updated_at = datetime.now(timezone.utc)
        customer.updated_by_id = ctx.user_id

    return {"client_id": customer.client_id}
