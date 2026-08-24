from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

from beyo_manager.domain.item_economics.division_serializers import serialize_task_production_time
from beyo_manager.domain.item_economics.serializers import serialize_task_price_scenario
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.item_economics.typical_filters import (
    SectionTypicalEvidence,
    TaskTypicalSelection,
    TypicalFilterSpec,
    derive_spec_from_primary_item,
)
from beyo_manager.services.queries.item_economics.get_task_budget_allocations import (
    get_task_budget_allocations,
)
from beyo_manager.services.queries.item_economics.get_task_production_time import (
    get_task_production_time,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.working_sections import (
    get_working_section_typical_times as typical_times_module,
)
from tests.integration.services.queries.item_economics.test_price_scenario_query import (
    _TypicalSession,
    _ctx,
    _step,
    _typical_row,
    module,
)
from tests.integration.services.queries.item_economics._narrowing_fixture import (
    cleanup_divergent_category_fixture,
    seed_divergent_category_task,
)


def _spec_row(section_id: str, narrowed: int | None, section: int | None, *, narrowed_count=5, section_count=12):
    return SimpleNamespace(
        client_id=section_id,
        spec_index=0,
        narrowed_typical_worker_seconds=narrowed,
        narrowed_sample_count=narrowed_count,
        section_typical_worker_seconds=section,
        section_sample_count=section_count,
    )


def _selection(*, basis="item_narrowed_uniform", category_id="icat_chair", section_count=2):
    spec = TypicalFilterSpec(item_category_ids=frozenset({category_id}))
    evidence = {
        section_id: SectionTypicalEvidence(section_id, 600, 5, 375, 12)
        for section_id in ("section_a", "section_b")
    }
    return TaskTypicalSelection(
        basis,
        "uniform_basis_v1",
        "primary_item_category_v1",
        spec,
        frozenset(list(evidence)[:section_count]),
        {
            section_id: SimpleNamespace(
                typical_worker_seconds=600,
                typical_basis="item_narrowed",
                evidence=row,
                sample_count=5,
            )
            for section_id, row in evidence.items()
        },
    )


@pytest.mark.integration
async def test_c1a_typical_block_passes_the_request_clock_to_the_statement(monkeypatch):
    captured = {}
    real_statement = module.typical_times_statement

    def spy(*args, **kwargs):
        captured.update(kwargs)
        return real_statement(*args, **kwargs)

    monkeypatch.setattr(module, "typical_times_statement", spy)
    context = _ctx(_TypicalSession([_step("section_a")], [_typical_row("section_a", 600)]))
    await module._typical_block(context, "tsk_scenario", None)

    assert captured["now"] == context.now
    assert captured["specs"] == ()


@pytest.mark.integration
async def test_c1b_same_frozen_context_produces_byte_identical_typicals(monkeypatch):
    frozen = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
    captured = []
    real_statement = module.typical_times_statement

    def spy(*args, **kwargs):
        captured.append(kwargs.get("now"))
        return real_statement(*args, **kwargs)

    monkeypatch.setattr(module, "typical_times_statement", spy)

    def make_context():
        context = _ctx(
            _TypicalSession([_step("section_a")], [_typical_row("section_a", 600)])
        )
        context.now = frozen
        return context

    first = await module._typical_block(make_context(), "tsk_scenario", None)
    second = await module._typical_block(make_context(), "tsk_scenario", None)
    def public(typical):
        return serialize_task_price_scenario(
            {
                "task_id": "task",
                "status": "not_evaluated",
                "item_binding": "bound",
                "can_commit": False,
                "currency": None,
                "calculation_version": 2,
                "config_fingerprint": None,
                "item": None,
                "saved": None,
                "model": None,
                "typical": typical,
                "anchors": None,
                "domain": None,
            }
        )["typical"]

    assert json.dumps(public(first), sort_keys=True) == json.dumps(
        public(second), sort_keys=True
    )
    assert captured == [frozen, frozen]
    assert first["total_seconds"] == second["total_seconds"] == 600


def test_c1c_working_section_typicals_keep_the_default_statement_clock():
    source = inspect.getsource(typical_times_module.get_working_section_typical_times)
    assert "typical_times_statement(ctx.workspace_id)" in source
    assert "typical_times_statement(ctx.workspace_id, now=ctx.now" not in source


@pytest.mark.parametrize(
    ("steps", "rows", "expected"),
    [
        ([], [], (0, True, 0, 0)),
        (
            [_step("section_a"), _step("section_b")],
            [_typical_row("section_a", 600), _typical_row("section_b", None)],
            (1200, True, 1, 2),
        ),
        (
            [_step("section_a"), _step("section_b")],
            [_typical_row("section_a", 0), _typical_row("section_b", 600)],
            (1200, True, 1, 2),
        ),
    ],
)
@pytest.mark.integration
async def test_c2_is_estimated_tracks_empty_none_and_zero_selected_typicals(steps, rows, expected):
    result = await module._typical_block(
        _ctx(_TypicalSession(steps, rows)), "tsk_scenario", None
    )
    assert (
        result["total_seconds"],
        result["is_estimated"],
        result["sections_without_sample"],
        result["sections_total"],
    ) == expected


@pytest.mark.integration
async def test_c2d_section_wide_uniform_does_not_make_is_estimated_true():
    result = await module._typical_block(
        _ctx(
            _TypicalSession(
                [_step("section_a")], [_spec_row("section_a", None, 600, narrowed_count=0)]
            )
        ),
        "tsk_scenario",
        TypicalFilterSpec(item_category_ids=frozenset({"icat_chair"})),
    )
    assert result["is_estimated"] is False
    assert result["sections_without_sample"] == 0


@pytest.mark.integration
async def test_c3_counts_only_participating_selected_typicals():
    result = await module._typical_block(
        _ctx(
            _TypicalSession(
                [
                    _step("usable"),
                    _step("none"),
                    _step("zero"),
                    _step("excluded", state=TaskStepStateEnum.SKIPPED),
                ],
                [
                    _typical_row("usable", 600),
                    _typical_row("none", None),
                    _typical_row("zero", 0),
                ],
            )
        ),
        "tsk_scenario",
        None,
    )
    assert result["sections_total"] == 3
    assert result["sections_without_sample"] == 2


@pytest.mark.parametrize(
    ("rows", "expected"),
    [([], 0), ([_typical_row("a", 600), _typical_row("b", 900), _typical_row("c", None)], 2250)],
)
@pytest.mark.integration
async def test_c4_price_terminal_and_median_are_duration_values(rows, expected):
    steps = [_step(section) for section in ("a", "b", "c")[: len(rows) or 3]]
    result = await module._typical_block(
        _ctx(_TypicalSession(steps, rows)), "tsk_scenario", None
    )
    assert result["total_seconds"] == expected


@pytest.mark.integration
async def test_c5_three_surfaces_use_the_same_published_literal(db_session):
    fixture = await seed_divergent_category_task(db_session)
    workspace = fixture["workspace"]
    narrowed_task = fixture["narrowed_task"]
    item = fixture["base_values"][5]
    now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
    price_context = _ctx(db_session, narrowed_task.client_id)
    price_context.identity["workspace_id"] = workspace.client_id
    price_context.now = now
    production_context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
        incoming_data={"task_client_id": narrowed_task.client_id},
        query_params={}, session=db_session, now=now,
    )
    allocations_context = ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "worker"},
        incoming_data={}, query_params={"task_ids": [narrowed_task.client_id]}, session=db_session, now=now,
    )
    try:
        price = await module._typical_block(
            price_context,
            narrowed_task.client_id,
            derive_spec_from_primary_item(item),
        )
        production = await get_task_production_time(production_context)
        allocations = await get_task_budget_allocations(allocations_context)
        production_row = next(
            row["typical"]
            for row in production["sections"]
            if row["working_section_id"] == fixture["section"].client_id
        )
        allocation_row = next(
            row
            for row in allocations["budget_allocations"][0]["steps"]
            if row["working_section_id"] == fixture["section"].client_id
        )
        assert (production_row["typical_worker_seconds"], production_row["typical_basis"], production_row["sample_count"]) == (600, "item_narrowed", 5)
        assert (allocation_row["typical_worker_seconds"], allocation_row["typical_basis"], allocation_row["sample_count"]) == (600, "item_narrowed", 5)
        assert price["total_seconds"] == 600
    finally:
        await cleanup_divergent_category_fixture(db_session, fixture)


