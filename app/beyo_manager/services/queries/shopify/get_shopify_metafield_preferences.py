from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.metafield_preferences import (
    map_shopify_metafield_definition_node,
    merge_metafield_preference_with_definition,
    normalize_item_category_ids,
    normalize_search_query,
    normalize_shop_integration_ids,
    parse_only_my_preferences,
)
from beyo_manager.domain.shopify.serializers import (
    serialize_shopify_metafield_preferences_response,
)
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import (
    ShopifyMetafieldPreference,
)
from beyo_manager.models.tables.shopify.shopify_shop_integration import (
    ShopifyShopIntegration,
)
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.metafield_definition_client import (
    SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE,
    fetch_shopify_metafield_definitions_by_ids,
    search_shopify_metafield_definitions_by_name_page,
)
from beyo_manager.services.queries.shopify.enrich_shopify_metafield_references import (
    enrich_shopify_metafield_definitions,
)


async def get_shopify_metafield_preferences(ctx: ServiceContext) -> dict:
    shop_integration_ids = normalize_shop_integration_ids(
        ctx.query_params.get("shop_integration_ids")
    )
    item_category_ids = normalize_item_category_ids(
        ctx.query_params.get("item_category_ids")
    )
    search_query = normalize_search_query(ctx.query_params.get("q"))
    only_my_preferences = parse_only_my_preferences(
        ctx.query_params.get("only_my_preferences")
    )
    search_offset = _parse_search_offset(ctx.query_params.get("search_offset"))

    if not shop_integration_ids or (not item_category_ids and search_query is None):
        raise ValidationError(
            "Provide shop_integration_ids and at least one of item_category_ids or q."
        )

    integrations_by_id = await _resolve_integrations(ctx, shop_integration_ids)
    if item_category_ids:
        await _validate_item_categories(ctx, item_category_ids)

    preferences_by_shop_and_category: dict[
        tuple[str, str], list[ShopifyMetafieldPreference]
    ] = defaultdict(list)
    created_by_ids: set[str] = set()
    if item_category_ids:
        query = select(ShopifyMetafieldPreference).where(
            ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
            ShopifyMetafieldPreference.shop_integration_id.in_(shop_integration_ids),
            ShopifyMetafieldPreference.item_category_id.in_(item_category_ids),
            ShopifyMetafieldPreference.is_deleted.is_(False),
            ShopifyMetafieldPreference.is_enabled.is_(True),
        )
        if only_my_preferences:
            query = query.where(ShopifyMetafieldPreference.created_by_id == ctx.user_id)
        query = query.order_by(
            ShopifyMetafieldPreference.shop_integration_id,
            ShopifyMetafieldPreference.item_category_id,
            ShopifyMetafieldPreference.sequence_order,
            ShopifyMetafieldPreference.created_at,
        )
        rows = (await ctx.session.execute(query)).scalars().all()
        for row in rows:
            preferences_by_shop_and_category[
                (row.shop_integration_id, row.item_category_id)
            ].append(row)
            if row.created_by_id:
                created_by_ids.add(row.created_by_id)

    created_by_by_id: dict[str, dict] = {}
    if created_by_ids:
        users = (
            (
                await ctx.session.execute(
                    select(User).where(User.client_id.in_(created_by_ids))
                )
            )
            .scalars()
            .all()
        )
        created_by_by_id = {
            user.client_id: serialize_user_working_section_member(user)
            for user in users
        }

    shops: list[dict] = []
    for shop_integration_id in shop_integration_ids:
        integration = integrations_by_id[shop_integration_id]
        access_token = (integration.access_token_encrypted or "").strip()
        should_search_for_shop = search_query is not None
        if not access_token and (
            should_search_for_shop
            or any(
                preferences_by_shop_and_category[(shop_integration_id, category_id)]
                for category_id in item_category_ids
            )
        ):
            raise ValidationError(
                "Shopify shop integration has no usable access token."
            )

        unavailable_definition_ids: list[str] = []
        definitions_by_id: dict[str, dict | None] = {}
        if item_category_ids:
            definition_ids = list(
                dict.fromkeys(
                    row.shopify_metafield_definition_id
                    for category_id in item_category_ids
                    for row in preferences_by_shop_and_category[
                        (shop_integration_id, category_id)
                    ]
                )
            )
            if definition_ids:
                definitions_by_id = await fetch_shopify_metafield_definitions_by_ids(
                    shop_domain=integration.shop_domain,
                    access_token_encrypted=access_token,
                    definition_ids=definition_ids,
                )

        search_nodes: list[dict] = []
        search_pagination = {
            "offset": search_offset,
            "limit": 20,
            "has_more": False,
            "next_offset": None,
        }
        if should_search_for_shop:
            saved_definition_ids = {
                preference.shopify_metafield_definition_id
                for category_id in item_category_ids
                for preference in preferences_by_shop_and_category[
                    (shop_integration_id, category_id)
                ]
            }
            search_page = await search_shopify_metafield_definitions_by_name_page(
                shop_domain=integration.shop_domain,
                access_token_encrypted=access_token,
                search_term=search_query or "",
                offset=search_offset,
            )
            search_nodes = [
                node
                for node in search_page.nodes
                if search_query is not None
                or node.get("id") not in saved_definition_ids
            ]
            search_pagination = {
                "offset": search_page.offset,
                "limit": search_page.limit,
                "has_more": search_page.has_more,
                "next_offset": (
                    search_page.offset + search_page.limit
                    if search_page.has_more
                    else None
                ),
            }

        definitions_to_enrich = {
            definition_id: definition
            for definition_id, definition in definitions_by_id.items()
            if _is_product_metafield_definition(definition)
        }
        for index, node in enumerate(search_nodes):
            definition_id = node.get("id")
            if isinstance(definition_id, str):
                existing_definition = definitions_to_enrich.get(definition_id)
                if existing_definition is not None:
                    search_nodes[index] = existing_definition
                else:
                    definitions_to_enrich[definition_id] = node
        if definitions_to_enrich:
            await enrich_shopify_metafield_definitions(
                definitions=definitions_to_enrich,
                shop_integration_id=shop_integration_id,
                shop_domain=integration.shop_domain,
                access_token_encrypted=access_token,
                granted_scopes=integration.granted_scopes,
            )

        item_categories: list[dict] = []
        for category_id in item_category_ids:
            merged_preferences = []
            for preference in preferences_by_shop_and_category[
                (shop_integration_id, category_id)
            ]:
                definition = definitions_by_id.get(
                    preference.shopify_metafield_definition_id
                )
                if not _is_product_metafield_definition(definition):
                    if (
                        preference.shopify_metafield_definition_id
                        not in unavailable_definition_ids
                    ):
                        unavailable_definition_ids.append(
                            preference.shopify_metafield_definition_id
                        )
                    continue
                merged_preferences.append(
                    merge_metafield_preference_with_definition(
                        preference=preference,
                        definition=definition,
                        created_by=created_by_by_id.get(preference.created_by_id or ""),
                    )
                )
            item_categories.append(
                {
                    "item_category_id": category_id,
                    "metafield_preferences": merged_preferences,
                }
            )

        search_results = [
            map_shopify_metafield_definition_node(node) for node in search_nodes
        ]

        shops.append(
            {
                "shop_integration_id": integration.client_id,
                "shop_domain": integration.shop_domain,
                "item_categories": item_categories,
                "unavailable_definition_ids": unavailable_definition_ids,
                "search_results": search_results,
                "search_pagination": search_pagination,
            }
        )

    return serialize_shopify_metafield_preferences_response({"shops": shops})


