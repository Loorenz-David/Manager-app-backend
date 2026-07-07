from beyo_manager.services.infra.location_tracker.models import LocationItem


def map_location_items(raw: list[dict]) -> list[LocationItem]:
    mapped: list[LocationItem] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        mapped.append(
            LocationItem(
                item_article_number=_as_optional_str(item.get("item_article_number")),
                sku=_as_optional_str(item.get("sku")),
                item_position=_as_optional_str(item.get("item_position")),
            )
        )
    return mapped


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None
