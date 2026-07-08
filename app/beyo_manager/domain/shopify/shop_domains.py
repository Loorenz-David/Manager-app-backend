from urllib.parse import urlparse
import re

from beyo_manager.errors.validation import ValidationError


_MYSHOPIFY_SUFFIX = ".myshopify.com"
_SHOP_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def normalize_shop_domain(raw_shop_domain: str) -> str:
    raw = raw_shop_domain.strip().lower()
    if not raw:
        raise ValidationError("shop_domain is required.")

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).strip().lower()
    if not host:
        raise ValidationError("shop_domain is required.")

    host = host.split("/", 1)[0].strip(".")
    if host.endswith(_MYSHOPIFY_SUFFIX):
        slug = host[: -len(_MYSHOPIFY_SUFFIX)]
    else:
        slug = host

    if "." in slug or not _SHOP_SLUG_PATTERN.fullmatch(slug):
        raise ValidationError("shop_domain must be a valid Shopify shop domain.")

    normalized = f"{slug}{_MYSHOPIFY_SUFFIX}"
    if len(normalized) > 255:
        raise ValidationError("shop_domain is too long.")
    return normalized


def is_valid_shop_domain(raw_shop_domain: str) -> bool:
    try:
        normalize_shop_domain(raw_shop_domain)
    except ValidationError:
        return False
    return True
