from enum import StrEnum


class CaseLinkEntityTypeEnum(StrEnum):
    TASK = "task"
    CUSTOMER = "customer"


class CaseLinkRoleEnum(StrEnum):
    ORIGIN = "origin"
    SUBJECT = "subject"
    CONTEXT = "context"
    ACTOR = "actor"
    RESOLUTION = "resolution"


class CaseStateEnum(StrEnum):
    OPEN = "open"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
