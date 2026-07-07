ITEMS_LOCATION_PATH = "manager-app/items/location"


def bearer_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
