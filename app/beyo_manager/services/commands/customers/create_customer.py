"""CMD-1: Create a Customer."""

from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_create_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_customer(ctx: ServiceContext) -> dict:
    """Create a new Customer with normalized contact fields."""
    request = parse_create_customer_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        customer = Customer(
            workspace_id=ctx.workspace_id,
            display_name=request.display_name,
            customer_type=request.customer_type,
            primary_email=request.primary_email,
            primary_phone_number=request.primary_phone_number,
            primary_email_normalized=request.primary_email_normalized,
            primary_phone_number_normalized=request.primary_phone_number_normalized,
            address=request.address,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(customer)
        await ctx.session.flush()

    return {"client_id": customer.client_id}
