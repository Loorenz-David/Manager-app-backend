import enum


class UpholsteryCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA = "danish_krona"
    EURO = "euro"


class UpholsteryInventoryConditionEnum(enum.Enum):
    AVAILABLE = "available"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class ThresholdPolicyScopeEnum(enum.Enum):
    WORKSPACE_DEFAULT = "workspace_default"
    UPHOLSTERY = "upholstery"


class SourcingEscalationPolicyEnum(enum.Enum):
    NONE = "none"
    RECOMMEND_REORDER = "recommend_reorder"
    ESCALATE_TO_PROCUREMENT = "escalate_to_procurement"


class InventoryWarningTierEnum(enum.Enum):
    NORMAL = "normal"
    LOW_STOCK_WARNING = "low_stock_warning"
    URGENT_REORDER = "urgent_reorder"
