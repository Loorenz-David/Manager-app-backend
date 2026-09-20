from beyo_manager.domain.items.properties_signature import compute_properties_signature

CRITERIA_NORMALIZATION_VERSION = 1


def normalize_stock_criteria(raw: dict) -> dict:
    result = {}
    for key, value in raw.items():
        if isinstance(value, str):
            result[key] = [value.strip().lower()] if value.strip() else value
        elif (
            isinstance(value, list)
            and value
            and all(isinstance(v, str) for v in value)
            and any(v.strip() for v in value)
        ):
            result[key] = sorted(
                {v.strip().lower() for v in value if v.strip().lower() != ""}
            )
        else:
            result[key] = value
    return result


def compute_stock_criteria_signature(raw: dict) -> str:
    return compute_properties_signature(normalize_stock_criteria(raw))
