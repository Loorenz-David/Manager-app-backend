from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.emails.mark_email_thread_read import mark_email_thread_read
from beyo_manager.services.commands.emails.send_email import send_email
from beyo_manager.services.commands.emails.send_email_batch import send_email_batch
from beyo_manager.services.commands.emails.sync_email_threads_batch_targeted import (
    sync_email_threads_batch_targeted,
)
from beyo_manager.services.commands.emails.requests.send_email_batch_request import (
    SendEmailBatchRequest,
)
from beyo_manager.services.commands.emails.requests.sync_thread_targeted_request import (
    SyncThreadsBatchTargetedRequest,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.emails.get_email_thread import get_email_thread
from beyo_manager.services.queries.emails.get_email_unread_counts import get_email_unread_counts
from beyo_manager.services.queries.emails.list_email_messages import list_email_messages
from beyo_manager.services.queries.emails.list_email_thread_topic_presets import (
    list_email_thread_topic_presets,
)
from beyo_manager.services.queries.emails.list_email_threads import list_email_threads
from beyo_manager.services.run_service import run_service

router = APIRouter()


class SendEmailBody(BaseModel):
    connection_client_id: str | None = None
    to_addresses: list[str]
    cc_addresses: list[str] = []
    bcc_addresses: list[str] = []
    subject: str
    text_body: str | None = None
    html_body: str | None = None
    entity_type: str | None = None
    entity_client_id: str | None = None
    major_entity_type: str | None = None
    major_entity_client_id: str | None = None
    topic: str | None = None



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


@router.get("/topic-presets")
async def list_topic_presets_route(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(list_email_thread_topic_presets, {}, claims, session)


@router.get("/unread-count")
async def unread_count_route(
    connection_client_id: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_client_id: str | None = Query(None),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        get_email_unread_counts,
        {},
        claims,
        session,
        query_params={
            "connection_client_id": connection_client_id,
            "entity_type": entity_type,
            "entity_client_id": entity_client_id,
        },
    )


@router.post("/send")
async def send_email_route(
    body: SendEmailBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(send_email, body.model_dump(), claims, session)


@router.post("/batch-send")
async def send_email_batch_route(
    body: SendEmailBatchRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(send_email_batch, body.model_dump(), claims, session)


@router.post("/sync-targeted")
async def sync_email_threads_batch_targeted_route(
    body: SyncThreadsBatchTargetedRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(sync_email_threads_batch_targeted, body.model_dump(), claims, session)


@router.get("")
async def list_email_threads_route(
    connection_client_id: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_client_id: str | None = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_email_threads,
        {},
        claims,
        session,
        query_params={
            "connection_client_id": connection_client_id,
            "entity_type": entity_type,
            "entity_client_id": entity_client_id,
            "unread_only": unread_only,
            "limit": limit,
            "offset": offset,
        },
    )


@router.get("/{thread_id}")
async def get_email_thread_route(
    thread_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_email_thread, {"thread_client_id": thread_id}, claims, session)


@router.post("/{thread_id}/sync")
async def sync_email_thread_targeted_route(
    thread_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        sync_email_threads_batch_targeted,
        {"thread_client_ids": [thread_id]},
        claims,
        session,
    )


@router.get("/{thread_id}/messages")
async def list_email_messages_route(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_email_messages,
        {"thread_client_id": thread_id},
        claims,
        session,
        query_params={"limit": limit, "offset": offset},
    )


@router.post("/{thread_id}/send")
async def reply_email_route(
    thread_id: str,
    body: SendEmailBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    payload = {**body.model_dump(), "thread_client_id": thread_id}
    return await _run(send_email, payload, claims, session)


@router.post("/{thread_id}/read")
async def mark_email_thread_read_route(
    thread_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(mark_email_thread_read, {"thread_client_id": thread_id}, claims, session)
