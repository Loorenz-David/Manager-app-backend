import asyncio
import logging
import re
import unicodedata
from collections.abc import Sequence
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from beyo_manager.services.infra.fargotex.client import (
    fetch_fargotex_category_html,
    fetch_fargotex_product_html,
)
from beyo_manager.services.infra.fargotex.constants import FARGOTEX_ORIGIN, MAX_FARGOTEX_PAGES
from beyo_manager.services.infra.fargotex.normalizer import normalize_fargotex_candidates
from beyo_manager.services.infra.fargotex.parser import (
    has_next_fargotex_page,
    parse_fargotex_listing_candidates,
    parse_fargotex_product_gallery,
    parse_fargotex_product_variations,
)

logger = logging.getLogger(__name__)
_MAX_PAGE_CONCURRENCY = 3
_MAX_PRODUCT_CONCURRENCY = 3
_GALLERY_CODE_PATTERN = re.compile(r"\A\d{1,3}\Z")
_FILENAME_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _matches_query(candidate: dict, q: str) -> bool:
    needle = q.strip().casefold()
    if not needle:
        return False
    haystack = " ".join(
        str(candidate.get(key) or "")
        for key in ("name", "code", "external_url")
    ).casefold()
    return needle in haystack


def _variation_candidate(parent: dict, variation: dict) -> dict | None:
    variation_id = variation.get("variation_id")
    variant_name = variation.get("variant_name")
    if variation_id is None or variant_name is None:
        return None

    variation_id_value = str(variation_id).strip()
    variant_name_value = str(variant_name).strip()
    if not variation_id_value or not variant_name_value:
        return None

    return {
        "name": f"{parent['name']} {variant_name_value}".strip(),
        "code": variation_id_value,
        "image": variation.get("image") or parent.get("image_url") or "",
        "external_url": parent.get("external_url"),
        "variant_name": variant_name_value,
        "parent_name": parent.get("name"),
        "sku": variation.get("sku"),
        "variation_id": variation_id_value,
    }


def _fold_source_text(value: str) -> str:
    """Case-fold and de-accent a source value while retaining separators."""
    folded = unquote(value).casefold().replace("ł", "l")
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", folded)
        if not unicodedata.combining(character)
    )


def _parent_gallery_tokens(parent: dict) -> list[str]:
    """Return stable, source-facing product tokens ordered by specificity."""
    external_url = str(parent.get("external_url") or "")
    source_value = ""
    if external_url:
        path_parts = [part for part in urlparse(external_url).path.split("/") if part]
        if path_parts:
            source_value = path_parts[-1]
    if not source_value:
        source_value = str(parent.get("name") or "")

    folded = _fold_source_text(source_value)
    words = _FILENAME_WORD_PATTERN.findall(folded)
    compact = "".join(words)
    # Prefer the product slug. If the slug contains a modifier, retain only
    # its most specific component rather than accepting weak words like `new`.
    tokens = [compact]
    if words:
        tokens.append(max(words, key=len))
    return list(dict.fromkeys(token for token in tokens if len(token) >= 3))


def resolve_fargotex_gallery_sample_code(
    parent: dict,
    gallery_image: dict,
) -> tuple[str | None, str]:
    """Resolve a numbered gallery sample only when it is tied to its parent.

    The generic parser hint is intentionally not used here. A number is valid
    only when it occurs immediately after the matched product's source-facing
    name/slug, which rejects image dimensions and unrelated gallery assets.
    """
    if not isinstance(parent, dict) or not isinstance(gallery_image, dict):
        return None, "invalid_input"

    image_url = str(gallery_image.get("image_url") or "").strip()
    source_path = unquote(urlparse(image_url).path)
    filename = source_path.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    if not stem:
        return None, "missing_filename"

    parent_tokens = _parent_gallery_tokens(parent)
    if not parent_tokens:
        return None, "missing_parent_token"

    folded_stem = _fold_source_text(stem)
    resolved_codes: set[str] = set()
    for parent_token in parent_tokens:
        search_start = 0
        while True:
            token_position = folded_stem.find(parent_token, search_start)
            if token_position < 0:
                break
            search_start = token_position + len(parent_token)

            # Prefixes such as `921nebbia05` are valid, but do not accept a
            # product token embedded in a larger alphabetic filename word.
            if token_position > 0 and folded_stem[token_position - 1].isalpha():
                continue

            suffix = folded_stem[token_position + len(parent_token) :]
            code_match = re.match(r"[-_]?(\d{1,3})(?=$|[-_])", suffix)
            if code_match:
                resolved_codes.add(code_match.group(1))

    if not resolved_codes:
        return None, "no_parent_associated_code"
    if len(resolved_codes) > 1:
        return None, "ambiguous_parent_associated_codes"

    return resolved_codes.pop(), "parent_filename"


