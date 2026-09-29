import asyncio

from beyo_manager.models.database import init_db
from beyo_manager.workers.heartbeat import start_heartbeat
from beyo_manager.services.infra.schedulers.delayed_scheduler_runner import run_delayed_scheduler_runner


async def main() -> None:
    await init_db()
    start_heartbeat()
    await run_delayed_scheduler_runner()


if __name__ == "__main__":
    asyncio.run(main())
