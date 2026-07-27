"""Single source of truth for a task's auxiliary instances (post-handling and
customer coordination) given its current type/source.

Called from every place that can change whether those instances *should* exist:
  * ``maybe_evaluate_task_ready`` — on the ``… -> READY`` transition
  * ``update_task`` — when a type/source-affecting field changes on a READY task

Idempotent and safe to call repeatedly: each ``_create_*`` helper early-returns
when a non-completed instance already exists, and the post-handling state sync
no-ops when there is nothing to change. New READY-conditional side effects should
be added here so the two call sites cannot drift.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.commands.task_customer_coordination._create_customer_coordination_in_session import (
    _create_customer_coordination_in_session,
)
from beyo_manager.services.commands.task_customer_coordination._teardown_customer_coordination_in_session import (
    _teardown_customer_coordination_in_session,
)
from beyo_manager.services.commands.task_post_handling._create_post_handling_in_session import (
    _create_post_handling_in_session,
)
from beyo_manager.services.commands.task_post_handling._sync_post_handling_state_in_session import (
    _sync_post_handling_state_in_session,
)
from beyo_manager.services.commands.task_post_handling._teardown_post_handling_in_session import (
    _teardown_post_handling_in_session,
)


async def reconcile_task_side_effects(
    session: AsyncSession,
    task: Task,
    *,
    workspace_id: str,
    now: datetime,
    user_id: str,
    username_snapshot: str | None = None,
) -> None:
    """Bring a task's auxiliary instances in line with its current fields.

    The caller owns the transaction (invoke inside a ``maybe_begin`` block).
    """
    # Auxiliary instances belong to the post-completion process, which only begins
    # once the task is READY. Creating them earlier would front-run the READY
    # transition that owns the invariant. Both creates are type/source-gated and
    # idempotent, so this covers "task changed into a qualifying type while READY".
    if task.state == TaskStateEnum.READY:
        await _create_post_handling_in_session(
            session,
            task,
            workspace_id=workspace_id,
            now=now,
            user_id=user_id,
            username_snapshot=username_snapshot,
        )
        await _create_customer_coordination_in_session(
            session,
            task,
            workspace_id=workspace_id,
            now=now,
            user_id=user_id,
            username_snapshot=username_snapshot,
        )

    # Keep an existing post-handling's state aligned with the task's current fields
    # (e.g. fulfillment_method / assortment edits flip PENDING <-> FILLED). Safe in
    # any non-terminal state; no-ops when there is no instance or nothing changed.
    await _sync_post_handling_state_in_session(
        session,
        task.client_id,
        workspace_id=workspace_id,
        now=now,
        user_id=user_id,
        username_snapshot=username_snapshot,
    )

    # Reverse direction: a type/source change may have made an existing instance no
    # longer applicable. Hard-delete such non-completed instances (with a history
    # record). Applicability is purely type/source-based, so this runs regardless of
    # state and no-ops whenever the task still requires the instance. Complementary
    # to the creates above — for a given instance only one side ever does work.
    await _teardown_post_handling_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=user_id,
        username_snapshot=username_snapshot,
    )
    await _teardown_customer_coordination_in_session(
        session,
        task,
        workspace_id=workspace_id,
        now=now,
        user_id=user_id,
        username_snapshot=username_snapshot,
    )
