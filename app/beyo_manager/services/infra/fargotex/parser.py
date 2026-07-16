import json
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from beyo_manager.services.infra.fargotex.constants import FARGOTEX_BASE_URL

_POST_ID_PATTERN = re.compile(r"\bpost-(\d+)\b")
_GALLERY_IMAGE_CODE_PATTERN = re.compile(r"(?:^|[-_])(\d{1,3})(?=$|[-_])")
_GALLERY_SAMPLE_BEFORE_SIZE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,3})(?=(?:[-_]w)?[-_]\d{3,4}(?:[-_.]|$))",
    re.IGNORECASE,
)
_GALLERY_SAMPLE_FILENAME_PATTERN = re.compile(
    r"[a-z]+[-_]?(\d{1,3})(?:[-_]\d{1,3})?$",
    re.IGNORECASE,
)
_WORDPRESS_DIMENSION_PATTERN = re.compile(r"[-_]\d{2,4}x\d{2,4}", re.IGNORECASE)
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


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


def _is_fargotex_product_url(url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(FARGOTEX_BASE_URL)
    path = parsed.path.rstrip("/")
    return (
        parsed.scheme == base.scheme
        and parsed.netloc == base.netloc
        and path.startswith("/produkt/")
        and bool(path.removeprefix("/produkt/"))
    )


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
        if not _is_fargotex_product_url(external_url):
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


class _FargotexVariationFormParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raw_variations: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "form" or self.raw_variations:
            return
        class_tokens = _extract_attr(attrs, "class").split()
        if "variations_form" not in class_tokens:
            return
        self.raw_variations = _extract_attr(attrs, "data-product_variations")


def _string_value(value: object) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _is_explicitly_false(value: object) -> bool:
    if value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    return isinstance(value, str) and value.strip().casefold() in {
        "false",
        "0",
        "no",
        "off",
    }


def _resolve_variation_label(attributes: object) -> str:
    if not isinstance(attributes, dict):
        return ""

    # Keep the source-specific lookup isolated so renamed or multi-dimensional
    # attribute schemes can be added without changing payload parsing.
    preferred_keys = (
        "attribute_pa_kolory",
        "attribute_kolory",
        "attribute_color",
        "attribute_colour",
    )
    for key in preferred_keys:
        label = _string_value(attributes.get(key))
        if label:
            return _collapse_whitespace(unescape(label))
    return ""


def _resolve_variation_image(variation: dict) -> str:
    image = variation.get("image")
    if not isinstance(image, dict):
        return ""
    for key in ("full_src", "url", "src"):
        value = _string_value(image.get(key))
        if value:
            return _absolutize_url(unescape(value))
    return ""


def _parse_variation_payload(raw_payload: str) -> list[dict]:
    if not raw_payload:
        return []

    try:
        payload = json.loads(unescape(raw_payload))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    variations: list[dict] = []
    for variation in payload:
        if not isinstance(variation, dict):
            continue
        if _is_explicitly_false(variation.get("variation_is_active")):
            continue
        if _is_explicitly_false(variation.get("variation_is_visible")):
            continue

        variation_id = _string_value(variation.get("variation_id"))
        attributes = variation.get("attributes")
        variant_name = _resolve_variation_label(attributes)
        if not variation_id or not variant_name:
            continue

        sku = _string_value(variation.get("sku"))
        variations.append(
            {
                "code": variation_id,
                "variation_id": variation_id,
                "sku": sku,
                "attributes": attributes if isinstance(attributes, dict) else {},
                "variant_name": variant_name,
                "image": _resolve_variation_image(variation),
            }
        )
    return variations


def parse_fargotex_product_variations(html: str) -> list[dict]:
    """Parse usable WooCommerce variations from a Fargotex product page."""
    parser = _FargotexVariationFormParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    return _parse_variation_payload(parser.raw_variations)


def _extract_gallery_image_code(image_url: str) -> str:
    path = urlparse(image_url).path
    filename = path.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]

    # Fargotex uses both `neon-01-w-1200` and `nebbia01-w-1200` naming
    # schemes. Resolve the sample immediately before the full-size suffix
    # before applying the separator-based fallback.
    size_match = _GALLERY_SAMPLE_BEFORE_SIZE_PATTERN.search(stem)
    if size_match:
        return size_match.group(1)

    # Do not mistake generated WordPress dimensions such as 100x100 or
    # 1024x1024 for upholstery sample numbers.
    stem_without_dimensions = _WORDPRESS_DIMENSION_PATTERN.sub("", stem)
    filename_match = _GALLERY_SAMPLE_FILENAME_PATTERN.search(stem_without_dimensions)
    if filename_match:
        return filename_match.group(1)

    trailing_match = re.search(r"(?<!\d)(\d{1,3})$", stem_without_dimensions)
    if trailing_match:
        return trailing_match.group(1)

    matches = _GALLERY_IMAGE_CODE_PATTERN.findall(stem_without_dimensions)
    return matches[-1] if matches else ""


