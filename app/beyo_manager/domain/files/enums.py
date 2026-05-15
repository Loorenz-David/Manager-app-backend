from enum import StrEnum


class PendingUploadStatusEnum(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
