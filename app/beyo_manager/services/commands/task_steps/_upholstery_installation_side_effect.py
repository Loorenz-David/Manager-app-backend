"""TEMPORARY bridge: a step transition in the "upholstery installation" working
section automatically advances that task's primary item's fabric requirement(s)
in lockstep, so fabric stock consumption doesn't depend on a separate manual
action (`POST /item-upholsteries/{id}/mark-in-use` / `/complete`) that in
practice was never being called.

Scope, deliberately narrow (see conversation record — revisit before generalizing):
  * Section match is by name (`working_section_name_snapshot`), case-insensitive,
    since working sections are workspace-defined and only the name is stable
    across workspaces — there is no fixed cross-workspace id to match on.
  * WORKING    -> promotes AVAILABLE requirements to IN_USE (`consume_to_in_use`).
  * COMPLETED  -> promotes IN_USE/AVAILABLE requirements to COMPLETED
    (`finish_in_use` / `complete_available_direct`).
  * Only the task's PRIMARY item is considered; RELATED items are ignored.
  * The "upholstery removal" section is out of scope — reversing fabric on
    removal is a separate, more involved flow.

Always a silent no-op when there's nothing to do (no primary item, no
upholstery on it, no requirement in the expected state) — this runs as a side
effect of a step transition and must never be the reason that transition fails.
The one exception is `consume_to_in_use`'s insufficient-stock guard, which is
deliberately allowed to raise: starting installation work without enough fabric
in stock is a real error, not something to swallow.

Call sites (three today):
  * `transition_step_state.py`    — worker-facing single-step transition.
  * `_step_transition_core.py`    — shared core behind the batch transition route.
  * `force_task_ready.py`         — calls this with `new_state=COMPLETED` even
    though the step itself is being closed as SKIPPED. See that file's inline
    comment for the (business, not structural) reasoning and its expiry
    condition.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskItemRoleEnum
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import ItemUpholsteryRequirement
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.services.commands.upholstery._inventory_mutations import (
    complete_available_direct,
    consume_to_in_use,
    finish_in_use,
)
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent

_UPHOLSTERY_INSTALLATION_SECTION_NAME = "upholstery installation"

_PROMOTABLE_TO_IN_USE = frozenset({ItemUpholsteryRequirementStateEnum.AVAILABLE})
_PROMOTABLE_TO_COMPLETED = frozenset(
    {ItemUpholsteryRequirementStateEnum.IN_USE, ItemUpholsteryRequirementStateEnum.AVAILABLE}
)


async def apply_upholstery_installation_side_effect(
    session: AsyncSession,
    *,
    workspace_id: str,
    task_id: str,
    step: TaskStep,
    new_state: TaskStepStateEnum,
    actor_id: str,
    now: datetime,
) -> list[WorkspaceEvent]:
    if new_state not in (TaskStepStateEnum.WORKING, TaskStepStateEnum.COMPLETED):
        return []
    section_name = (step.working_section_name_snapshot or "").strip().lower()
    if section_name != _UPHOLSTERY_INSTALLATION_SECTION_NAME:
        return []

    primary_task_item = (
        await session.execute(
            select(TaskItem).where(
                TaskItem.workspace_id == workspace_id,
                TaskItem.task_id == task_id,
                TaskItem.role == TaskItemRoleEnum.PRIMARY,
                TaskItem.removed_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if primary_task_item is None:
        return []

    item_upholsteries = (
        await session.execute(
            select(ItemUpholstery).where(
                ItemUpholstery.workspace_id == workspace_id,
                ItemUpholstery.item_id == primary_task_item.item_id,
                ItemUpholstery.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    if not item_upholsteries:
        return []

    target_state = (
        ItemUpholsteryRequirementStateEnum.IN_USE
        if new_state == TaskStepStateEnum.WORKING
        else ItemUpholsteryRequirementStateEnum.COMPLETED
    )

    events: list[WorkspaceEvent] = []
    for iup in item_upholsteries:
        changed = await _promote_requirements(
            session,
            workspace_id=workspace_id,
            item_upholstery_id=iup.client_id,
            target_state=target_state,
            actor_id=actor_id,
            now=now,
        )
        if changed:
            events.append(
                WorkspaceEvent(
                    event_name="item:upholstery-requirement-state-changed",
                    client_id=iup.client_id,
                    workspace_id=workspace_id,
                    extra={"new_state": target_state.value},
                )
            )
    return events


async def _promote_requirements(
    session: AsyncSession,
    *,
    workspace_id: str,
    item_upholstery_id: str,
    target_state: ItemUpholsteryRequirementStateEnum,
    actor_id: str,
    now: datetime,
) -> bool:
    source_states = (
        _PROMOTABLE_TO_IN_USE
        if target_state == ItemUpholsteryRequirementStateEnum.IN_USE
        else _PROMOTABLE_TO_COMPLETED
    )
    requirements = (
        await session.execute(
            select(ItemUpholsteryRequirement).where(
                ItemUpholsteryRequirement.workspace_id == workspace_id,
                ItemUpholsteryRequirement.item_upholstery_id == item_upholstery_id,
                ItemUpholsteryRequirement.state.in_(source_states),
                ItemUpholsteryRequirement.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    if not requirements:
        return False

    for req in requirements:
        if req.upholstery_inventory_id is not None:
            await _apply_inventory_mutation(session, req, target_state, workspace_id)
        req.state = target_state
        req.updated_by_id = actor_id
        if target_state == ItemUpholsteryRequirementStateEnum.IN_USE:
            req.in_use_at = now
        else:
            req.completed_at = now
    return True


async def _apply_inventory_mutation(
    session: AsyncSession,
    req: ItemUpholsteryRequirement,
    target_state: ItemUpholsteryRequirementStateEnum,
    workspace_id: str,
) -> None:
    if target_state == ItemUpholsteryRequirementStateEnum.IN_USE:
        await consume_to_in_use(
            session=session,
            workspace_id=workspace_id,
            upholstery_inventory_id=req.upholstery_inventory_id,
            quantity=req.amount_meters,
        )
        return

    if req.state == ItemUpholsteryRequirementStateEnum.IN_USE:
        await finish_in_use(
            session=session,
            workspace_id=workspace_id,
            upholstery_inventory_id=req.upholstery_inventory_id,
            quantity=req.amount_meters,
            source=req.source,
        )
    else:
        await complete_available_direct(
            session=session,
            workspace_id=workspace_id,
            upholstery_inventory_id=req.upholstery_inventory_id,
            quantity=req.amount_meters,
            source=req.source,
        )
