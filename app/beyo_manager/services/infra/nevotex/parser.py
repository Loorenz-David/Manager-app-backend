import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

_PRODUCT_ROW_PARAM = "ProductId"
_SUGGESTION_CLASS = "js-suggestion"
_DETAILS_LINK_TITLE = "Visa"
_ARTICLE_NUMBER_PATTERN = re.compile(r"^\d+$")


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _query_value(url: str, key: str) -> str:
    if not url:
        return ""
    values = parse_qs(urlparse(url).query).get(key)
    return values[0].strip() if values else ""


def _article_number_from_variant(variant_id: str) -> str:
    suffix = variant_id.rsplit("_", 1)[-1].strip()
    return suffix if _ARTICLE_NUMBER_PATTERN.match(suffix) else ""


def _article_number_from_url(url: str) -> str:
    segment = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].strip()
    return segment if _ARTICLE_NUMBER_PATTERN.match(segment) else ""


class _SearchResultsParser(HTMLParser):
    """Collects the product rows Nevotex renders as ``li[data-param="ProductId"]``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self._current: dict | None = None
        self._in_suggestion = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li":
            # Browsers auto-close an open <li> when the next one starts.
            self._finish_row()
            if _extract_attr(attrs, "data-param") == _PRODUCT_ROW_PARAM:
                self._current = {
                    "product_id": _extract_attr(attrs, "data-paramvalue"),
                    "details_page": _extract_attr(attrs, "data-selected-details-page"),
                    "image": "",
                    "alt_name": "",
                    "suggestion_parts": [],
                    "url": "",
                }
            return

        if self._current is None:
            return

        if tag == "img":
            if not self._current["image"]:
                self._current["image"] = _extract_attr(attrs, "src")
            if not self._current["alt_name"]:
                self._current["alt_name"] = _extract_attr(attrs, "alt")
            return

        if tag == "a":
            if _extract_attr(attrs, "title") == _DETAILS_LINK_TITLE and not self._current["url"]:
                self._current["url"] = _extract_attr(attrs, "href")
            return

        if tag == "span" and _SUGGESTION_CLASS in _extract_attr(attrs, "class").split():
            self._in_suggestion = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._in_suggestion = False
        elif tag == "li":
            self._finish_row()

    def handle_data(self, data: str) -> None:
        if self._current is None or not self._in_suggestion:
            return
        text = _collapse_whitespace(data)
        if text:
            self._current["suggestion_parts"].append(text)

    def close(self) -> None:
        super().close()
        self._finish_row()

    def _finish_row(self) -> None:
        if self._current is None:
            return
        self.rows.append(self._current)
        self._current = None
        self._in_suggestion = False


def _build_raw_product(row: dict) -> dict:
    details_page = row["details_page"]
    variant_id = _query_value(details_page, "VariantID")
    product_id = row["product_id"].strip() or _query_value(details_page, "ProductId")
    url = row["url"].strip()

    # The article number is the variant, not the base product: a search for 1008336
    # resolves to ProductId 1008301 / VariantID VARGRP249_1008336.
    number = (
        _article_number_from_variant(variant_id)
        or _article_number_from_url(url)
        or product_id
    )

    name = _collapse_whitespace(row["alt_name"]) or _collapse_whitespace(
        " ".join(row["suggestion_parts"])
    )

    return {
        "productId": product_id,
        "variantId": variant_id,
        "number": number,
        "name": name,
        "image": row["image"].strip(),
        "url": url,
    }


def parse_nevotex_search_results(html: str, limit: int | None = None) -> list[dict]:
    parser = _SearchResultsParser()
    parser.feed(html)
    parser.close()
    products = [_build_raw_product(row) for row in parser.rows]
    if limit is not None:
        return products[:limit]
    return products
