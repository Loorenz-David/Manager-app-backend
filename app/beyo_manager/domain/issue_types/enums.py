import enum


class IssueSourceEnum(enum.Enum):
    INTERNAL_INSPECTION = "internal_inspection"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    IMPORTED = "imported"
