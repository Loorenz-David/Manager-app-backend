"""Apply Postgres triggers required for LISTEN/NOTIFY task wakeup.

Run once after `alembic upgrade head`:
    python scripts/apply_db_triggers.py

The trigger fires pg_notify('task_open', task_id) on every INSERT and
state UPDATE to 'open' on execution_tasks, waking the task router immediately
rather than waiting for the fallback poll interval.
"""
import asyncio

import asyncpg

from beyo_manager.config import settings

_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION notify_task_open()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify('task_open', NEW.client_id::text);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_task_open ON execution_tasks;

CREATE TRIGGER trg_task_open
AFTER INSERT OR UPDATE OF state ON execution_tasks
FOR EACH ROW WHEN (NEW.state = 'open')
EXECUTE FUNCTION notify_task_open();
"""


async def _apply() -> None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(_TRIGGER_SQL)
        print("[apply_db_triggers] Trigger trg_task_open applied.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(_apply())
