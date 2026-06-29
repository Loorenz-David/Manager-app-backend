from enum import StrEnum


class WorkspaceSpecializationEnum(StrEnum):
    WOOD_WORKER = "wood_worker"
    UPHOLSTERY_WORKER = "upholstery_worker"
    QUALITY_CONTROL = "quality_control"


# Backward-compatible alias for older imports.
WorkspaceRoleNameEnum = WorkspaceSpecializationEnum