def build_fargotex_gallery_candidates(
    parent: dict,
    gallery_images: list[dict],
) -> list[dict]:
    """Build raw candidates from numbered gallery samples in source order."""
    if not isinstance(parent, dict) or not isinstance(gallery_images, list):
        return []

    parent_code = str(parent.get("code") or "").strip()
    parent_name = str(parent.get("name") or "").strip()
    if not parent_code or not parent_name:
        return []

    candidates: list[dict] = []
    seen_gallery_codes: set[str] = set()
    seen_media_ids: set[str] = set()

    for index, gallery_image in enumerate(gallery_images):
        if not isinstance(gallery_image, dict):
            continue

        raw_position = gallery_image.get("position")
        position = str(raw_position).strip() if raw_position is not None else ""
        if not position.isdigit():
            position = str(index + 1)

        # The parser marks the first gallery item as main and preserves its
        # position, so resolver callers can also provide a sample-only slice.
        if gallery_image.get("is_main") is True or position == "1":
            continue

        image_url = str(gallery_image.get("image_url") or "").strip()
        parsed_image_url = urlparse(image_url)
        gallery_code, resolution_reason = resolve_fargotex_gallery_sample_code(
            parent,
            gallery_image,
        )
        if (
            gallery_code is None
            or not _GALLERY_CODE_PATTERN.fullmatch(gallery_code)
            or parsed_image_url.scheme not in {"http", "https"}
            or not parsed_image_url.netloc
            or not parsed_image_url.path
        ):
            logger.debug(
                "Fargotex gallery item skipped parent=%s position=%s reason=%s",
                parent_name,
                position,
                resolution_reason,
            )
            continue

        if gallery_code in seen_gallery_codes:
            logger.warning(
                "Duplicate Fargotex gallery sample skipped parent=%s gallery_code=%s",
                parent_name,
                gallery_code,
            )
            continue

        media_id = str(gallery_image.get("media_id") or "").strip()
        if media_id and media_id in seen_media_ids:
            logger.warning(
                "Duplicate Fargotex gallery source skipped parent=%s media_id=%s",
                parent_name,
                media_id,
            )
            continue

        seen_gallery_codes.add(gallery_code)
        if media_id:
            seen_media_ids.add(media_id)

        candidates.append(
            {
                "name": f"{parent_name} {gallery_code}",
                "code": f"{parent_code}-{gallery_code}",
                "image": image_url,
                "external_url": parent.get("external_url"),
                "variant_name": gallery_code,
                "gallery_code": gallery_code,
                "gallery_position": position,
                "parent_name": parent_name,
            }
        )

    return candidates


