from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.commands.cases.add_participant import add_participant
from beyo_manager.services.commands.cases.create_case import create_case
from beyo_manager.services.commands.cases.create_conversation import create_conversation
from beyo_manager.services.commands.cases.edit_message import edit_message
from beyo_manager.services.commands.cases.link_entity import link_entity
from beyo_manager.services.commands.cases.mark_read import mark_read
from beyo_manager.services.commands.cases.remove_participant import remove_participant
from beyo_manager.services.commands.cases.send_message import send_message
from beyo_manager.services.commands.cases.soft_delete_message import soft_delete_message
from beyo_manager.services.commands.cases.unlink_entity import unlink_entity
from beyo_manager.services.commands.cases.update_case import update_case
from beyo_manager.services.commands.cases.update_case_state import update_case_state
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.cases.get_case import get_case
from beyo_manager.services.queries.cases.get_conversation import get_conversation
from beyo_manager.services.queries.cases.get_unread_counts import get_unread_counts
from beyo_manager.services.queries.cases.list_cases import list_cases
from beyo_manager.services.queries.cases.list_linked_entities import list_linked_entities
from beyo_manager.services.queries.cases.list_messages import list_messages
from beyo_manager.services.queries.cases.list_participants import list_participants
from beyo_manager.services.run_service import run_service

router = APIRouter()


class CreateCaseBody(BaseModel):
    client_id: str | None = None
    case_type_id: str | None = None
    type_label: str | None = None


class UpdateCaseBody(BaseModel):
    case_client_id: str
    case_type_id: str | None = None
    type_label: str | None = None


class UpdateCaseStateBody(BaseModel):
    case_client_id: str
    new_state: str


class LinkEntityBody(BaseModel):
    case_client_id: str
    entity_type: str
    entity_client_id: str
    role: str


class AddParticipantBody(BaseModel):
    case_client_id: str
    user_ids: list[str]


class CreateConversationBody(BaseModel):
    client_id: str | None = None
    case_client_id: str


class SendMessageBody(BaseModel):
    client_id: str | None = None
    conversation_client_id: str
    content: list
    plain_text: str = ""


class EditMessageBody(BaseModel):
    message_client_id: str
    content: list
    plain_text: str = ""


class MarkReadBody(BaseModel):
    case_participant_client_id: str
    up_to_message_seq: int


async def _run(command, data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(command, ServiceContext(identity=claims, incoming_data=data, session=session))
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("")
async def create_case_route(body: CreateCaseBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(create_case, body.model_dump(), claims, session)


@router.get("")
async def list_cases_route(state: str | None = None, created_by_id: str | None = None, entity_type: str | None = None, entity_client_id: str | None = None, offset: int = 0, limit: int = 50, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(list_cases, {"state": state, "created_by_id": created_by_id, "entity_type": entity_type, "entity_client_id": entity_client_id, "offset": offset, "limit": limit}, claims, session)


@router.get("/unread-counts")
async def unread_counts_route(conversation_client_ids: str | None = None, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    ids = conversation_client_ids.split(",") if conversation_client_ids else None
    return await _run(get_unread_counts, {"conversation_client_ids": ids}, claims, session)


@router.get("/{case_client_id}")
async def get_case_route(case_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(get_case, {"case_client_id": case_client_id}, claims, session)


@router.patch("/{case_client_id}")
async def update_case_route(case_client_id: str, body: UpdateCaseBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(update_case, {**body.model_dump(), "case_client_id": case_client_id}, claims, session)


@router.patch("/{case_client_id}/state")
async def update_case_state_route(case_client_id: str, body: UpdateCaseStateBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(update_case_state, {**body.model_dump(), "case_client_id": case_client_id}, claims, session)


@router.post("/{case_client_id}/links")
async def link_entity_route(case_client_id: str, body: LinkEntityBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(link_entity, {**body.model_dump(), "case_client_id": case_client_id}, claims, session)


@router.delete("/links/{case_link_client_id}")
async def unlink_entity_route(case_link_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(unlink_entity, {"case_link_client_id": case_link_client_id}, claims, session)


@router.get("/{case_client_id}/links")
async def list_links_route(case_client_id: str, entity_type: str | None = None, role: str | None = None, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(list_linked_entities, {"case_client_id": case_client_id, "entity_type": entity_type, "role": role}, claims, session)


@router.post("/{case_client_id}/participants")
async def add_participant_route(case_client_id: str, body: AddParticipantBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(add_participant, {**body.model_dump(), "case_client_id": case_client_id}, claims, session)


@router.delete("/participants/{case_participant_client_id}")
async def remove_participant_route(case_participant_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(remove_participant, {"case_participant_client_id": case_participant_client_id}, claims, session)


@router.get("/{case_client_id}/participants")
async def list_participants_route(case_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(list_participants, {"case_client_id": case_client_id}, claims, session)


@router.post("/{case_client_id}/conversations")
async def create_conversation_route(case_client_id: str, body: CreateConversationBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(create_conversation, {**body.model_dump(), "case_client_id": case_client_id}, claims, session)


@router.get("/conversations/{conversation_client_id}")
async def get_conversation_route(conversation_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(get_conversation, {"conversation_client_id": conversation_client_id}, claims, session)


@router.post("/conversations/{conversation_client_id}/messages")
async def send_message_route(conversation_client_id: str, body: SendMessageBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(send_message, {**body.model_dump(), "conversation_client_id": conversation_client_id}, claims, session)


@router.get("/conversations/{conversation_client_id}/messages")
async def list_messages_route(conversation_client_id: str, before_seq: int | None = None, limit: int = 50, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(list_messages, {"conversation_client_id": conversation_client_id, "before_seq": before_seq, "limit": limit}, claims, session)


@router.patch("/messages/{message_client_id}")
async def edit_message_route(message_client_id: str, body: EditMessageBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(edit_message, {**body.model_dump(), "message_client_id": message_client_id}, claims, session)


@router.delete("/messages/{message_client_id}")
async def soft_delete_message_route(message_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(soft_delete_message, {"message_client_id": message_client_id}, claims, session)


@router.post("/messages/mark-read")
async def mark_read_route(body: MarkReadBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(mark_read, body.model_dump(), claims, session)
