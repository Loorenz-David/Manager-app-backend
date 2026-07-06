from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.services.context import ServiceContext


async def resolve_email_connection(
    ctx: ServiceContext,
    connection_client_id: str | None,
) -> EmailConnection:
    if connection_client_id:
        return await _load_by_id(ctx.session, ctx.workspace_id, connection_client_id)
    return await _load_for_user(ctx.session, ctx.workspace_id, ctx.user_id)


async def resolve_email_connection_for_actor(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
    connection_client_id: str | None,
) -> EmailConnection:
    if connection_client_id:
        return await _load_by_id(session, workspace_id, connection_client_id)
    return await _load_for_user(session, workspace_id, user_id)


async def _load_by_id(
    session: AsyncSession,
    workspace_id: str,
    connection_client_id: str,
) -> EmailConnection:
    result = await session.execute(
        select(EmailConnection).where(
            EmailConnection.workspace_id == workspace_id,
            EmailConnection.client_id == connection_client_id,
            EmailConnection.deleted_at.is_(None),
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise NotFound("Email connection not found.")
    return connection


async def _load_for_user(
    session: AsyncSession,
    workspace_id: str,
    user_id: str,
) -> EmailConnection:
    result = await session.execute(
        select(EmailConnection).where(
            EmailConnection.workspace_id == workspace_id,
            EmailConnection.owner_user_id == user_id,
            EmailConnection.deleted_at.is_(None),
            EmailConnection.status == EmailConnectionStatusEnum.ACTIVE.value,
        )
    )
    connections = list(result.scalars().all())
    if not connections:
        raise NotFound("No active email connection found for your account.")
    if len(connections) > 1:
        raise ValidationError(
            "Multiple email connections found for your account. Specify connection_client_id."
        )
    return connections[0]