def test_c6_price_and_production_resolution_have_the_exact_six_key_shape():
    selection = _selection(section_count=2)
    typical = {
        "total_seconds": 1200,
        "is_estimated": False,
        "sections_without_sample": 0,
        "sections_total": 2,
        "method": "median_completed_section_totals",
        "window_days": 90,
        "min_sample_size": 5,
        "typical_resolution": selection,
    }
    price = serialize_task_price_scenario(
        {
            "task_id": "task",
            "status": "not_evaluated",
            "item_binding": "bound",
            "can_commit": False,
            "currency": None,
            "calculation_version": 2,
            "config_fingerprint": None,
            "item": None,
            "saved": None,
            "model": None,
            "typical": typical,
            "anchors": None,
            "domain": None,
        }
    )
    production = serialize_task_production_time(
        {
            "task_id": "task",
            "status": "not_evaluated",
            "item_binding": "bound",
            "division": {"sections": []},
            "typicals": {},
            "typical_resolution": selection,
        }
    )
    expected_keys = frozenset(
        {
            "task_typical_basis",
            "reconciliation_method",
            "comparability_profile",
            "applied_filter",
            "participating_section_count",
            "sections_by_basis",
        }
    )
    assert frozenset(price["typical"]["typical_resolution"]) == expected_keys
    assert frozenset(production["typical_resolution"]) == expected_keys
    assert price["typical"]["typical_resolution"]["task_typical_basis"] == "item_narrowed_uniform"
    assert price["typical"]["typical_resolution"]["applied_filter"] == {
        "item_category_ids": ["icat_chair"]
    }
    assert price["typical"]["typical_resolution"]["participating_section_count"] == 2


