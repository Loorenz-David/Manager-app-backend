import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from beyo_manager.services.infra.ohlssons_tyger.constants import (
    OHLSSONS_TYGER_DETAIL_PREFIX,
)

_CODE_PATTERN = re.compile(
    r"(Artikelnummer|Artikelnr|Art\.nr|Art nr|Produktnummer|Varunummer|SKU)\s*[:#]?\s*([A-Za-z0-9._/-]+)",
    re.IGNORECASE,
)
_META_PATTERN_TEMPLATE = r'<meta[^>]+{attr}=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']'
_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN_TEMPLATE = r"<{tag}\b[^>]*>(.*?)</{tag}>"


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _absolutize_url(raw_url: str, base_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(base_url, value)


def _extract_attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _extract_image_from_attrs(attrs: list[tuple[str, str | None]]) -> str:
    for key in ("src", "data-src", "data-original"):
        value = _extract_attr(attrs, key)
        if value:
            return value
    srcset = _extract_attr(attrs, "srcset")
    if srcset:
        return srcset.split(",")[0].strip().split(" ")[0]
    return ""


class _ListingParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.current_link: dict | None = None
        self.results_by_url: dict[str, dict] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = _extract_attr(attrs, "href")
            if OHLSSONS_TYGER_DETAIL_PREFIX not in href:
                return
            detail_url = _absolutize_url(href, self.base_url)
            if OHLSSONS_TYGER_DETAIL_PREFIX not in urlparse(detail_url).path:
                return
            self.current_link = {
                "detail_url": detail_url,
                "name_parts": [],
                "image_url": "",
            }
            return

        if tag == "img" and self.current_link is not None and not self.current_link["image_url"]:
            self.current_link["image_url"] = _extract_image_from_attrs(attrs)

    def handle_data(self, data: str) -> None:
        if self.current_link is None:
            return
        text = _collapse_whitespace(data)
        if text:
            self.current_link["name_parts"].append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self.current_link is None:
            return
        detail_url = self.current_link["detail_url"]
        existing = self.results_by_url.get(detail_url)
        name = _collapse_whitespace(" ".join(self.current_link["name_parts"]))
        image_url = self.current_link["image_url"]
        if existing is None:
            self.results_by_url[detail_url] = {
                "name": name,
                "detail_url": detail_url,
                "image_url": image_url,
            }
        else:
            if not existing["name"] and name:
                existing["name"] = name
            if not existing["image_url"] and image_url:
                existing["image_url"] = image_url
        self.current_link = None


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        text = _collapse_whitespace(data)
        if text:
            self.parts.append(text)


def _extract_meta_content(html: str, attr: str, name: str) -> str:
    pattern = re.compile(
        _META_PATTERN_TEMPLATE.format(attr=attr, name=re.escape(name)),
        re.IGNORECASE,
    )
    match = pattern.search(html)
    return _collapse_whitespace(unescape(match.group(1))) if match else ""


def _strip_tags(html: str) -> str:
    return _collapse_whitespace(unescape(re.sub(r"<[^>]+>", " ", html)))


def _extract_tag_text(html: str, tag: str) -> str:
    pattern = re.compile(_TAG_PATTERN_TEMPLATE.format(tag=tag), re.IGNORECASE | re.DOTALL)
    match = pattern.search(html)
    return _strip_tags(match.group(1)) if match else ""


def _extract_visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return _collapse_whitespace(" ".join(parser.parts))


def _extract_code(visible_text: str) -> str:
    match = _CODE_PATTERN.search(visible_text)
    if not match:
        return ""
    return match.group(2).strip().strip(":;,.#")


def _fallback_code_from_detail_url(detail_url: str) -> str:
    return urlparse(detail_url).path.rstrip("/").rsplit("/", 1)[-1].strip()


def _extract_first_image(html: str, base_url: str) -> str:
    for key in ("property", "name"):
        content = _extract_meta_content(html, key, "og:image")
        if content:
            return _absolutize_url(content, base_url)

    image_match = re.search(
        r"<img[^>]+(?:src|data-src|data-original)=[\"']([^\"']+)[\"']",
        html,
        re.IGNORECASE,
    )
    if image_match:
        return _absolutize_url(unescape(image_match.group(1)), base_url)
    return ""


def parse_ohlssons_tyger_listing_candidates(
    html: str,
    base_url: str,
    limit: int | None = None,
) -> list[dict]:
    parser = _ListingParser(base_url)
    parser.feed(html)
    parser.close()
    items = list(parser.results_by_url.values())
    if limit is not None:
        return items[:limit]
    return items


def parse_ohlssons_tyger_detail(
    html: str,
    detail_url: str,
    base_url: str,
    fallback_name: str = "",
    fallback_image: str = "",
) -> dict | None:
    if not html.strip():
        return None

    name = (
        _extract_tag_text(html, "h1")
        or _extract_meta_content(html, "property", "og:title")
        or _extract_tag_text(html, "title")
        or _collapse_whitespace(fallback_name)
    )

    visible_text = _extract_visible_text(html)
    code = _extract_code(visible_text) or _fallback_code_from_detail_url(detail_url)
    image = _extract_first_image(html, base_url) or _absolutize_url(fallback_image, base_url)

    return {
        "name": _collapse_whitespace(name),
        "code": _collapse_whitespace(code),
        "image": _absolutize_url(image, base_url),
        "detail_url": detail_url,
    }
