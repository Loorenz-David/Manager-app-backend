"""`state=` on `GET /snapshots/versions` (G-2, 2026-09-28): a comma list of the
three states, parsed as `priority` is."""

import pytest

from beyo_manager.domain.stock_report.enums import StockReportSnapshotVersionStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.queries.stock_report._version_state_filter import (
    parse_version_state_filter,
    version_state_predicate,
)

pytestmark = pytest.mark.unit

DRAFT = StockReportSnapshotVersionStateEnum.DRAFT
ACTIVE = StockReportSnapshotVersionStateEnum.ACTIVE
CLOSED = StockReportSnapshotVersionStateEnum.CLOSED


@pytest.mark.parametrize("raw", [None, "", " ", ",", " , "])
def test_omitted_or_empty_means_every_state(raw):
    assert parse_version_state_filter(raw) is None
    assert version_state_predicate(parse_version_state_filter(raw)) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("draft", [DRAFT]),
        ("active,closed", [ACTIVE, CLOSED]),
        # Spaces and an empty token are tolerated; repeats fold; order is kept.
        ("draft, ,closed", [DRAFT, CLOSED]),
        ("closed,closed,active", [CLOSED, ACTIVE]),
    ],
)
def test_lists_are_parsed_in_order_with_repeats_folded(raw, expected):
    assert parse_version_state_filter(raw) == expected


@pytest.mark.parametrize("raw", ["all", "active,x", "DRAFT", "open"])
def test_unknown_tokens_are_refused_with_the_identity(raw):
    with pytest.raises(ValidationError, match="STOCK_REPORT_UNKNOWN_VERSION_STATE"):
        parse_version_state_filter(raw)


def test_predicate_is_the_or_of_the_state_pairs():
    single = str(version_state_predicate([DRAFT]))
    assert "active_at IS NULL" in single
    both = str(version_state_predicate([ACTIVE, CLOSED]))
    assert "closed_at IS NOT NULL" in both
    assert "active_at IS NOT NULL" in both and " OR " in both
