from uuid import uuid4

import pytest

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.tasks.create_task import create_task
from beyo_manager.services.context import ServiceContext


def _ctx(session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=session,
    )


async def _seed_workspace_and_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _disable_event_dispatch(monkeypatch) -> None:
    async def _noop_dispatch(_events):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.tasks.create_task.event_bus.dispatch", _noop_dispatch)


@pytest.mark.integration
async def test_create_task_snapshots_name_from_existing_customer(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)
    customer = Customer(
        workspace_id=workspace.client_id,
        display_name="Existing Customer",
        primary_email="existing@example.com",
        primary_email_normalized="existing@example.com",
        created_by_id=user.client_id,
    )
    db_session.add(customer)
    await db_session.flush()

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": TaskTypeEnum.INTERNAL,
                "customer_id": customer.client_id,
            },
        )
    )

    task = await db_session.get(Task, result["client_id"])
    assert task.customer_name_snapshot == "Existing Customer"


@pytest.mark.integration
async def test_create_task_snapshots_name_from_inline_customer_payload(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "task_type": TaskTypeEnum.INTERNAL,
                "customer_display_name": "Inline Customer",
                "primary_email": "inline@example.com",
            },
        )
    )

    task = await db_session.get(Task, result["client_id"])
    assert task.customer_name_snapshot == "Inline Customer"


@pytest.mark.integration
async def test_create_task_without_customer_leaves_name_snapshot_null(db_session, monkeypatch):
    workspace, user = await _seed_workspace_and_user(db_session)
    await _disable_event_dispatch(monkeypatch)

    result = await create_task(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"task_type": TaskTypeEnum.INTERNAL},
        )
    )

    task = await db_session.get(Task, result["client_id"])
    assert task.customer_name_snapshot is None
