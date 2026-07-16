from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.services.commands.working_sections.set_user_working_sections_order import (
    set_user_working_sections_order,
)
from beyo_manager.services.context import ServiceContext


def _ctx(db_session, *, workspace_id: str, user_id: str, incoming_data: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data=incoming_data,
        query_params={},
        session=db_session,
    )


async def _seed_user_with_sections(db_session, section_names: list[str]):
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

    now = datetime.now(timezone.utc)
    section_ids: list[str] = []
    for order, name in enumerate(section_names):
        section = WorkingSection(
            workspace_id=workspace.client_id,
            name=name,
            created_by_id=user.client_id,
        )
        db_session.add(section)
        await db_session.flush()
        section_ids.append(section.client_id)
        db_session.add(
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=section.client_id,
                user_id=user.client_id,
                sort_order=order,
                assigned_at=now,
                assigned_by_id=user.client_id,
            )
        )
    await db_session.flush()
    return workspace, user, section_ids


@pytest.mark.integration
async def test_reorder_rewrites_sort_order_and_worker_view_follows_it(db_session, monkeypatch):
    async def _fake_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.working_sections.set_user_working_sections_order.dispatch",
        _fake_dispatch,
    )

    workspace, user, section_ids = await _seed_user_with_sections(
        db_session, ["Disassembly", "Padding", "Assembly"]
    )
    reversed_ids = list(reversed(section_ids))

    result = await set_user_working_sections_order(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            incoming_data={"user_id": user.client_id, "ordered_working_section_ids": reversed_ids},
        )
    )
    assert result["ordered_section_ids"] == reversed_ids

    rows = (
        await db_session.execute(
            select(WorkingSectionMembership.working_section_id, WorkingSectionMembership.sort_order).where(
                WorkingSectionMembership.user_id == user.client_id,
                WorkingSectionMembership.removed_at.is_(None),
            )
        )
    ).all()
    sort_order_by_section = {row.working_section_id: row.sort_order for row in rows}
    assert [sort_order_by_section[sid] for sid in reversed_ids] == [0, 1, 2]


@pytest.mark.integration
async def test_reorder_rejects_payload_not_matching_active_set(db_session, monkeypatch):
    async def _fake_dispatch(_events):
        return None

    monkeypatch.setattr(
        "beyo_manager.services.commands.working_sections.set_user_working_sections_order.dispatch",
        _fake_dispatch,
    )

    workspace, user, section_ids = await _seed_user_with_sections(
        db_session, ["Disassembly", "Padding", "Assembly"]
    )

    # Drop one section from the payload → must not match the user's active set.
    with pytest.raises(ValidationError):
        await set_user_working_sections_order(
            _ctx(
                db_session,
                workspace_id=workspace.client_id,
                user_id=user.client_id,
                incoming_data={
                    "user_id": user.client_id,
                    "ordered_working_section_ids": section_ids[:2],
                },
            )
        )
