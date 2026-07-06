from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.cases.notification_targets import resolve_case_notification_targets
from beyo_manager.domain.emails.enums import EmailThreadEntityTypeEnum
from beyo_manager.domain.notifications.pin_conditions import EventFacts
from beyo_manager.domain.tasks.notification_targets import resolve_task_notification_targets
from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.tasks.task import Task


async def resolve_email_notification_targets(
    session: AsyncSession,
    *,
    workspace_id: str,
    thread: EmailThread,
    connection: EmailConnection,
) -> set[str]:
    sources = [asyncio.sleep(0, result={connection.owner_user_id})]

    if thread.entity_type == EmailThreadEntityTypeEnum.TASK.value and thread.entity_client_id:
        sources.append(_resolve_task_targets(session, workspace_id, thread.entity_client_id))
    elif thread.entity_type == EmailThreadEntityTypeEnum.CASE.value and thread.entity_client_id:
        sources.append(_resolve_case_targets(session, thread.entity_client_id))

    resolved = await asyncio.gather(*sources)
    return set().union(*resolved)


async def _resolve_task_targets(
    session: AsyncSession,
    workspace_id: str,
    task_client_id: str,
) -> set[str]:
    result = await session.execute(
        select(Task).where(
            Task.client_id == task_client_id,
            Task.workspace_id == workspace_id,
            Task.is_deleted.is_(False),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        return set()
    event_facts: EventFacts = {"state": task.state.value}
    return await resolve_task_notification_targets(
        session=session,
        workspace_id=workspace_id,
        task_client_id=task.client_id,
        task_created_by_id=task.created_by_id,
        actor_id="",
        event_facts=event_facts,
    )


async def _resolve_case_targets(session: AsyncSession, case_client_id: str) -> set[str]:
    result = await session.execute(select(Case).where(Case.client_id == case_client_id))
    case = result.scalar_one_or_none()
    if case is None:
        return set()
    return await resolve_case_notification_targets(session, case)
