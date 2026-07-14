from __future__ import annotations

from sqlalchemy import select

from beyo_manager.domain.shopify.enums import ShopifyIntegrationStatusEnum
from beyo_manager.domain.shopify.metafield_preferences import (
    merge_metafield_preference_with_definition,
)
from beyo_manager.domain.shopify.serializers import serialize_shopify_metafield_preference
from beyo_manager.domain.users.serializers import serialize_user_working_section_member
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.shopify.shopify_metafield_preference import ShopifyMetafieldPreference
from beyo_manager.models.tables.shopify.shopify_shop_integration import ShopifyShopIntegration
from beyo_manager.models.tables.users.user import User
from beyo_manager.services.commands.shopify.requests.create_shopify_metafield_preferences_request import (
    CreateShopifyMetafieldPreferencesRequest,
    parse_create_shopify_metafield_preferences_request,
)
from beyo_manager.services.commands.utils.client_id import validate_provided_client_id
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.shopify.metafield_definition_client import (
    SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE,
    fetch_shopify_metafield_definition_by_id,
)


async def create_shopify_metafield_preferences(
    ctx: ServiceContext,
) -> list[dict]:
    request = parse_create_shopify_metafield_preferences_request(ctx.incoming_data)

    for selection in request.preferences:
        if selection.client_id is not None:
            validate_provided_client_id(
                selection.client_id,
                ShopifyMetafieldPreference.CLIENT_ID_PREFIX,
            )

    async with maybe_begin(ctx.session):
        await _validate_item_category(ctx, request)
        integrations_by_id = await _resolve_integrations(ctx, request)

        definitions_by_selection: dict[tuple[str, str], dict] = {}
        for selection in request.preferences:
            integration = integrations_by_id[selection.shop_integration_id]
            access_token = (integration.access_token_encrypted or "").strip()
            if not access_token:
                raise ValidationError("Shopify shop integration has no usable access token.")
            definition = await fetch_shopify_metafield_definition_by_id(
                shop_domain=integration.shop_domain,
                access_token_encrypted=access_token,
                definition_id=selection.shopify_metafield_definition_id,
            )
            if not _is_product_metafield_definition(definition):
                raise NotFound("Shopify metafield definition not found.")
            definitions_by_selection[
                (selection.shop_integration_id, selection.shopify_metafield_definition_id)
            ] = definition

        creator = await ctx.session.scalar(select(User).where(User.client_id == ctx.user_id))
        created_by = serialize_user_working_section_member(creator) if creator is not None else None
        preferences_by_key: dict[tuple[str, str], ShopifyMetafieldPreference] = {}

        for selection in request.preferences:
            key = (selection.shop_integration_id, selection.shopify_metafield_definition_id)
            existing = (
                await ctx.session.execute(
                    select(ShopifyMetafieldPreference)
                    .where(
                        ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
                        ShopifyMetafieldPreference.shop_integration_id == selection.shop_integration_id,
                        ShopifyMetafieldPreference.item_category_id == request.item_category_id,
                        ShopifyMetafieldPreference.shopify_metafield_definition_id
                        == selection.shopify_metafield_definition_id,
                    )
                    .order_by(
                        ShopifyMetafieldPreference.is_deleted.asc(),
                        ShopifyMetafieldPreference.created_at.desc(),
                    )
                )
            ).scalars().first()

            if existing is None:
                preference_kwargs: dict[str, str] = {}
                if selection.client_id is not None:
                    client_id_owner = await ctx.session.get(
                        ShopifyMetafieldPreference,
                        selection.client_id,
                    )
                    if client_id_owner is not None:
                        raise ConflictError("Provided client_id is already in use.")
                    preference_kwargs["client_id"] = selection.client_id
                existing = ShopifyMetafieldPreference(
                    **preference_kwargs,
                    workspace_id=ctx.workspace_id,
                    item_category_id=request.item_category_id,
                    shop_integration_id=selection.shop_integration_id,
                    shopify_metafield_definition_id=selection.shopify_metafield_definition_id,
                    sequence_order=selection.sequence_order,
                    is_enabled=True,
                    created_by_id=ctx.user_id,
                )
                ctx.session.add(existing)
            else:
                changed = (
                    existing.is_deleted
                    or not existing.is_enabled
                    or existing.sequence_order != selection.sequence_order
                )
                if existing.is_deleted:
                    existing.is_deleted = False
                    existing.deleted_at = None
                    existing.deleted_by_id = None
                existing.is_enabled = True
                if changed:
                    existing.sequence_order = selection.sequence_order
                    existing.updated_by_id = ctx.user_id
            preferences_by_key[key] = existing

        await ctx.session.flush()
        return [
            serialize_shopify_metafield_preference(
                merge_metafield_preference_with_definition(
                    preference=preferences_by_key[(selection.shop_integration_id, selection.shopify_metafield_definition_id)],
                    definition=definitions_by_selection[
                        (selection.shop_integration_id, selection.shopify_metafield_definition_id)
                    ],
                    created_by=created_by,
                )
            )
            for selection in request.preferences
        ]


async def _validate_item_category(
    ctx: ServiceContext,
    request: CreateShopifyMetafieldPreferencesRequest,
) -> None:
    category = await ctx.session.scalar(
        select(ItemCategory).where(
            ItemCategory.workspace_id == ctx.workspace_id,
            ItemCategory.client_id == request.item_category_id,
            ItemCategory.is_deleted.is_(False),
        )
    )
    if category is None:
        raise NotFound("Item category not found.")


async def _resolve_integrations(
    ctx: ServiceContext,
    request: CreateShopifyMetafieldPreferencesRequest,
) -> dict[str, ShopifyShopIntegration]:
    requested_ids = list(dict.fromkeys(selection.shop_integration_id for selection in request.preferences))
    integrations = (
        await ctx.session.execute(
            select(ShopifyShopIntegration).where(
                ShopifyShopIntegration.workspace_id == ctx.workspace_id,
                ShopifyShopIntegration.client_id.in_(requested_ids),
                ShopifyShopIntegration.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    integrations_by_id = {integration.client_id: integration for integration in integrations}
    missing_ids = [integration_id for integration_id in requested_ids if integration_id not in integrations_by_id]
    if missing_ids:
        raise NotFound("Shopify shop integration not found.")
    inactive = [
        integration
        for integration in integrations_by_id.values()
        if integration.status != ShopifyIntegrationStatusEnum.ACTIVE
    ]
    if inactive:
        raise ValidationError("Shopify shop integration is not active.")
    return integrations_by_id


def _is_product_metafield_definition(definition: dict | None) -> bool:
    return bool(
        isinstance(definition, dict)
        and definition.get("ownerType") == SHOPIFY_PRODUCT_METAFIELD_OWNER_TYPE
    )
