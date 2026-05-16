from sqlalchemy import select

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.users.requests.update_self_profile_request import (
    parse_update_self_profile_request,
)
from beyo_manager.services.context import ServiceContext


async def update_self_profile(ctx: ServiceContext) -> dict:
    request = parse_update_self_profile_request(ctx.incoming_data)

    async with ctx.session.begin():
        user = await ctx.session.scalar(
            select(User).where(User.client_id == ctx.user_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if request.email is not None and request.email != user.email:
            conflict = await ctx.session.scalar(
                select(User).where(
                    User.email == request.email,
                    User.client_id != ctx.user_id,
                )
            )
            if conflict is not None:
                raise ConflictError("Email is already in use.")
            user.email = request.email

        if "phone_number" in ctx.incoming_data:
            user.phone_number = request.phone_number

        if "profile_picture" in ctx.incoming_data:
            user.profile_picture = request.profile_picture

    return {"user": serialize_user_profile(user)}
