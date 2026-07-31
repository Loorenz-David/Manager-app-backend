from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.users.serializers import serialize_user_profile
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import (
    CLOCK_IN_CODE_INDEX_NAME,
    UserWorkProfile,
)
from beyo_manager.models.tables.workspaces.workspace_membership import WorkspaceMembership
from beyo_manager.services.commands.users.requests.update_user_admin_request import (
    parse_update_user_admin_request,
)
from beyo_manager.services.context import ServiceContext


_WORK_PROFILE_FIELDS = (
    "salary_per_hour_before_tax",
    "salary_per_hour_after_tax",
    "clock_in_code",
)
_CLOCK_IN_CODE_TAKEN = (
    "Clock-in code is already in use in this workspace and may belong to an inactive worker."
)


async def update_user_admin(ctx: ServiceContext) -> dict:
    request = parse_update_user_admin_request(ctx.incoming_data)

    async with ctx.session.begin():
        membership = await ctx.session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ctx.workspace_id,
                WorkspaceMembership.user_id == request.user_client_id,
                WorkspaceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise NotFound("User not found in workspace.")

        user = await ctx.session.scalar(
            select(User).where(User.client_id == request.user_client_id)
        )
        if user is None:
            raise NotFound("User not found.")

        if request.email is not None and request.email != user.email:
            conflict = await ctx.session.scalar(
                select(User).where(
                    User.email == request.email,
                    User.client_id != request.user_client_id,
                )
            )
            if conflict is not None:
                raise ConflictError("Email is already in use.")
            user.email = request.email

        if "phone_number" in ctx.incoming_data:
            user.phone_number = request.phone_number

        if "profile_picture" in ctx.incoming_data:
            user.profile_picture = request.profile_picture

        work_profile = await ctx.session.scalar(
            select(UserWorkProfile).where(
                UserWorkProfile.user_id == request.user_client_id,
                UserWorkProfile.workspace_id == ctx.workspace_id,
            )
        )
        touches_work_profile = any(f in ctx.incoming_data for f in _WORK_PROFILE_FIELDS)
        created_work_profile = False
        if work_profile is None and touches_work_profile:
            work_profile = UserWorkProfile(
                user_id=request.user_client_id,
                workspace_id=ctx.workspace_id,
                created_by_id=ctx.user_id,
            )
            created_work_profile = True
            ctx.session.add(work_profile)
        if work_profile is not None:
            if "salary_per_hour_before_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_before_tax = request.salary_per_hour_before_tax
            if "salary_per_hour_after_tax" in ctx.incoming_data:
                work_profile.salary_per_hour_after_tax = request.salary_per_hour_after_tax
            if "clock_in_code" in ctx.incoming_data:
                await _assign_clock_in_code(ctx, work_profile, request.clock_in_code)
            if touches_work_profile and not created_work_profile:
                # users README: updated_by_id is required on every update command
                # (nullable only at creation time).
                work_profile.updated_by_id = ctx.user_id

    return {"user": serialize_user_profile(user, work_profile)}


async def _assign_clock_in_code(
    ctx: ServiceContext,
    work_profile: UserWorkProfile,
    clock_in_code: str | None,
) -> None:
    """Set or clear the worker's shop-floor clock code, workspace-unique while set."""
    if clock_in_code is not None:
        taken = await ctx.session.scalar(
            select(UserWorkProfile.client_id).where(
                UserWorkProfile.workspace_id == ctx.workspace_id,
                UserWorkProfile.clock_in_code == clock_in_code,
                UserWorkProfile.user_id != work_profile.user_id,
            )
        )
        if taken is not None:
            raise ConflictError(_CLOCK_IN_CODE_TAKEN)

    work_profile.clock_in_code = clock_in_code
    try:
        # The pre-check above loses to a concurrent assignment of the same code;
        # the partial unique index is the real arbiter, so flush inside the
        # command and translate its error into the same friendly 409.
        await ctx.session.flush()
    except IntegrityError as exc:
        if CLOCK_IN_CODE_INDEX_NAME in str(exc.orig):
            raise ConflictError(_CLOCK_IN_CODE_TAKEN) from exc
        raise