def _parse_search_offset(raw: str | None) -> int:
    if raw is None or not str(raw).strip():
        return 0
    try:
        offset = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("search_offset must be a non-negative integer.") from exc
    if offset < 0:
        raise ValidationError("search_offset must be a non-negative integer.")
    return offset


async def _resolve_integrations(
    ctx: ServiceContext,
    requested_ids: list[str],
) -> dict[str, ShopifyShopIntegration]:
    integrations = (
        (
            await ctx.session.execute(
                select(ShopifyShopIntegration).where(
                    ShopifyShopIntegration.workspace_id == ctx.workspace_id,
                    ShopifyShopIntegration.client_id.in_(requested_ids),
                    ShopifyShopIntegration.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    integrations_by_id = {
        integration.client_id: integration for integration in integrations
    }
    if any(
        integration_id not in integrations_by_id for integration_id in requested_ids
    ):
        raise NotFound("Shopify shop integration not found.")
    if any(
        integration.status != ShopifyIntegrationStatusEnum.ACTIVE
        for integration in integrations_by_id.values()
    ):
        raise ValidationError("Shopify shop integration is not active.")
    return integrations_by_id


async def _validate_item_categories(
    ctx: ServiceContext, requested_ids: list[str]
) -> None:
    rows = (
        (
            await ctx.session.execute(
                select(ItemCategory.client_id).where(
                    ItemCategory.workspace_id == ctx.workspace_id,
                    ItemCategory.client_id.in_(requested_ids),
                    ItemCategory.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    if any(category_id not in set(rows) for category_id in requested_ids):
        raise NotFound("Item category not found.")


def _is_product_metafield_definition(definition: dict | None) -> bool:
    return bool(
        isinstance(definition, dict)
        and definition.get("ownerType") == SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE
    )
