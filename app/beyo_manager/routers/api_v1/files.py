from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.commands.files.confirm_upload import confirm_upload
from beyo_manager.services.commands.files.generate_upload_url import generate_upload_url
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.files.get_pending_upload_download_url import get_pending_upload_download_url
from beyo_manager.services.run_service import run_service

router = APIRouter()


class GenerateUploadUrlBody(BaseModel):
    file_name: str
    content_type: str
    use_case: str = "record_attachment"
    file_size_bytes: int | None = None


class ConfirmUploadBody(BaseModel):
    storage_key: str


class PendingUploadDownloadBody(BaseModel):
    pending_upload_client_id: str


async def _run(command, data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(command, ServiceContext(identity=claims, incoming_data=data, session=session))
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("/upload-url")
async def request_upload_url(body: GenerateUploadUrlBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(generate_upload_url, body.model_dump(), claims, session)


@router.post("/confirm-upload")
async def confirm_upload_route(body: ConfirmUploadBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(confirm_upload, body.model_dump(), claims, session)


@router.post("/download-url")
async def pending_upload_download_url(body: PendingUploadDownloadBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(get_pending_upload_download_url, body.model_dump(), claims, session)
