from __future__ import annotations

import re
from beyo_manager.domain.shopify.results import (
    ShopifyMetafieldDefinitionResult,
    ShopifyMetafieldPreferenceResult,
)

SHOPIFY_METAFIELD_DEFINITION_GID_PATTERN = re.compile(
    r"^gid://shopify/MetafieldDefinition/[^/]+$"
)


def is_shopify_metafield_definition_gid(value: str) -> bool:
    return bool(
        isinstance(value, str)
        and SHOPIFY_METAFIELD_DEFINITION_GID_PATTERN.fullmatch(value.strip())
    )


def _normalize_id_list(raw: str | None) -> list[str]:
    if raw is None:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for value in str(raw).split(","):
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def normalize_item_category_ids(raw: str | None) -> list[str]:
    return _normalize_id_list(raw)


def normalize_shop_integration_ids(raw: str | None) -> list[str]:
    return _normalize_id_list(raw)


def parse_only_my_preferences(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_search_query(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _clean_optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _definition_type(node: dict) -> str | None:
    value = node.get("type")
    if isinstance(value, dict):
        return _clean_optional_string(value.get("name"))
    return _clean_optional_string(value)


def _definition_validations(node: dict) -> list[dict] | None:
    value = node.get("validations")
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, dict)]


def map_shopify_metafield_definition_node(
    node: dict,
) -> ShopifyMetafieldDefinitionResult:
    return ShopifyMetafieldDefinitionResult(
        shopify_metafield_definition_id=_clean_optional_string(node.get("id")) or "",
        name=_clean_optional_string(node.get("name")),
        namespace=_clean_optional_string(node.get("namespace")),
        key=_clean_optional_string(node.get("key")),
        description=_clean_optional_string(node.get("description")),
        type=_definition_type(node),
        validations=_definition_validations(node),
        reference_options=(
            node.get("reference_options")
            if isinstance(node.get("reference_options"), dict)
            else None
        ),
    )


def merge_metafield_preference_with_definition(
    *,
    preference: object,
    definition: dict,
    created_by: dict | None,
) -> ShopifyMetafieldPreferenceResult:
    definition_result = map_shopify_metafield_definition_node(definition)
    return ShopifyMetafieldPreferenceResult(
        client_id=preference.client_id,
        item_category_id=preference.item_category_id,
        shop_integration_id=preference.shop_integration_id,
        shopify_metafield_definition_id=preference.shopify_metafield_definition_id,
        name=definition_result.name,
        namespace=definition_result.namespace,
        key=definition_result.key,
        description=definition_result.description,
        type=definition_result.type,
        validations=definition_result.validations,
        reference_options=definition_result.reference_options,
        sequence_order=preference.sequence_order,
        is_enabled=preference.is_enabled,
        created_at=preference.created_at.isoformat(),
        updated_at=preference.updated_at.isoformat() if preference.updated_at else None,
        created_by=created_by,
    )
