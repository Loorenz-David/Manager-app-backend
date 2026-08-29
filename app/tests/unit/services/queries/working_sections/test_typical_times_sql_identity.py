"""Byte-identity guard for the no-spec typical-times statement.

The snapshot was captured before the item-aware refactor and held byte-identical
through it (HC-4). It was deliberately re-baselined once for the quantity
normalization change, which added the PRIMARY-item joins and the additive
typical_unit_worker_seconds column to the no-spec branch; it must not be
regenerated for anything short of another owner-approved statement change.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    typical_times_statement,
)


SNAPSHOT_PATH = Path(__file__).with_name("snapshots") / "typical_times_no_spec_sql.txt"


def compile_typical_times_sql(*, now: datetime | None = None) -> str:
    return str(typical_times_statement("ws_snapshot", now=now).compile(dialect=postgresql.dialect()))


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"now": datetime(2026, 8, 22, tzinfo=timezone.utc)}, {"specs": ()}],
    ids=["default-clock", "injected-clock", "explicit-no-spec"],
)
def test_typical_times_statement_matches_pre_refactor_snapshot_at_both_clock_forms(kwargs):
    snapshot = SNAPSHOT_PATH.read_text()

    assert str(typical_times_statement("ws_snapshot", **kwargs).compile(dialect=postgresql.dialect())) == snapshot
