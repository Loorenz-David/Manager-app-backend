"""The request models draft versions added (2026-09-28): the create body's title
and schedule rules (plan §4.1, FQ-6, Q-5, R-9), the PATCH-version body (§4.5,
P-14), the requested-quantity body
(§4.11, Q-9), the versioned missing body, and the history helper (§3.5, Q-10)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from beyo_manager.domain.stock_report.enums import (
    StockReportQuantityRequestedSourceEnum,
)
from beyo_manager.domain.stock_report.snapshot_rules import (
    snapshot_history_quantities,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.requests import (
    parse_activate_stock_report_snapshot_version_request,
    parse_apply_stock_report_snapshot_version_priorities_request,
    parse_create_stock_report_snapshot_version_request,
    parse_refresh_stock_report_snapshot_version_requested_request,
    parse_set_stock_report_item_snapshot_missing_quantity_request,
    parse_set_stock_report_item_snapshot_requested_quantity_request,
    parse_update_stock_report_snapshot_version_request,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# POST /snapshots/versions body
# ---------------------------------------------------------------------------


def test_empty_body_is_the_v6_create():
    request = parse_create_stock_report_snapshot_version_request({})
    assert request.draft is False
    assert request.title is None
    assert request.scheduled_activation_at is None
    assert request.scheduled_activation_keeps_active_missing is False
    assert request.schedule_requested is False


def test_a_schedule_is_a_date_or_the_flag_true_never_the_defaults():
    """R-9: the documented default body carries no schedule; a date, or the flag
    `true`, does — and the command refuses those with `draft: false`."""
    assert (
        parse_create_stock_report_snapshot_version_request(
            {
                "draft": False,
                "title": None,
                "scheduled_activation_at": None,
                "scheduled_activation_keeps_active_missing": False,
            }
        ).schedule_requested
        is False
    )
    assert (
        parse_create_stock_report_snapshot_version_request(
            {"scheduled_activation_at": "2026-12-01T06:00:00+00:00"}
        ).schedule_requested
        is True
    )
    assert (
        parse_create_stock_report_snapshot_version_request(
            {"scheduled_activation_keeps_active_missing": True}
        ).schedule_requested
        is True
    )


def test_title_is_trimmed_then_capped():
    padded = " " * 3 + "a" * 200 + " " * 3
    assert (
        parse_create_stock_report_snapshot_version_request({"title": padded}).title
        == "a" * 200
    )
    assert (
        parse_create_stock_report_snapshot_version_request({"title": "   "}).title
        is None
    )
    assert (
        parse_create_stock_report_snapshot_version_request({"title": ""}).title is None
    )
    with pytest.raises(ValidationError, match="title"):
        parse_create_stock_report_snapshot_version_request({"title": "a" * 201})


def test_schedule_must_be_aware_and_is_normalised_to_utc():
    with pytest.raises(ValidationError, match="scheduled_activation_at"):
        parse_create_stock_report_snapshot_version_request(
            {"draft": True, "scheduled_activation_at": "2026-10-05T06:00:00"}
        )
    request = parse_create_stock_report_snapshot_version_request(
        {"draft": True, "scheduled_activation_at": "2026-10-05T06:00:00+02:00"}
    )
    assert request.scheduled_activation_at == datetime(
        2026, 10, 5, 4, 0, tzinfo=timezone.utc
    )
    assert request.scheduled_activation_at.utcoffset() == timedelta(0)
    assert request.scheduled_activation_at.isoformat().endswith("+00:00")


@pytest.mark.parametrize(
    "body",
    [
        {"draft": "yes"},
        {"scheduled_activation_keeps_active_missing": 1},
        {"unexpected": True},
        {"title": 12},
    ],
)
def test_create_body_is_strict(body):
    with pytest.raises(ValidationError):
        parse_create_stock_report_snapshot_version_request(body)


# ---------------------------------------------------------------------------
# apply-priorities body
# ---------------------------------------------------------------------------


def test_apply_body_defaults_the_target_to_the_active_version():
    request = parse_apply_stock_report_snapshot_version_priorities_request(
        {"client_id": "srv_1"}
    )
    assert request.target_version_id is None
    assert (
        parse_apply_stock_report_snapshot_version_priorities_request(
            {"client_id": "srv_1", "target_version_id": "srv_2"}
        ).target_version_id
        == "srv_2"
    )


# ---------------------------------------------------------------------------
# activate body (§4.2, Q-8, R-6) and refresh body (§4.3)
# ---------------------------------------------------------------------------


def test_activate_body_defaults_to_reset_and_is_manual_without_the_handler_key():
    request = parse_activate_stock_report_snapshot_version_request(
        {"client_id": "srv_1"}
    )
    assert request.keep_active_missing is False
    assert request.scheduled is False
    assert (
        parse_activate_stock_report_snapshot_version_request(
            {"client_id": "srv_1", "keep_active_missing": True}
        ).keep_active_missing
        is True
    )


def test_activate_body_is_scheduled_when_the_handler_sends_its_key_as_utc():
    """R-6: presence of `expected_scheduled_activation_at` is what makes a fire
    scheduled; it is parsed as an aware datetime in UTC (Q-5), never a string."""
    request = parse_activate_stock_report_snapshot_version_request(
        {
            "client_id": "srv_1",
            "expected_scheduled_activation_at": "2026-10-05T06:00:00+02:00",
        }
    )
    assert request.scheduled is True
    assert request.expected_scheduled_activation_at == datetime(
        2026, 10, 5, 4, 0, tzinfo=timezone.utc
    )


@pytest.mark.parametrize(
    "body",
    [
        {"client_id": "srv_1", "refresh_quantity_requested": False},  # v7's body
        {"client_id": "srv_1", "keep_active_missing": "yes"},
        {
            "client_id": "srv_1",
            "expected_scheduled_activation_at": "2026-10-05T06:00:00",
        },
        {},
    ],
)
def test_activate_body_is_strict(body):
    with pytest.raises(ValidationError):
        parse_activate_stock_report_snapshot_version_request(body)


def test_refresh_body_keeps_overrides_by_default_and_is_strict():
    request = parse_refresh_stock_report_snapshot_version_requested_request(
        {"client_id": "srv_1"}
    )
    assert request.keep_manual_requested is True
    assert (
        parse_refresh_stock_report_snapshot_version_requested_request(
            {"client_id": "srv_1", "keep_manual_requested": False}
        ).keep_manual_requested
        is False
    )
    for body in (
        {"client_id": "srv_1", "keep_manual_requested": 1},
        {"client_id": "srv_1", "unexpected": True},
    ):
        with pytest.raises(ValidationError):
            parse_refresh_stock_report_snapshot_version_requested_request(body)


# ---------------------------------------------------------------------------
# PATCH /snapshots/versions/{client_id} body (plan §4.5, P-14)
# ---------------------------------------------------------------------------


def test_update_body_tells_an_omitted_key_from_a_null_one():
    empty = parse_update_stock_report_snapshot_version_request({"client_id": "srv_1"})
    assert not any(
        empty.sent(field)
        for field in (
            "title",
            "scheduled_activation_at",
            "scheduled_activation_keeps_active_missing",
        )
    )
    assert empty.schedule_keys_sent is False
    cleared = parse_update_stock_report_snapshot_version_request(
        {"client_id": "srv_1", "title": None, "scheduled_activation_at": None}
    )
    assert cleared.sent("title") and cleared.title is None
    assert cleared.sent("scheduled_activation_at")
    assert cleared.scheduled_activation_at is None
    # A schedule key sent as `null` is still a schedule key (v7 §5.19).
    assert cleared.schedule_keys_sent is True
    flag_only = parse_update_stock_report_snapshot_version_request(
        {"client_id": "srv_1", "scheduled_activation_keeps_active_missing": False}
    )
    assert flag_only.schedule_keys_sent is True
    assert not flag_only.sent("scheduled_activation_at")
    title_only = parse_update_stock_report_snapshot_version_request(
        {"client_id": "srv_1", "title": "  Monday push  "}
    )
    assert title_only.title == "Monday push"
    assert title_only.schedule_keys_sent is False


def test_update_body_applies_the_create_rules():
    request = parse_update_stock_report_snapshot_version_request(
        {"client_id": "srv_1", "scheduled_activation_at": "2026-10-05T06:00:00+02:00"}
    )
    assert request.scheduled_activation_at == datetime(
        2026, 10, 5, 4, 0, tzinfo=timezone.utc
    )
    assert request.scheduled_activation_at.isoformat().endswith("+00:00")
    assert (
        parse_update_stock_report_snapshot_version_request(
            {"client_id": "srv_1", "title": "   "}
        ).title
        is None
    )
    for body in (
        {"client_id": "srv_1", "scheduled_activation_at": "2026-10-05T06:00:00"},
        {"client_id": "srv_1", "title": "x" * 201},
        {"client_id": "srv_1", "scheduled_activation_keeps_active_missing": None},
        {"client_id": "srv_1", "scheduled_activation_keeps_active_missing": 1},
        {"client_id": "srv_1", "draft": True},
    ):
        with pytest.raises(ValidationError):
            parse_update_stock_report_snapshot_version_request(body)


# ---------------------------------------------------------------------------
# requested-quantity body (Q-9) and the versioned missing body
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"client_id": "sri_1", "version_id": "srv_1"},
        {"client_id": "sri_1", "version_id": "srv_1", "quantity_requested": -1},
        {"client_id": "sri_1", "version_id": "srv_1", "quantity_requested": "3"},
        {"client_id": "sri_1", "version_id": "srv_1", "quantity_requested": 3.0},
        {"client_id": "sri_1", "quantity_requested": 3},
    ],
)
def test_requested_quantity_body_refuses_missing_negative_string_and_no_version(body):
    with pytest.raises(ValidationError):
        parse_set_stock_report_item_snapshot_requested_quantity_request(body)


def test_requested_quantity_body_accepts_zero_and_null():
    base = {"client_id": "sri_1", "version_id": "srv_1"}
    assert (
        parse_set_stock_report_item_snapshot_requested_quantity_request(
            {**base, "quantity_requested": 0}
        ).quantity_requested
        == 0
    )
    assert (
        parse_set_stock_report_item_snapshot_requested_quantity_request(
            {**base, "quantity_requested": None}
        ).quantity_requested
        is None
    )


def test_missing_body_accepts_null_and_keeps_the_version_optional():
    shortcut = parse_set_stock_report_item_snapshot_missing_quantity_request(
        {"client_id": "sri_1", "quantity_missing": 2}
    )
    assert shortcut.version_id is None
    versioned = parse_set_stock_report_item_snapshot_missing_quantity_request(
        {"client_id": "sri_1", "version_id": "srv_1", "quantity_missing": None}
    )
    assert (versioned.version_id, versioned.quantity_missing) == ("srv_1", None)
    with pytest.raises(ValidationError):
        parse_set_stock_report_item_snapshot_missing_quantity_request(
            {"client_id": "sri_1", "quantity_missing": "2"}
        )


# ---------------------------------------------------------------------------
# snapshot_history_quantities (Q-10)
# ---------------------------------------------------------------------------


def _snapshot(*, active_at, scanner, manual):
    return SimpleNamespace(
        active_at=active_at,
        quantity_requested_scanner=scanner,
        quantity_requested_manual=manual,
    )


NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)
ROW = SimpleNamespace(quantity_requested=14)


@pytest.mark.parametrize(
    ("snapshot", "expected"),
    [
        # Activated, no override: the frozen Scanner value.
        (_snapshot(active_at=NOW, scanner=10, manual=None), (10, "scanner")),
        # Activated with an override: the override, source manual.
        (_snapshot(active_at=NOW, scanner=10, manual=7), (7, "manual")),
        # A draft: the live row, unless overridden.
        (_snapshot(active_at=None, scanner=None, manual=None), (14, "scanner")),
        (_snapshot(active_at=None, scanner=None, manual=3), (3, "manual")),
    ],
)
def test_history_quantities_are_the_effective_value_and_its_source(snapshot, expected):
    values = snapshot_history_quantities(snapshot, row=ROW)
    assert set(values) == {"quantity_requested", "quantity_requested_source"}
    assert values["quantity_requested"] == expected[0]
    assert values[
        "quantity_requested_source"
    ] is StockReportQuantityRequestedSourceEnum(expected[1])
