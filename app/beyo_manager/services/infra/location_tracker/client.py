from __future__ import annotations

import logging
from typing import Any

import httpx

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.location_tracker.constants import ITEMS_LOCATION_PATH, bearer_headers

logger = logging.getLogger(__name__)


class LocationTrackerClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        # Build the absolute endpoint URL once. We join explicitly rather than relying on
        # httpx base_url merging, which concatenates paths and would fuse a path-prefixed
        # base (e.g. https://host/api) with the endpoint into https://host/apimanager-app/...
        self._items_location_url = f"{base_url.rstrip('/')}/{ITEMS_LOCATION_PATH.lstrip('/')}"
        self._headers = bearer_headers(api_key)
        self._timeout = httpx.Timeout(timeout_seconds)

    async def patch_item_locations(self, changes: list[dict]) -> None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
            ) as client:
                response = await client.patch(self._items_location_url, json=changes)
        except httpx.TimeoutException as exc:
            logger.warning("location_tracker | patch timed out | changes=%d", len(changes))
            raise ExternalServiceError("Location tracker request timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("location_tracker | patch request error | changes=%d error=%s", len(changes), exc)
            raise ExternalServiceError("Location tracker request failed.") from exc

        if response.status_code < 200 or response.status_code >= 300:
            logger.warning("location_tracker | patch unexpected status=%s", response.status_code)
            raise ExternalServiceError(
                f"Location tracker returned unexpected status {response.status_code}."
            )

    async def get_item_locations(self, q: str, item_identity: list[str]) -> list[dict[str, Any]]:
        params = {
            "q": q,
            "item_identity": ",".join(item_identity),
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
            ) as client:
                response = await client.get(self._items_location_url, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("location_tracker | get timed out | q=%r", q)
            raise ExternalServiceError("Location tracker request timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("location_tracker | get request error | q=%r error=%s", q, exc)
            raise ExternalServiceError("Location tracker request failed.") from exc

        if response.status_code < 200 or response.status_code >= 300:
            logger.warning("location_tracker | get unexpected status=%s q=%r", response.status_code, q)
            raise ExternalServiceError(
                f"Location tracker returned unexpected status {response.status_code}."
            )

        try:
            raw = response.json()
        except ValueError as exc:
            logger.warning("location_tracker | get invalid json | q=%r", q)
            raise ExternalServiceError("Location tracker returned a non-JSON response.") from exc

        if not isinstance(raw, list):
            logger.warning("location_tracker | get unexpected shape | q=%r", q)
            raise ExternalServiceError("Location tracker returned an unexpected response shape.")

        return [item for item in raw if isinstance(item, dict)]
