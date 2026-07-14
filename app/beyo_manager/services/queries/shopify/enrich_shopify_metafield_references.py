from __future__ import annotations

import logging
import re
from collections import defaultdict

from beyo_manager.domain.shopify.scopes import has_all_required_scopes
from beyo_manager.errors.external_service import ShopifyGraphQLError
from beyo_manager.services.infra.shopify.metaobject_client import (
    ShopifyMetaobjectEntriesResult,
    fetch_shopify_metaobject_definitions_by_ids,
    fetch_shopify_metaobject_entries_by_type,
)

logger = logging.getLogger(__name__)

METAOBJECT_REFERENCE_TYPES = frozenset(
    {"metaobject_reference", "list.metaobject_reference"}
)
METAOBJECT_DEFINITION_ID_VALIDATION = "metaobject_definition_id"
METAOBJECT_DEFINITION_GID_PATTERN = re.compile(
    r"^gid://shopify/MetaobjectDefinition/[^/]+$"
)
REQUIRED_METAOBJECT_DEFINITION_SCOPE = "read_metaobject_definitions"
REQUIRED_METAOBJECT_ENTRY_SCOPE = "read_metaobjects"


async def enrich_shopify_metafield_definitions(
    *,
    definitions: dict[str, dict],
    shop_integration_id: str,
    shop_domain: str,
    access_token_encrypted: str,
    granted_scopes: list[str] | None,
) -> None:
    """Attach normalized reference options to supported definitions in-place.

    Definitions are collected per shop by the caller. This lets the resolver
    deduplicate both definition lookups and entry lookups across categories and
    search results while keeping Shopify resources isolated by store.
    """
    reference_definitions = {
        definition_id: definition
        for definition_id, definition in definitions.items()
        if _reference_type(definition) in METAOBJECT_REFERENCE_TYPES
    }
    if not reference_definitions:
        return

    selection_modes = {
        definition_id: _selection_mode(definition)
        for definition_id, definition in reference_definitions.items()
    }
    for definition_id, definition in reference_definitions.items():
        definition["reference_options"] = _empty_reference_options(
            selection_mode=selection_modes[definition_id]
        )

    if not has_all_required_scopes(
        (REQUIRED_METAOBJECT_DEFINITION_SCOPE,), granted_scopes or ()
    ):
        for definition_id in reference_definitions:
            _set_unavailable(
                reference_definitions[definition_id],
                selection_mode=selection_modes[definition_id],
                reason="metaobject_definition_inaccessible",
            )
            _log_unavailable(
                shop_integration_id=shop_integration_id,
                shop_domain=shop_domain,
                metafield_definition_id=definition_id,
                metaobject_definition_id=None,
                reason="metaobject_definition_inaccessible",
            )
        return

    definition_ids_by_metafield: dict[str, str | None] = {
        definition_id: _metaobject_definition_id(definition)
        for definition_id, definition in reference_definitions.items()
    }
    requested_definition_ids = list(
        dict.fromkeys(
            value for value in definition_ids_by_metafield.values() if value is not None
        )
    )
    for definition_id, metaobject_definition_id in definition_ids_by_metafield.items():
        if metaobject_definition_id is None:
            _set_unavailable(
                reference_definitions[definition_id],
                selection_mode=selection_modes[definition_id],
                reason="missing_metaobject_definition_id",
            )
            _log_unavailable(
                shop_integration_id=shop_integration_id,
                shop_domain=shop_domain,
                metafield_definition_id=definition_id,
                metaobject_definition_id=None,
                reason="missing_metaobject_definition_id",
            )

    if not requested_definition_ids:
        return

    try:
        metaobject_definitions = await fetch_shopify_metaobject_definitions_by_ids(
            shop_domain=shop_domain,
            access_token_encrypted=access_token_encrypted,
            definition_ids=requested_definition_ids,
        )
    except ShopifyGraphQLError:
        for (
            definition_id,
            metaobject_definition_id,
        ) in definition_ids_by_metafield.items():
            if metaobject_definition_id is None:
                continue
            _set_unavailable(
                reference_definitions[definition_id],
                selection_mode=selection_modes[definition_id],
                reason="metaobject_definition_inaccessible",
            )
            _log_unavailable(
                shop_integration_id=shop_integration_id,
                shop_domain=shop_domain,
                metafield_definition_id=definition_id,
                metaobject_definition_id=metaobject_definition_id,
                reason="metaobject_definition_inaccessible",
            )
        return

    definitions_by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for definition_id, metaobject_definition_id in definition_ids_by_metafield.items():
        if metaobject_definition_id is None:
            continue
        metaobject_definition = metaobject_definitions.get(metaobject_definition_id)
        if not isinstance(metaobject_definition, dict):
            _set_unavailable(
                reference_definitions[definition_id],
                selection_mode=selection_modes[definition_id],
                reason="metaobject_definition_not_found",
            )
            _log_unavailable(
                shop_integration_id=shop_integration_id,
                shop_domain=shop_domain,
                metafield_definition_id=definition_id,
                metaobject_definition_id=metaobject_definition_id,
                reason="metaobject_definition_not_found",
            )
            continue
        metaobject_type = metaobject_definition.get("type")
        if not isinstance(metaobject_type, str) or not metaobject_type.strip():
            _set_unavailable(
                reference_definitions[definition_id],
                selection_mode=selection_modes[definition_id],
                reason="metaobject_definition_inaccessible",
            )
            _log_unavailable(
                shop_integration_id=shop_integration_id,
                shop_domain=shop_domain,
                metafield_definition_id=definition_id,
                metaobject_definition_id=metaobject_definition_id,
                reason="metaobject_definition_inaccessible",
            )
            continue
        definitions_by_type[metaobject_type].append(
            (definition_id, metaobject_definition_id)
        )

    entries_by_type: dict[str, ShopifyMetaobjectEntriesResult | None] = {}
    for metaobject_type in definitions_by_type:
        if not has_all_required_scopes(
            (REQUIRED_METAOBJECT_ENTRY_SCOPE,), granted_scopes or ()
        ):
            entries_by_type[metaobject_type] = None
            continue
        try:
            entries_by_type[
                metaobject_type
            ] = await fetch_shopify_metaobject_entries_by_type(
                shop_domain=shop_domain,
                access_token_encrypted=access_token_encrypted,
                metaobject_type=metaobject_type,
            )
        except ShopifyGraphQLError:
            entries_by_type[metaobject_type] = None

    for metaobject_type, type_references in definitions_by_type.items():
        entries = entries_by_type[metaobject_type]
        for definition_id, metaobject_definition_id in type_references:
            definition = reference_definitions[definition_id]
            metaobject_definition = metaobject_definitions.get(metaobject_definition_id)
            if entries is None:
                reason = "metaobject_entries_unavailable"
                _set_unavailable(
                    definition,
                    selection_mode=selection_modes[definition_id],
                    reason=reason,
                )
                _log_unavailable(
                    shop_integration_id=shop_integration_id,
                    shop_domain=shop_domain,
                    metafield_definition_id=definition_id,
                    metaobject_definition_id=metaobject_definition_id,
                    reason=reason,
                )
                continue

            reference_options = _successful_reference_options(
                selection_mode=selection_modes[definition_id],
                metaobject_definition=metaobject_definition,
                entries=entries,
            )
            if entries.truncated:
                reference_options["availability"] = "partial"
                reference_options["unavailable_reason"] = "metaobject_entries_truncated"
                _log_unavailable(
                    shop_integration_id=shop_integration_id,
                    shop_domain=shop_domain,
                    metafield_definition_id=definition_id,
                    metaobject_definition_id=metaobject_definition_id,
                    reason="metaobject_entries_truncated",
                )
            definition["reference_options"] = reference_options


