from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.emails.enums import EmailThreadEntityTypeEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.commands.emails.send_email import send_email
from beyo_manager.services.commands.tasks.requests import (
    parse_send_customer_coordination_reply_request,
)
from beyo_manager.services.commands.tasks.send_customer_coordination_email_batch import (
    _load_item_contexts,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext
from beyo_manager.services.infra.email_enrichment.enricher import ContentEnricher
from beyo_manager.services.infra.email_enrichment.var_parsers.registry import VAR_PARSER_MAP


async def send_customer_coordination_reply(ctx: ServiceContext) -> dict:
    request = parse_send_customer_coordination_reply_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        task = await _load_task(ctx, request.task_id)
        thread = await _load_thread(ctx, request.thread_client_id)
        _validate_coordination_thread(thread, request.task_id)

        coordination = await _load_thread_coordination(ctx, thread.entity_client_id)
        if coordination.task_id != request.task_id:
            raise ValidationError("The selected coordination thread does not belong to the provided task.")

        customer = await _load_customer(ctx, task.customer_id)
        if customer is None or not customer.primary_email:
            raise ValidationError("Task customer does not have a primary email address for reply.")

        latest_message = await _load_latest_message(ctx, thread.client_id)
        resolved_subject = request.subject or latest_message.subject if latest_message else request.subject
        if not resolved_subject:
            raise ValidationError("Could not resolve a reply subject for the selected coordination thread.")

        item_contexts_by_task_id = await _load_item_contexts(ctx, [request.task_id])
        item_context = item_contexts_by_task_id.get(request.task_id)
        enrichment_context = EnrichmentContext(
            task=task,
            customer=customer,
            item=item_context.item if item_context else None,
            item_category=item_context.item_category if item_context else None,
        )
        enricher = ContentEnricher(VAR_PARSER_MAP)

        delegated_ctx = ServiceContext(
            identity=ctx.identity,
            session=ctx.session,
            incoming_data={
                "thread_client_id": thread.client_id,
                "connection_client_id": request.connection_client_id,
                "to_addresses": [customer.primary_email],
                "subject": enricher.enrich(resolved_subject, enrichment_context),
                "text_body": (
                    enricher.enrich(request.text_body, enrichment_context)
                    if request.text_body is not None
                    else None
                ),
                "html_body": (
                    enricher.enrich(request.html_body, enrichment_context)
                    if request.html_body is not None
                    else None
                ),
            },
        )
        return await send_email(delegated_ctx)


async def _load_task(ctx: ServiceContext, task_id: str) -> Task:
    result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id == task_id,
            Task.is_deleted.is_(False),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFound("Task not found.")
    return task


async def _load_thread(ctx: ServiceContext, thread_client_id: str) -> EmailThread:
    result = await ctx.session.execute(
        select(EmailThread).where(
            EmailThread.workspace_id == ctx.workspace_id,
            EmailThread.client_id == thread_client_id,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise NotFound("Email thread not found.")
    return thread


def _validate_coordination_thread(thread: EmailThread, task_id: str) -> None:
    if thread.entity_type != EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value:
        raise ValidationError("The selected email thread is not a task customer coordination thread.")
    if thread.major_entity_type != EmailThreadEntityTypeEnum.TASK.value:
        raise ValidationError("The selected email thread is not attached to a task.")
    if thread.major_entity_client_id != task_id:
        raise ValidationError("The selected coordination thread does not belong to the provided task.")
    if not thread.entity_client_id:
        raise ValidationError("The selected coordination thread is missing its coordination reference.")


async def _load_thread_coordination(
    ctx: ServiceContext,
    coordination_id: str | None,
) -> TaskCustomerCoordination:
    result = await ctx.session.execute(
        select(TaskCustomerCoordination).where(
            TaskCustomerCoordination.workspace_id == ctx.workspace_id,
            TaskCustomerCoordination.client_id == coordination_id,
        )
    )
    coordination = result.scalar_one_or_none()
    if coordination is None:
        raise NotFound("Task customer coordination not found for the selected email thread.")
    return coordination


async def _load_customer(ctx: ServiceContext, customer_id: str | None) -> Customer | None:
    if not customer_id:
        return None
    result = await ctx.session.execute(
        select(Customer).where(
            Customer.workspace_id == ctx.workspace_id,
            Customer.client_id == customer_id,
            Customer.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _load_latest_message(ctx: ServiceContext, thread_id: str) -> EmailMessage | None:
    result = await ctx.session.execute(
        select(EmailMessage)
        .where(
            EmailMessage.workspace_id == ctx.workspace_id,
            EmailMessage.thread_id == thread_id,
        )
        .order_by(EmailMessage.sent_or_received_at.desc(), EmailMessage.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
