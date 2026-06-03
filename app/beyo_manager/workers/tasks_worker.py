import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.task_steps.finalize_pending_step_completion import (
    handle_finalize_pending_step_completion,
)

HANDLER_MAP = {
    TaskType.DELAYED_STEP_COMPLETION: handle_finalize_pending_step_completion,
}


async def main() -> None:
    await init_db()
    await run_worker("queue:tasks", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
