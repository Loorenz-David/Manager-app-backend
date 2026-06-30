import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from beyo_manager.services.infra.selfmade.constants import SELFMADE_BASE_URL

_RESULT_TOTAL_PATTERN = re.compile(r"(\d[\d\s]*)")


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _absolutize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if value.startswith("//"):
        return f"https:{value}"
    return urljoin(SELFMADE_BASE_URL, value)


def _extract_attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key == name and value:
            return value
    return ""


def _has_class(attrs: list[tuple[str, str | None]], *classes: str) -> bool:
    class_tokens = set(_extract_attr(attrs, "class").split())
    return all(class_name in class_tokens for class_name in classes)


def _is_class(attrs: list[tuple[str, str | None]], *classes: str) -> bool:
    class_tokens = set(_extract_attr(attrs, "class").split())
    return any(class_name in class_tokens for class_name in classes)


def _extract_image_from_attrs(attrs: list[tuple[str, str | None]]) -> str:
    for key in ("data-src", "src", "data-lazy-src"):
        value = _extract_attr(attrs, key)
        if value:
            return _absolutize_url(value)
    srcset = _extract_attr(attrs, "srcset")
    if srcset:
        return _absolutize_url(srcset.split(",")[0].strip().split(" ")[0])
    return ""


class _SelfmadeListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results_by_url: dict[str, dict] = {}
        self.current_card: dict | None = None
        self.card_depth = 0
        self.capture_stack: list[list[object]] = []
        self.ignored_price_depth = 0
        self.result_total_parts: list[str] = []
        self.capture_result_total = False
        self.has_next_page = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.current_card is None and tag == "div" and _has_class(attrs, "card", "product-box"):
            self.current_card = {
                "detail_url": "",
                "name_parts": [],
                "image_url": "",
                "price_parts": [],
                "availability_labels": [],
                "variant_parts": [],
            }
            self.card_depth = 1
            return

        if self.current_card is not None:
            self._handle_card_starttag(tag, attrs)
            if tag in {"div", "article", "section", "li"}:
                self.card_depth += 1
            return

        if _is_class(attrs, "result-total-label"):
            self.capture_result_total = True
        if tag == "input" and _is_class(attrs, "search-result-total"):
            value = _extract_attr(attrs, "value")
            if value:
                self.result_total_parts.append(value)
        if _has_class(attrs, "page-item", "page-next") and not _has_class(attrs, "disabled"):
            self.has_next_page = True

    def _handle_card_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        assert self.current_card is not None

        for capture in self.capture_stack:
            capture[1] = int(capture[1]) + 1

        if tag == "a" and (
            _is_class(attrs, "product-card-link") or _is_class(attrs, "product-box--search-wrapper")
        ):
            href = _extract_attr(attrs, "href")
            if href and not self.current_card["detail_url"]:
                self.current_card["detail_url"] = _absolutize_url(href)

        if tag == "img" and _is_class(attrs, "product-image") and not self.current_card["image_url"]:
            self.current_card["image_url"] = _extract_image_from_attrs(attrs)

        if _is_class(attrs, "list-price"):
            self.ignored_price_depth += 1
        elif self.ignored_price_depth > 0:
            self.ignored_price_depth += 1

        if _is_class(attrs, "product-name"):
            self.capture_stack.append(["name", 1])
        elif _is_class(attrs, "product-price"):
            self.capture_stack.append(["price", 1])
        elif _is_class(attrs, "marker"):
            self.capture_stack.append(["availability", 1])
        elif _is_class(attrs, "product-variant-label"):
            self.capture_stack.append(["variant", 1])

    def handle_endtag(self, tag: str) -> None:
        if self.current_card is not None:
            if self.ignored_price_depth > 0:
                self.ignored_price_depth -= 1
            for capture in self.capture_stack:
                capture[1] = int(capture[1]) - 1
            while self.capture_stack and int(self.capture_stack[-1][1]) <= 0:
                self.capture_stack.pop()
            if tag in {"div", "article", "section", "li"}:
                self.card_depth -= 1
                if self.card_depth <= 0:
                    self._flush_card()
                    self.current_card = None
                    self.card_depth = 0
                    self.capture_stack = []
                    self.ignored_price_depth = 0
            return

        if self.capture_result_total and tag in {"div", "span", "p"}:
            self.capture_result_total = False

    def handle_data(self, data: str) -> None:
        text = _collapse_whitespace(data)
        if not text:
            return

        if self.current_card is None:
            if self.capture_result_total:
                self.result_total_parts.append(text)
            return

        if not self.capture_stack:
            return

        capture = str(self.capture_stack[-1][0])
        if capture == "price" and self.ignored_price_depth == 0:
            self.current_card["price_parts"].append(text)
        elif capture == "name":
            self.current_card["name_parts"].append(text)
        elif capture == "availability":
            self.current_card["availability_labels"].append(text)
        elif capture == "variant":
            self.current_card["variant_parts"].append(text)

    def _flush_card(self) -> None:
        assert self.current_card is not None
        detail_url = self.current_card["detail_url"]
        if not detail_url:
            return

        if detail_url not in self.results_by_url:
            self.results_by_url[detail_url] = {
                "detail_url": detail_url,
                "name": _collapse_whitespace(" ".join(self.current_card["name_parts"])),
                "image_url": self.current_card["image_url"],
                "raw_price": _collapse_whitespace(" ".join(self.current_card["price_parts"])),
                "availability_labels": self.current_card["availability_labels"],
                "variant_label": _collapse_whitespace(" ".join(self.current_card["variant_parts"])),
            }


def _parse(html: str) -> _SelfmadeListingParser:
    parser = _SelfmadeListingParser()
    parser.feed(html)
    parser.close()
    return parser


def parse_selfmade_listing_candidates(html: str) -> list[dict]:
    return list(_parse(html).results_by_url.values())


def parse_selfmade_result_total(html: str) -> int | None:
    parser = _parse(html)
    text = " ".join(parser.result_total_parts)
    match = _RESULT_TOTAL_PATTERN.search(text)
    if not match:
        return None
    return int(match.group(1).replace(" ", ""))


def has_next_selfmade_page(html: str) -> bool:
    return _parse(html).has_next_page
