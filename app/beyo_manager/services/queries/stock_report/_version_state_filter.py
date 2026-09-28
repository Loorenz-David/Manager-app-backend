"""The `state` query parameter of `GET /api/v1/stock-report/snapshots/versions`
(draft versions, 2026-09-28; G-2 from the frontend's gaps document): a comma list of
`draft|active|closed`, parsed as `priority` is (`_priority_filter.py`).

`parse_version_state_filter` returns `None` for "every state" (the parameter omitted
or empty) or a list of `StockReportSnapshotVersionStateEnum`; tokens are stripped,
empties ignored, repeats folded, and any unknown token — `all` included, there is no
such shorthand here — is a 422. `version_state_predicate` turns the list into the
`OR` of the §3.1 pairs through `_predicates.py`, so the read and the writers share
one spelling of each state.
"""

from __future__ import annotations

from sqlalchemy import or_

from beyo_manager.domain.stock_report.enums import StockReportSnapshotVersionStateEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report._predicates import (
    version_is_active,
    version_is_closed,
    version_is_draft,
)

_PREDICATES = {
    StockReportSnapshotVersionStateEnum.DRAFT: version_is_draft,
    StockReportSnapshotVersionStateEnum.ACTIVE: version_is_active,
    StockReportSnapshotVersionStateEnum.CLOSED: version_is_closed,
}


def parse_version_state_filter(raw):
    if raw is None:
        return None
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    if not tokens:
        return None
    states = []
    for token in tokens:
        try:
            state = StockReportSnapshotVersionStateEnum(token)
        except ValueError:
            raise ValidationError(
                f"STOCK_REPORT_UNKNOWN_VERSION_STATE: '{token}' is not one of "
                "draft, active, closed."
            ) from None
        if state not in states:
            states.append(state)
    return states


def version_state_predicate(states):
    """The `WHERE` clause for a parsed filter, or `None` when every state is wanted."""
    if states is None:
        return None
    return or_(*(_PREDICATES[state]() for state in states))
