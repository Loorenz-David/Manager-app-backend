from __future__ import annotations
import re
import json
from dataclasses import dataclass
from beyo_manager.domain.stock_report.enums import StockCriteriaMismatchReasonEnum
from beyo_manager.domain.stock_report.scanner_property_tables import (
    DRAWERS_QTY_KEY,
    DRAWERS_RANGE_KEY,
    EXCLUDED_ITEM_PROPERTY_KEYS,
    WOOD_GROUP_KEY,
    WOOD_TYPE_KEY,
    drawer_range_of,
    wood_group_of_token,
)


@dataclass(frozen=True)
class CriterionFailure:
    key: str
    reason: StockCriteriaMismatchReasonEnum


def tokenize_property_value(value: str) -> list[str]:
    return [part.strip().lower() for part in re.split(r"[,/]", value) if part.strip()]


def _property_value(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value).removesuffix(".0")
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return None


def build_item_property_bag(item) -> dict[str, str]:
    bag = {}
    for key in sorted((item.properties or {}).keys()):
        raw_key, raw_value = key, (item.properties or {})[key]
        value = _property_value(raw_value)
        normalized_key = raw_key.strip() if isinstance(raw_key, str) else ""
        if normalized_key and value is not None and value.strip():
            bag[normalized_key] = value.strip()
    for key in EXCLUDED_ITEM_PROPERTY_KEYS:
        bag.pop(key, None)
    bag["quantity"] = str(item.quantity)
    if wood := bag.get(WOOD_TYPE_KEY):
        if (
            (group := wood_group_of_token(tokenize_property_value(wood)[0]))
            if tokenize_property_value(wood)
            else None
        ):
            bag[WOOD_GROUP_KEY] = group
    if (drawers := bag.get(DRAWERS_QTY_KEY)) and (
        drawer_range := drawer_range_of(drawers)
    ):
        bag[DRAWERS_RANGE_KEY] = drawer_range
    return bag


def evaluate_stock_criteria(item, criteria: dict) -> list[CriterionFailure]:
    bag = build_item_property_bag(item)
    failures = []
    for key, accepted in criteria.items():
        value = bag.get(key)
        if isinstance(accepted, list) and not accepted:
            failures.append(
                CriterionFailure(
                    key, StockCriteriaMismatchReasonEnum.CRITERION_NOT_UNDERSTOOD
                )
            )
            continue
        if value is None:
            source_key = (
                WOOD_TYPE_KEY
                if key == WOOD_GROUP_KEY
                else DRAWERS_QTY_KEY
                if key == DRAWERS_RANGE_KEY
                else None
            )
            reason = (
                StockCriteriaMismatchReasonEnum.NO_GROUP_FOR_VALUE
                if source_key in bag
                else StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM
            )
            failures.append(CriterionFailure(key, reason))
            continue
        if accepted is None:
            continue
        tokens = tokenize_property_value(value)
        if not tokens:
            failures.append(
                CriterionFailure(
                    key, StockCriteriaMismatchReasonEnum.MISSING_ON_ITEM
                )
            )
            continue
        if not any(token in accepted for token in tokens):
            failures.append(
                CriterionFailure(
                    key, StockCriteriaMismatchReasonEnum.VALUE_NOT_ACCEPTED
                )
            )
    return sorted(failures, key=lambda failure: failure.key)


def matches_stock_criteria(item, criteria: dict) -> bool:
    return not evaluate_stock_criteria(item, criteria)