class _FargotexGalleryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.wrapper_depth = 0
        self.current_item: dict | None = None
        self.items: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        class_tokens = _extract_attr(attrs, "class").split()
        is_wrapper = "woocommerce-product-gallery__wrapper" in class_tokens

        if self.wrapper_depth == 0:
            if not is_wrapper:
                return
            self.wrapper_depth = 1
            return

        if self.current_item is None and "woocommerce-product-gallery__image" in class_tokens:
            self.current_item = {
                "anchor_url": "",
                "image_url": "",
                "thumbnail_url": "",
                "alt": "",
                "media_id": _extract_attr(attrs, "data-image-id")
                or _extract_attr(attrs, "data-attachment-id")
                or _extract_attr(attrs, "data-media-id"),
            }

        if self.current_item is not None:
            if not self.current_item["media_id"]:
                self.current_item["media_id"] = (
                    _extract_attr(attrs, "data-image-id")
                    or _extract_attr(attrs, "data-attachment-id")
                    or _extract_attr(attrs, "data-media-id")
                )
            if tag == "a" and not self.current_item["anchor_url"]:
                self.current_item["anchor_url"] = _extract_attr(attrs, "href")
            elif tag == "img" and not self.current_item["image_url"]:
                self.current_item["image_url"] = _extract_attr(attrs, "data-large_image")
                if not self.current_item["image_url"]:
                    self.current_item["image_url"] = _extract_attr(attrs, "data-src")
                if not self.current_item["image_url"]:
                    self.current_item["image_url"] = _extract_attr(attrs, "src")
                self.current_item["thumbnail_url"] = _extract_attr(attrs, "src")
                if not self.current_item["thumbnail_url"]:
                    self.current_item["thumbnail_url"] = _extract_attr(attrs, "data-src")
                self.current_item["alt"] = _extract_attr(attrs, "alt")

        if tag not in _VOID_TAGS:
            self.wrapper_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.wrapper_depth == 0:
            return

        if self.current_item is not None and self.wrapper_depth == 2:
            self._flush_item()

        if tag not in _VOID_TAGS:
            self.wrapper_depth -= 1
            if self.wrapper_depth == 0:
                self.current_item = None

    def _flush_item(self) -> None:
        if self.current_item is None:
            return
        item = self.current_item
        image_url = _absolutize_url(item["anchor_url"] or item["image_url"])
        thumbnail_url = _absolutize_url(item["thumbnail_url"])
        position = len(self.items) + 1
        self.items.append(
            {
                "position": position,
                "image_code": _extract_gallery_image_code(image_url),
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "alt": _collapse_whitespace(item["alt"]),
                "media_id": _collapse_whitespace(item["media_id"]),
                "is_main": position == 1,
            }
        )
        self.current_item = None


def parse_fargotex_product_gallery(html: str) -> list[dict]:
    """Resolve ordered gallery assets without inferring variation identity."""
    parser = _FargotexGalleryParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    return parser.items


# Explicit alias for callers that describe the result as gallery images.
parse_fargotex_gallery_images = parse_fargotex_product_gallery


class _FargotexNextPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found_next_page = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            class_tokens = _extract_attr(attrs, "class").split()
            if "next" in class_tokens or "nextp" in class_tokens:
                self.found_next_page = True
        elif tag == "link":
            rel_tokens = _extract_attr(attrs, "rel").split()
            if "next" in rel_tokens:
                self.found_next_page = True


def has_next_fargotex_page(html: str) -> bool:
    parser = _FargotexNextPageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return False
    return parser.found_next_page
