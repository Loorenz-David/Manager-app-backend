import logging
from urllib.parse import unquote

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.services.infra.nevotex.constants import (
    NEVOTEX_BASE_URL as _NEVOTEX_BASE_URL,
)

logger = logging.getLogger(__name__)


def _absolutize_image(raw_image: str) -> str:
    decoded = unquote(raw_image.strip())
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    if decoded.startswith("/"):
        return f"{_NEVOTEX_BASE_URL}{decoded}"
    return f"{_NEVOTEX_BASE_URL}/{decoded}"


def _absolutize_external_url(raw_url: str) -> str:
    decoded = unquote(raw_url.strip())
    if not decoded:
        return ""
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    if decoded.startswith("/"):
        return f"{_NEVOTEX_BASE_URL}{decoded}"
    return f"{_NEVOTEX_BASE_URL}/{decoded}"


def _resolve_external_url(raw: dict) -> str | None:
    for key in ("link", "url", "productUrl", "productURL", "productLink", "uri"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return _absolutize_external_url(value)
    return None


def normalize_nevotex_candidate(raw: dict) -> dict | None:
    name_value = raw.get("name")
    code_value = raw.get("number")
    image_value = raw.get("image")

    name = name_value.strip() if isinstance(name_value, str) else ""
    code = code_value.strip() if isinstance(code_value, str) else ""
    image_raw = image_value.strip() if isinstance(image_value, str) else ""

    if not name or not code or not image_raw:
        logger.debug(
            "Skipping malformed Nevotex product: %r",
            {key: raw.get(key) for key in ("productId", "name", "number", "image")},
        )
        return None

    return {
        "client_id": None,
        "name": name,
        "code": code,
        "image_url": _absolutize_image(image_raw),
        "external_url": _resolve_external_url(raw),
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": UpholsteryInventoryConditionEnum.OUT_OF_STOCK.value,
        "upholstery_category": None,
        "origin": "nevotex",
    }


def normalize_nevotex_candidates(raw_products: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for raw in raw_products:
        candidate = normalize_nevotex_candidate(raw)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
