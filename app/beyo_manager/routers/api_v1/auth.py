from decimal import Decimal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims, require_roles
from beyo_manager.routers.utils.rate_limit import ip_rate_limit
from beyo_manager.routers.utils.roles import ADMIN
from beyo_manager.services.commands.auth.logout_user import logout_user
from beyo_manager.services.commands.auth.refresh_token import refresh_token
from beyo_manager.services.commands.auth.sign_in_user import sign_in_user
from beyo_manager.services.commands.users.register_user import register_user
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()
_REFRESH_COOKIE = "refresh_token"


class SignInBody(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str
    app_scope: str = "admin"


class RegisterUserBody(BaseModel):
    username: str
    email: str
    password: str
    phone_number: str | None = None
    role_id: str | None = None
    role_name: str | None = None
    working_section_ids: list[str] = []
    salary_per_hour_before_tax: Decimal | None = None
    salary_per_hour_after_tax: Decimal | None = None


@router.post("/sign-in")
async def sign_in_route(
    body: SignInBody,
    response: Response,
    session: AsyncSession = Depends(get_db),
    _rate: None = Depends(ip_rate_limit(10, 60, "sign-in")),
):
    outcome = await run_service(sign_in_user, ServiceContext(identity={}, incoming_data=body.model_dump(), session=session))
    if not outcome.success:
        return build_err(outcome.error)
    data = dict(outcome.data)
    refresh_token_value = data.pop("_refresh_token")
    response.set_cookie(_REFRESH_COOKIE, refresh_token_value, httponly=True, secure=True, samesite="lax")
    return build_ok(data)


@router.post("/logout")
async def logout_route(
    request: Request,
    response: Response,
    claims: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(identity=claims, incoming_data={"refresh_token": request.cookies.get(_REFRESH_COOKIE)}, session=session)
    outcome = await run_service(logout_user, ctx)
    response.delete_cookie(_REFRESH_COOKIE, httponly=True, samesite="lax")
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("/refresh")
async def refresh_route(request: Request, session: AsyncSession = Depends(get_db)):
    ctx = ServiceContext(identity={}, incoming_data={"refresh_token": request.cookies.get(_REFRESH_COOKIE)}, session=session)
    outcome = await run_service(refresh_token, ctx)
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("/register")
async def register_user_route(
    body: RegisterUserBody,
    claims: dict = Depends(require_roles([ADMIN])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(register_user, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
