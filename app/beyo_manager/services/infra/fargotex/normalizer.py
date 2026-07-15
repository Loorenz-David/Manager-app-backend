import logging

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.services.infra.fargotex.constants import (
    FARGOTEX_BASE_URL,
    FARGOTEX_ORIGIN,
)

logger = logging.getLogger(__name__)


def _absolutize_image(raw_image: str) -> str:
    value = raw_image.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{FARGOTEX_BASE_URL}{value}"
    return f"{FARGOTEX_BASE_URL}/{value}"


def _absolutize_external_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{FARGOTEX_BASE_URL}{value}"
    return f"{FARGOTEX_BASE_URL}/{value}"


def normalize_fargotex_candidate(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None

    name_value = raw.get("name")
    code_value = raw.get("code")
    image_value = raw.get("image")
    external_url_value = raw.get("external_url")

    name = name_value.strip() if isinstance(name_value, str) else ""
    code = (
        str(code_value).strip()
        if isinstance(code_value, (str, int, float)) and not isinstance(code_value, bool)
        else ""
    )
    image_raw = image_value.strip() if isinstance(image_value, str) else ""
    external_url_raw = external_url_value.strip() if isinstance(external_url_value, str) else ""

    if not name or not code or not image_raw:
        logger.debug(
            "Skipping malformed Fargotex product: %r",
            {key: raw.get(key) for key in ("name", "code", "image", "external_url")},
        )
        return None

    normalized = {
        "client_id": None,
        "name": name,
        "code": code,
        "image_url": _absolutize_image(image_raw),
        "external_url": _absolutize_external_url(external_url_raw) if external_url_raw else None,
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": UpholsteryInventoryConditionEnum.OUT_OF_STOCK.value,
        "upholstery_category": None,
        "origin": FARGOTEX_ORIGIN,
    }

    for key in (
        "variant_name",
        "variation_id",
        "parent_name",
        "sku",
        "gallery_code",
        "gallery_position",
    ):
        value = raw.get(key)
        if value is None or isinstance(value, bool):
            continue
        value_string = str(value).strip()
        if value_string:
            normalized[key] = value_string

    return normalized


def normalize_fargotex_candidates(raw_products: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        candidate = normalize_fargotex_candidate(raw)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
