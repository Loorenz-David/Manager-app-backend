import enum


class CustomerTypeEnum(enum.Enum):
    PERSON = "person"
    COMPANY = "company"
    UNKNOWN = "unknown"


class CustomerStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
