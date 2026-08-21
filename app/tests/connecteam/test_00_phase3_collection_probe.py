from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.phase3_collection_probe(position="prefix")
async def test_phase3_collection_probe_prefix(db_session, redis_client, isolated_redis_prefix):
    assert await db_session.scalar(text("SELECT 1")) == 1
    key = f"{isolated_redis_prefix}:phase3:collection-probe:prefix"
    redis_client.set(key, "1")
    assert redis_client.get(key) == "1"
