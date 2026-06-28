from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.models.tables.cases.case import Case
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.cases.create_case import create_case
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.cases.get_case import get_case
from beyo_manager.services.queries.cases.list_cases import list_cases


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        session=db_session,
    )


async def _seed_workspace_user(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


@pytest.mark.integration
async def test_create_case_assigns_global_scalar_id_and_default_reference_number(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user(db_session)
    await db_session.commit()

    async def _fake_dispatch(_events):
        return None

    async def _fake_create_instant_task(**_kwargs):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.cases.create_case.dispatch", _fake_dispatch)
    monkeypatch.setattr(
        "beyo_manager.services.commands.cases.create_case.create_instant_task",
        _fake_create_instant_task,
    )

    result = await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={},
        )
    )

    case = await db_session.scalar(select(Case).where(Case.client_id == result["case_client_id"]))

    assert case is not None
    assert result["scalar_id"] == case.scalar_id
    assert result["reference_number"] == case.reference_number
    assert case.scalar_id >= 1
    assert case.reference_number == f"N-{case.scalar_id:04d}"


@pytest.mark.integration
async def test_create_case_uses_entity_prefix_and_serializers_expose_reference_fields(db_session, monkeypatch):
    workspace, user = await _seed_workspace_user(db_session)
    await db_session.commit()

    async def _fake_dispatch(_events):
        return None

    async def _fake_create_instant_task(**_kwargs):
        return None

    monkeypatch.setattr("beyo_manager.services.commands.cases.create_case.dispatch", _fake_dispatch)
    monkeypatch.setattr(
        "beyo_manager.services.commands.cases.create_case.create_instant_task",
        _fake_create_instant_task,
    )

    create_result = await create_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={
                "entity_type": "task",
                "entity_client_id": "tsk_01KW4MQ1QMTGZXWEPMYR1Y8RGQ",
            },
        )
    )

    case_payload = await get_case(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"case_client_id": create_result["case_client_id"]},
        )
    )
    list_payload = await list_cases(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={},
        )
    )
    case = await db_session.scalar(select(Case).where(Case.client_id == create_result["case_client_id"]))

    assert case is not None
    assert create_result["scalar_id"] == case.scalar_id
    assert create_result["reference_number"] == case.reference_number
    assert case.reference_number == f"tsk-{case.scalar_id:04d}"
    assert case_payload["case"]["scalar_id"] == case.scalar_id
    assert case_payload["case"]["reference_number"] == case.reference_number
    assert list_payload["cases"][0]["scalar_id"] == case.scalar_id
    assert list_payload["cases"][0]["reference_number"] == case.reference_number
