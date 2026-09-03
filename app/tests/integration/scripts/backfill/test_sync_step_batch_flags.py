from uuid import uuid4

import pytest

from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum, TaskTypeEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace import Workspace
from scripts.backfill.sync_step_batch_flags import sync_step_batch_flags


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_drifted_section(db_session, *, section_flag: bool):
    """A section whose steps all carry the OPPOSITE flag — one per state of interest.

    Mirrors the photography drift: the section was flipped after its steps were
    created, so every step still holds the pre-flip snapshot.
    """
    suffix = uuid4().hex[:10]
    workspace = Workspace(
        client_id=f"ws_{suffix}",
        name=f"Batch flag workspace {suffix}",
    )
    db_session.add(workspace)
    await db_session.flush()

    section = WorkingSection(
        client_id=f"wsc_{suffix}",
        workspace_id=workspace.client_id,
        name=f"batch-flag-section-{suffix}",
        allows_batch_working=section_flag,
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
    )
    db_session.add_all([section, task])
    await db_session.flush()

    states = [
        TaskStepStateEnum.PENDING,
        TaskStepStateEnum.WORKING,
        TaskStepStateEnum.PAUSED,
        TaskStepStateEnum.COMPLETED,
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.FAILED,
        TaskStepStateEnum.CANCELLED,
    ]
    steps = {}
    for index, state in enumerate(states):
        step = TaskStep(
            client_id=f"tsp_{suffix}_{index}",
            workspace_id=workspace.client_id,
            task_id=task.client_id,
            working_section_id=section.client_id,
            state=state,
            # the stale snapshot: the opposite of what the section now says
            allows_batch_working=not section_flag,
        )
        db_session.add(step)
        steps[state] = step
    await db_session.flush()

    return workspace, section, steps


@pytest.mark.parametrize("section_flag", [False, True])
async def test_execute_corrects_open_steps_only(db_session, section_flag):
    """Open steps are re-stamped; terminal steps keep their historical snapshot.

    A closed step's flag is the record of the rule it was worked under, and the
    analytics concurrency sweep divides a batchable interval's time across its
    overlaps while leaving a non-batch interval's whole. Rewriting closed steps
    would retroactively change worked-time attribution.
    """
    workspace, section, steps = await _seed_drifted_section(
        db_session, section_flag=section_flag
    )

    await sync_step_batch_flags(
        db_session,
        dry_run=False,
        workspace_id=workspace.client_id,
        section_id=section.client_id,
    )
    for step in steps.values():
        await db_session.refresh(step)

    open_states = [
        TaskStepStateEnum.PENDING,
        TaskStepStateEnum.WORKING,
        TaskStepStateEnum.PAUSED,
    ]
    for state in open_states:
        assert steps[state].allows_batch_working is section_flag, (
            f"open step in {state} should have been re-stamped"
        )

    terminal_states = [
        TaskStepStateEnum.COMPLETED,
        TaskStepStateEnum.SKIPPED,
        TaskStepStateEnum.FAILED,
        TaskStepStateEnum.CANCELLED,
    ]
    for state in terminal_states:
        assert steps[state].allows_batch_working is (not section_flag), (
            f"terminal step in {state} must keep its historical snapshot"
        )


async def test_dry_run_reports_drift_without_writing(db_session):
    workspace, section, steps = await _seed_drifted_section(
        db_session, section_flag=False
    )

    drifted = await sync_step_batch_flags(
        db_session,
        dry_run=True,
        workspace_id=workspace.client_id,
        section_id=section.client_id,
    )

    assert len(drifted) == 1
    assert drifted[0].section_id == section.client_id
    assert drifted[0].open_drifted == 3
    assert drifted[0].closed_drifted == 4

    for step in steps.values():
        await db_session.refresh(step)
        assert step.allows_batch_working is True, "dry run must not write"


async def test_is_idempotent_and_reports_no_drift_once_synced(db_session):
    workspace, section, _steps = await _seed_drifted_section(
        db_session, section_flag=False
    )

    await sync_step_batch_flags(
        db_session,
        dry_run=False,
        workspace_id=workspace.client_id,
        section_id=section.client_id,
    )

    # Second pass: only the untouched terminal steps still "differ", and they are
    # never repaired — so the open population is clean and stays clean.
    drifted = await sync_step_batch_flags(
        db_session,
        dry_run=True,
        workspace_id=workspace.client_id,
        section_id=section.client_id,
    )

    assert len(drifted) == 1
    assert drifted[0].open_drifted == 0
    assert drifted[0].closed_drifted == 4


async def test_leaves_sections_without_drift_alone(db_session):
    suffix = uuid4().hex[:10]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Clean workspace {suffix}")
    db_session.add(workspace)
    await db_session.flush()

    section = WorkingSection(
        client_id=f"wsc_{suffix}",
        workspace_id=workspace.client_id,
        name=f"clean-section-{suffix}",
        allows_batch_working=True,
    )
    task = Task(
        client_id=f"tsk_{suffix}",
        workspace_id=workspace.client_id,
        task_scalar_id=1,
        task_type=TaskTypeEnum.INTERNAL,
        state=TaskStateEnum.PENDING,
    )
    db_session.add_all([section, task])
    await db_session.flush()

    step = TaskStep(
        client_id=f"tsp_{suffix}",
        workspace_id=workspace.client_id,
        task_id=task.client_id,
        working_section_id=section.client_id,
        state=TaskStepStateEnum.PENDING,
        allows_batch_working=True,
    )
    db_session.add(step)
    await db_session.flush()

    drifted = await sync_step_batch_flags(
        db_session,
        dry_run=True,
        workspace_id=workspace.client_id,
        section_id=section.client_id,
    )

    assert drifted == []
