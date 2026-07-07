from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.enums import ItemStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.analytics.user_section_daily_work_stats import UserSectionDailyWorkStats
from beyo_manager.models.tables.analytics.working_section_daily_work_stats import WorkingSectionDailyWorkStats
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.working_sections.working_section_dependency import WorkingSectionDependency
from beyo_manager.models.tables.working_sections.working_section_item_category import (
    WorkingSectionItemCategory,
)
from beyo_manager.models.tables.working_sections.working_section_membership import (
    WorkingSectionMembership,
)
from beyo_manager.models.tables.working_sections.working_section_supported_issue_type import (
    WorkingSectionSupportedIssueType,
)
from beyo_manager.services.commands.bootstrap.phases.seed_issue_type_links import seed_issue_type_links
from beyo_manager.services.commands.bootstrap.phases.seed_issue_types import seed_issue_types
from beyo_manager.services.commands.bootstrap.phases.seed_item_categories import seed_item_categories
from beyo_manager.services.commands.bootstrap.phases.seed_working_section_item_categories import (
    seed_working_section_item_categories,
)
from beyo_manager.services.commands.bootstrap.phases.seed_working_sections import seed_working_sections


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


async def _seed_bootstrap_phase_data(db_session, workspace_id: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    item_category_ids = await seed_item_categories(db_session, workspace_id)
    issue_type_ids = await seed_issue_types(db_session, workspace_id)
    section_ids = await seed_working_sections(db_session, workspace_id)
    await seed_issue_type_links(
        db_session,
        workspace_id,
        issue_type_ids,
        item_category_ids,
        section_ids,
    )
    await seed_working_section_item_categories(
        db_session,
        workspace_id,
        section_ids,
        item_category_ids,
    )
    return item_category_ids, issue_type_ids, section_ids


@pytest.mark.integration
async def test_seed_working_sections_soft_deletes_obsolete_sanding_and_preserves_history(db_session):
    workspace, user = await _seed_workspace_and_user(db_session)
    item_category_ids, issue_type_ids, _ = await _seed_bootstrap_phase_data(db_session, workspace.client_id)

    sanding = WorkingSection(
        workspace_id=workspace.client_id,
        name="sanding",
        image="legacy-image",
        order_list=4,
        allows_batch_working=False,
    )
    db_session.add(sanding)
    await db_session.flush()

    structural_repair_id = await db_session.scalar(
        select(WorkingSection.client_id).where(
            WorkingSection.workspace_id == workspace.client_id,
            WorkingSection.name == "structural repair",
            WorkingSection.is_deleted.is_(False),
        )
    )
    assembly_id = await db_session.scalar(
        select(WorkingSection.client_id).where(
            WorkingSection.workspace_id == workspace.client_id,
            WorkingSection.name == "assembly",
            WorkingSection.is_deleted.is_(False),
        )
    )
    dining_chairs_id = item_category_ids["Dining Chairs"]
    scratches_id = issue_type_ids["Scratches"]

    db_session.add_all(
        [
            WorkingSectionDependency(
                workspace_id=workspace.client_id,
                dependent_section_id=sanding.client_id,
                prerequisite_section_id=structural_repair_id,
            ),
            WorkingSectionDependency(
                workspace_id=workspace.client_id,
                dependent_section_id=assembly_id,
                prerequisite_section_id=sanding.client_id,
            ),
            WorkingSectionSupportedIssueType(
                workspace_id=workspace.client_id,
                working_section_id=sanding.client_id,
                issue_type_id=scratches_id,
            ),
            WorkingSectionItemCategory(
                workspace_id=workspace.client_id,
                working_section_id=sanding.client_id,
                item_category_id=dining_chairs_id,
            ),
            WorkingSectionMembership(
                workspace_id=workspace.client_id,
                working_section_id=sanding.client_id,
                user_id=user.client_id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by_id=user.client_id,
            ),
        ]
    )
    await db_session.flush()

    task = Task(
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
        created_by_id=user.client_id,
    )
    db_session.add(task)
    await db_session.flush()

    task_step = TaskStep(
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        state=TaskStepStateEnum.PENDING,
        readiness_status=TaskStepReadinessStatusEnum.READY,
        working_section_id=sanding.client_id,
        total_dependencies=0,
        completed_dependencies=0,
        working_section_name_snapshot="sanding",
        allows_batch_working=False,
        created_by_id=user.client_id,
    )
    db_session.add(task_step)
    await db_session.flush()

    item = Item(
        workspace_id=workspace.client_id,
        item_category_id=dining_chairs_id,
        state=ItemStateEnum.PENDING,
        item_category_snapshot="Dining Chairs",
        item_major_category_snapshot="seat",
        created_by_id=user.client_id,
    )
    db_session.add(item)
    await db_session.flush()

    item_issue = ItemIssue(
        workspace_id=workspace.client_id,
        item_id=item.client_id,
        step_id=task_step.client_id,
        worker_id=user.client_id,
        working_section_id=sanding.client_id,
        item_category_id=dining_chairs_id,
        issue_type_id=scratches_id,
        issue_type_snapshot="Scratches",
        issue_mode_snapshot="graded",
        placement_of_issue_snapshot="frame",
        intensity=1,
    )
    db_session.add(item_issue)
    db_session.add(
        WorkingSectionDailyWorkStats(
            workspace_id=workspace.client_id,
            working_section_id=sanding.client_id,
            section_name_snapshot="sanding",
            work_date=date(2026, 7, 7),
        )
    )
    db_session.add(
        UserSectionDailyWorkStats(
            workspace_id=workspace.client_id,
            user_id=user.client_id,
            working_section_id=sanding.client_id,
            section_name_snapshot="sanding",
            user_display_name_snapshot=user.username,
            work_date=date(2026, 7, 7),
        )
    )
    await db_session.flush()

    await seed_working_sections(db_session, workspace.client_id)

    refreshed_sanding = await db_session.scalar(
        select(WorkingSection).where(WorkingSection.client_id == sanding.client_id)
    )
    assert refreshed_sanding is not None
    assert refreshed_sanding.is_deleted is True
    assert refreshed_sanding.deleted_at is not None

    dependencies = (
        await db_session.execute(
            select(WorkingSectionDependency).where(
                WorkingSectionDependency.workspace_id == workspace.client_id,
                (
                    (WorkingSectionDependency.dependent_section_id == sanding.client_id)
                    | (WorkingSectionDependency.prerequisite_section_id == sanding.client_id)
                ),
            )
        )
    ).scalars().all()
    assert dependencies == []

    issue_links = (
        await db_session.execute(
            select(WorkingSectionSupportedIssueType).where(
                WorkingSectionSupportedIssueType.workspace_id == workspace.client_id,
                WorkingSectionSupportedIssueType.working_section_id == sanding.client_id,
            )
        )
    ).scalars().all()
    assert issue_links == []

    item_category_links = (
        await db_session.execute(
            select(WorkingSectionItemCategory).where(
                WorkingSectionItemCategory.workspace_id == workspace.client_id,
                WorkingSectionItemCategory.working_section_id == sanding.client_id,
            )
        )
    ).scalars().all()
    assert item_category_links == []

    membership = await db_session.scalar(
        select(WorkingSectionMembership).where(
            WorkingSectionMembership.workspace_id == workspace.client_id,
            WorkingSectionMembership.working_section_id == sanding.client_id,
            WorkingSectionMembership.user_id == user.client_id,
        )
    )
    assert membership is not None
    assert membership.removed_at is not None

    preserved_task_step = await db_session.scalar(select(TaskStep).where(TaskStep.client_id == task_step.client_id))
    preserved_item_issue = await db_session.scalar(select(ItemIssue).where(ItemIssue.client_id == item_issue.client_id))
    preserved_daily_stats = await db_session.scalar(
        select(WorkingSectionDailyWorkStats).where(
            WorkingSectionDailyWorkStats.workspace_id == workspace.client_id,
            WorkingSectionDailyWorkStats.working_section_id == sanding.client_id,
        )
    )
    preserved_user_daily_stats = await db_session.scalar(
        select(UserSectionDailyWorkStats).where(
            UserSectionDailyWorkStats.workspace_id == workspace.client_id,
            UserSectionDailyWorkStats.working_section_id == sanding.client_id,
        )
    )
    assert preserved_task_step is not None
    assert preserved_item_issue is not None
    assert preserved_daily_stats is not None
    assert preserved_user_daily_stats is not None


@pytest.mark.integration
async def test_seed_working_sections_restores_soft_deleted_managed_section(db_session):
    workspace, _ = await _seed_workspace_and_user(db_session)
    assembly = WorkingSection(
        workspace_id=workspace.client_id,
        name="assembly",
        image="old-image",
        order_list=999,
        allows_batch_working=True,
        is_deleted=True,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(assembly)
    await db_session.flush()

    section_ids = await seed_working_sections(db_session, workspace.client_id)

    refreshed_assembly = await db_session.scalar(
        select(WorkingSection).where(WorkingSection.client_id == assembly.client_id)
    )
    assert refreshed_assembly is not None
    assert refreshed_assembly.client_id == section_ids["assembly"]
    assert refreshed_assembly.is_deleted is False
    assert refreshed_assembly.deleted_at is None
    assert refreshed_assembly.order_list == 8
    assert refreshed_assembly.allows_batch_working is False
    assert refreshed_assembly.image is not None


@pytest.mark.integration
async def test_seed_working_sections_syncs_managed_relations_without_touching_custom_sections(db_session):
    workspace, _ = await _seed_workspace_and_user(db_session)
    item_category_ids, issue_type_ids, section_ids = await _seed_bootstrap_phase_data(db_session, workspace.client_id)

    custom_section = WorkingSection(
        workspace_id=workspace.client_id,
        name="custom polishing",
        image="custom-image",
        order_list=42,
        allows_batch_working=False,
    )
    db_session.add(custom_section)
    await db_session.flush()

    cleaning_seat_id = section_ids["cleaning seat"]
    disassembly_id = section_ids["disassembly"]
    photography_id = section_ids["photography"]
    dining_chairs_id = item_category_ids["Dining Chairs"]
    scratches_id = issue_type_ids["Scratches"]

    db_session.add_all(
        [
            WorkingSectionDependency(
                workspace_id=workspace.client_id,
                dependent_section_id=cleaning_seat_id,
                prerequisite_section_id=photography_id,
            ),
            WorkingSectionDependency(
                workspace_id=workspace.client_id,
                dependent_section_id=custom_section.client_id,
                prerequisite_section_id=disassembly_id,
            ),
            WorkingSectionSupportedIssueType(
                workspace_id=workspace.client_id,
                working_section_id=cleaning_seat_id,
                issue_type_id=scratches_id,
            ),
            WorkingSectionSupportedIssueType(
                workspace_id=workspace.client_id,
                working_section_id=custom_section.client_id,
                issue_type_id=scratches_id,
            ),
            WorkingSectionItemCategory(
                workspace_id=workspace.client_id,
                working_section_id=cleaning_seat_id,
                item_category_id=item_category_ids["Dining Tables"],
            ),
            WorkingSectionItemCategory(
                workspace_id=workspace.client_id,
                working_section_id=custom_section.client_id,
                item_category_id=dining_chairs_id,
            ),
        ]
    )
    await db_session.flush()

    reseeded_section_ids = await seed_working_sections(db_session, workspace.client_id)
    await seed_issue_type_links(
        db_session,
        workspace.client_id,
        issue_type_ids,
        item_category_ids,
        reseeded_section_ids,
    )
    await seed_working_section_item_categories(
        db_session,
        workspace.client_id,
        reseeded_section_ids,
        item_category_ids,
    )

    stale_dependency = await db_session.scalar(
        select(WorkingSectionDependency).where(
            WorkingSectionDependency.workspace_id == workspace.client_id,
            WorkingSectionDependency.dependent_section_id == cleaning_seat_id,
            WorkingSectionDependency.prerequisite_section_id == photography_id,
        )
    )
    custom_dependency = await db_session.scalar(
        select(WorkingSectionDependency).where(
            WorkingSectionDependency.workspace_id == workspace.client_id,
            WorkingSectionDependency.dependent_section_id == custom_section.client_id,
            WorkingSectionDependency.prerequisite_section_id == disassembly_id,
        )
    )
    stale_issue_link = await db_session.scalar(
        select(WorkingSectionSupportedIssueType).where(
            WorkingSectionSupportedIssueType.workspace_id == workspace.client_id,
            WorkingSectionSupportedIssueType.working_section_id == cleaning_seat_id,
            WorkingSectionSupportedIssueType.issue_type_id == scratches_id,
        )
    )
    custom_issue_link = await db_session.scalar(
        select(WorkingSectionSupportedIssueType).where(
            WorkingSectionSupportedIssueType.workspace_id == workspace.client_id,
            WorkingSectionSupportedIssueType.working_section_id == custom_section.client_id,
            WorkingSectionSupportedIssueType.issue_type_id == scratches_id,
        )
    )
    stale_item_category_link = await db_session.scalar(
        select(WorkingSectionItemCategory).where(
            WorkingSectionItemCategory.workspace_id == workspace.client_id,
            WorkingSectionItemCategory.working_section_id == cleaning_seat_id,
            WorkingSectionItemCategory.item_category_id == item_category_ids["Dining Tables"],
        )
    )
    custom_item_category_link = await db_session.scalar(
        select(WorkingSectionItemCategory).where(
            WorkingSectionItemCategory.workspace_id == workspace.client_id,
            WorkingSectionItemCategory.working_section_id == custom_section.client_id,
            WorkingSectionItemCategory.item_category_id == dining_chairs_id,
        )
    )

    expected_dependency = await db_session.scalar(
        select(WorkingSectionDependency).where(
            WorkingSectionDependency.workspace_id == workspace.client_id,
            WorkingSectionDependency.dependent_section_id == cleaning_seat_id,
            WorkingSectionDependency.prerequisite_section_id == disassembly_id,
        )
    )

    assert stale_dependency is None
    assert custom_dependency is not None
    assert stale_issue_link is None
    assert custom_issue_link is not None
    assert stale_item_category_link is None
    assert custom_item_category_link is not None
    assert expected_dependency is not None
