"""Shared data shapes for the Scanner stock-demand paths (master plan §6.5).

`DemandEntry` is the parsed shape of one demand-request entry. `item_category_key`
is derived automatically at construction (MC-8's category-resolution key); the
normalized-properties fields are supplied by whoever builds the entry (the demand
parser in `stock_demand_request.py`, phase 7; or a test fixture) because both
callers already hold the raw `properties` dict and call
`normalize_stock_criteria`/`compute_stock_criteria_signature` themselves (MC-3).

`DemandOutcome` and `StockDemandResult` describe what `apply_stock_demand`
(phase 6) reports back per entry and overall.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from beyo_manager.domain.stock_report.enums import (
    StockDemandDeletedOutcomeEnum,
    StockDemandOutcomeEnum,
)
from beyo_manager.services.infra.events.domain_event import WorkspaceEvent


@dataclass(frozen=True)
class DemandEntry:
    index: int
    item_category_raw: str
    item_category_key: str = field(init=False)
    properties_raw: dict
    properties_normalized: dict
    properties_signature: str
    quantity_requested: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "item_category_key", self.item_category_raw.strip().lower()
        )


@dataclass(frozen=True)
class DemandOutcome:
    index: int
    item_category_raw: str
    properties_raw: dict
    outcome: StockDemandOutcomeEnum


@dataclass(frozen=True)
class DemandDeleteEntry:
    """One entry of the Scanner **delete** request (phase 13A, §14E E2).

    `DemandEntry` without `quantity_requested`: the delete body carries no quantity,
    and a `quantityRequested` key sent anyway is an unknown key, ignored like any
    other (§14E E2/U7). `item_category_key` is derived the same way, so both
    `_demand_lookup.py` helpers take this type unchanged — "the same engine as
    find-or-create" (§14E E4).
    """

    index: int
    item_category_raw: str
    item_category_key: str = field(init=False)
    properties_raw: dict
    properties_normalized: dict
    properties_signature: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "item_category_key", self.item_category_raw.strip().lower()
        )


@dataclass(frozen=True)
class DemandDeleteOutcome:
    index: int
    item_category_raw: str
    properties_raw: dict
    outcome: StockDemandDeletedOutcomeEnum


@dataclass
class StockDemandResult:
    outcomes: list[DemandOutcome] = field(default_factory=list)
    events: list[WorkspaceEvent] = field(default_factory=list)
