"""Each process names its connections and logs its connection peak (Step 12 budget).

Staging and production share one RDS instance with max_connections=79, so the
per-service pool limits are a budget. These two signals are how it is checked:
`application_name` attributes every connection in pg_stat_activity to a process, and
`db_pool_peak` logs the most connections a process ever held at once.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import types

import pytest
from sqlalchemy import text

from beyo_manager.models import database

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.mark.parametrize(
    ("spec_name", "argv0", "expected"),
    [
        ("beyo_manager.workers.tasks_worker", "/app/x.py", "managerbeyo:tasks_worker"),
        (None, "/usr/local/bin/uvicorn", "managerbeyo:uvicorn"),
        (None, "run.py", "managerbeyo:run"),
    ],
)
async def test_application_name_is_the_process(monkeypatch, spec_name, argv0, expected):
    main = types.ModuleType("__main__")
    main.__spec__ = types.SimpleNamespace(name=spec_name) if spec_name else None
    monkeypatch.setitem(sys.modules, "__main__", main)
    monkeypatch.setattr(sys, "argv", [argv0])

    assert database._application_name() == expected


async def test_connections_carry_the_name_and_the_peak_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(database, "_application_name", lambda: "managerbeyo:probe")
    await database.init_db()

    async def hold(seconds):
        async for session in database.get_db_session():
            name = await session.scalar(text("select current_setting('application_name')"))
            await asyncio.sleep(seconds)
            return name

    # Root level only: the logger must be visible at INFO without being set itself
    # (a logger under "sqlalchemy" is not, because SQLAlchemy sets it to WARNING).
    with caplog.at_level(logging.INFO):
        names = await asyncio.gather(hold(0.2), hold(0.2), hold(0.2))
        await hold(0)  # fewer than the peak: no new line

    assert set(names) == {"managerbeyo:probe"}
    peaks = [r.getMessage() for r in caplog.records if r.getMessage().startswith("db_pool_peak")]
    counts = [int(p.split("checked_out=")[1].split()[0]) for p in peaks]
    # Concurrent checkouts may be seen together, so only the order and the top are fixed.
    assert counts == sorted(set(counts))
    assert peaks[-1].startswith("db_pool_peak | application=managerbeyo:probe checked_out=3 ")
