"""`parse_stock_demand_body` — MC-8 steps 5-7 (intention §8B; master plan §6.5).

Raw-bytes parsing for the demand webhook: UTF-8 decode, JSON decode, per-entry shape
(the demand entry defect table), then the duplicate-identity rule. Collects every
defect before raising, so the 422 message names every offending entry (§8 "the error
names every offending entry").
"""

from __future__ import annotations

import json

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.stock_demand_entries import DemandEntry

_MAX_QUANTITY_REQUESTED = 2147483647


def parse_stock_demand_body(raw: bytes) -> list[DemandEntry]:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError("Malformed request: body is not valid UTF-8 JSON.") from None

    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        raise ValidationError("Malformed request: body is not valid JSON.") from None

    if not isinstance(payload, list) or len(payload) == 0:
        raise ValidationError(
            "Malformed request: body must be a JSON array with at least one entry."
        )

    defects: list[str] = []
    entries: list[DemandEntry] = []
    first_index_by_identity: dict[tuple[str, str], int] = {}

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            defects.append(f"entry {index}: must be an object")
            continue

        item_category_raw = item.get("itemCategory")
        category_ok = isinstance(item_category_raw, str) and bool(item_category_raw.strip())
        if not category_ok:
            defects.append(f"entry {index}: itemCategory must be a non-blank string")

        properties_raw = item.get("properties")
        properties_ok = isinstance(properties_raw, dict)
        if not properties_ok:
            defects.append(f"entry {index}: properties must be an object")

        quantity_requested = item.get("quantityRequested")
        quantity_ok = type(quantity_requested) is int and 0 <= quantity_requested <= _MAX_QUANTITY_REQUESTED
        if not quantity_ok:
            defects.append(
                f"entry {index}: quantityRequested must be an integer between 0 and "
                f"{_MAX_QUANTITY_REQUESTED}"
            )

        if not (category_ok and properties_ok and quantity_ok):
            continue

        entry = DemandEntry(
            index=index,
            item_category_raw=item_category_raw,
            properties_raw=properties_raw,
            properties_normalized=normalize_stock_criteria(properties_raw),
            properties_signature=compute_stock_criteria_signature(properties_raw),
            quantity_requested=quantity_requested,
        )
        identity = (entry.item_category_key, entry.properties_signature)
        if identity in first_index_by_identity:
            defects.append(
                f"entries {first_index_by_identity[identity]} and {index} resolve to "
                "the same identity"
            )
        else:
            first_index_by_identity[identity] = index
        entries.append(entry)

    if defects:
        raise ValidationError("Malformed request: " + "; ".join(defects) + ".")

    return entries