class FargotexExternalUpholsteryProvider:
    async def search(self, q: str, limit: int) -> Sequence[dict[str, Any]]:
        needle = q.strip()
        if not needle or limit <= 0:
            return []

        matching_parents: list[dict[str, Any]] = []
        seen_parents: set[tuple[str, str]] = set()
        semaphore = asyncio.Semaphore(_MAX_PAGE_CONCURRENCY)

        async def _fetch_page(page: int) -> tuple[int, str | None]:
            try:
                async with semaphore:
                    html = await fetch_fargotex_category_html(page=page)
                return page, html
            except httpx.HTTPError as exc:
                logger.warning("Fargotex category fetch failed for page=%s: %s", page, exc)
                return page, None
            except Exception:
                logger.exception("Unexpected Fargotex category fetch failure for page=%s", page)
                return page, None

        for batch_start in range(1, MAX_FARGOTEX_PAGES + 1, _MAX_PAGE_CONCURRENCY):
            batch_pages = range(
                batch_start,
                min(batch_start + _MAX_PAGE_CONCURRENCY, MAX_FARGOTEX_PAGES + 1),
            )
            page_results = await asyncio.gather(
                *[_fetch_page(page) for page in batch_pages]
            )

            stop_pagination = False
            for page, html in sorted(page_results, key=lambda item: item[0]):
                if html is None:
                    stop_pagination = True
                    break
                try:
                    raw_candidates = parse_fargotex_listing_candidates(html)
                    normalized_candidates = normalize_fargotex_candidates(raw_candidates)
                except Exception:
                    logger.exception("Unexpected Fargotex parse failure for page=%s", page)
                    stop_pagination = True
                    break

                for candidate in normalized_candidates:
                    if not _matches_query(candidate, needle):
                        continue
                    key = (FARGOTEX_ORIGIN, str(candidate["code"]))
                    if key in seen_parents:
                        continue
                    seen_parents.add(key)
                    matching_parents.append(candidate)

                if not has_next_fargotex_page(html):
                    stop_pagination = True
                    break

            if stop_pagination:
                break

        if not matching_parents:
            return []

        product_semaphore = asyncio.Semaphore(_MAX_PRODUCT_CONCURRENCY)

        async def _expand_parent(parent: dict) -> list[dict]:
            product_url = str(parent.get("external_url") or "")
            try:
                async with product_semaphore:
                    product_html = await fetch_fargotex_product_html(product_url)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Fargotex product expansion fetch failed url=%s parent=%s: %s",
                    product_url,
                    parent.get("name"),
                    exc,
                )
                return [parent]
            except Exception:
                logger.exception(
                    "Unexpected Fargotex product expansion fetch failure url=%s parent=%s",
                    product_url,
                    parent.get("name"),
                )
                return [parent]

            try:
                gallery_images = parse_fargotex_product_gallery(product_html)
            except Exception:
                gallery_images = []
                logger.exception(
                    "Fargotex product gallery parse failed url=%s parent=%s",
                    product_url,
                    parent.get("name"),
                )
            if not isinstance(gallery_images, list):
                gallery_images = []

            try:
                gallery_candidates = normalize_fargotex_candidates(
                    build_fargotex_gallery_candidates(parent, gallery_images)
                )
            except Exception:
                gallery_candidates = []
                logger.exception(
                    "Fargotex gallery candidate resolution failed url=%s parent=%s",
                    product_url,
                    parent.get("name"),
                )

            if gallery_candidates:
                logger.debug(
                    "Fargotex product expansion url=%s parent=%s "
                    "gallery_images_total=%s gallery_samples_accepted=%s "
                    "raw_variations_total=0 variation_candidates_accepted=0 "
                    "selected_candidate_source=gallery",
                    product_url,
                    parent.get("name"),
                    len(gallery_images),
                    len(gallery_candidates),
                )
                return gallery_candidates

            try:
                raw_variations = parse_fargotex_product_variations(product_html)
            except Exception:
                logger.exception(
                    "Fargotex product variation parse failed url=%s parent=%s",
                    product_url,
                    parent.get("name"),
                )
                return [parent]
            if not isinstance(raw_variations, list):
                logger.warning(
                    "Fargotex product variation parser returned unsupported data "
                    "url=%s parent=%s",
                    product_url,
                    parent.get("name"),
                )
                return [parent]

            expanded: list[dict] = []
            for raw_variation in raw_variations:
                if not isinstance(raw_variation, dict):
                    continue
                raw_candidate = _variation_candidate(parent, raw_variation)
                if raw_candidate is None:
                    continue
                candidate = normalize_fargotex_candidates([raw_candidate])
                if candidate:
                    expanded.append(candidate[0])

            if expanded:
                logger.debug(
                    "Fargotex product expansion url=%s parent=%s "
                    "gallery_images_total=%s gallery_samples_accepted=0 "
                    "raw_variations_total=%s variation_candidates_accepted=%s "
                    "selected_candidate_source=woocommerce_variations",
                    product_url,
                    parent.get("name"),
                    len(gallery_images),
                    len(raw_variations),
                    len(expanded),
                )
                return expanded

            logger.debug(
                "Fargotex product expansion url=%s parent=%s "
                "gallery_images_total=%s gallery_samples_accepted=0 "
                "raw_variations_total=%s variation_candidates_accepted=0 "
                "selected_candidate_source=parent_fallback",
                product_url,
                parent.get("name"),
                len(gallery_images),
                len(raw_variations),
            )
            return [parent]

        results: list[dict] = []
        seen_candidates: set[tuple[str, str]] = set()
        next_parent_index = 1

        def _append_candidates(expanded_batch: list[dict]) -> bool:
            for candidate in expanded_batch:
                variation_id = candidate.get("variation_id")
                identity = variation_id if variation_id else candidate.get("code")
                key = (FARGOTEX_ORIGIN, str(identity))
                if key in seen_candidates:
                    continue
                seen_candidates.add(key)
                results.append(candidate)
                if len(results) >= limit:
                    return True
            return False

        first_batch = await _expand_parent(matching_parents[0])
        if _append_candidates(first_batch):
            return results[:limit]

        # Gather small ordered batches so requests remain bounded while
        # asyncio.gather preserves category/parent order in the final output.
        while next_parent_index < len(matching_parents) and len(results) < limit:
            batch = matching_parents[
                next_parent_index : next_parent_index + _MAX_PRODUCT_CONCURRENCY
            ]
            next_parent_index += len(batch)
            expanded_batches = await asyncio.gather(*[_expand_parent(parent) for parent in batch])

            for expanded_batch in expanded_batches:
                if _append_candidates(expanded_batch):
                    return results[:limit]

        return results[:limit]
