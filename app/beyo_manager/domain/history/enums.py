from enum import StrEnum


class HistoryRecordEntityTypeEnum(StrEnum):
    ITEM = "item"
    ITEM_UPHOLSTERY = "item_upholstery"
    ITEM_UPHOLSTERY_REQUIREMENT = "item_upholstery_requirement"
    TASK = "task"
    CASE = "case"
    USER = "user"


class HistoryRecordChangeTypeEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
