import logging

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.services.infra.ohlssons_tyger.constants import (
    OHLSSONS_TYGER_BASE_URL,
    OHLSSONS_TYGER_ORIGIN,
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
        return f"{OHLSSONS_TYGER_BASE_URL}{value}"
    return f"{OHLSSONS_TYGER_BASE_URL}/{value}"


def normalize_ohlssons_tyger_candidate(raw: dict) -> dict | None:
    name_value = raw.get("name")
    code_value = raw.get("code")
    image_value = raw.get("image")

    name = name_value.strip() if isinstance(name_value, str) else ""
    code = code_value.strip() if isinstance(code_value, str) else ""
    image_raw = image_value.strip() if isinstance(image_value, str) else ""

    if not name or not code or not image_raw:
        logger.debug(
            "Skipping malformed Ohlssons Tyger product: %r",
            {key: raw.get(key) for key in ("detail_url", "name", "code", "image")},
        )
        return None

    return {
        "client_id": None,
        "name": name,
        "code": code,
        "image_url": _absolutize_image(image_raw),
        "external_url": raw.get("detail_url"),
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": UpholsteryInventoryConditionEnum.OUT_OF_STOCK.value,
        "upholstery_category": None,
        "origin": OHLSSONS_TYGER_ORIGIN,
    }


def normalize_ohlssons_tyger_candidates(raw_products: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for raw in raw_products:
        candidate = normalize_ohlssons_tyger_candidate(raw)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
