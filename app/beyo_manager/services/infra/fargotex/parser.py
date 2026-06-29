import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from beyo_manager.services.infra.fargotex.constants import FARGOTEX_BASE_URL

_POST_ID_PATTERN = re.compile(r"\bpost-(\d+)\b")


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _absolutize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(FARGOTEX_BASE_URL, value)


def _extract_attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _extract_image_from_attrs(attrs: list[tuple[str, str | None]]) -> str:
    for key in ("src", "data-src", "data-lazy-src"):
        value = _extract_attr(attrs, key)
        if value:
            return value
    srcset = _extract_attr(attrs, "srcset")
    if srcset:
        return srcset.split(",")[0].strip().split(" ")[0]
    return ""


def _slug_from_url(url: str) -> str:
    return urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].strip()


class _FargotexListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results_by_url: dict[str, dict] = {}
        self.current_card: dict | None = None
        self.li_depth = 0
        self.capture_name = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li":
            class_attr = _extract_attr(attrs, "class")
            class_tokens = class_attr.split()
            if self.current_card is None and "product" in class_tokens:
                post_id_match = _POST_ID_PATTERN.search(class_attr)
                self.current_card = {
                    "name_parts": [],
                    "fallback_name": "",
                    "code": post_id_match.group(1) if post_id_match else "",
                    "image": "",
                    "external_url": "",
                }
                self.li_depth = 1
                return
            if self.current_card is not None:
                self.li_depth += 1

        if self.current_card is None:
            return

        if tag == "a":
            href = _extract_attr(attrs, "href")
            absolute_href = _absolutize_url(href)
            if "/produkt/" in absolute_href and not self.current_card["external_url"]:
                self.current_card["external_url"] = absolute_href
            class_attr = _extract_attr(attrs, "class")
            if "woocommerce-loop-product__title" in class_attr or "product_title" in class_attr:
                self.capture_name = True

        elif tag == "h3":
            class_attr = _extract_attr(attrs, "class")
            if "woocommerce-loop-product__title" in class_attr or "product_title" in class_attr:
                self.capture_name = True

        elif tag == "img":
            if not self.current_card["image"]:
                image = _extract_image_from_attrs(attrs)
                if image:
                    self.current_card["image"] = image
            alt = _extract_attr(attrs, "alt")
            if alt and not self.current_card["fallback_name"]:
                self.current_card["fallback_name"] = _collapse_whitespace(alt)

    def handle_endtag(self, tag: str) -> None:
        if self.current_card is None:
            return

        if tag in {"a", "h3"}:
            self.capture_name = False

        if tag == "li":
            self.li_depth -= 1
            if self.li_depth <= 0:
                self._flush_card()
                self.current_card = None
                self.li_depth = 0
                self.capture_name = False

    def handle_data(self, data: str) -> None:
        if self.current_card is None or not self.capture_name:
            return
        text = _collapse_whitespace(data)
        if text:
            self.current_card["name_parts"].append(text)

    def _flush_card(self) -> None:
        assert self.current_card is not None
        external_url = self.current_card["external_url"]
        if not external_url or "/produkt/" not in external_url:
            return

        name = _collapse_whitespace(" ".join(self.current_card["name_parts"]))
        if not name:
            name = self.current_card["fallback_name"]
        code = self.current_card["code"] or _slug_from_url(external_url)
        image = _absolutize_url(self.current_card["image"])

        if external_url not in self.results_by_url:
            self.results_by_url[external_url] = {
                "name": name or _slug_from_url(external_url),
                "code": code,
                "image": image,
                "external_url": external_url,
            }


def parse_fargotex_listing_candidates(html: str) -> list[dict]:
    parser = _FargotexListingParser()
    parser.feed(html)
    parser.close()
    return list(parser.results_by_url.values())


def has_next_fargotex_page(html: str) -> bool:
    if re.search(r'<a[^>]+(?:class="[^"]*(?:nextp|next page-numbers)[^"]*"|href="[^"]+")[^>]+(?:class="[^"]*(?:nextp|next page-numbers)[^"]*"|href="[^"]+")', html, re.IGNORECASE):
        return True
    return re.search(r'<link[^>]+rel="next"[^>]+href="[^"]+"', html, re.IGNORECASE) is not None
