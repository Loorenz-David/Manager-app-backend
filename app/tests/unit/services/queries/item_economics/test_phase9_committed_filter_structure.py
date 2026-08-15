"""The structural arbiter for the committed-current filter (phase-8 r3 N1).

A filter-deletion mutation whose correct row stays in the candidate set cannot be
arbitrated order-independently by a behavioural assertion — the mutated query may
pick the right row by accident. So this reads the *compiled* statement and asserts
the three literal clauses are present, which no heap order affects.

Mechanism follows the repo precedent at
``tests/unit/services/queries/upholstery/test_list_upholstery_inventories.py:34-46,63-64``
with two adaptations: these three services call ``scalar`` / ``scalars`` rather than
``execute``, and the evaluation SELECT is not the first statement they issue — it is
the 3rd or 4th call depending on the fixture. Selecting by call ordinal would be
fixture-dependent, so the statement is selected by its compiled text naming
``item_cost_evaluations``.

Boundary: three sites, the first phase to touch the status queries. The four other
production sites carrying the same filter are recorded in master plan §11.
``list_task_evaluations.py`` carries two of the three clauses **by design** (it
returns the whole committed chain) and is deliberately not a site here.
"""

from types import SimpleNamespace

import pytest

from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_item_lifetime_economics import (
    get_item_lifetime_economics,
)
from beyo_manager.services.queries.item_economics.get_task_budget_status import (
    get_task_budget_status,
)
from beyo_manager.services.queries.item_economics.get_task_budget_status_worker import (
    get_task_budget_status_worker,
)


_EVALUATION_TABLE = "item_cost_evaluations"

_REQUIRED_CLAUSES = (
    "item_cost_evaluations.kind = 'committed'",
    "item_cost_evaluations.superseded_at is null",
    "item_cost_evaluations.is_deleted is false",
)


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _CapturingSession:
    """Capture every statement, and answer just enough to reach the early return."""

    def __init__(self, scalar_returns):
        self._scalar_returns = list(scalar_returns)
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return self._scalar_returns.pop(0) if self._scalar_returns else None

    async def scalars(self, statement):
        self.statements.append(statement)
        return _ScalarsResult([])


def _compiled(statement) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True})).lower()


def _ctx(session, data: dict) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_phase9", "user_id": "usr_phase9", "role_name": "manager"},
        incoming_data=data,
        session=session,
        query_params={},
    )


def _task():
    return SimpleNamespace(client_id="tsk_phase9", workspace_id="ws_phase9")


def _item():
    return SimpleNamespace(client_id="itm_phase9", workspace_id="ws_phase9")


async def _run_budget_status(session) -> None:
    await get_task_budget_status(_ctx(session, {"task_client_id": "tsk_phase9"}))


async def _run_budget_status_worker(session) -> None:
    await get_task_budget_status_worker(_ctx(session, {"task_client_id": "tsk_phase9"}))


async def _run_lifetime(session) -> None:
    await get_item_lifetime_economics(_ctx(session, {"item_client_id": "itm_phase9"}))


# Each row drives a DIFFERENT production function; no two share a call graph.
_SITES = (
    # (id, runner, the scalar() answers that reach the evaluation SELECT)
    (
        "get_task_budget_status.py:106-108",
        _run_budget_status,
        # task found, no PRIMARY item, then the evaluation SELECT itself
        (_task(), None, None),
    ),
    (
        "get_task_budget_status_worker.py:30-32",
        _run_budget_status_worker,
        (_task(), None, None),
    ),
    (
        "get_item_lifetime_economics.py:46-48",
        _run_lifetime,
        # the item lookup; the evaluation SELECT goes through scalars()
        (_item(),),
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("runner", "scalar_returns"),
    [(runner, returns) for _, runner, returns in _SITES],
    ids=[site_id for site_id, _, _ in _SITES],
)
async def test_committed_current_filter_is_present_in_the_compiled_select(
    runner, scalar_returns
) -> None:
    session = _CapturingSession(scalar_returns)

    await runner(session)

    evaluation_statements = [
        compiled
        for compiled in (_compiled(statement) for statement in session.statements)
        if _EVALUATION_TABLE in compiled
    ]
    # Non-vacuity: exactly one statement reads the evaluation table, so the
    # assertions below cannot be satisfied by some other query.
    assert len(evaluation_statements) == 1
    compiled = evaluation_statements[0]
    for clause in _REQUIRED_CLAUSES:
        assert clause in compiled
