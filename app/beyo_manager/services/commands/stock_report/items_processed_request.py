"""`parse_items_processed_body` — MC-8 steps 5-7 (intention §8B; master plan §6.5).

Raw-bytes parsing for the processed webhook: UTF-8 decode, JSON decode, per-entry
shape. Unlike the demand webhook, duplicates are **not** an error here (v1 §4.3;
MC-8 step 7) — a repeated `article_number` is decided per entry in request order by
the command, so this parser collects every defect and returns the numbers **as
received** (echo); stripping happens in the command (plan 9 task 1).
"""

from __future__ import annotations

import json

from beyo_manager.errors.validation import ValidationError


def parse_items_processed_body(raw: bytes) -> list[str]:
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
    numbers: list[str] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            defects.append(f"entry {index}: must be an object")
            continue

        article_number_raw = item.get("article_number")
        article_number_ok = isinstance(article_number_raw, str) and bool(
            article_number_raw.strip()
        )
        if not article_number_ok:
            defects.append(f"entry {index}: article_number must be a non-blank string")
            continue

        numbers.append(article_number_raw)

    if defects:
        raise ValidationError("Malformed request: " + "; ".join(defects) + ".")

    return numbers
