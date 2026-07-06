from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER
from beyo_manager.services.commands.emails.create_email_template import create_email_template
from beyo_manager.services.commands.emails.delete_email_template import delete_email_template
from beyo_manager.services.commands.emails.update_email_template import update_email_template
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.emails.get_email_template import get_email_template
from beyo_manager.services.queries.emails.list_email_templates import list_email_templates
from beyo_manager.services.run_service import run_service

router = APIRouter()


class CreateEmailTemplateBody(BaseModel):
    name: str
    subject: str
    content: str
    topic: EmailTemplateTopicEnum
    template_type: EmailTemplateTypeEnum


class UpdateEmailTemplateBody(BaseModel):
    name: str | None = None
    subject: str | None = None
    content: str | None = None
    topic: EmailTemplateTopicEnum | None = None
    template_type: EmailTemplateTypeEnum | None = None


async def _run(command, incoming_data: dict, claims: dict, session: AsyncSession, query_params: dict | None = None):
    outcome = await run_service(
        command,
        ServiceContext(
            identity=claims,
            incoming_data=incoming_data,
            query_params=query_params or {},
            session=session,
        ),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.put("")
async def create_email_template_route(
    body: CreateEmailTemplateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(create_email_template, body.model_dump(), claims, session)


@router.get("")
async def list_email_templates_route(
    topic: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_email_templates,
        {},
        claims,
        session,
        query_params={"topic": topic, "limit": limit, "offset": offset},
    )


@router.get("/{template_id}")
async def get_email_template_route(
    template_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_email_template, {"template_client_id": template_id}, claims, session)


@router.patch("/{template_id}")
async def update_email_template_route(
    template_id: str,
    body: UpdateEmailTemplateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        update_email_template,
        {**body.model_dump(), "template_client_id": template_id},
        claims,
        session,
    )


@router.delete("/{template_id}")
async def delete_email_template_route(
    template_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_email_template, {"template_client_id": template_id}, claims, session)
