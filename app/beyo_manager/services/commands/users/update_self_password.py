import bcrypt
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.users.requests.update_self_password_request import (
    parse_update_self_password_request,
)
from beyo_manager.services.context import ServiceContext


async def update_self_password(ctx: ServiceContext) -> dict:
    request = parse_update_self_password_request(ctx.incoming_data)

    async with ctx.session.begin():
        user = await ctx.session.scalar(
            select(User).where(User.client_id == ctx.user_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if not bcrypt.checkpw(
            request.current_password.encode("utf-8"),
            user.password.encode("utf-8"),
        ):
            raise ValidationError("current_password: current password is incorrect.")

        user.password = bcrypt.hashpw(
            request.new_password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

    return {}
