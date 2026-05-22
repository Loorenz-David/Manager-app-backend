import enum


class ItemStateEnum(enum.Enum):
    PENDING = "pending"
    STALLED = "stalled"
    FIXING = "fixing"
    READY = "ready"


class ItemCurrencyEnum(enum.Enum):
    SWEDISH_KRONA = "swedish_krona"
    DANISH_KRONA = "danish_krona"
    EURO = "euro"


class ItemMajorCategoryEnum(enum.Enum):
    WOOD = "wood"
    SEAT = "seat"


class ItemIssueStateEnum(enum.Enum):
    PENDING = "pending"
    FIXING = "fixing"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    SKIPPED = "skipped"
    RESOLVED = "resolved"


class ItemUpholsterySourceEnum(enum.Enum):
    INTERNAL = "internal"
    CUSTOMER = "customer"


class ItemUpholsteryRequirementSourceEnum(enum.Enum):
    INVENTORY = "inventory"
    SURPLUS = "surplus"


class ItemUpholsteryRequirementStateEnum(enum.Enum):
    MISSING_QUANTITY = "missing_quantity"
    AVAILABLE = "available"
    NEEDS_ORDERING = "needs_ordering"
    ORDERED = "ordered"
    IN_USE = "in_use"
    COMPLETED = "completed"
    FAILED = "failed"
