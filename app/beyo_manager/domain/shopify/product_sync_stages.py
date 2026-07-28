from beyo_manager.domain.shopify.enums import ShopifyProductSyncStageEnum


_STAGE_ORDER = {
    ShopifyProductSyncStageEnum.QUEUED: 0,
    ShopifyProductSyncStageEnum.PRODUCT_CREATED: 1,
    ShopifyProductSyncStageEnum.VARIANT_CONFIGURED: 2,
    ShopifyProductSyncStageEnum.INVENTORY_SET: 3,
}


def should_run_stage(
    current_stage: ShopifyProductSyncStageEnum,
    target_stage: ShopifyProductSyncStageEnum,
) -> bool:
    return _STAGE_ORDER[current_stage] < _STAGE_ORDER[target_stage]
