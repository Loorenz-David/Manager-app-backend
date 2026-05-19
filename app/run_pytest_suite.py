import asyncio
import pytest
import sys
from beyo_manager.models.database import init_db, close_db

async def run_tests():
    await init_db()
    try:
        rc = pytest.main(["-x"])
    finally:
        await close_db()
    return rc

if __name__ == "__main__":
    rc = asyncio.run(run_tests())
    sys.exit(rc)
