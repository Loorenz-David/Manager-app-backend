import enum


class UpholsteryCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA = "danish_krona"
    EURO = "euro"


class UpholsteryInventoryConditionEnum(enum.Enum):
    AVAILABLE = "available"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class UpholsteryOrderStateEnum(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"

