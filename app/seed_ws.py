import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO workspaces (client_id, name, time_zone, created_at)
            VALUES ('ws_test', 'workspace_test_fixture', 'UTC', NOW())
            ON CONFLICT (client_id) DO NOTHING
        """))
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
    print('WS_TEST_SEEDED')
