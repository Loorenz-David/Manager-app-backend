from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import get_jwt_claims
from beyo_manager.services.commands.images.confirm_upload import confirm_upload
from beyo_manager.services.commands.images.create_annotation import create_annotation
from beyo_manager.services.commands.images.delete_annotation import delete_annotation
from beyo_manager.services.commands.images.generate_upload_url import generate_upload_url
from beyo_manager.services.commands.images.reorder_links import reorder_links
from beyo_manager.services.commands.images.soft_delete_image import soft_delete_image
from beyo_manager.services.commands.images.unlink_image import unlink_image
from beyo_manager.services.commands.images.update_annotation import update_annotation
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.images.get_download_url import get_download_url
from beyo_manager.services.queries.images.get_image import get_image
from beyo_manager.services.queries.images.list_images_for_entity import list_images_for_entity
from beyo_manager.services.run_service import run_service

router = APIRouter()


class GenerateImageUploadUrlBody(BaseModel):
    entity_type: str
    entity_client_id: str
    file_name: str
    content_type: str
    file_size_bytes: int | None = None


class ConfirmImageUploadBody(BaseModel):
    pending_upload_client_id: str
    entity_type: str
    entity_client_id: str


class UnlinkImageBody(BaseModel):
    image_client_id: str
    entity_type: str
    entity_client_id: str


class ReorderLinksBody(BaseModel):
    entity_type: str
    entity_client_id: str
    ordered_image_client_ids: list[str]


class CreateAnnotationBody(BaseModel):
    image_client_id: str | None = None
    annotation_type: str | None = None
    data: dict
    accuracy: int | None = None


class UpdateAnnotationBody(BaseModel):
    data: dict
    accuracy: int | None = None


async def _run(command, data: dict, claims: dict, session: AsyncSession):
    outcome = await run_service(command, ServiceContext(identity=claims, incoming_data=data, session=session))
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.post("/upload-url")
async def image_upload_url_route(body: GenerateImageUploadUrlBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(generate_upload_url, body.model_dump(), claims, session)


@router.post("/confirm-upload")
async def image_confirm_upload_route(body: ConfirmImageUploadBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(confirm_upload, body.model_dump(), claims, session)


@router.get("")
async def list_images_route(entity_type: str, entity_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(list_images_for_entity, {"entity_type": entity_type, "entity_client_id": entity_client_id}, claims, session)


@router.delete("/links")
async def unlink_image_route(body: UnlinkImageBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(unlink_image, body.model_dump(), claims, session)


@router.post("/reorder")
async def reorder_links_route(body: ReorderLinksBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(reorder_links, body.model_dump(), claims, session)


@router.get("/{image_client_id}")
async def get_image_route(image_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(get_image, {"image_client_id": image_client_id}, claims, session)


@router.get("/{image_client_id}/download-url")
async def image_download_url_route(image_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(get_download_url, {"image_client_id": image_client_id}, claims, session)


@router.delete("/{image_client_id}")
async def soft_delete_image_route(image_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(soft_delete_image, {"image_client_id": image_client_id}, claims, session)


@router.post("/{image_client_id}/annotations")
async def create_annotation_route(image_client_id: str, body: CreateAnnotationBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(create_annotation, {**body.model_dump(), "image_client_id": image_client_id}, claims, session)


@router.delete("/{image_client_id}/annotations/{annotation_client_id}")
async def delete_annotation_route(image_client_id: str, annotation_client_id: str, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(delete_annotation, {"image_client_id": image_client_id, "annotation_client_id": annotation_client_id}, claims, session)


@router.patch("/{image_client_id}/annotations/{annotation_client_id}")
async def update_annotation_route(image_client_id: str, annotation_client_id: str, body: UpdateAnnotationBody, claims: dict = Depends(get_jwt_claims), session: AsyncSession = Depends(get_db)):
    return await _run(
        update_annotation,
        {**body.model_dump(exclude_unset=True), "image_client_id": image_client_id, "annotation_client_id": annotation_client_id},
        claims,
        session,
    )
