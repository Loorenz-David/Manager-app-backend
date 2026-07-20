from datetime import date, datetime, timedelta, timezone

from beyo_manager.services.infra.connecteam.time_activities_client import parse_time_activities
from scripts.backfill.curate_shifts_from_connecteam import _split_windows


def test_split_windows_respects_92_day_cap_and_is_contiguous():
    windows = _split_windows(date(2026, 1, 1), date(2026, 7, 1))  # ~181 days
    assert windows[0][0] == date(2026, 1, 1)
    assert windows[-1][1] == date(2026, 7, 1)
    assert all((end - start).days <= 92 for start, end in windows)
    for (_, prev_end), (next_start, _) in zip(windows, windows[1:]):
        assert next_start == prev_end + timedelta(days=1)  # no gaps or overlaps


def test_split_windows_single_window_when_small():
    assert _split_windows(date(2026, 1, 1), date(2026, 1, 10)) == [(date(2026, 1, 1), date(2026, 1, 10))]


# Exact shape from the Connecteam Time Activities API reference.
_SAMPLE = {
    "requestId": "a1b2c3d4",
    "data": {
        "timeActivitiesByUsers": [
            {
                "userId": 9170357,
                "shifts": [
                    {
                        "id": "shift-abc123",
                        "start": {"timestamp": 1704110400, "timezone": "America/New_York"},
                        "end": {"timestamp": 1704139200, "timezone": "America/New_York"},
                        "isAutoClockOut": False,
                    }
                ],
                "manualBreaks": [],
                "timeOffs": [],
            }
        ]
    },
}


def test_parses_completed_shift_to_utc():
    parsed = parse_time_activities(_SAMPLE)
    assert parsed.skipped_open == 0
    assert len(parsed.shifts) == 1
    shift = parsed.shifts[0]
    assert shift.connecteam_user_id == "9170357"
    assert shift.shift_id == "shift-abc123"
    # Unix seconds are absolute UTC; the IANA timezone is metadata only.
    assert shift.start_at == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert shift.end_at == datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc)
    assert shift.is_auto_clock_out is False


def test_open_shift_is_skipped_and_counted():
    payload = {
        "data": {
            "timeActivitiesByUsers": [
                {
                    "userId": 42,
                    "shifts": [
                        {"id": "open", "start": {"timestamp": 1704110400}, "end": None},
                        {"id": "open2", "start": {"timestamp": 1704110400}},  # end absent
                    ],
                }
            ]
        }
    }
    parsed = parse_time_activities(payload)
    assert parsed.shifts == []
    assert parsed.skipped_open == 2


def test_dedupes_by_shift_id_and_skips_userless_or_startless():
    payload = {
        "data": {
            "timeActivitiesByUsers": [
                {
                    "userId": 7,
                    "shifts": [
                        {"id": "s1", "start": {"timestamp": 1000}, "end": {"timestamp": 2000}},
                        {"id": "s1", "start": {"timestamp": 1000}, "end": {"timestamp": 2000}},  # dup
                        {"id": "s2", "start": None, "end": {"timestamp": 2000}},  # no start → skip
                    ],
                },
                {"userId": None, "shifts": [{"id": "x", "start": {"timestamp": 1}, "end": {"timestamp": 2}}]},
            ]
        }
    }
    parsed = parse_time_activities(payload)
    assert [s.shift_id for s in parsed.shifts] == ["s1"]


def test_empty_payload():
    assert parse_time_activities({}).shifts == []
    assert parse_time_activities({"data": {"timeActivitiesByUsers": []}}).shifts == []
