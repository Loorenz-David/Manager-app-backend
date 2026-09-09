from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import (
    WorkingSectionDependency,
)
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections.list_working_sections import (
    list_working_sections,
)

_COMPACT_KEYS = {
    "client_id",
    "name",
    "image",
    "order_list",
    "allows_batch_working",
    "allows_shopify_product_modifications",
}
_FULL_ONLY_KEYS = {"dependencies", "item_categories", "supported_issue_types", "members"}


def _ctx(db_session, *, workspace_id: str, user_id: str, query_params: dict) -> ServiceContext:
    return ServiceContext(
        identity={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role_name": "manager",
            "username": "tester",
        },
        incoming_data={},
        query_params=query_params,
        session=db_session,
    )


async def _seed(db_session) -> tuple[Workspace, User, WorkingSection, WorkingSection]:
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

    prerequisite = WorkingSection(
        client_id=f"wsec_a_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Prerequisite {suffix}",
        image="prereq.png",
        order_list=1,
    )
    dependent = WorkingSection(
        client_id=f"wsec_b_{suffix}",
        workspace_id=workspace.client_id,
        name=f"Dependent {suffix}",
        image="dependent.png",
        order_list=2,
        allows_batch_working=True,
        allows_shopify_product_modifications=True,
    )
    db_session.add_all([prerequisite, dependent])
    await db_session.flush()

    db_session.add_all(
        [
            WorkingSectionDependency(
                client_id=f"wsd_{suffix}",
                workspace_id=workspace.client_id,
                dependent_section_id=dependent.client_id,
                prerequisite_section_id=prerequisite.client_id,
            ),
            WorkingSectionMembership(
                client_id=f"wsme_{suffix}",
                workspace_id=workspace.client_id,
                working_section_id=dependent.client_id,
                user_id=user.client_id,
                sort_order=0,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
        ]
    )
    await db_session.flush()
    return workspace, user, prerequisite, dependent


@pytest.mark.asyncio
async def test_list_working_sections_defaults_to_full_serialization(db_session):
    workspace, user, prerequisite, dependent = await _seed(db_session)

    result = await list_working_sections(
        _ctx(db_session, workspace_id=workspace.client_id, user_id=user.client_id, query_params={})
    )

    sections = {row["client_id"]: row for row in result["working_sections"]}
    assert set(sections) == {prerequisite.client_id, dependent.client_id}
    full_row = sections[dependent.client_id]
    assert _FULL_ONLY_KEYS <= set(full_row)
    assert full_row["dependencies"] == [
        {"client_id": prerequisite.client_id, "name": prerequisite.name}
    ]
    assert [member["client_id"] for member in full_row["members"]] == [user.client_id]


@pytest.mark.asyncio
async def test_list_working_sections_compact_omits_relations_and_keeps_pagination(db_session):
    workspace, user, prerequisite, dependent = await _seed(db_session)

    result = await list_working_sections(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={"compact": "true", "limit": 1},
        )
    )

    rows = result["working_sections"]
    assert len(rows) == 1
    # order_list ordering is preserved by the compact branch
    assert rows[0]["client_id"] == prerequisite.client_id
    assert set(rows[0]) == _COMPACT_KEYS
    assert rows[0]["name"] == prerequisite.name
    assert rows[0]["image"] == "prereq.png"
    assert rows[0]["order_list"] == 1
    assert rows[0]["allows_batch_working"] is False
    assert rows[0]["allows_shopify_product_modifications"] is False
    assert result["working_sections_pagination"] == {"has_more": True, "limit": 1, "offset": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["false", "False", "", "1", "yes", None])
async def test_list_working_sections_non_true_compact_stays_full(db_session, raw):
    workspace, user, _prerequisite, dependent = await _seed(db_session)

    result = await list_working_sections(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={"compact": raw},
        )
    )

    assert _FULL_ONLY_KEYS <= set(result["working_sections"][0])


@pytest.mark.asyncio
async def test_list_working_sections_compact_accepts_router_boolean_casing(db_session):
    """The router forwards str(bool) — 'True'/'False', not 'true'/'false'."""
    workspace, user, prerequisite, _dependent = await _seed(db_session)

    result = await list_working_sections(
        _ctx(
            db_session,
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            query_params={"compact": str(True)},
        )
    )

    assert set(result["working_sections"][0]) == _COMPACT_KEYS
