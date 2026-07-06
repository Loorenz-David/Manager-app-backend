from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailProviderTypeEnum, EmailSecurityEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER
from beyo_manager.services.commands.emails.create_email_connection import create_email_connection
from beyo_manager.services.commands.emails.delete_email_connection import delete_email_connection
from beyo_manager.services.commands.emails.sync_email_connection import sync_email_connection
from beyo_manager.services.commands.emails.test_email_connection import test_email_connection
from beyo_manager.services.commands.emails.update_email_connection import update_email_connection
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.emails.get_email_connection import get_email_connection
from beyo_manager.services.queries.emails.list_email_connections import list_email_connections
from beyo_manager.services.run_service import run_service

router = APIRouter()


class EmailConnectionBody(BaseModel):
    email_address: str
    display_name: str | None = None
    provider_type: EmailProviderTypeEnum = EmailProviderTypeEnum.SMTP_IMAP
    smtp_host: str
    smtp_port: int
    smtp_security: EmailSecurityEnum
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int
    imap_security: EmailSecurityEnum
    imap_username: str
    imap_password: str
    inbox_folder: str = "INBOX"


class UpdateEmailConnectionBody(BaseModel):
    display_name: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: EmailSecurityEnum | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    imap_security: EmailSecurityEnum | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    inbox_folder: str | None = None


async def _run(command, incoming_data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(
        command,
        ServiceContext(identity=claims, incoming_data=incoming_data, session=session),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("")
async def create_email_connection_route(
    body: EmailConnectionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(create_email_connection, body.model_dump(), claims, session)


@router.get("")
async def list_email_connections_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
    owner_user_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    outcome = await run_service(
        list_email_connections,
        ServiceContext(
            identity=claims,
            incoming_data={},
            query_params={"owner_user_id": owner_user_id, "limit": limit, "offset": offset},
            session=session,
        ),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.get("/{connection_id}")
async def get_email_connection_route(
    connection_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_email_connection, {"connection_client_id": connection_id}, claims, session)


@router.put("/{connection_id}")
async def update_email_connection_route(
    connection_id: str,
    body: UpdateEmailConnectionBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        update_email_connection,
        {**body.model_dump(), "connection_client_id": connection_id},
        claims,
        session,
    )


@router.delete("/{connection_id}")
async def delete_email_connection_route(
    connection_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_email_connection, {"connection_client_id": connection_id}, claims, session)


@router.post("/{connection_id}/test")
async def test_email_connection_route(
    connection_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(test_email_connection, {"connection_client_id": connection_id}, claims, session)


@router.post("/{connection_id}/sync")
async def sync_email_connection_route(
    connection_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(sync_email_connection, {"connection_client_id": connection_id}, claims, session)
