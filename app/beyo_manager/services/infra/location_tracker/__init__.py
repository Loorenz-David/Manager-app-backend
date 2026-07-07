from beyo_manager.config import settings
from beyo_manager.errors.base import DomainError
from beyo_manager.services.infra.location_tracker.client import LocationTrackerClient


def get_location_tracker_client() -> LocationTrackerClient:
    base_url = (settings.location_tracker_base_url or "").strip()
    api_key = (settings.location_tracker_api_key or "").strip()

    if not base_url or not api_key:
        raise DomainError(
            "LOCATION_TRACKER_BASE_URL and LOCATION_TRACKER_API_KEY must be configured."
        )

    return LocationTrackerClient(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=settings.location_tracker_timeout_seconds,
    )
