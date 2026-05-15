import asyncio

from beyo_manager.models.database import init_db
from beyo_manager.services.infra.execution.task_router import run_task_router


async def main() -> None:
    await init_db()
    await run_task_router()


if __name__ == "__main__":
    asyncio.run(main())
