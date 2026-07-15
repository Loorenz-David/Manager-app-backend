from __future__ import annotations

from collections.abc import Mapping
import json


_WEIGHT_UNIT_MAP = {
    "kg": "KILOGRAMS",
    "g": "GRAMS",
    "lb": "POUNDS",
    "oz": "OUNCES",
}


def build_normalized_product_sync_payload(
    item: Mapping[str, object],
    *,
    shop_integration_id: str | None = None,
) -> dict:
    barcode = _clean_str(item.get("item_article_number")) or _clean_str(
        item.get("article_number")
    )

    product = {
        "title": _required_str(item.get("title")),
        "descriptionHtml": _clean_str(item.get("description")),
        "status": _normalize_status(item.get("status")),
        "tags": _normalize_tags(item.get("tags")),
        "productType": _clean_str(item.get("product_category")),
    }

    inventory_item: dict[str, object] = {}
    sku = _clean_str(item.get("sku"))
    if sku is not None:
        inventory_item["sku"] = sku

    weight_payload = _normalize_weight(item.get("weight"))
    if weight_payload is not None:
        inventory_item["measurement"] = {"weight": weight_payload}

    variant = {
        "barcode": barcode,
        "price": _clean_str(item.get("price")),
        "inventoryItem": inventory_item or None,
    }

    metafields = []
    for key, value in ((item.get("metafields") or {}) or {}).items():
        cleaned_key = _clean_str(key)
        if cleaned_key is None:
            continue
        metafield_type = "single_line_text_field"
        metafield_value = value
        if isinstance(value, Mapping) and ("type" in value or "value" in value):
            metafield_type = _clean_str(value.get("type")) or "single_line_text_field"
            metafield_value = value.get("value")
        metafields.append(
            {
                "key": cleaned_key,
                "type": metafield_type,
                "value": _stringify_metafield_value(metafield_value),
            }
        )

    payload = {
        "product": _drop_none(product),
        "variant": _drop_none(variant),
        "metafields": metafields,
    }

    adjustments = []
    for adjustment in item.get("inventory_adjustments") or []:
        if not isinstance(adjustment, Mapping):
            continue
        if shop_integration_id is not None and adjustment.get("shop_integration_id") != shop_integration_id:
            continue
        quantity = adjustment.get("quantity_to_add")
        location_id = _clean_str(adjustment.get("location_id"))
        if isinstance(quantity, int) and quantity > 0 and location_id is not None:
            adjustments.append(
                {
                    "location_id": location_id,
                    "quantity_to_add": quantity,
                }
            )
    if adjustments:
        payload["inventory"] = {"adjustments": adjustments}
    return payload


def _normalize_status(value: object) -> str:
    status = _clean_str(value)
    if status is None:
        return "DRAFT"
    return status.upper()


def _normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for tag in value:
        cleaned = _clean_str(tag)
        if cleaned is not None:
            normalized.append(cleaned)
    return normalized


def _normalize_weight(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    unit = _WEIGHT_UNIT_MAP[str(value["unit"]).strip().lower()]
    return {
        "value": float(value["value"]),
        "unit": unit,
    }


def _drop_none(payload: Mapping[str, object]) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def _required_str(value: object) -> str:
    cleaned = _clean_str(value)
    if cleaned is None:
        raise ValueError("title is required")
    return cleaned


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _stringify_metafield_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"))
