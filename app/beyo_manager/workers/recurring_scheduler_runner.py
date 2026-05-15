import asyncio

from beyo_manager.models.database import init_db
from beyo_manager.services.infra.schedulers.recurring_scheduler_runner import run_recurring_scheduler_runner


async def main() -> None:
    await init_db()
    await run_recurring_scheduler_runner()


if __name__ == "__main__":
    asyncio.run(main())
