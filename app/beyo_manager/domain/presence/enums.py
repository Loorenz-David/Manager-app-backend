from enum import StrEnum


class EntityType(StrEnum):
    CASE_LIST = "case_list"
    CASE = "case"
    CONVERSATION_LIST = "conversation_list"
    CONVERSATION = "conversation"
    TASK = "task"
    TASK_STEP = "task_step"
    ITEM_UPHOLSTERY = "item_upholstery"
