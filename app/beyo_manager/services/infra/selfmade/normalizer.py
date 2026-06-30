import logging
import re
from collections.abc import Sequence
from urllib.parse import urlparse

from beyo_manager.domain.upholstery.enums import UpholsteryInventoryConditionEnum
from beyo_manager.services.infra.selfmade.constants import (
    SELFMADE_BASE_URL,
    SELFMADE_ORIGIN,
)

logger = logging.getLogger(__name__)

_PRICE_PATTERN = re.compile(r"(\d+(?:[\s.]\d{3})*(?:,\d+)?)\s*kr(?:\s*/\s*m|/m)?", re.IGNORECASE)


def _absolutize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{SELFMADE_BASE_URL}{value}"
    return f"{SELFMADE_BASE_URL}/{value}"


def extract_selfmade_code(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    code = slug.rsplit("-", 1)[-1]
    return code if code.isdigit() else None


def _parse_price(raw_price: str) -> tuple[float | None, str | None]:
    text = raw_price.strip()
    if not text:
        return None, None

    unit = "m" if re.search(r"kr\s*/\s*m|kr/m", text, re.IGNORECASE) else None
    matches = _PRICE_PATTERN.findall(text)
    if not matches:
        return None, unit

    value = matches[-1].replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(value), unit
    except ValueError:
        return None, unit


def _normalize_availability(labels: object) -> str | None:
    if not isinstance(labels, Sequence) or isinstance(labels, (str, bytes)):
        return None
    values = [str(label).strip() for label in labels if str(label).strip()]
    return ", ".join(values) if values else None


def normalize_selfmade_candidate(raw: dict) -> dict | None:
    name_value = raw.get("name")
    detail_url_value = raw.get("detail_url")
    image_url_value = raw.get("image_url")
    raw_price_value = raw.get("raw_price")

    name = name_value.strip() if isinstance(name_value, str) else ""
    detail_url = _absolutize_url(detail_url_value) if isinstance(detail_url_value, str) else ""
    image_url = _absolutize_url(image_url_value) if isinstance(image_url_value, str) else ""
    raw_price = raw_price_value.strip() if isinstance(raw_price_value, str) else ""
    code = extract_selfmade_code(detail_url) if detail_url else None
    price_amount, unit = _parse_price(raw_price)

    if not name or not code or not detail_url or not image_url:
        logger.debug(
            "Skipping malformed Selfmade product: %r",
            {key: raw.get(key) for key in ("detail_url", "name", "image_url", "raw_price")},
        )
        return None

    return {
        "client_id": None,
        "name": name,
        "code": code,
        "image_url": image_url,
        "external_url": detail_url,
        "favorite": None,
        "list_order": None,
        "current_stored_amount_meters": 0,
        "inventory_condition": UpholsteryInventoryConditionEnum.OUT_OF_STOCK.value,
        "upholstery_category": None,
        "origin": SELFMADE_ORIGIN,
        "price": price_amount,
        "price_amount": price_amount,
        "price_currency": "SEK",
        "unit": unit,
        "availability": _normalize_availability(raw.get("availability_labels")),
    }


def normalize_selfmade_candidates(raw_candidates: Sequence[dict]) -> list[dict]:
    candidates: list[dict] = []
    for raw in raw_candidates:
        candidate = normalize_selfmade_candidate(raw)
        if candidate is not None:
            candidates.append(candidate)
    return candidates
