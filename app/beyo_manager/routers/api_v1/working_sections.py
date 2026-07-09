from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.working_sections.create_working_section import (
	create_working_section,
)
from beyo_manager.services.commands.working_sections.delete_working_section import (
	delete_working_section,
)
from beyo_manager.services.commands.working_sections.edit_working_section import (
	edit_working_section,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.get_working_section import (
	get_working_section,
)
from beyo_manager.services.queries.working_sections.get_worker_working_sections import (
	get_worker_working_sections,
)
from beyo_manager.services.queries.working_sections.get_user_last_active_step_record import (
	get_user_last_active_step_record,
)
from beyo_manager.services.queries.working_sections.list_working_section_steps import (
	list_working_section_steps,
)
from beyo_manager.services.queries.working_sections.list_working_sections import (
	list_working_sections,
)
from beyo_manager.services.run_service import run_service

router = APIRouter()


class WorkingSectionCreateBody(BaseModel):
	client_id: str | None = None
	name: str
	image: str | None = None
	order_list: int | None = None
	allows_batch_working: bool = False
	allows_shopify_product_modifications: bool = False
	working_section_dependencies: list[str] = Field(default_factory=list)
	working_section_item_categories: list[str] = Field(default_factory=list)
	working_section_supported_issue_types: list[str] = Field(default_factory=list)


class WorkingSectionEditBody(BaseModel):
	name: str | None = None
	image: str | None = None
	order_list: int | None = None
	allows_batch_working: bool | None = None
	allows_shopify_product_modifications: bool | None = None
	working_section_dependencies: list[str] | None = None
	working_section_item_categories: list[str] | None = None
	working_section_supported_issue_types: list[str] | None = None


@router.put("")
async def create_working_section_route(
	body: WorkingSectionCreateBody,
	claims: dict = Depends(require_roles([ADMIN, MANAGER])),
	session: AsyncSession = Depends(get_db),
):
	ctx = ServiceContext(incoming_data=body.model_dump(), identity=claims, session=session)
	outcome = await run_service(create_working_section, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)

@router.get("")
async def list_working_sections_route(
	claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
	session: AsyncSession = Depends(get_db),
	limit: int = Query(50, le=200),
	offset: int = Query(0, ge=0),
):
	ctx = ServiceContext(
		incoming_data={},
		query_params={"limit": limit, "offset": offset},
		identity=claims,
		session=session,
	)
	outcome = await run_service(list_working_sections, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.get("/me")
async def get_worker_working_sections_route(
	claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
	session: AsyncSession = Depends(get_db),
	today_start: str | None = Query(None),
):
	ctx = ServiceContext(
		incoming_data={},
		query_params={"today_start": today_start} if today_start else {},
		identity=claims,
		session=session,
	)
	outcome = await run_service(get_worker_working_sections, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.get("/steps/user-last-active")
async def get_user_last_active_step_record_route(
	claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
	session: AsyncSession = Depends(get_db),
):
	ctx = ServiceContext(
		incoming_data={},
		query_params={},
		identity=claims,
		session=session,
	)
	outcome = await run_service(get_user_last_active_step_record, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.get("/{working_section_id}")
async def get_working_section_route(
	working_section_id: str,
	claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
	session: AsyncSession = Depends(get_db),
):
	ctx = ServiceContext(
		incoming_data={"client_id": working_section_id},
		identity=claims,
		session=session,
	)
	outcome = await run_service(get_working_section, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.get("/{working_section_id}/steps")
async def list_working_section_steps_route(
	working_section_id: str,
	claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
	session: AsyncSession = Depends(get_db),
	q: str | None = Query(None),
	task_types: str | None = Query(None),
	item_major_category: str | None = Query(None),
	major_category: str | None = Query(None),
	upholstery_search: bool = Query(False),
	limit: int = Query(50, le=200),
	offset: int = Query(0, ge=0),
	record_step_state: str | None = Query(None),
	readiness_statuses: str | None = Query(None),
):
	ctx = ServiceContext(
		incoming_data={"working_section_id": working_section_id},
		query_params={
			"q": q,
			"task_types": task_types,
			"item_major_category": item_major_category,
			"major_category": major_category,
			"upholstery_search": str(upholstery_search).lower(),
			"limit": limit,
			"offset": offset,
			"record_step_state": record_step_state,
			"readiness_statuses": readiness_statuses,
		},
		identity=claims,
		session=session,
	)
	outcome = await run_service(list_working_section_steps, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.patch("/{working_section_id}")
async def edit_working_section_route(
	working_section_id: str,
	body: WorkingSectionEditBody,
	claims: dict = Depends(require_roles([ADMIN, MANAGER])),
	session: AsyncSession = Depends(get_db),
):
	ctx = ServiceContext(
		incoming_data={"client_id": working_section_id, **body.model_dump(exclude_unset=True)},
		identity=claims,
		session=session,
	)
	outcome = await run_service(edit_working_section, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)


@router.delete("/{working_section_id}")
async def delete_working_section_route(
	working_section_id: str,
	claims: dict = Depends(require_roles([ADMIN, MANAGER])),
	session: AsyncSession = Depends(get_db),
):
	ctx = ServiceContext(
		incoming_data={"client_id": working_section_id},
		identity=claims,
		session=session,
	)
	outcome = await run_service(delete_working_section, ctx)
	if not outcome.success:
		return build_err(outcome.error)
	return build_ok(outcome.data)
