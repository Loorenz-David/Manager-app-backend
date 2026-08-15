"""C1 — the drift alarm on the item-economics living docs.

Anchored on ``parents[4]`` rather than the working directory: pytest and alembic
both run from ``backend/app/`` while the docs live at ``backend/docs/``, so a
cwd-relative path would pass or fail depending on where the run was started.

This is a cheap containment check, not a substitute for reading the page. The
literals below are copied character-for-character from the intention document
(`docs/architecture/under_construction/implementation/item_cost_calculation/
planning/intention.md`) — §6A.4:718-720 for the presentation rule and
§8A.2:1367-1369 for the two cost-number definitions. Paraphrasing either side of
this comparison defeats its only purpose.
"""

from pathlib import Path

import pytest


_DOMAIN_DOCS = Path(__file__).resolve().parents[4] / "docs" / "domains" / "item_economics"

_REQUIRED_FILES = ("README.md", "api.md", "events.md", "states.md")

# Verbatim from intention §6A.4:718-720.
_PRESENTATION_RULE = (
    "a percentage term must never be presented as computing the legally "
    "payable tax amount."
)

# Verbatim from intention §8A.2:1367-1369 — both cost-number definitions.
_TWO_COST_NUMBERS = (
    "`task_steps.total_cost_minor` (salary-priced, working **+ paused**, "
    "compensation's remit) and `item_cost_results.consumed_cost_minor` "
    "(allowance-priced, working only) answer different questions and differ for "
    "the same episode by construction."
)


def _normalized(file_name: str) -> str:
    """Collapse the markdown line wrapping so a rewrap cannot break the alarm."""
    return " ".join((_DOMAIN_DOCS / file_name).read_text().split())


@pytest.mark.unit
@pytest.mark.parametrize("file_name", _REQUIRED_FILES, ids=_REQUIRED_FILES)
def test_living_docs_folder_carries_its_four_files(file_name: str) -> None:
    assert (_DOMAIN_DOCS / file_name).is_file()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("file_name", "literal"),
    [
        ("README.md", _PRESENTATION_RULE),
        ("README.md", _TWO_COST_NUMBERS),
        ("README.md", "planning allocation"),
        ("README.md", "worker-minutes"),
    ],
    ids=[
        "intention-6A.4-presentation-rule",
        "intention-8A.2-two-cost-numbers",
        "P-D-planning-allocation",
        "P-C-worker-minutes",
    ],
)
def test_living_docs_pin_their_semantic_authorities(file_name: str, literal: str) -> None:
    assert " ".join(literal.split()) in _normalized(file_name)
