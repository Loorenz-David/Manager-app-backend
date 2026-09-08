from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from beyo_manager.errors.external_service import ExternalServiceError
from beyo_manager.services.infra.nevotex.client import fetch_nevotex_raw_products

_PRODUCT_HTML = (
    '<section><li data-param="ProductId" data-paramvalue="1008301" '
    'data-selected-details-page="/Default.aspx?ProductId=1008301&VariantID=VARGRP249_1008336">'
    '<img src="/admin/public/getimage.ashx?image=%2FFiles%2F1008336.jpg" '
    'alt="Tyg Eros 36 Light brown ">'
    '<a title="Visa" href="/produkter/mobeltyger/eros/1008336">Visa</a>'
    '</li><li id="ViewAllProductResults" data-all-results-page="/soekresultat">'
    '<span class="js-suggestion">1008336</span></li></section>'
)

_NO_RESULTS_HTML = (
    '<section><li id="NoProductResults">Vi hittade inga produkter</li></section>'
)


def _mock_response(status_code: int, text: str) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


def _patched_client(response: MagicMock | None = None, *, side_effect=None):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=response, side_effect=side_effect)
    return mock_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_requests_the_swift_search_endpoint_with_verified_params() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client = _patched_client(_mock_response(200, _PRODUCT_HTML))
        mock_client_class.return_value = mock_client

        await fetch_nevotex_raw_products("1008336", limit=7)

    url, = mock_client.get.call_args.args
    assert url == "https://nevotex.se/service-pages/product-and-content-search-results"
    assert mock_client.get.call_args.kwargs["params"] == {
        "defaultpdpId": "null",
        "IsVariant": "false",
        "redirect": "false",
        "eq": "1008336",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parses_products_out_of_the_html_fragment() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(200, _PRODUCT_HTML))

        result = await fetch_nevotex_raw_products("1008336", limit=7)

    assert result == [
        {
            "productId": "1008301",
            "variantId": "VARGRP249_1008336",
            "number": "1008336",
            "name": "Tyg Eros 36 Light brown",
            "image": "/admin/public/getimage.ashx?image=%2FFiles%2F1008336.jpg",
            "url": "/produkter/mobeltyger/eros/1008336",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_zero_results_is_not_treated_as_an_outage() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(200, _NO_RESULTS_HTML))

        result = await fetch_nevotex_raw_products("query with no results", limit=7)

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_limit_truncates_parsed_products() -> None:
    html = "<section>" + "".join(
        f'<li data-param="ProductId" data-paramvalue="100830{index}">'
        f'<img alt="Tyg {index}" src="/a.jpg"></li>'
        for index in range(5)
    ) + "</section>"

    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(200, html))

        result = await fetch_nevotex_raw_products("q", limit=2)

    assert len(result) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timeout_logs_warning_and_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(
            side_effect=httpx.TimeoutException("timed out")
        )

        with patch("beyo_manager.services.infra.nevotex.client.logger.warning") as warning_mock:
            with pytest.raises(ExternalServiceError, match="timed out"):
                await fetch_nevotex_raw_products("q", limit=7)

    warning_mock.assert_called_once_with("Nevotex search timed out for q=%r", "q")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_error_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(
            side_effect=httpx.ConnectError("boom")
        )

        with pytest.raises(ExternalServiceError, match="request failed"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_200_response_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(503, ""))

        with pytest.raises(ExternalServiceError, match="503"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redirect_status_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(301, ""))

        with pytest.raises(ExternalServiceError, match="301"):
            await fetch_nevotex_raw_products("q", limit=7)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_non_html_body_raises_external_service_error() -> None:
    with patch("beyo_manager.services.infra.nevotex.client.httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = _patched_client(_mock_response(200, "not markup"))

        with pytest.raises(ExternalServiceError, match="unexpected response shape"):
            await fetch_nevotex_raw_products("q", limit=7)
