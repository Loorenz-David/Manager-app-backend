"""The migration job runs its steps in order and stops at the first failure.

A failed `alembic upgrade head` must not be followed by the trigger step, and any
failure must surface as a non-zero exit so a deployment stops before replacing the
application. No database here: the step runner is a recorder.
"""

from __future__ import annotations

import pytest

from beyo_manager.config import settings
from scripts import migrate as migrate_module

pytestmark = pytest.mark.unit


def _recording_runner(returncodes: dict[str, int]):
    calls: list[str] = []

    def runner(argv):
        name = "alembic" if "alembic" in argv else "triggers"
        calls.append(name)
        return returncodes.get(name, 0)

    return runner, calls


def test_steps_run_alembic_then_triggers():
    runner, calls = _recording_runner({})

    assert migrate_module.run_steps(runner) == migrate_module.EXIT_OK
    assert calls == ["alembic", "triggers"]


def test_alembic_failure_stops_before_triggers():
    runner, calls = _recording_runner({"alembic": 1})

    assert migrate_module.run_steps(runner) == migrate_module.EXIT_STEP_FAILED
    assert calls == ["alembic"]


def test_trigger_failure_is_reported():
    runner, calls = _recording_runner({"triggers": 2})

    assert migrate_module.run_steps(runner) == migrate_module.EXIT_STEP_FAILED
    assert calls == ["alembic", "triggers"]


def test_steps_use_the_current_interpreter_not_path_lookup():
    for _, argv in migrate_module.STEPS:
        assert argv[0] == migrate_module.sys.executable
        assert argv[1] == "-m"


def test_code_heads_matches_the_migration_graph():
    heads = migrate_module.code_heads()
    assert len(heads) == 1


def test_error_messages_mask_the_database_password(monkeypatch):
    password = "Pa55-word-that-must-not-leak"
    monkeypatch.setattr(
        settings,
        "database_url",
        f"postgresql+asyncpg://app:{password}@db.internal:5432/x",
    )

    message = migrate_module._safe_error(
        RuntimeError(f"could not connect with {password} to db.internal")
    )

    assert password not in message
    assert "db.internal" in message
