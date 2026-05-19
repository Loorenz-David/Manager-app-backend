"""Analytics worker — consumes step transition events and updates metrics tables."""

import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.analytics.process_step_transition import handle_process_step_transition

HANDLER_MAP = {
    TaskType.PROCESS_STEP_TRANSITION: handle_process_step_transition,
}


async def main() -> None:
    await init_db()
    await run_worker("queue:analytics", HANDLER_MAP)


if __name__ == "__main__":
    asyncio.run(main())
