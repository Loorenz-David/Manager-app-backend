from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[4]
_HANDOFF_GLOB = "docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_*.md"


def _handoff() -> Path:
    matches = sorted(_ROOT.glob(_HANDOFF_GLOB))
    assert len(matches) == 1
    return matches[0]


@pytest.mark.unit
def test_budget_signals_handoff_has_metadata_and_five_answers():
    text = _handoff().read_text()
    assert "## Metadata" in text
    assert "planning/intention.md" in text
    assert "plans/plan_3.md" in text
    for index in range(1, 6):
        heading = f"### Open question {index}"
        assert heading in text
        answer = text.split(heading, 1)[1].split("\n### ", 1)[0].strip()
        assert answer


@pytest.mark.unit
def test_budget_signals_handoff_pins_the_three_request_corrections():
    text = _handoff().read_text()
    corrections = (
        "`over_cost_minor` may be `0` while `over_seconds > 0` — acceptance criterion 2 is not satisfiable as written",
        "N rows means one row per **distinct** visible requested id",
        "the route has two different 422 envelopes",
    )
    assert "## Corrections to the request" in text
    for correction in corrections:
        assert correction in text


@pytest.mark.unit
def test_budget_signals_handoff_records_the_served_contract():
    text = _handoff().read_text()
    assert "a negative budget before any work is a forecast" in text
    assert "no work left to come means no forecast" in text
    assert "production-time shows no amber on an infeasible task" in text
    assert "| Field | Type | Meaning |" in text
    for value in ("within_budget", "projected_over", "over", "no_budget"):
        assert f"`{value}`" in text
    for value in ("swedish_krona", "danish_krona", "euro", "no_currency"):
        assert f"`{value}`" in text
    assert "ADMIN and MANAGER only; WORKER and SELLER receive 403" in text
    assert "rows are ordered by `task_id` ascending" in text
    assert "no server timestamp is served" in text
