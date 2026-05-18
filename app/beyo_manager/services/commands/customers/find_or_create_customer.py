"""CMD-4: Find existing Customer by normalized email/phone or create one."""

from sqlalchemy import or_, select

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import (
    _normalize_email,
    _normalize_phone,
    parse_find_or_create_customer_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def find_or_create_customer(ctx: ServiceContext) -> dict:
    """Return an existing active customer matched by email/phone, or create one."""
    request = parse_find_or_create_customer_request(ctx.incoming_data)

    normalized_email = _normalize_email(request.primary_email)
    normalized_phone = _normalize_phone(request.primary_phone_number)

    if normalized_email is None and normalized_phone is None:
        raise ValidationError("At least one of primary_email or primary_phone_number must be provided.")

    async with maybe_begin(ctx.session):
        lookup_conditions = []
        if normalized_email is not None:
            lookup_conditions.append(Customer.primary_email_normalized == normalized_email)
        if normalized_phone is not None:
            lookup_conditions.append(Customer.primary_phone_number_normalized == normalized_phone)

        existing_result = await ctx.session.execute(
            select(Customer)
            .where(
                Customer.workspace_id == ctx.workspace_id,
                Customer.is_deleted.is_(False),
                or_(*lookup_conditions),
            )
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            return {"client_id": existing.client_id, "was_created": False}

        customer = Customer(
            workspace_id=ctx.workspace_id,
            display_name=request.display_name,
            customer_type=request.customer_type,
            primary_email=request.primary_email,
            primary_phone_number=request.primary_phone_number,
            primary_email_normalized=normalized_email,
            primary_phone_number_normalized=normalized_phone,
            address=request.address,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(customer)
        await ctx.session.flush()

    return {"client_id": customer.client_id, "was_created": True}
