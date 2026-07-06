import asyncio

from beyo_manager.core.logging.config import configure_logging
from beyo_manager.models.database import init_db
from beyo_manager.services.infra.email_idle.supervisor import run_email_idle_watcher


async def main() -> None:
    configure_logging()
    await init_db()
    await run_email_idle_watcher()


if __name__ == "__main__":
    asyncio.run(main())
