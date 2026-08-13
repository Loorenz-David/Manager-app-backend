import enum


class CostModelTermCalculationTypeEnum(enum.Enum):
    PERCENTAGE_OF_EXPECTED_SALE_PRICE = "percentage_of_expected_sale_price"
    FIXED_AMOUNT = "fixed_amount"
    ITEM_PURCHASE_COST = "item_purchase_cost"


class ItemCostEvaluationKindEnum(enum.Enum):
    PROJECTION = "projection"
    COMMITTED = "committed"


class EconomicsStatusEnum(enum.Enum):
    ITEM_MISSING_MAJOR_CATEGORY = "item_missing_major_category"
    NOT_CONFIGURED_NO_COST_GROUP = "not_configured_no_cost_group"
    NOT_CONFIGURED_AMBIGUOUS_COST_GROUP = "not_configured_ambiguous_cost_group"
    NOT_CONFIGURED_NO_BASIS_VERSION = "not_configured_no_basis_version"
    NOT_CONFIGURED_NO_COST_MODEL_VERSION = "not_configured_no_cost_model_version"
    ITEM_UNVALUED = "item_unvalued"
    ITEM_MISSING_EXPECTED_PRICE = "item_missing_expected_price"
    ITEM_MISSING_PURCHASE_COST = "item_missing_purchase_cost"
    CURRENCY_MISMATCH = "currency_mismatch"
    NOT_EVALUATED = "not_evaluated"
    INFEASIBLE = "infeasible"
    OK = "ok"
