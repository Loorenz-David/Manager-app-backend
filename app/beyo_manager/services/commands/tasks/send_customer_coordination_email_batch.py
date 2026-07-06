from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum, EmailThreadEntityTypeEnum
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.send_email_messages import (
    SendEmailMessagesPayload,
)
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.services.commands.emails._connection_resolver import resolve_email_connection
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.task_customer_coordination._transition_coordination_to_coordinating_in_session import (
    _transition_coordination_to_coordinating_in_session,
)
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
    SendCustomerCoordinationEmailBatchRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext
from beyo_manager.services.infra.email_enrichment.enricher import ContentEnricher
from beyo_manager.services.infra.email_enrichment.var_parsers.registry import VAR_PARSER_MAP
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.events import event_bus
from beyo_manager.services.infra.events.build_event import build_workspace_event
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject


@dataclass
class _ItemContext:
    item: Item
    item_category: ItemCategory | None


async def send_customer_coordination_email_batch(ctx: ServiceContext) -> dict:
    request = SendCustomerCoordinationEmailBatchRequest.model_validate(ctx.incoming_data)
    job = None
    skipped: list[dict] = []
    queued_thread_ids: list[str] = []
    queued_message_ids: list[str] = []
    transitioned: list[TaskCustomerCoordination] = []

    async with maybe_begin(ctx.session):
        connection = await resolve_email_connection(ctx, request.connection_client_id)
        assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)

        tasks = await _load_tasks(ctx, request.task_ids)
        tasks_by_id = {task.client_id: task for task in tasks}

        customer_ids = [task.customer_id for task in tasks if task.customer_id]
        customers_by_id = await _load_customers(ctx, customer_ids)
        tccs_by_task_id = await _load_tccs(ctx, request.task_ids)
        item_contexts_by_task_id = await _load_item_contexts(ctx, request.task_ids)

        enricher = ContentEnricher(VAR_PARSER_MAP)
        now = datetime.now(timezone.utc)
        queued_coordinations: list[TaskCustomerCoordination] = []

        for task_id in request.task_ids:
            task = tasks_by_id.get(task_id)
            if task is None:
                skipped.append({"task_client_id": task_id, "reason": "task_not_found"})
                continue

            coordination = tccs_by_task_id.get(task_id)
            if coordination is None:
                skipped.append({"task_client_id": task_id, "reason": "no_coordination_record"})
                continue

            customer = customers_by_id.get(task.customer_id) if task.customer_id else None
            if customer is None or not customer.primary_email:
                skipped.append({"task_client_id": task_id, "reason": "no_customer_email"})
                continue

            item_context = item_contexts_by_task_id.get(task_id)
            enrichment_context = EnrichmentContext(
                task=task,
                customer=customer,
                item=item_context.item if item_context else None,
                item_category=item_context.item_category if item_context else None,
            )
            enriched_subject = enricher.enrich(request.subject, enrichment_context)
            enriched_text = enricher.enrich(request.text_body, enrichment_context) if request.text_body else None
            enriched_html = enricher.enrich(request.html_body, enrichment_context) if request.html_body else None

            rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"
            thread = EmailThread(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                entity_type=EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value,
                entity_client_id=coordination.client_id,
                major_entity_type=EmailThreadEntityTypeEnum.TASK.value,
                major_entity_client_id=task.client_id,
                topic=None,
                subject_normalized=normalize_subject(enriched_subject),
                last_message_at=now,
            )
            ctx.session.add(thread)
            await ctx.session.flush()

            message = EmailMessage(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                thread_id=thread.client_id,
                direction=EmailMessageDirectionEnum.OUTBOUND.value,
                from_address=connection.email_address,
                from_name=connection.display_name,
                to_addresses_json=[customer.primary_email],
                cc_addresses_json=[],
                bcc_addresses_json=[],
                subject=enriched_subject,
                text_body=enriched_text,
                html_body=enriched_html,
                body_preview=(enriched_text or "")[:300] or None,
                rfc_message_id=rfc_message_id,
                in_reply_to=None,
                references_json=[],
                sent_or_received_at=now,
                created_by_user_id=ctx.user_id,
            )
            ctx.session.add(message)
            await ctx.session.flush()

            queued_thread_ids.append(thread.client_id)
            queued_message_ids.append(message.client_id)
            queued_coordinations.append(coordination)

        transitioned = await _transition_coordination_to_coordinating_in_session(
            session=ctx.session,
            coordinations=queued_coordinations,
            now=now,
            user_id=ctx.user_id,
            username_snapshot=ctx.identity.get("username"),
        )

        if queued_thread_ids:
            job = await create_instant_task(
                session=ctx.session,
                task_type=TaskType.SEND_EMAIL_MESSAGES,
                payload=asdict(
                    SendEmailMessagesPayload(
                        workspace_id=ctx.workspace_id,
                        connection_client_id=connection.client_id,
                        message_ids=queued_message_ids,
                        request_kind="coordination_batch",
                        requested_by_user_id=ctx.user_id,
                    )
                ),
                max_try=3,
            )

    result = {
        "job_id": job.client_id if job else None,
        "status": "queued" if job else "nothing_to_send",
        "queued_count": len(queued_thread_ids),
        "skipped_count": len(skipped),
        "skipped": skipped,
    }

    if transitioned:
        await event_bus.dispatch(
            [
                build_workspace_event(
                    coordination,
                    "task_customer_coordination:coordinating",
                    workspace_id=ctx.workspace_id,
                )
                for coordination in transitioned
            ]
        )

    return result



