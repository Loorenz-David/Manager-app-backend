from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemCurrencyEnum, ItemUpholsterySourceEnum
from beyo_manager.domain.task_steps.enums import StepEventReasonEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import (
    TaskFulfillmentMethodEnum,
    TaskItemLocationEnum,
    TaskItemRoleEnum,
    TaskNoteTypeEnum,
    TaskPriorityEnum,
    TaskReturnMethodEnum,
    TaskReturnSourceEnum,
    TaskTypeEnum,
)
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER, WORKER
from beyo_manager.services.commands.tasks.add_item_to_task import add_item_to_task
from beyo_manager.services.commands.tasks.append_note_read_by import append_note_read_by
from beyo_manager.services.commands.tasks.cancel_task import cancel_task
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.commands.tasks.create_task_note import create_task_note
from beyo_manager.services.commands.tasks.delete_task import delete_task
from beyo_manager.services.commands.tasks.delete_task_note import delete_task_note
from beyo_manager.services.commands.tasks.fail_task import fail_task
from beyo_manager.services.commands.tasks.remove_item_from_task import remove_item_from_task
from beyo_manager.services.commands.tasks.resolve_task import resolve_task
from beyo_manager.services.commands.tasks.send_customer_coordination_email_batch import (
    send_customer_coordination_email_batch,
)
from beyo_manager.services.commands.tasks.send_customer_coordination_reply import (
    send_customer_coordination_reply,
)
from beyo_manager.services.commands.tasks.update_task import update_task
from beyo_manager.services.commands.tasks.update_task_ready_by_at import update_task_ready_by_at
from beyo_manager.services.commands.tasks.update_task_schedule import update_task_schedule
from beyo_manager.services.commands.tasks.update_task_note import update_task_note
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
    SendCustomerCoordinationEmailBatchRequest,
)
from beyo_manager.services.commands.task_post_handling.complete_task_post_handling import (
    complete_task_post_handling,
)
from beyo_manager.services.commands.task_customer_coordination.complete_task_customer_coordination import (
    complete_task_customer_coordination,
)
from beyo_manager.services.commands.task_customer_coordination.fail_task_customer_coordination import (
    fail_task_customer_coordination,
)
from beyo_manager.services.commands.task_steps.add_step_dependency import add_step_dependency
from beyo_manager.services.commands.task_steps.add_task_steps import add_task_steps
from beyo_manager.services.commands.task_steps.assign_worker_to_step import assign_worker_to_step
from beyo_manager.services.commands.task_steps.cancel_pending_step_completion import (
    cancel_pending_step_completion,
)
from beyo_manager.services.commands.task_steps.mark_step_time_inaccurate import mark_step_time_inaccurate
from beyo_manager.services.commands.task_steps.remove_step_dependency import remove_step_dependency
from beyo_manager.services.commands.task_steps.remove_task_step import (
    remove_task_step,
    remove_task_steps,
)
from beyo_manager.services.commands.task_steps.transition_step_state import transition_step_state
from beyo_manager.services.commands.task_steps.transition_step_state_batch import transition_step_state_batch
from beyo_manager.services.commands.task_steps.update_task_step_ready_by_at import (
    update_task_step_ready_by_at,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.tasks.count_task_post_handling_states import (
    count_task_post_handling_states,
)
from beyo_manager.services.queries.tasks.count_task_customer_coordination_states import (
    count_task_customer_coordination_states,
)
from beyo_manager.services.queries.tasks.count_task_step_states import count_task_step_states
from beyo_manager.services.queries.tasks.get_task_notes import get_task_notes
from beyo_manager.services.queries.tasks.list_task_coordination_threads import (
    list_task_coordination_threads,
)
from beyo_manager.services.queries.tasks.list_task_post_handlings import list_task_post_handlings
from beyo_manager.services.queries.tasks.list_task_steps import list_task_steps
from beyo_manager.services.queries.tasks.task_flow_records import get_task_flow_records
from beyo_manager.services.queries.tasks.tasks import get_task, list_task_counts, list_tasks
from beyo_manager.services.run_service import run_service
from beyo_manager.services.commands.task_post_handling.update_task_post_handling import update_task_post_handling

router = APIRouter()


class _TaskItemInputBody(BaseModel):
    client_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str | None = None
    quantity: int = 1
    designer: str | None = None
    height_in_cm: int | None = None
    width_in_cm: int | None = None
    depth_in_cm: int | None = None
    item_value_minor: int | None = None
    item_cost_minor: int | None = None
    item_currency: ItemCurrencyEnum | None = None
    item_position: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    external_source: str | None = None
    external_order_id: str | None = None


class _TaskItemIssueBody(BaseModel):
    issue_type_id: str | None = None
    step_id: str
    worker_id: str
    working_section_id: str
    item_category_id: str
    issue_type_snapshot: str
    placement_of_issue_snapshot: str | None = None
    intensity: int


class _TaskItemUpholsteryBody(BaseModel):
    client_id: str | None = None
    upholstery_id: str | None = None
    source: ItemUpholsterySourceEnum
    name: str | None = None
    code: str | None = None
    amount_meters: float | None = None
    time_to_fix_in_seconds: int | None = None


class _TaskNoteInputBody(BaseModel):
    client_id: str | None = None
    note_type: TaskNoteTypeEnum
    content: list
    plain_text: str = ""
    users_read_list: list[str] | None = None


class _CreateTaskBody(BaseModel):
    client_id: str | None = None
    task_type: TaskTypeEnum
    title: str | None = None
    summary: str | None = None
    priority: TaskPriorityEnum = TaskPriorityEnum.NORMAL
    ready_by_at: datetime | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    return_source: TaskReturnSourceEnum | None = None
    item_location: TaskItemLocationEnum | None = None
    return_method: TaskReturnMethodEnum | None = None
    fulfillment_method: TaskFulfillmentMethodEnum | None = None
    assortment: str | None = None
    additional_details: dict | None = None
    customer_id: str | None = None
    customer_display_name: str | None = None
    primary_phone_number: str | None = None
    secondary_phone_number: str | None = None
    primary_email: str | None = None
    secondary_email: str | None = None
    customer_address: dict | None = None
    item: _TaskItemInputBody | None = None
    item_issues: list[_TaskItemIssueBody] | None = None
    item_upholstery: _TaskItemUpholsteryBody | None = None
    notes: list[_TaskNoteInputBody] | None = None
    steps: list["_TaskStepInputBody"] | None = None


class _UpdateTaskBody(BaseModel):
    title: str | None = None
    summary: str | None = None
    priority: TaskPriorityEnum | None = None
    ready_by_at: datetime | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    return_source: TaskReturnSourceEnum | None = None
    item_location: TaskItemLocationEnum | None = None
    return_method: TaskReturnMethodEnum | None = None
    fulfillment_method: TaskFulfillmentMethodEnum | None = None
    assortment: str | None = None
    additional_details: dict | None = None


class _UpdateReadyByAtBody(BaseModel):
    ready_by_at: datetime | None = None


class _UpdateScheduleBody(BaseModel):
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None


class _UpdateTaskPostHandlingBody(BaseModel):
    fulfillment_method: TaskFulfillmentMethodEnum | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    task_type: TaskTypeEnum | None = None
    assortment: str | None = None


class _CompleteTaskPostHandlingBody(BaseModel):
    post_handling_id: str | None = None
    force: bool = False


class _CompleteTaskCustomerCoordinationBody(BaseModel):
    coordination_id: str | None = None


class _FailTaskCustomerCoordinationBody(BaseModel):
    coordination_ids: list[str] | None = None


class _SendCustomerCoordinationReplyBody(BaseModel):
    thread_client_id: str
    connection_client_id: str | None = None
    subject: str | None = None
    text_body: str | None = None
    html_body: str | None = None


class _AddItemToTaskBody(BaseModel):
    item_id: str
    role: TaskItemRoleEnum


class _UpdateNoteBody(BaseModel):
    note_type: TaskNoteTypeEnum | None = None
    content: list | None = None
    plain_text: str | None = None


class _MarkNoteReadByBody(BaseModel):
    user_ids: list[str]


class _TaskStepInputBody(BaseModel):
    client_id: str | None = None
    working_section_id: str
    worker_id: str | None = None
    sequence_order: int | None = None
    ready_by_at: datetime | None = None


class _UpdateStepReadyByAtItemBody(BaseModel):
    step_id: str
    ready_by_at: datetime | None = None


class _UpdateStepsReadyByAtBody(BaseModel):
    items: list[_UpdateStepReadyByAtItemBody]


class _AssignWorkerBody(BaseModel):
    worker_id: str


class _TransitionStepBody(BaseModel):
    new_state: TaskStepStateEnum
    credited_user_id: str | None = None
    reason: StepEventReasonEnum | None = None
    description: str | None = None
    mark_closing_record_inaccurate: bool = False


class _BatchTransitionItemBody(BaseModel):
    task_id: str
    step_id: str
    mark_closing_record_inaccurate: bool = False


class _BatchTransitionStepBody(BaseModel):
    items: list[_BatchTransitionItemBody]
    new_state: TaskStepStateEnum
    reason: StepEventReasonEnum | None = None
    description: str | None = None


class _MarkStepTimeInaccurateBody(BaseModel):
    pass  # No body fields; record_id comes from URL path


@router.put("")
async def route_create_task(
    body: _CreateTaskBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(exclude_unset=True),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_tasks(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    working_section_ids: str | None = Query(None),
    task_states: str | None = Query(None),
    task_step_states: str | None = Query(None),
    step_readiness_statuses: str | None = Query(None),
    priorities: str | None = Query(None),
    task_types: str | None = Query(None),
    return_sources: str | None = Query(None),
    post_handling_states: str | None = Query(None),
    customer_coordination_states: str | None = Query(None),
    ready_from_date: str | None = Query(None),
    ready_to_date: str | None = Query(None),
    scheduled_from_date: str | None = Query(None),
    scheduled_to_date: str | None = Query(None),
    upholstery_requirement_states: str | None = Query(None),
    deleted: bool = Query(False),
    order_by: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "limit": limit,
            "offset": offset,
            "q": q,
            "working_section_ids": working_section_ids,
            "task_states": task_states,
            "task_step_states": task_step_states,
            "step_readiness_statuses": step_readiness_statuses,
            "priorities": priorities,
            "task_types": task_types,
            "return_sources": return_sources,
            "post_handling_states": post_handling_states,
            "customer_coordination_states": customer_coordination_states,
            "ready_from_date": ready_from_date,
            "ready_to_date": ready_to_date,
            "scheduled_from_date": scheduled_from_date,
            "scheduled_to_date": scheduled_to_date,
            "upholstery_requirement_states": upholstery_requirement_states,
            "deleted": deleted,
            "order_by": order_by,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_tasks, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/counts")
async def route_list_task_counts(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    task_states: str | None = Query(None),
    task_step_states: str | None = Query(None),
    step_readiness_statuses: str | None = Query(None),
    priorities: str | None = Query(None),
    task_types: str | None = Query(None),
    return_sources: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "task_states": task_states,
            "task_step_states": task_step_states,
            "step_readiness_statuses": step_readiness_statuses,
            "priorities": priorities,
            "task_types": task_types,
            "return_sources": return_sources,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_counts, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/post-handling/counts")
async def route_count_task_post_handling_states(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    post_handling_states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"post_handling_states": post_handling_states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(count_task_post_handling_states, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/customer-coordination/counts")
async def route_count_task_customer_coordination_states(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    customer_coordination_states: str | None = Query(None),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"customer_coordination_states": customer_coordination_states},
        identity=claims,
        session=session,
    )
    outcome = await run_service(count_task_customer_coordination_states, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/customer-coordination/email-batch")
async def route_send_customer_coordination_email_batch(
    body: SendCustomerCoordinationEmailBatchRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(send_customer_coordination_email_batch, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/customer-coordination/reply")
async def route_send_customer_coordination_reply(
    task_id: str,
    body: _SendCustomerCoordinationReplyBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(send_customer_coordination_reply, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/customer-coordination/threads")
async def route_list_task_coordination_threads(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
    coordination_states: str | None = Query(None),
    task_states: str | None = Query(None),
    task_types: str | None = Query(None),
    q: str | None = Query(None, max_length=200),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={
            "coordination_states": coordination_states,
            "task_states": task_states,
            "task_types": task_types,
            "q": q,
            "limit": limit,
            "offset": offset,
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_coordination_threads, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}")
async def route_get_task(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}/flow-records")
async def route_get_task_flow_records(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_task_flow_records, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}/post-handling")
async def route_list_task_post_handlings(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_post_handlings, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/post-handling/complete")
async def route_complete_task_post_handling(
    task_id: str,
    body: _CompleteTaskPostHandlingBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(complete_task_post_handling, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/customer-coordination/complete")
async def route_complete_task_customer_coordination(
    task_id: str,
    body: _CompleteTaskCustomerCoordinationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(complete_task_customer_coordination, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/customer-coordination/fail")
async def route_fail_task_customer_coordination(
    task_id: str,
    body: _FailTaskCustomerCoordinationBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(fail_task_customer_coordination, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}")
async def route_update_task(
    task_id: str,
    body: _UpdateTaskBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/ready-by-at")
async def route_update_task_ready_by_at(
    task_id: str,
    body: _UpdateReadyByAtBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_ready_by_at, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/schedule")
async def route_update_task_schedule(
    task_id: str,
    body: _UpdateScheduleBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_schedule, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/post-handling")
async def route_update_task_post_handling(
    task_id: str,
    body: _UpdateTaskPostHandlingBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_post_handling, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}")
async def route_delete_task(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/resolve")
async def route_resolve_task(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(resolve_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/cancel")
async def route_cancel_task(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(cancel_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/fail")
async def route_fail_task(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(fail_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/items")
async def route_add_item_to_task(
    task_id: str,
    body: _AddItemToTaskBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(add_item_to_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}/items/{item_id}")
async def route_remove_item_from_task(
    task_id: str,
    item_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "item_id": item_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(remove_item_from_task, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/notes")
async def route_create_note(
    task_id: str,
    body: list[_TaskNoteInputBody],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "notes": [note.model_dump() for note in body]},
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_task_note, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}/notes")
async def route_get_task_notes(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_task_notes, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/notes/{note_id}")
async def route_update_note(
    task_id: str,
    note_id: str,
    body: _UpdateNoteBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": note_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_note, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/notes/{note_id}/read-by")
async def route_mark_note_read_by(
    task_id: str,
    note_id: str,
    body: _MarkNoteReadByBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "client_id": note_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(append_note_read_by, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}/notes/{note_id}")
async def route_delete_note(
    task_id: str,
    note_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": note_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_task_note, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}/steps")
async def route_list_task_steps(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        query_params={"limit": limit, "offset": offset},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_task_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("/{task_id}/steps/counts")
async def route_count_task_step_states(
    task_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(count_task_step_states, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/steps")
async def route_add_task_step(
    task_id: str,
    body: list[_TaskStepInputBody],
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "task_id": task_id,
            "steps": [step.model_dump() for step in body],
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(add_task_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{task_id}/steps/ready-by-at")
async def route_update_task_steps_ready_by_at(
    task_id: str,
    body: _UpdateStepsReadyByAtBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={
            "task_id": task_id,
            "items": [item.model_dump() for item in body.items],
        },
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_task_step_ready_by_at, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/steps/{step_id}/assign-worker")
async def route_assign_worker_to_step(
    task_id: str,
    step_id: str,
    body: _AssignWorkerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"step_id": step_id, "task_id": task_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(assign_worker_to_step, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


class _AddDependencyBody(BaseModel):
    prerequisite_step_id: str


@router.delete("/{task_id}/steps")
async def route_remove_task_steps(
    task_id: str,
    body: list[str],
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_ids": body},
        identity=claims,
        session=session,
    )
    outcome = await run_service(remove_task_steps, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}/steps/{step_id}")
async def route_remove_task_step(
    task_id: str,
    step_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(remove_task_step, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/steps/{step_id}/dependencies")
async def route_add_step_dependency(
    task_id: str,
    step_id: str,
    body: _AddDependencyBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(add_step_dependency, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}/steps/{step_id}/dependencies/{dependency_id}")
async def route_remove_step_dependency(
    task_id: str,
    step_id: str,
    dependency_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id, "dependency_id": dependency_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(remove_step_dependency, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/steps/{step_id}/transition")
async def route_transition_step_state(
    task_id: str,
    step_id: str,
    body: _TransitionStepBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id, **body.model_dump()},
        identity=claims,
        session=session,
    )
    outcome = await run_service(transition_step_state, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/steps/transition-batch")
async def route_transition_step_state_batch(
    body: _BatchTransitionStepBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(transition_step_state_batch, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{task_id}/steps/{step_id}/pending-completion")
async def route_cancel_pending_step_completion(
    task_id: str,
    step_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(cancel_pending_step_completion, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/{task_id}/steps/{step_id}/state-records/{record_id}/mark-inaccurate")
async def route_mark_step_time_inaccurate(
    task_id: str,
    step_id: str,
    record_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"task_id": task_id, "step_id": step_id, "record_id": record_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(mark_step_time_inaccurate, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
