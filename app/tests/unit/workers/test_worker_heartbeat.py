"""The heartbeat file behind the worker container health checks.

Off unless WORKER_HEARTBEAT_FILE is set, so a host without it (the legacy server)
gets no new files; when set, it keeps the file fresh from the event loop.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from beyo_manager.config import settings
from beyo_manager.workers import heartbeat

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fresh_module_state(monkeypatch):
    monkeypatch.setattr(heartbeat, "_task", None)
    yield
    if heartbeat._task is not None:
        heartbeat._task.cancel()


async def test_unset_does_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "worker_heartbeat_file", None)

    heartbeat.start_heartbeat()

    assert heartbeat._task is None
    assert list(tmp_path.iterdir()) == []


async def test_set_keeps_the_file_fresh(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"
    monkeypatch.setattr(settings, "worker_heartbeat_file", str(path))
    monkeypatch.setattr(heartbeat, "HEARTBEAT_INTERVAL_SECONDS", 0.05)

    heartbeat.start_heartbeat()
    await asyncio.sleep(0.02)
    assert path.exists()
    first = os.stat(path).st_mtime_ns

    await asyncio.sleep(0.2)
    assert os.stat(path).st_mtime_ns > first


async def test_starting_twice_keeps_one_task(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "worker_heartbeat_file", str(tmp_path / "heartbeat"))

    heartbeat.start_heartbeat()
    first = heartbeat._task
    heartbeat.start_heartbeat()

    assert heartbeat._task is first
