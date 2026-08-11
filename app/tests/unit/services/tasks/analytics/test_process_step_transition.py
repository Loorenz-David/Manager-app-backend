from types import SimpleNamespace

import pytest

from beyo_manager.services.queries.analytics.reconcile_user_time import _CompletionTotals
from beyo_manager.services.tasks.analytics import process_step_transition as module


# NOTE: neither time nor completion counters are booked via per-interval increments here.
# Both are recomputed-and-SET from records — time by reconcile_user_day_time / the sweep,
# completions by reconcile_user_day_completions. See tests/unit/domain/analytics/test_concurrency.py
# and tests/integration/services/queries/analytics/test_reconcile_user_time.py.


class _FakeSession:
    """Returns queued scalars in call order (completed_count, then issues_count)."""

    def __init__(self, scalars):
        self._scalars = list(scalars)
        self.calls = 0

    async def scalar(self, _stmt):
        self.calls += 1
        return self._scalars.pop(0)


@pytest.mark.unit
def test_completion_delta_is_zero_when_recompute_matches_stored():
    """The property that makes the analytics worker safe under at-least-once retries.

    Replaying a transition recomputes identical counts, so the Σ-table deltas collapse
    to zero and lifetime/section-wide totals cannot inflate.
    """
    stored = _CompletionTotals(completed_count=7, issues_count=3, issues_resolved_count=3)
    recomputed = _CompletionTotals(completed_count=7, issues_count=3, issues_resolved_count=3)

    delta = recomputed.as_delta(stored)

    assert delta == _CompletionTotals(
        completed_count=0, issues_count=0, issues_resolved_count=0
    )


@pytest.mark.unit
def test_completion_delta_reports_only_the_genuine_change():
    stored = _CompletionTotals(completed_count=7, issues_count=3, issues_resolved_count=3)
    recomputed = _CompletionTotals(completed_count=8, issues_count=5, issues_resolved_count=5)

    delta = recomputed.as_delta(stored)

    assert delta.completed_count == 1
    assert delta.issues_count == 2
    assert delta.issues_resolved_count == 2


@pytest.mark.unit
def test_completion_delta_can_go_negative_when_records_are_removed():
    """A deleted record must be able to pull the Σ tables back down, not just up."""
    stored = _CompletionTotals(completed_count=4, issues_count=2, issues_resolved_count=2)
    recomputed = _CompletionTotals(completed_count=3, issues_count=0, issues_resolved_count=0)

    delta = recomputed.as_delta(stored)

    assert delta.completed_count == -1
    assert delta.issues_count == -2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recompute_step_completion_totals_assigns_absolute_values():
    """Absolute SET, not increment — pre-existing values are overwritten, never added to."""
    step = SimpleNamespace(
        total_completed_count=99,
        total_issues_count=99,
        total_issues_resolved_count=99,
    )
    session = _FakeSession([1, 4])  # completed_count, issues_count

    await module._recompute_step_completion_totals(session, "ws_1", "tsp_1", step)

    assert step.total_completed_count == 1
    assert step.total_issues_count == 4
    # Resolved mirrors total: reaching COMPLETED is what resolves a step's issues.
    assert step.total_issues_resolved_count == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recompute_step_completion_totals_is_idempotent():
    step = SimpleNamespace(
        total_completed_count=0,
        total_issues_count=0,
        total_issues_resolved_count=0,
    )

    await module._recompute_step_completion_totals(_FakeSession([1, 2]), "ws_1", "tsp_1", step)
    first = (step.total_completed_count, step.total_issues_count, step.total_issues_resolved_count)
    await module._recompute_step_completion_totals(_FakeSession([1, 2]), "ws_1", "tsp_1", step)
    second = (step.total_completed_count, step.total_issues_count, step.total_issues_resolved_count)

    assert first == second == (1, 2, 2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recompute_step_completion_totals_tolerates_missing_step():
    session = _FakeSession([])

    await module._recompute_step_completion_totals(session, "ws_1", "tsp_1", None)

    assert session.calls == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recompute_step_completion_totals_coerces_null_counts_to_zero():
    step = SimpleNamespace(
        total_completed_count=5,
        total_issues_count=5,
        total_issues_resolved_count=5,
    )
    session = _FakeSession([None, None])

    await module._recompute_step_completion_totals(session, "ws_1", "tsp_1", step)

    assert step.total_completed_count == 0
    assert step.total_issues_count == 0
    assert step.total_issues_resolved_count == 0