@pytest.mark.integration
async def test_c7_typical_block_delegates_statistics_and_has_no_private_terms(monkeypatch):
    calls = []
    real_fallback = module.apply_business_fallback

    def spy(values, *, terminal):
        calls.append((list(values), terminal))
        return real_fallback(values, terminal=terminal)

    monkeypatch.setattr(module, "apply_business_fallback", spy)
    result = await module._typical_block(
        _ctx(_TypicalSession([_step("section_a")], [_typical_row("section_a", 600)])),
        "tsk_scenario",
        None,
    )
    source = inspect.getsource(module._typical_block)
    assert calls == [([600], Fraction(0, 1))]
    assert result["total_seconds"] == 600
    assert "median" not in source
    assert "percentile" not in source
    assert ">= TYPICAL_MIN_SAMPLE_SIZE" not in source
    assert "< TYPICAL_MIN_SAMPLE_SIZE" not in source


def test_c7_item_economics_fork_sweep_finds_only_the_shared_median():
    root = Path(__file__).resolve().parents[6] / "app" / "beyo_manager"
    roots = [root / "domain" / "item_economics", root / "services" / "queries" / "item_economics"]
    hits = {
        path.name
        for directory in roots
        for path in directory.glob("*.py")
        if any(term in path.read_text() for term in ("percentile_cont", "_median", "median("))
    }
    assert hits == {"typical_filters.py"}


@pytest.mark.integration
async def test_c8_narrowing_changes_the_published_number_and_basis():
    spec = TypicalFilterSpec(item_category_ids=frozenset({"icat_chair"}))
    narrowed = await module._typical_block(
        _ctx(_TypicalSession([_step("section_a")], [_spec_row("section_a", 600, 375)])),
        "tsk_scenario",
        spec,
    )
    broad = await module._typical_block(
        _ctx(_TypicalSession([_step("section_a")], [_typical_row("section_a", 375)])),
        "tsk_scenario",
        None,
    )
    assert narrowed["total_seconds"] == 600
    assert narrowed["typical_resolution"].task_typical_basis == "item_narrowed_uniform"
    assert broad["total_seconds"] == 375
    assert narrowed["total_seconds"] != broad["total_seconds"]


@pytest.mark.integration
async def test_c8_divergent_fixture_measures_narrowed_600_against_section_375(db_session):
    fixture = await seed_divergent_category_task(db_session)
    workspace = fixture["workspace"]
    narrowed_task = fixture["narrowed_task"]
    plain_task = fixture["plain_task"]
    item = fixture["base_values"][5]
    now = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)

    def context(task_id):
        return ServiceContext(
            identity={"workspace_id": workspace.client_id, "user_id": "usr", "role_name": "manager"},
            incoming_data={"task_client_id": task_id}, query_params={}, session=db_session, now=now,
        )

    try:
        narrowed = await module._typical_block(
            context(narrowed_task.client_id),
            narrowed_task.client_id,
            derive_spec_from_primary_item(item),
        )
        plain = await module._typical_block(context(plain_task.client_id), plain_task.client_id, None)
        assert narrowed["total_seconds"] == 600
        assert narrowed["typical_resolution"].task_typical_basis == "item_narrowed_uniform"
        assert plain["total_seconds"] == 375
        assert narrowed["total_seconds"] != plain["total_seconds"]
    finally:
        await cleanup_divergent_category_fixture(db_session, fixture)
