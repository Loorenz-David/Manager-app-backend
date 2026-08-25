from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.pause_reasons.pause_reason_user_link import (
    PauseReasonUserLink,
)
from beyo_manager.models.tables.pause_reasons.pause_reason_working_section_link import (
    PauseReasonWorkingSectionLink,
)
from beyo_manager.models.tables.roles.role import Role
from beyo_manager.models.tables.roles.workspace_role import WorkspaceRole
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)
from beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons import (
    seed_pause_reasons,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.pause_reasons.list_pause_reasons import (
    list_pause_reasons,
)


async def _seed_workspace(db_session, name_prefix: str):
    suffix = uuid4().hex[:8]
    workspace = None
    if name_prefix == "Query workspace":
        workspace = await db_session.scalar(
            select(Workspace).order_by(Workspace.client_id)
        )
    workspace_is_new = workspace is None
    if workspace is None:
        workspace = Workspace(client_id=f"ws_{suffix}", name=f"{name_prefix} {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"query_user_{suffix}",
        email=f"query_{suffix}@example.com",
        password="secret",
    )
    db_session.add(user)
    if workspace_is_new:
        db_session.add(workspace)
    await db_session.flush()
    return workspace, user


async def _add_member(db_session, workspace, user):
    role = await db_session.scalar(select(Role).where(Role.name == RoleNameEnum.WORKER))
    if role is None:
        role = Role(name=RoleNameEnum.WORKER)
        db_session.add(role)
        await db_session.flush()
    workspace_role = await db_session.scalar(
        select(WorkspaceRole).where(
            WorkspaceRole.workspace_id == workspace.client_id,
            WorkspaceRole.role_id == role.client_id,
            WorkspaceRole.specialization.is_(None),
        )
    )
    if workspace_role is None:
        workspace_role = WorkspaceRole(
            workspace_id=workspace.client_id,
            role_id=role.client_id,
        )
        db_session.add(workspace_role)
        await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            workspace_role_id=workspace_role.client_id,
            is_active=True,
        )
    )
    await db_session.flush()


@pytest.mark.integration
async def test_list_pause_reasons_returns_offset_pagination_and_workspace_scope(
    db_session,
):
    workspace, user = await _seed_workspace(db_session, "Query workspace")
    other_workspace, other_user = await _seed_workspace(db_session, "Other workspace")
    await seed_pause_reasons(db_session, workspace.client_id)

    ctx = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id},
        # Offset 2, not 1: the seed now holds four PERSONAL rows (lunch, coffee, meeting, other),
        # and this case is about the tail page — the one that exhausts the set and reports
        # has_more False.
        query_params={
            "limit": 2,
            "offset": 2,
            "pause_type": PauseTypeEnum.PERSONAL.value,
        },
        incoming_data={},
        session=db_session,
    )
    result = await list_pause_reasons(ctx)

    assert len(result["pause_reasons"]) == 2
    assert result["pause_reasons_pagination"] == {
        "has_more": False,
        "limit": 2,
        "offset": 2,
    }
    assert all(row["pause_type"] == "personal" for row in result["pause_reasons"])
    other_ctx = ServiceContext(
        identity={
            "workspace_id": other_workspace.client_id,
            "user_id": other_user.client_id,
        },
        query_params={"limit": 50, "offset": 0},
        incoming_data={},
        session=db_session,
    )
    assert (await list_pause_reasons(other_ctx))["pause_reasons"] == []


@pytest.mark.integration
async def test_list_pause_reasons_filters_all_ids_with_unrestricted_fallback(
    db_session,
):
    workspace, user = await _seed_workspace(db_session, "Query workspace")
    await _add_member(db_session, workspace, user)
    second_user = User(
        client_id=f"usr_{uuid4().hex[:8]}",
        username=f"query_second_{uuid4().hex[:8]}",
        email=f"query_second_{uuid4().hex[:8]}@example.com",
        password="secret",
    )
    db_session.add(second_user)
    await db_session.flush()
    await _add_member(db_session, workspace, second_user)

    section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"Query section {uuid4().hex[:8]}",
        created_by_id=user.client_id,
    )
    other_section = WorkingSection(
        workspace_id=workspace.client_id,
        name=f"Other query section {uuid4().hex[:8]}",
        created_by_id=user.client_id,
    )
    global_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Global {uuid4().hex[:8]}",
        slug=f"custom_global_{uuid4().hex[:8]}",
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
    )
    restricted_reason = PauseReason(
        workspace_id=workspace.client_id,
        name=f"Restricted {uuid4().hex[:8]}",
        slug=f"custom_restricted_{uuid4().hex[:8]}",
        pause_type=PauseTypeEnum.PERSONAL,
        is_system_managed=False,
    )
    db_session.add_all([section, other_section, global_reason, restricted_reason])
    await db_session.flush()
    db_session.add_all(
        [
            PauseReasonUserLink(
                workspace_id=workspace.client_id,
                pause_reason_id=restricted_reason.client_id,
                user_id=user.client_id,
            ),
            PauseReasonWorkingSectionLink(
                workspace_id=workspace.client_id,
                pause_reason_id=restricted_reason.client_id,
                working_section_id=section.client_id,
            ),
        ]
    )
    await db_session.flush()

    async def listed_ids(*, user_ids, section_ids):
        result = await list_pause_reasons(
            ServiceContext(
                identity={
                    "workspace_id": workspace.client_id,
                    "user_id": user.client_id,
                },
                query_params={
                    "limit": 200,
                    "offset": 0,
                    "user_ids": user_ids,
                    "working_section_ids": section_ids,
                },
                incoming_data={},
                session=db_session,
            )
        )
        return {row["client_id"]: row for row in result["pause_reasons"]}

    matching = await listed_ids(
        user_ids=[user.client_id], section_ids=[section.client_id]
    )
    assert global_reason.client_id in matching
    assert restricted_reason.client_id in matching
    assert matching[restricted_reason.client_id]["linked_user_ids"] == [user.client_id]
    assert matching[restricted_reason.client_id]["linked_working_section_ids"] == [
        section.client_id
    ]

    wrong_section = await listed_ids(
        user_ids=[user.client_id], section_ids=[other_section.client_id]
    )
    assert global_reason.client_id in wrong_section
    assert restricted_reason.client_id not in wrong_section

    all_users = await listed_ids(
        user_ids=[user.client_id, second_user.client_id],
        section_ids=[section.client_id],
    )
    assert global_reason.client_id in all_users
    assert restricted_reason.client_id not in all_users

    unknown = await listed_ids(user_ids=["usr_unknown"], section_ids=["wsec_unknown"])
    assert global_reason.client_id in unknown
    assert restricted_reason.client_id not in unknown
