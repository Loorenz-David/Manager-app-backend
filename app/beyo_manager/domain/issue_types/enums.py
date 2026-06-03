import enum


class IssueSourceEnum(enum.Enum):
    MANUAL = "manual"
    INTERNAL_INSPECTION = "internal_inspection"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    IMPORTED = "imported"


class IssueModeEnum(enum.Enum):
    GRADED = "graded"
    SWITCH = "switch"
