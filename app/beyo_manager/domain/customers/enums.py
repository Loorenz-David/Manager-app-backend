import enum


class CustomerTypeEnum(enum.Enum):
    PRIVATE = "private"
    COMPANY = "company"
    UNKNOWN = "unknown"


class CustomerStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