def _reference_type(definition: dict) -> str | None:
    type_value = definition.get("type")
    if isinstance(type_value, dict):
        type_value = type_value.get("name")
    return type_value if isinstance(type_value, str) else None


def _selection_mode(definition: dict) -> str:
    return (
        "multiple"
        if _reference_type(definition) == "list.metaobject_reference"
        else "single"
    )


def _metaobject_definition_id(definition: dict) -> str | None:
    validations = definition.get("validations")
    if not isinstance(validations, list):
        return None
    for validation in validations:
        if not isinstance(validation, dict):
            continue
        if validation.get("name") != METAOBJECT_DEFINITION_ID_VALIDATION:
            continue
        value = validation.get("value")
        if isinstance(value, str) and METAOBJECT_DEFINITION_GID_PATTERN.fullmatch(
            value.strip()
        ):
            return value.strip()
    return None


def _empty_reference_options(*, selection_mode: str) -> dict:
    return {
        "reference_kind": "metaobject",
        "selection_mode": selection_mode,
        "metaobject_definition": None,
        "options": [],
        "pagination": {"has_more": False, "end_cursor": None},
    }


def _set_unavailable(definition: dict, *, selection_mode: str, reason: str) -> None:
    definition["reference_options"] = _empty_reference_options(
        selection_mode=selection_mode
    )
    definition["reference_options"]["availability"] = "unavailable"
    definition["reference_options"]["unavailable_reason"] = reason


def _successful_reference_options(
    *,
    selection_mode: str,
    metaobject_definition: dict,
    entries: ShopifyMetaobjectEntriesResult,
) -> dict:
    return {
        "reference_kind": "metaobject",
        "selection_mode": selection_mode,
        "metaobject_definition": {
            "id": metaobject_definition.get("id"),
            "name": metaobject_definition.get("name"),
            "type": metaobject_definition.get("type"),
        },
        "options": entries.options,
        "pagination": {
            "has_more": entries.has_more,
            "end_cursor": entries.end_cursor,
        },
    }


def _log_unavailable(
    *,
    shop_integration_id: str,
    shop_domain: str,
    metafield_definition_id: str,
    metaobject_definition_id: str | None,
    reason: str,
) -> None:
    logger.warning(
        "Shopify metaobject reference enrichment unavailable | "
        "shop_integration_id=%s shop_domain=%s metafield_definition_id=%s "
        "metaobject_definition_id=%s reason=%s",
        shop_integration_id,
        shop_domain,
        metafield_definition_id,
        metaobject_definition_id,
        reason,
    )
