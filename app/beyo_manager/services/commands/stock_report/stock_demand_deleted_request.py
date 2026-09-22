"""`parse_stock_demand_deleted_body` — the delete webhook's raw-bytes parser
(phase 13A; master plan §6.5; intention §8B MC-8, §14E E2).

The demand entry rules for `itemCategory` and `properties`, and **nothing else**:
`quantityRequested` is an unknown key here and is ignored exactly like any other
(§14E E2/U7; Scanner v2 §4A.1 "sent anyway, it is ignored"). Every defect is
collected before raising, so the 422 names every offending entry; duplicates are
detected on the **normalized** identity `(item_category_key, properties_signature)`
(MC-3, MC-8 step 7). The raw `itemCategory` and `properties` are kept on the entry
because the response echoes them as received (§14E E7).

The two field checks are written inline here rather than shared with
`stock_demand_request.py` (phase 7): that module has no per-field validator
functions to import — the checks are inline expressions inside one loop — so sharing
them would mean editing APPROVED code for no observable guarantee (owner card D-3,
closed 2026-09-22 as "no change").
"""

from __future__ import annotations

import json

from beyo_manager.domain.stock_report.criteria_normalization import (
    compute_stock_criteria_signature,
    normalize_stock_criteria,
)
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.stock_report.stock_demand_entries import (
    DemandDeleteEntry,
)


def parse_stock_demand_deleted_body(raw: bytes) -> list[DemandDeleteEntry]:
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
    entries: list[DemandDeleteEntry] = []
    first_index_by_identity: dict[tuple[str, str], int] = {}

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            defects.append(f"entry {index}: must be an object")
            continue

        item_category_raw = item.get("itemCategory")
        category_ok = isinstance(item_category_raw, str) and bool(
            item_category_raw.strip()
        )
        if not category_ok:
            defects.append(f"entry {index}: itemCategory must be a non-blank string")

        properties_raw = item.get("properties")
        properties_ok = isinstance(properties_raw, dict)
        if not properties_ok:
            defects.append(f"entry {index}: properties must be an object")

        if not (category_ok and properties_ok):
            continue

        entry = DemandDeleteEntry(
            index=index,
            item_category_raw=item_category_raw,
            properties_raw=properties_raw,
            properties_normalized=normalize_stock_criteria(properties_raw),
            properties_signature=compute_stock_criteria_signature(properties_raw),
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
