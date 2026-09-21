"""Plan 7 — C1, C2, C4, C6, C7: `receive_stock_demand_webhook` (master plan §6.5;
intention §8B MC-8 auth order; §2.5 workspace guard; §8B MC-9 part 1 deadline; §4A
MC-3 identity invariant).

`REQ(body_bytes, headers)` (plan 7 §6) = calling the command directly with
`ServiceContext(identity={}, incoming_data={"raw_body": ..., "headers": ...},
session=db_session)`, exactly as the router builds it. The two settings are
configured for the seeded workspace W unless a row says otherwise.

**Fix round 1 (batch B2, 2026-09-21) additions:** C2(a)/C2(x)/C2(y) — the three
rows whose outcome names persisted state, previously discharged only at parser
scope (S1) — and C4(a)-(h), the M4 identity invariant proven through this endpoint
with real JSON bytes (B1), which the parser-level signature-equality tests
(`test_stock_demand_request.py`) do not reach. Tests only; no production change.
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
)
from beyo_manager.errors.stock_report import LocationTrackerWebhookAuthError
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.services.commands.stock_report import (
    apply_stock_demand as apply_stock_demand_module,
)
from beyo_manager.services.commands.stock_report.receive_stock_demand_webhook import (
    receive_stock_demand_webhook,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service
from tests.helpers.statement_listener import count_writes, record_statements
from tests.helpers.stock_report import (
    assert_stock_report_clean,
    capture_dispatch,
    purge_stock_report_workspace,
    seed_stock_report_workspace,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API_KEY = "test-scanner-key"
NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

# MC-9's four write tables (test_apply_stock_demand.py's WRITE_TABLES, restated here
# so this file stays self-contained): what "nothing written" (plan 7 §6) measures.
WRITE_TABLES = {
    "stock_report_items",
    "stock_task_assignments",
    "stock_report_history_records",
    "tasks",
}


def _configure(monkeypatch, *, api_key=API_KEY, workspace_id):
    monkeypatch.setattr(settings, "manager_api_key_to_location_tracker_app", api_key)
    monkeypatch.setattr(settings, "location_tracker_webhook_workspace_id", workspace_id)


def _ctx(session, *, raw_body=b"[]", headers=None):
    headers = {"x-api-key": API_KEY} if headers is None else headers
    return ServiceContext(
        identity={},
        incoming_data={"raw_body": raw_body, "headers": headers},
        session=session,
        now=NOW,
    )


def _body(entries: list[dict]) -> bytes:
    return json.dumps(entries).encode("utf-8")


def _one_entry_body(properties: object, *, category="Dining Chairs", quantity=1) -> bytes:
    return _body([{"itemCategory": category, "properties": properties, "quantityRequested": quantity}])


async def _live_row_count(session, workspace_id) -> int:
    rows = (
        await session.execute(
            select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
        )
    ).scalars().all()
    return len(rows)


_VALID_BODY = b'[{"itemCategory": "Dining Chairs", "properties": {"wood_group": ["teak"]}, "quantityRequested": 5}]'


# ---------------------------------------------------------------------------
# C1 — auth order (MC-8 steps 2-4)
# ---------------------------------------------------------------------------


async def test_c1a_key_setting_none_is_401(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        # A *real* workspace, not a placeholder: if a mutation makes verification
        # wrongly succeed, the call proceeds into apply_stock_demand and either
        # writes a row (caught below) or raises for an unrelated reason (a
        # nonexistent placeholder workspace would raise the *same* exception type
        # from apply_stock_demand's own step-2 check, masking the mutation).
        _configure(monkeypatch, api_key=None, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))
        assert excinfo.value.http_status == 401

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1b_key_setting_blank_is_401(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, api_key="   ", workspace_id=workspace_id)
        # The header carries the blank key's own value, byte for byte: without the
        # strip() check, a bare `is None` guard lets this through to compare_digest,
        # where it would match and this row would wrongly succeed.
        with pytest.raises(LocationTrackerWebhookAuthError):
            await receive_stock_demand_webhook(
                _ctx(db_session, raw_body=_VALID_BODY, headers={"x-api-key": "   "})
            )

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1c_workspace_setting_none_is_401(db_session, monkeypatch):
    _configure(monkeypatch, workspace_id=None)
    with pytest.raises(LocationTrackerWebhookAuthError):
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))


async def test_c1d_missing_header_is_401(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError):
            await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY, headers={}))

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1e_wrong_header_is_401(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError):
            await receive_stock_demand_webhook(
                _ctx(db_session, raw_body=_VALID_BODY, headers={"x-api-key": "wrong"})
            )

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1f_non_ascii_header_is_401_not_500(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await receive_stock_demand_webhook(
                _ctx(db_session, raw_body=_VALID_BODY, headers={"x-api-key": "clé-non-ascii"})
            )
        assert excinfo.value.http_status == 401

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1g_workspace_setting_names_no_workspace_is_401(db_session, monkeypatch):
    _configure(monkeypatch, workspace_id="ws_stock_demand_does_not_exist")
    with pytest.raises(LocationTrackerWebhookAuthError):
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))


async def test_c1h_all_401_messages_are_byte_identical(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        messages = set()

        _configure(monkeypatch, api_key=None, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))
        messages.add(excinfo.value.message)

        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY, headers={}))
        messages.add(excinfo.value.message)

        _configure(monkeypatch, workspace_id="ws_stock_demand_does_not_exist")
        with pytest.raises(LocationTrackerWebhookAuthError) as excinfo:
            await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))
        messages.add(excinfo.value.message)

        assert messages == {"Unauthorized."}

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c1i_verify_runs_before_parse(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        with pytest.raises(LocationTrackerWebhookAuthError):
            await receive_stock_demand_webhook(
                _ctx(db_session, raw_body=b"not json", headers={"x-api-key": "wrong"})
            )

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C2 — rows whose outcome names persisted state (S1: parser scope proves the
# 422/acceptance half only; these prove the write half through the command).
# ---------------------------------------------------------------------------


async def test_c2a_c2x_malformed_bodies_write_nothing_through_the_command(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)

        # C2(a): invalid UTF-8 bytes.
        async with record_statements(db_session) as statements:
            with pytest.raises(ValidationError) as excinfo:
                await receive_stock_demand_webhook(_ctx(db_session, raw_body=b"\xff\xfe"))
        assert excinfo.value.http_status == 422
        assert count_writes(statements, WRITE_TABLES) == 0

        # C2(x): entries 0 and 2 malformed, entry 1 valid — the batch is atomic
        # (§8), so entry 1 is not applied either: nothing written, message names
        # entries 0 and 2 only.
        body = _body(
            [
                {"itemCategory": "", "properties": {}, "quantityRequested": 1},
                {"itemCategory": "Dining Chairs", "properties": {}, "quantityRequested": 1},
                {"itemCategory": "Dining Chairs", "properties": {}, "quantityRequested": -1},
            ]
        )
        async with record_statements(db_session) as statements:
            with pytest.raises(ValidationError) as excinfo:
                await receive_stock_demand_webhook(_ctx(db_session, raw_body=body))
        assert excinfo.value.http_status == 422
        assert "entry 0" in excinfo.value.message
        assert "entry 2" in excinfo.value.message
        assert "entry 1" not in excinfo.value.message
        assert count_writes(statements, WRITE_TABLES) == 0
        assert await _live_row_count(db_session, workspace_id) == 0

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c2y_extra_key_is_ignored_and_the_entry_is_applied(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body = _body(
            [
                {
                    "itemCategory": "Dining Chairs",
                    "properties": {},
                    "quantityRequested": 3,
                    "location": "LC1",
                }
            ]
        )

        response = await receive_stock_demand_webhook(_ctx(db_session, raw_body=body))

        assert response["results"][0]["outcome"] == "applied"
        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.quantity_requested == 3

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C4 — the M4 identity invariant, proven through the endpoint with real JSON
# bytes (B1). The parser-level signature-equality tests in
# `test_stock_demand_request.py` stay — they are good tests and now carry
# verified mutation arming — but the rows' own outcome is persisted database
# state, so it is proven here: two successive raw deliveries, then a live-row
# count. See intention §4A MC-3, final bullet.
# ---------------------------------------------------------------------------


async def test_c4a_key_order_is_one_live_row(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"a": ["x"], "b": ["y"]})
        body_2 = _one_entry_body({"b": ["y"], "a": ["x"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4b_list_element_order_is_one_live_row(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"wood_group": ["teak", "dark"]})
        body_2 = _one_entry_body({"wood_group": ["dark", "teak"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4c_list_element_case_and_whitespace_is_one_live_row(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"wood_group": ["Teak"]})
        body_2 = _one_entry_body({"wood_group": [" teak "]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4d_duplicate_list_elements_is_one_live_row(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"wood_group": ["teak", "teak"]})
        body_2 = _one_entry_body({"wood_group": ["teak"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4e_bare_string_vs_one_element_list_is_one_live_row(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"wood_group": "teak"})
        body_2 = _one_entry_body({"wood_group": ["teak"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 1

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4f_key_case_is_two_live_rows(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"Wood_Group": ["teak"]})
        body_2 = _one_entry_body({"wood_group": ["teak"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 2

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4g_key_whitespace_is_two_live_rows(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({" wood_group": ["teak"]})
        body_2 = _one_entry_body({"wood_group": ["teak"]})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 2

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c4h_not_understood_number_forms_is_two_live_rows(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body_1 = _one_entry_body({"n": 1})
        body_2 = _one_entry_body({"n": 1.0})

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_1))
        await receive_stock_demand_webhook(_ctx(db_session, raw_body=body_2))

        assert await _live_row_count(db_session, workspace_id) == 2

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C5 — success body (echo as received; exact key set)
# ---------------------------------------------------------------------------


async def test_c5a_results_echo_as_received_and_stored_row_is_normalized(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        body = (
            b'[{"itemCategory": "Dining Chairs", "properties": {"wood_group": ["Teak", "Dark"]}, '
            b'"quantityRequested": 5}, '
            b'{"itemCategory": "Bar Stools", "properties": {}, "quantityRequested": 1}]'
        )

        response = await receive_stock_demand_webhook(_ctx(db_session, raw_body=body))

        assert response["results"] == [
            {
                "itemCategory": "Dining Chairs",
                "properties": {"wood_group": ["Teak", "Dark"]},
                "outcome": "applied",
            },
            {
                "itemCategory": "Bar Stools",
                "properties": {},
                "outcome": "category_not_found",
            },
        ]

        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.properties == {"wood_group": ["dark", "teak"]}
        assert row.properties_signature == compute_stock_criteria_signature(
            {"wood_group": ["Teak", "Dark"]}
        )

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


async def test_c5b_every_result_has_exactly_the_three_keys(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)

        response = await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))

        for result in response["results"]:
            assert set(result.keys()) == {"itemCategory", "properties", "outcome"}

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C6 — workspace fidelity
# ---------------------------------------------------------------------------


async def test_c6a_created_row_and_events_carry_the_configured_workspace(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch, "beyo_manager.services.commands.stock_report.receive_stock_demand_webhook.dispatch"
        )

        await receive_stock_demand_webhook(_ctx(db_session, raw_body=_VALID_BODY))

        row = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert row.workspace_id == workspace_id
        assert len(captured) == 1
        assert captured[0].workspace_id == workspace_id

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()


# ---------------------------------------------------------------------------
# C7 — the demand time limit, run through run_service (the sleeping mutation
# lives in phase 6's C7(c); this row proves the command wires it correctly)
# ---------------------------------------------------------------------------


async def test_c7a_deadline_exceeded_answers_503_through_run_service(db_session, monkeypatch):
    seeded = await seed_stock_report_workspace(db_session)
    await db_session.commit()
    workspace_id = seeded.workspace.client_id
    try:
        _configure(monkeypatch, workspace_id=workspace_id)
        captured = capture_dispatch(
            monkeypatch, "beyo_manager.services.commands.stock_report.receive_stock_demand_webhook.dispatch"
        )
        monkeypatch.setattr(
            apply_stock_demand_module,
            "time",
            SimpleNamespace(monotonic=lambda: 10**9),
        )

        outcome = await run_service(
            receive_stock_demand_webhook, _ctx(db_session, raw_body=_VALID_BODY)
        )

        assert outcome.success is False
        assert outcome.error.http_status == 503

        rows = (
            await db_session.execute(
                select(StockReportItem).where(StockReportItem.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert rows == []
        assert captured == []

        await assert_stock_report_clean(db_session, workspace_id)
    finally:
        await purge_stock_report_workspace(db_session, workspace_id)
        await db_session.commit()
