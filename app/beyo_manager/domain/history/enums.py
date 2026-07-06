from enum import StrEnum


class HistoryRecordEntityTypeEnum(StrEnum):
    ITEM = "item"
    ITEM_UPHOLSTERY = "item_upholstery"
    ITEM_UPHOLSTERY_REQUIREMENT = "item_upholstery_requirement"
    TASK = "task"
    TASK_POST_HANDLING = "task_post_handling"
    TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
    CASE = "case"
    USER = "user"


class HistoryRecordChangeTypeEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
