import enum


class CustomerTypeEnum(enum.Enum):
    PERSON = "person"
    COMPANY = "company"
    UNKNOWN = "unknown"


class CustomerStatusEnum(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerHistoryChangeTypeEnum(enum.Enum):
    CREATED = "created"
    PROFILE_UPDATED = "profile_updated"
    CONTACT_UPDATED = "contact_updated"
    ADDRESS_UPDATED = "address_updated"
    STATUS_UPDATED = "status_updated"
    SOFT_DELETED = "soft_deleted"
    RESTORED = "restored"
    MERGED = "merged"
    REDACTED = "redacted"
    ANONYMIZED = "anonymized"
    CORRECTION = "correction"
    RETRACTION = "retraction"
