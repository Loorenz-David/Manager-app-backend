from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products


def _mock_response(status_code: int, json_body) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body
    return response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_nevotex_response_returns_empty_list() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, []))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("query with no results", limit=7)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_containers_without_product_key_returns_empty_list() -> None:
    containers = [
        {"template": "SomethingElse", "id": "abc"},
        {"template": "AnotherThing", "id": "def"},
    ]
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, containers))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("q", limit=7)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_logs_warning_and_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_class.return_value = mock_client

        with patch("beyo_manager.services.infra.nevotex.client.logger.warning") as warning_mock:
            with pytest.raises(ExternalServiceError, match="timed out"):
                await fetch_nevotex_raw_products("q", limit=7)

    warning_mock.assert_called_once_with("Nevotex search timed out for q=%r", "q")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_200_response_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(503, None))
        mock_client_class.return_value = mock_client

        with pytest.raises(ExternalServiceError, match="503"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_products_are_flattened_across_containers() -> None:
    containers = [
        {"Product": [{"name": "A", "number": "1", "image": "%2fa.jpg"}]},
        {"Product": [{"name": "B", "number": "2", "image": "%2fb.jpg"}]},
    ]
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, containers))
        mock_client_class.return_value = mock_client

        result = await fetch_nevotex_raw_products("q", limit=7)

    assert result == [
        {"name": "A", "number": "1", "image": "%2fa.jpg"},
        {"name": "B", "number": "2", "image": "%2fb.jpg"},
    ]