async def _load_tasks(ctx: ServiceContext, task_ids: list[str]) -> list[Task]:
    result = await ctx.session.execute(
        select(Task).where(
            Task.workspace_id == ctx.workspace_id,
            Task.client_id.in_(task_ids),
            Task.is_deleted.is_(False),
        )
    )
    return list(result.scalars().all())


async def _load_customers(ctx: ServiceContext, customer_ids: list[str | None]) -> dict[str, Customer]:
    normalized_ids = [customer_id for customer_id in customer_ids if customer_id]
    if not normalized_ids:
        return {}

    result = await ctx.session.execute(
        select(Customer).where(
            Customer.workspace_id == ctx.workspace_id,
            Customer.client_id.in_(normalized_ids),
            Customer.is_deleted.is_(False),
        )
    )
    return {customer.client_id: customer for customer in result.scalars().all()}


async def _load_tccs(ctx: ServiceContext, task_ids: list[str]) -> dict[str, TaskCustomerCoordination]:
    result = await ctx.session.execute(
        select(TaskCustomerCoordination).where(
            TaskCustomerCoordination.workspace_id == ctx.workspace_id,
            TaskCustomerCoordination.task_id.in_(task_ids),
        )
    )
    latest_by_task_id: dict[str, TaskCustomerCoordination] = {}
    for coordination in result.scalars().all():
        current = latest_by_task_id.get(coordination.task_id)
        if current is None or coordination.created_at > current.created_at:
            latest_by_task_id[coordination.task_id] = coordination
    return latest_by_task_id


async def _load_item_contexts(ctx: ServiceContext, task_ids: list[str]) -> dict[str, _ItemContext]:
    result = await ctx.session.execute(
        select(TaskItem, Item, ItemCategory)
        .join(
            Item,
            (Item.client_id == TaskItem.item_id)
            & (Item.workspace_id == ctx.workspace_id)
            & (Item.is_deleted.is_(False)),
        )
        .outerjoin(
            ItemCategory,
            (ItemCategory.client_id == Item.item_category_id)
            & (ItemCategory.workspace_id == ctx.workspace_id)
            & (ItemCategory.is_deleted.is_(False)),
        )
        .where(
            TaskItem.workspace_id == ctx.workspace_id,
            TaskItem.task_id.in_(task_ids),
            TaskItem.role == TaskItemRoleEnum.PRIMARY,
            TaskItem.removed_at.is_(None),
        )
    )

    contexts_by_task_id: dict[str, _ItemContext] = {}
    for task_item, item, item_category in result.all():
        contexts_by_task_id[task_item.task_id] = _ItemContext(item=item, item_category=item_category)
    return contexts_by_task_id
